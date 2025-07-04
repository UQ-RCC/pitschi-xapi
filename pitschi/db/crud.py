import base64
from sqlalchemy.orm import aliased, Session
from sqlalchemy import inspect, and_, or_, func
from pydantic import parse_obj_as
from urllib.parse import quote
from . import models, schemas
from typing import List
from datetime import datetime,timedelta
import enum
import pytz
import pitschi.config as config
import pitschi.utils as utils
import logging
import pitschi.mail as mail
from sqlalchemy import func

logger = logging.getLogger('pitschixapi')

class PermissionException(Exception):
    pass

class NotfoundException(Exception):
    pass

class AlreadyExistException(Exception):
    pass

class CannotChangeException(Exception):
    pass

def row2dict(row, keep_id = False):
    d = {}
    for column in row.__table__.columns:
        if not keep_id and column.name == 'id':
            continue
        row_val = getattr(row, column.name)
        if isinstance(row_val, enum.Enum):
            row_val = row_val.value
        d[column.name] = row_val
    return d


################# system stats
def set_stat(db: Session, name: str, value: str, desc: str = '', isstring: bool = True):
    _stat = db.query(models.SystemStats).filter(models.SystemStats.name == name).first()
    if not _stat:
        _stat = models.SystemStats(name=name, value=value, isstring=isstring, description=desc)
        db.add(_stat)
    else:
        db.query(models.SystemStats).\
            filter(models.SystemStats.name == name).\
            update({"value": value, "description": desc, 'isstring': isstring})
    db.commit()
    db.flush()

def get_stat(db: Session, name:str):
    return db.query(models.SystemStats).filter(models.SystemStats.name == name).first()

################# user
def get_user(db: Session, username: str, password: str):
    return db.query(models.PUser).filter(models.PUser.username == username).filter(models.PUser.password == password).first()

def create_user(db: Session, username: str, password: str, desc: str):
    user = models.PUser(username=username, password=password, desc=desc)
    db.add(user)
    db.commit()
    db.flush()

def create_admin_if_not_exist(db: Session):
    _admin = db.query(models.PUser).filter(models.PUser.username == config.get("admin", "admin_username")).first()
    if not _admin:
        create_user(db, config.get("admin", "admin_username"), config.get("admin", "admin_password"), "Auto added")




################### datasets
def get_datasets_to_reset(db: Session, since_days: int = 30):
    since = datetime.now() - timedelta(days=since_days)
    return (
        db.query(models.Dataset, models.Booking).\
        join(models.Dataset.booking ).\
        filter(models.Dataset.mode.in_([models.Mode.imported, models.Mode.ingested]), 
            models.Dataset.status == models.Status.failed,
            models.Booking.bookingdate >= since).all()
    )


def get_datasets(db: Session, username: str):
    return db.query(models.Dataset).\
            join(models.Dataset.booking).\
            filter(func.lower(models.Booking.username) == username.lower()).all()

def get_datasets_from_original(db: Session, username: str, origmachine: str, origpath: str):
    _usr = username.lower()
    return db.query(models.Dataset).\
            filter(models.Dataset.originalmachine == origmachine).\
            filter(models.Dataset.originalpath == origpath).\
        join(models.Dataset.booking).\
            filter(or_(func.lower(models.Booking.username) == _usr, func.lower(models.Booking.assistant) == _usr)).all()

def get_datasets_from_one_machine(db: Session, username: str, origmachine: str, date: datetime.date):
    return db.query(models.Dataset).\
            filter(and_(func.date(models.Dataset.modified) >= date),\
                    (func.date(models.Dataset.modified) <= date )).\
            filter(models.Dataset.originalmachine == origmachine).\
        join(models.Dataset.booking).\
            filter(func.lower(models.Booking.username) == username.lower()).all()

def get_dataset(db: Session, datasetid: int):
    return db.query(models.Dataset).\
            filter(models.Dataset.id == datasetid).first()

def get_files_in_dataset(db: Session, datasetid: int):
    return db.query(models.File).\
            filter(models.File.dataset_id == datasetid).all()

def get_file(db: Session, fileid: int):
    return db.query(models.File).\
            filter(models.File.id == fileid).first()

def get_file_using_path(db: Session, datasetid: int, filepath: str):
    return db.query(models.File).\
            filter(models.File.dataset_id == datasetid).\
            filter(models.File.path == filepath).first()

def create_dataset(db: Session, dataset: schemas.DatasetCreate):
    files = dataset.files
    dataset.files = []
    # handle datetime, convert the datatime to utc
    if dataset.received:
        dataset.received = utils.convert_to_utc(dataset.received)
    if dataset.finished:
        dataset.finished = utils.convert_to_utc(dataset.finished)
    if dataset.modified:
        dataset.modified = utils.convert_to_utc(dataset.modified)
    
    datasetModel = models.Dataset(**dataset.dict())
    db.add(datasetModel)
    db.flush()
    db.refresh(datasetModel)
    for file in files:
        afile = models.File(**file.dict())
        afile.dataset_id = datasetModel.id
        if file.received:
            file.received = utils.convert_to_utc(file.received)
        if file.finished:
            file.finished = utils.convert_to_utc(file.finished)
        if file.modified:
            file.modified = utils.convert_to_utc(file.modified)
        db.add(afile)
        db.flush()
        dataset.files.append(afile)
    db.commit()
    # send email
    if dataset.mode == models.Mode.imported and dataset.status == models.Status.success:
        # send email
        logger.debug("Send email about the import")
        _dataset_info = summarize_dataset_info(db, datasetModel.id)
        if _dataset_info:
            send_import_email(db, _dataset_info)
    return datasetModel


def send_import_email(db, _dataset_info):
    """
    send an import email
    """
    _title = f"Successfully imported dataset to RDM"
    _to_address = _dataset_info.user.email
    # if this dataset is a result of a assistance
    if _dataset_info.booking and _dataset_info.booking.assistant:
        _to_address = get_ppms_user(db, _dataset_info.booking.assistant).email
    _cloud_rdm_url=f"https://cloud.rdm.uq.edu.au/index.php/apps/files/?dir=/{_dataset_info.project.collection}/{_dataset_info.relpathfromrootcollection}"
    _samba_url = 'smb:' + _dataset_info.networkpath.replace('\\', '/')
    _contents = f"""
                <html>
                    <head></head>
                    <body>
                        <p>Dear {_dataset_info.user.name},<br /></p>
                        <p>Pitschi has successfully imported dataset from {_dataset_info.system.name} into RDM {_dataset_info.project.collection} for project "{_dataset_info.project.name}".</p>

                        <p>You can view the dataset using the following systems (please allow time for synchronization):</p>
                            <ul>
                                <li><b>Cloud RDM</b> <a href="{_cloud_rdm_url}">here</a>.</li>
                                <li><b>Windows</b> Enter this text into File Explorer: <b>{_dataset_info.networkpath}</b>. Please use your UQ username (eg: uq\\uqxxxxxx) and password.</li>
                                <li><b>MacOS</b> Go to Finder and then on the menu Go-> Connect to Server.... Enter this text: <b>{_samba_url}</b>. Please use your UQ username (eg: uq\\uqxxxxxx) and password.</li>
                                <li><b>Linux</b> Enter this text into File Manager (Caja, Nautilus, etc): <b>{_samba_url}</b>. Please use your UQ username (eg: uq\\uqxxxxxx) and password.</li>
                                <li><b>CVL</b> Look for collection: <b>{_dataset_info.project.collection.strip().split("-")[-1]}</b> and then {_dataset_info.relpathfromrootcollection}</li>
                                <li><b>Image Processing Portal</b> <a href="https://ipp.rcc.uq.edu.au/?component=filesmanager&relpath={_dataset_info.project.collection.strip().split("-")[-1]}/{_dataset_info.relpathfromrootcollection}">here</a></li>
                            </ul>
                        </p>
                        You will receive another email once the dataset has been successfully ingested into Pitschi.
                        <br />
                        Regards,<br />
                        Pitschi Team
                    </body>
                </html>
                """
    mail.send_mail(_to_address, _title, _contents)

def create_file(db: Session, file: schemas.FileCreate):
    if file.received:
        file.received = utils.convert_to_utc(file.received)
    if file.finished:
        file.finished = utils.convert_to_utc(file.finished)
    if file.modified:
        file.modified = utils.convert_to_utc(file.modified)
    afile = models.File(**file.dict())
    afile.dataset_id = file.dataset_id
    db.add(afile)
    db.flush()
    db.commit()
    db.refresh(afile)

def update_dataset_space_datasetid(db: Session, datasetid: int, spaceid: str, clowderdatasetid: str):
    updateObj = {}
    if spaceid:
        updateObj["space"] = spaceid
    if clowderdatasetid:
        updateObj["datasetid"] = clowderdatasetid
    db.query(models.Dataset).\
        filter(models.Dataset.id == datasetid).\
        update(updateObj)
    db.commit()

def update_dataset_mode_status(db: Session, datasetid: int, mode: models.Mode, status: models.Status):
    update_obj = {"mode": mode, "status": status}
    if status != models.Status.ongoing:
        update_obj['finished'] = datetime.now(pytz.utc)
    db.query(models.Dataset).\
        filter(models.Dataset.id == datasetid).\
        update(update_obj)
    db.commit()

def update_file_mode_status(db: Session, fileid: int, mode: models.Mode, status: models.Status):
    update_obj = {"mode": mode, "status": status}
    if status != models.Status.ongoing:
        update_obj['finished'] = datetime.now(pytz.utc)
    db.query(models.File).\
        filter(models.File.id == fileid).\
        update(update_obj)
    db.commit()

def update_file(db: Session, fileid: int, updatedata: dict):
    _file_in_db = get_file(db, fileid)
    if _file_in_db:
        existing_f_dic = row2dict(_file_in_db, True)
        stored_f_model = schemas.File(**existing_f_dic)
        updated_f_item = stored_f_model.copy(update=updatedata)
        db.query(models.File).filter(models.File.id == fileid).update(updated_f_item.dict())
        db.flush()
        db.commit()
            

def update_dataset(db: Session, datasetid: int , dataset: schemas.DatasetCreate):
    files = dataset.files
    
    if dataset.received:
        dataset.received = utils.convert_to_utc(dataset.received)
    if dataset.finished:
        dataset.finished = utils.convert_to_utc(dataset.finished)
    if dataset.modified:
        dataset.modified = utils.convert_to_utc(dataset.modified)
    _dataset_db = get_dataset(db, datasetid)
    _ds_mode_db = _dataset_db.mode
    _ds_status_db = _dataset_db.status
    
    # ignore if _dataset not exists
    if _dataset_db:
        existing_ds_dic = row2dict(_dataset_db, True)
        stored_ds_model = schemas.Dataset(**existing_ds_dic)
        update_ds_data = dataset.dict(exclude_unset=True)
        updated_ds_item = stored_ds_model.copy(update=update_ds_data)
        del updated_ds_item.files
        del updated_ds_item.repo
        updated_ds_item_dict = updated_ds_item.dict()
        logger.debug(f"updated dataset: {updated_ds_item_dict}")
        db.query(models.Dataset).filter(models.Dataset.id == datasetid).update(updated_ds_item_dict)
        ## TODO: send an email here if the update is about imported successfully, saying the data is already in RDM, but not yet ingester
        db.flush()
        db.commit()
        for file in files:
            if file.received:
                file.received = utils.convert_to_utc(file.received)
            if file.finished:
                file.finished = utils.convert_to_utc(file.finished)
            if file.modified:
                file.modified = utils.convert_to_utc(file.modified)
            _file_in_db = get_file_using_path(db, datasetid, file.path)
            if _file_in_db:
                existing_f_dic = row2dict(_file_in_db, True)
                stored_f_model = schemas.File(**existing_f_dic)
                update_f_data = file.dict(exclude_unset=True)
                updated_f_item = stored_f_model.copy(update=update_f_data)
                db.query(models.File).filter(models.File.id == _file_in_db.id).update(updated_f_item.dict())
            else:
                afile = models.File(**file.dict())
                afile.dataset_id = datasetid
                db.add(afile)
                db.flush()
            db.commit()
        logger.debug(f"@update dataset: dataset mode={dataset.mode} dataset status= {dataset.status}")
        if _ds_mode_db == models.Mode.imported and  _ds_status_db == models.Status.ongoing and \
            dataset.mode == models.Mode.imported and dataset.status == models.Status.success:
            # send email
            logger.debug("Send email about the import")
            _dataset_info = summarize_dataset_info(db, datasetid)
            if _dataset_info:
                send_import_email(db, _dataset_info)

        
############# ppms
def get_core(db: Session, coreid: int):
    return db.query(models.Core).\
            filter(models.Core.id == coreid).first()

def create_core(db: Session, core: schemas.Core):
    """
    Create a PPMS core, or update if needed
    """
    _a_core = get_core(db, core.id)
    if _a_core:
        core_update = core.dict(exclude_unset=True)
        for col in [c.name for c in _a_core.__table__.columns]:
            if col in core_update:
                if getattr(_a_core, col) == core_update[col]:
                    core_update.pop(col)
        if core_update:
            logger.debug(f'updating core {core.id}: {core_update}')
            db.query(models.Core).filter(models.Core.id == core.id).update(core_update)
            db.flush()
            db.commit()
            db.refresh(_a_core)
    else:
        logger.debug(f'creating core {core.id}')
        _a_core = models.Core(**core.dict())
        db.add(_a_core)
        db.flush()
        db.commit()
        db.refresh(_a_core)
    return _a_core

def get_system(db: Session, systemid: int):
    return db.query(models.System).\
            filter(models.System.id == systemid).first()

def get_system_pid(db: Session, systemid: int):
    return db.query(models.System).\
            filter(models.System.id == systemid).first().pid

def get_system_ror(db: Session, systemid: int):
    return get_core(db, get_system(db, systemid).coreid).rorid

def get_system_byname(db: Session, systemname: str):
    return db.query(models.System).\
            filter(models.System.name == systemname).first()


def create_system(db: Session, system: schemas.System):
    """
    Create a PPMS system, or update if needed
    """
    _a_system = get_system(db, system.id)
    if _a_system:
        system_update = system.dict(exclude_unset=True)
        for col in [c.name for c in _a_system.__table__.columns]:
            if col in system_update:
                if getattr(_a_system, col) == system_update[col]:
                    system_update.pop(col)
        if system_update:
            logger.debug(f'updating system {system.id}: {system_update}')
            db.query(models.System).filter(models.System.id == system.id).update(system_update)
            db.flush()
            db.commit()
            db.refresh(_a_system)
    else:
        logger.debug(f'creating system {system.id}')
        _a_system = models.System(**system.dict())
        db.add(_a_system)
        db.flush()
        db.commit()
        db.refresh(_a_system)
    return _a_system

def get_ppms_user(db: Session, username: str):
    return db.query(models.User).\
            filter(func.lower(models.User.username) == username.lower()).first()

def get_ppms_user_by_uid(db: Session, uid: int):
    return db.query(models.User).\
            filter(models.User.userid == uid).all()

def get_ppms_user_by_email(db: Session, email: str):
    return db.query(models.User).\
            filter(models.User.email == email).first()

def create_ppms_user(db: Session, user: schemas.User):
    '''
    create user, or update if needed
    '''
    _a_user = get_ppms_user(db, user.username)
    if _a_user:
        user_update = user.dict(exclude_unset=True)
        for col in [c.name for c in _a_user.__table__.columns]:
            if col in user_update:
                if getattr(_a_user, col) == user_update[col]:
                    user_update.pop(col)
        if user_update:
            logger.debug(f'updating user {user.username}: {user_update}')
            db.query(models.User).filter(func.lower(models.User.username) == user.username.lower()).update(user_update, synchronize_session='fetch')
            db.flush()
            db.commit()
            db.refresh(_a_user)
    else:
        logger.debug(f'creating user {user.username}')
        _a_user = models.User(**user.dict())
        db.add(_a_user)
        db.flush()
        db.commit()
        db.refresh(_a_user)
    return _a_user
    
def update_ppms_user_id(db: Session, userlogin: str, uid: int):
    _ppms_user = get_ppms_user(db, userlogin)
    if _ppms_user:
        _ppms_user.userid = uid
        db.flush()
        db.commit()
        

def update_ppms_user_email(db: Session, userlogin: str, email: str):
    _ppms_user = get_ppms_user(db, userlogin)
    if _ppms_user:
        _ppms_user.email = email
        db.flush()
        db.commit()

def update_ppms_user_name(db: Session, userlogin: str, name: str):
    _ppms_user = get_ppms_user(db, userlogin)
    if _ppms_user:
        _ppms_user.name = name
        db.flush()
        db.commit()

def get_booking(db: Session, bookingid: int):
    return db.query(models.Booking).\
            filter(models.Booking.id == bookingid).first()

def get_bookings(db: Session, bookingdate: datetime.date):
    return db.query(models.Booking).\
            filter(models.Booking.bookingdate == bookingdate). \
            filter(models.Booking.cancelled == False).all()

def get_bookings_filter_system(db: Session, systemid: int, bookingdate: datetime.date):
    # there may be a better way
    bookings =  db.query(models.Booking).\
                filter(models.Booking.systemid == systemid). \
                filter(models.Booking.username != None). \
                filter(models.Booking.bookingdate == bookingdate). \
                filter(models.Booking.cancelled == False).all()
    for booking in bookings:
        if booking.projectid:
            booking.project = get_project(db, booking.projectid)
            if booking.project.collection:
                _c_caches = db.query(models.CollectionCache).\
                            filter(models.CollectionCache.collection_name == booking.project.collection).\
                            order_by(models.CollectionCache.priority.desc()).all()
                _caches = []
                for _c_cache in _c_caches:
                    _cache = db.query(models.Cache).filter(models.Cache.name == _c_cache.cache_name).one_or_none()
                    if _cache:
                        _cache.priority = _c_cache.priority
                        _caches.append(_cache)
                booking.project.caches = _caches
    return bookings


def get_bookings_filter_system_and_user(db: Session, systemid: int, bookingdate: datetime.date, username: str):
    _usr = username.lower()
    bookings =  db.query(models.Booking).\
                filter(models.Booking.systemid == systemid). \
                filter(or_(func.lower(models.Booking.username) == _usr, func.lower(models.Booking.assistant) == _usr)). \
                filter(models.Booking.bookingdate == bookingdate). \
                filter(models.Booking.cancelled == False).\
                join(models.UserProject).\
                filter(func.lower(models.UserProject.username) == func.lower(models.Booking.username)).\
                filter(models.UserProject.projectid == models.Booking.projectid).\
                filter(models.UserProject.enabled).all()
    for booking in bookings:
        if booking.projectid:
            booking.project = get_project(db, booking.projectid)
            if booking.project.collection:
                _c_caches = db.query(models.CollectionCache).\
                            filter(models.CollectionCache.collection_name == booking.project.collection).\
                            order_by(models.CollectionCache.priority.desc()).all()
                _caches = []
                for _c_cache in _c_caches:
                    _cache = db.query(models.Cache).filter(models.Cache.name == _c_cache.cache_name).one_or_none()
                    if _cache:
                        _cache.priority = _c_cache.priority
                        _caches.append(_cache)
                booking.project.caches = _caches
    return bookings


def cancel_booking(db: Session, bookingid: int):
    booking = get_booking(db, bookingid)
    if booking:
        booking.cancelled = True
        db.flush()
        db.commit()

def create_booking(db: Session, booking_session: schemas.Booking):
    '''
    create booking, or update if needed
    '''
    session = parse_obj_as(schemas.Booking, booking_session)
    if session.username and session.projectid:
        userproject = db.query(models.UserProject). \
                        filter(func.lower(models.UserProject.username) == session.username.lower()). \
                        filter(models.UserProject.projectid == session.projectid).first()
        if not userproject:
            # need to add a disabled project member for booking foreign key constraint with userproject
            userprojectobj = models.UserProject(username=session.username, projectid=session.projectid, enabled=False)
            db.add(userprojectobj)
            db.flush()
    booking = get_booking(db, session.id)
    if booking:
        # update -> important
        booking_update = session.dict(exclude_unset=True)
        for col in [c.name for c in booking.__table__.columns]:
            if col in booking_update:
                if getattr(booking, col) == booking_update[col]:
                    booking_update.pop(col)
        if booking_update:
            logger.debug(f'updating booking {session.id}: {booking_update}')
            db.query(models.Booking).filter(models.Booking.id == session.id).update(booking_update)
            db.flush()
            db.commit()
            db.refresh(booking)
    else:
        logger.debug(f'creating booking {session.id}')
        booking = models.Booking(**session.dict())
        db.add(booking)
        db.flush()
        db.commit()
        db.refresh(booking)
    return booking

def get_project(db: Session, projectid: int):
    return db.query(models.Project).\
            filter(models.Project.id == projectid).first()

def get_project_users(db: Session, projectid: int):
    return db.query(models.UserProject).\
            filter(models.UserProject.enabled).\
            filter(models.UserProject.projectid == projectid).all()

def update_project_users(db: Session, projectid: int, members: list):
    _dedup_members = list(set([m.lower() for m in members]))
    if len(_dedup_members) < len(members):
        _usrs = ','.join(members)
        logger.warning(f'ignore duplicate project {projectid} members: {_usrs}')
    _all_members = db.query(models.UserProject).\
            filter(models.UserProject.projectid == projectid).all()
    # add new members
    _new_members = [m for m in _dedup_members if m not in [u.username.lower() for u in _all_members]]
    if len(_new_members) > 0:
        _usrs = ','.join(_new_members)
        logger.debug(f'add new project {projectid} members: {_usrs}')
        for _new_member in _new_members:
            userprojectobj = models.UserProject(username=_new_member, projectid=projectid)
            db.add(userprojectobj)
        db.flush()
        db.commit()
    # enable members that are currently disabled
    _disabled_members = db.query(models.UserProject).\
            filter(~models.UserProject.enabled).\
            filter(models.UserProject.projectid == projectid).\
            filter(func.lower(models.UserProject.username).in_(_dedup_members))
    if _disabled_members.count() > 0:
        _usrs = ','.join([u.username for u in _disabled_members.all()])
        logger.debug(f'enable disabled project {projectid} members: {_usrs}')
        _disabled_members.update({ models.UserProject.enabled: True }, synchronize_session='fetch')
        db.flush()
        db.commit()
    # disable non-members that are currently enabled
    _non_members = db.query(models.UserProject).\
            filter(models.UserProject.enabled).\
            filter(models.UserProject.projectid == projectid).\
            filter(~func.lower(models.UserProject.username).in_(_dedup_members))
    if _non_members.count() > 0:
        _usrs = ','.join([u.username for u in _non_members.all()])
        logger.debug(f'disable enabled project {projectid} non-members: {_usrs}')
        _non_members.update({ models.UserProject.enabled: False }, synchronize_session='fetch')
        db.flush()
        db.commit()

def create_project(db: Session, project: schemas.Project):
    """
    Create a new project, or update if needed
    """
    _a_project = get_project(db, project.id)
    if _a_project:
        project_update = project.dict(exclude_unset=True)
        for col in [c.name for c in _a_project.__table__.columns]:
            if col in project_update:
                if getattr(_a_project, col) == project_update[col]:
                    project_update.pop(col)
        if project_update:
            logger.debug(f'updating project {project.id}: {project_update}')
            db.query(models.Project).filter(models.Project.id == project.id).update(project_update)
            db.flush()
            db.commit()
            db.refresh(_a_project)
    else:
        logger.debug(f'creating project {project.id}')
        _a_project = models.Project(**project.dict())
        db.add(_a_project)
        db.flush()
        db.commit()
        db.refresh(_a_project)
    return _a_project

def update_project_collection(db: Session, id: int, q_collection: str):
    project = get_project(db, id)
    if project and (project.collection != q_collection):
        logger.debug(f'updating project {project.id} collection: {project.collection} -> {q_collection}')
        project.collection = q_collection
        db.flush()
        db.commit()

def update_project_name(db: Session, id: int, name: str):
    project = get_project(db, id)
    if project:
        project.name = name
        db.flush()
        db.commit()

def get_imported_success_datasets(db: Session):
    return db.query(models.Dataset).\
            filter(models.Dataset.mode == models.Mode.imported).\
            filter(models.Dataset.status == models.Status.success ).\
            all()
                
def get_project_from_booking(db: Session, bookingid: int):
    booking = get_booking(db, bookingid)
    if booking:
        return get_project(db, booking.projectid)
    else:
        return None

def get_booking_datasets(db: Session, bookingid: int):
    return db.query(models.Dataset).\
            filter(models.Dataset.bookingid == bookingid).\
            all()


def summarize_dataset_info(db: Session, datasetid: int):
    dataset = get_dataset(db, datasetid)
    if dataset:
        booking = get_booking(db, dataset.bookingid)
        dataset.booking = booking
        if booking:
            dataset.user = get_ppms_user(db, booking.username)
            dataset.system = get_system(db, booking.systemid)
            dataset.project = get_project(db, booking.projectid)
    return dataset



######### collection and cache
def get_collection(db: Session, collection_name: str):
    return db.query(models.Collection).\
            filter(models.Collection.name == collection_name).first()

def create_collection(db: Session, acollection: schemas.CollectionBase):
    collection = db.query(models.Collection).\
            filter(models.Collection.name == acollection.name).one_or_none()
    if not collection:
        logger.info(f'create collection: {acollection.name}')
        collection = models.Collection(**acollection.dict())
        db.add(collection)
        db.flush()
        db.commit()
        db.refresh(collection)
    return collection

def get_collection_cache(db: Session, collection_name: str, cache_name: str):
    return db.query(models.CollectionCache).\
            filter(models.CollectionCache.collection_name == collection_name).\
            filter(models.CollectionCache.cache_name == cache_name).\
            first()

def get_collection_caches(db: Session, collection_name: str):
    return db.query(models.CollectionCache).\
            filter(models.CollectionCache.collection_name == collection_name).\
            all()


def create_collection_cache(db: Session, acollectioncache: schemas.CollectionCacheBase):
    collectioncache = get_collection_cache(db, acollectioncache.collection_name, acollectioncache.cache_name)
    if not collectioncache:
        collectioncache = models.CollectionCache(**acollectioncache.dict())
        db.add(collectioncache)
        db.flush()
        db.commit()
        db.refresh(collectioncache)
    return collectioncache


def get_caches(db: Session):
    return db.query(models.Cache).all()


def delete_collection_cache(db: Session, collectionid: str, cache_name: str):
    _collection_cache = db.query(models.CollectionCache).\
                filter(models.CollectionCache.collection_name == collectionid).\
                filter(models.CollectionCache.cache_name == cache_name).\
                first()
    if _collection_cache:
        db.delete(_collection_cache)
        db.commit()


#################### get projects info
# TODO: merge get_projects_full and get_projects
def get_projects_full(db: Session, userinfo: bool = True, collectioninfo: bool = True):
    """
    Get projects and all its information: collections, users
    """
    projects =  db.query(models.Project).\
                filter(models.Project.collection != None).\
                filter(models.Project.active == True).all()
    for _project in projects:
        if userinfo:
            _users = db.query(models.User).join(models.UserProject).filter(models.UserProject.enabled).filter(models.UserProject.projectid == _project.id).all()
            _project.participants = _users
        if collectioninfo:
            _caches = db.query(models.CollectionCache).filter(models.CollectionCache.collection_name == _project.collection).all()
            _project.caches = _caches
    return projects


def get_projects(db: Session):
    """
    Get projects information only
    """
    return db.query(models.Project).all()


def get_collections(db: Session):
    """
    Get all collections information
    """
    return db.query(models.Collection).all()

def get_collection(db: Session, collectionid: str):
    """
    Get single collection
    """
    return db.query(models.CollectionCache).\
        filter(models.CollectionCache.collection_name == collectionid).all()

def update_collection(db: Session, collectionid: str, collectioncacheinfo: schemas.CollectionCacheBase):
    """
    Get all collections information
    """
    _collection_cache_in_db = db.query(models.CollectionCache).\
                        filter(models.CollectionCache.collection_name == collectionid).\
                        filter(models.CollectionCache.cache_name == collectioncacheinfo.cache_name).first()
    if not _collection_cache_in_db:
        # create a new one
        collectioncache = models.CollectionCache(**collectioncacheinfo.dict())
        db.add(collectioncache)
        db.flush()
        db.commit()
        db.refresh(collectioncache)
    else:
        existing_cc_dic = row2dict(_collection_cache_in_db, True)
        stored_cc_model = schemas.CollectionCacheBase(**existing_cc_dic)
        update_cc_data = collectioncacheinfo.dict(exclude_unset=True)
        updated_cc_item = stored_cc_model.copy(update=update_cc_data)
        db.query(models.CollectionCache).\
                        filter(models.CollectionCache.collection_name == collectionid).\
                        filter(models.CollectionCache.cache_name == collectioncacheinfo.cache_name).\
                        update(updated_cc_item.dict())




### daily tasks
def get_daily_tasks(db: Session, systemid: int):
    """
    Get daily tasks from a system
    """
    return db.query(models.DailyTask).\
        filter(models.DailyTask.systemid == systemid).all()


def add_daily_task(db: Session, task: schemas.DailyTaskBase):
    """
    add daily task
    """
    dailytask = models.DailyTask(**task.dict())
    db.add(dailytask)
    db.flush()
    db.commit()
    db.refresh(dailytask)
    return dailytask


def complete_daily_task(db: Session, taskid: int, status: models.Status):
    """
    Comlete the task
    """
    db.query(models.DailyTask).\
        filter(models.DailyTask.id == taskid).\
        update({"status": status, "finished": datetime.now(pytz.timezone(config.get('ppms', 'timezone')))  })
