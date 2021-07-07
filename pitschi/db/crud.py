import base64
from sqlalchemy.orm import Session
from sqlalchemy import inspect, and_, or_, func
from urllib.parse import quote
from . import models, schemas
from typing import List
import enum, datetime
import pytz
import pitschi.config as config
import pitschi.utils as utils
import logging
import pitschi.mail as mail
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
def get_datasets(db: Session, username: str):
    return db.query(models.Dataset).\
            join(models.Dataset.booking).\
            filter(models.Booking.username == username).all()

def get_datasets_from_original(db: Session, username: str, origmachine: str, origpath: str):
    return db.query(models.Dataset).\
            filter(models.Dataset.origionalmachine == origmachine).\
            filter(models.Dataset.origionalpath == origpath).\
        join(models.Dataset.booking).\
            filter(models.Booking.username == username).all()

def get_datasets_from_one_machine(db: Session, username: str, origmachine: str, date: datetime.date):
    return db.query(models.Dataset).\
            filter(and_(func.date(models.Dataset.modified) >= date),\
                    (func.date(models.Dataset.modified) <= date )).\
            filter(models.Dataset.origionalmachine == origmachine).\
        join(models.Dataset.booking).\
            filter(models.Booking.username == username).all()

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
    # handle datetime
    if dataset.received:
        dataset.received = utils.localize_time(dataset.received)
    if dataset.finished:
        dataset.finished = utils.localize_time(dataset.finished)
    if dataset.modified:
        dataset.modified = utils.localize_time(dataset.modified)
    datasetModel = models.Dataset(**dataset.dict())
    db.add(datasetModel)
    db.flush()
    db.refresh(datasetModel)
    for file in files:
        afile = models.File(**file.dict())
        afile.dataset_id = datasetModel.id
        if file.received:
            file.received = utils.localize_time(file.received)
        if file.finished:
            file.finished = utils.localize_time(file.finished)
        if file.modified:
            file.modified = utils.localize_time(file.modified)
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
            send_import_email(_dataset_info)
    return datasetModel


def send_import_email(_dataset_info):
    """
    send an import email
    """
    _title = f"Successully imported dataset to RDM"
    _to_address = _dataset_info.user.email
    _cloud_rdm_url=f"https://cloud.rdm.uq.edu.au/index.php/apps/files/?dir=/{_dataset_info.project.collection}/{_dataset_info.relpathfromrootcollection}"
    _samba_url=f"smb://shares01.rdm.uq.edu.au/{_dataset_info.project.collection}/{_dataset_info.relpathfromrootcollection}"
    _contents = f"""
                <html>
                    <head></head>
                    <body>
                        <p>Dear {_dataset_info.user.name},<br /></p>
                        <p>Pitschi has successfully imported dataset from {_dataset_info.system.name} into RDM.</p>

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
        file.received = utils.localize_time(file.received)
    if file.finished:
        file.finished = utils.localize_time(file.finished)
    if file.modified:
        file.modified = utils.localize_time(file.modified)
    afile = models.File(**file.dict())
    afile.dataset_id = file.dataset_id
    db.add(afile)
    db.flush()
    db.refresh(afile)
    db.commit()

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
        update_obj['finished'] = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone')))
    db.query(models.Dataset).\
        filter(models.Dataset.id == datasetid).\
        update({"mode": mode, "status": status})
    db.commit()

def update_file_mode_status(db: Session, fileid: int, mode: models.Mode, status: models.Status):
    update_obj = {"mode": mode, "status": status}
    if status != models.Status.ongoing:
        update_obj['finished'] = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone')))
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
        db.query(models.File).filter(models.File.id == fileid).update(updated_f_item)
        db.flush()
        db.commit()
            

def update_dataset(db: Session, datasetid: int , dataset: schemas.DatasetCreate):
    files = dataset.files
    if dataset.received:
        dataset.received = utils.localize_time(dataset.received)
    if dataset.finished:
        dataset.finished = utils.localize_time(dataset.finished)
    if dataset.modified:
        dataset.modified = utils.localize_time(dataset.modified)
    _dataset_db = get_dataset(db, datasetid)
    _ds_mode_db = _dataset_db.mode
    _ds_status_db = _dataset_db.status
    logger.debug(f"@update dataset: datasetdb mode={_ds_mode_db} databsetdb_status= {_ds_status_db}")
    # ignore if _dataset not exists
    if _dataset_db:
        existing_ds_dic = row2dict(_dataset_db, True)
        stored_ds_model = schemas.Dataset(**existing_ds_dic)
        update_ds_data = dataset.dict(exclude_unset=True)
        updated_ds_item = stored_ds_model.copy(update=update_ds_data)
        del updated_ds_item.files
        db.query(models.Dataset).filter(models.Dataset.id == datasetid).update(updated_ds_item)
        ## TODO: send an email here if the update is about imported successfully, saying the data is already in RDM, but not yet ingester
        db.flush()
        db.commit()
        for file in files:
            if file.received:
                file.received = utils.localize_time(file.received)
            if file.finished:
                file.finished = utils.localize_time(file.finished)
            if file.modified:
                file.modified = utils.localize_time(file.modified)
            _file_in_db = get_file_using_path(db, datasetid, file.path)
            if _file_in_db:
                existing_f_dic = row2dict(_file_in_db, True)
                stored_f_model = schemas.File(**existing_f_dic)
                update_f_data = file.dict(exclude_unset=True)
                updated_f_item = stored_f_model.copy(update=update_f_data)
                db.query(models.File).filter(models.File.id == _file_in_db.id).update(updated_f_item)
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
                send_import_email(_dataset_info)

        
############# ppms
def get_system(db: Session, systemid: int):
    return db.query(models.System).\
            filter(models.System.id == systemid).first()

def get_system_byname(db: Session, systemname: str):
    return db.query(models.System).\
            filter(models.System.name == systemname).first()


def create_system(db: Session, system: schemas.System):
    """
    Create a PPMS system. no need to update
    """
    _a_system = get_system(db, system.id)
    if not _a_system:
        _a_system = models.System(**system.dict())
        db.add(_a_system)
        db.flush()
        db.refresh(_a_system)
        db.commit()
    return _a_system

def get_ppms_user(db: Session, username: str):
    return db.query(models.User).\
            filter(models.User.username == username).first()

def get_ppms_user_by_email(db: Session, email: str):
    return db.query(models.User).\
            filter(models.User.email == email).first()

def create_ppms_user(db: Session, auser: schemas.User):
    user = get_ppms_user(db, auser.username)
    if not user:
        user = models.User(**auser.dict())
        db.add(user)
        db.flush()
        db.refresh(user)
        db.commit()
    return user
    

def get_booking(db: Session, bookingid: int):
    return db.query(models.Booking).\
            filter(models.Booking.id == bookingid).first()

def get_bookings(db: Session, bookingdate: datetime.date):
    return db.query(models.Booking).\
            filter(models.Booking.bookingdate == bookingdate). \
            filter(models.Booking.cancelled == False).all()

def get_bookings_filter_system(db: Session, systemid: int, bookingdate: datetime.date):
    # this is all because I cannot do a join properlly using sqlalchemy
    bookings =  db.query(models.Booking).\
                filter(models.Booking.systemid == systemid). \
                filter(models.Booking.bookingdate == bookingdate). \
                filter(models.Booking.projectid != None). \
                filter(models.Booking.cancelled == False).all()
    for booking in bookings:
        booking.project = get_project(db, booking.projectid)
    return bookings


def get_bookings_filter_system_and_user(db: Session, systemid: int, bookingdate: datetime.date, username: str):
    bookings =  db.query(models.Booking).\
                filter(models.Booking.systemid == systemid). \
                filter(models.Booking.username == username). \
                filter(models.Booking.projectid != None). \
                filter(models.Booking.bookingdate == bookingdate). \
                filter(models.Booking.cancelled == False).all()
    for booking in bookings:
        booking.project = get_project(db, booking.projectid)
    return bookings


def cancel_booking(db: Session, bookingid: int):
    booking = get_booking(db, bookingid)
    if booking:
        booking.cancelled = True
        db.flush()
        db.commit()

def create_booking(db: Session, session: schemas.Booking):
    booking = get_booking(db, session.id)
    if not booking:
        if session.username and session.projectid:
            userproject = db.query(models.UserProject). \
                            filter(models.UserProject.username == session.username). \
                            filter(models.UserProject.projectid == session.projectid).first()
            if not userproject:
                userprojectobj = models.UserProject(username=session.username, projectid=session.projectid)
                db.add(userprojectobj)
                db.flush()
        booking = models.Booking(**session.dict())
        db.add(booking)
        db.flush()
        db.refresh(booking)
        db.commit()
    else:
        # update -> important
        existing_booking_dic = row2dict(booking, True)
        stored_booking_model = schemas.Booking(**existing_booking_dic)
        update_booking_data = session.dict(exclude_unset=True)
        updated_booking_item = stored_booking_model.copy(update=update_booking_data)
        updated_booking_item_dict = updated_booking_item.dict()
        db.query(models.Booking).filter(models.Booking.id == session.id).update(updated_booking_item)
        db.flush()
        db.commit()
    return booking

def create_user_project(db: Session, userproject: schemas.UserProjectBase):
    _user_project = db.query(models.UserProject).\
                        filter(models.UserProject.username == userproject.username).\
                        filter(models.UserProject.projectid == userproject.projectid).\
                        first()
    if not _user_project:
        userproject = models.UserProject(username=userproject.username, projectid=userproject.projectid)
        db.add(userproject)
        db.flush()
        db.commit()

def get_project(db: Session, projectid: int):
    return db.query(models.Project).\
            filter(models.Project.id == projectid).first()


def create_project(db: Session, aproject: schemas.Project):
    """
    Create a new project.
    If exists, update
    If not, create new one
    """
    project = get_project(db, aproject.id)
    if not project:
        project = models.Project(**aproject.dict())
        db.add(project)
        db.flush()
        db.refresh(project)
        db.commit()
    return project

def update_project_collection(db: Session, id: int, q_collection: str):
    project = get_project(db, id)
    if project:
        project.collection = q_collection
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
