import logging

from fastapi import APIRouter, Depends, BackgroundTasks, status
import pytz
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session
import datetime
import pitschi.config as config
import pitschi.utils as utils
import pitschi.mail as mail
import pitschi.clowder_rest as clowderful
import os, json
from fastapi_utils.tasks import repeat_every

router = APIRouter()
logger = logging.getLogger('pitschixapi')
from fastapi_utils.session import FastAPISessionMaker
database_uri = (f"{config.get('database', 'type')}://"
                f"{config.get('database', 'username')}:"
                f"{config.get('database', 'password')}@"
                f"{config.get('database', 'host')}/"
                f"{config.get('database', 'name')}")
sessionmaker = FastAPISessionMaker(database_uri)
# from pitschi.db.database import SessionLocal

def check_all_files_in_dataset(db, dataset, project, logger):
    """
    Checks whether all the files in the given dataset are there
    All files paths will be turned to lower case as Windows does not differenate cases in path
    """
    logger.debug(f"@check-dataset: Start checking datataset {dataset.name} with {len(dataset.files)} files")
    file_items = { file.path.lower():file for file in dataset.files }
    qcollection = project.collection.strip().split("-")[-1]
    # do a walk over: /prefix/QCollection/dataset
    _relpathfromrootcollection = dataset.relpathfromrootcollection.replace("\\", "/")
    dataset_root = f"{config.get('rdm', 'prefix', default='/data')}/{qcollection}/{_relpathfromrootcollection}"
    ignore_folders = []
    for root, dirs, files in os.walk(dataset_root, topdown = True):
        # go to clowder and create those
        for dir in dirs:
            _current_dir_fullpath = os.path.join(root, dir)
            if dir.startswith('.'):
                ignore_folders.append(_current_dir_fullpath)
                continue
        ### files
        for file in files:
            _to_ignore = file.startswith('.')
            for folder in ignore_folders:
                if folder in root:
                    _to_ignore = True
            _file_fullpath = os.path.join(root, file)
            if not _to_ignore:
                # since rel path is windows
                if  dataset_root.endswith("/"):
                    _file_rel_path = _file_fullpath.replace(dataset_root, "").replace("/", "\\")
                else:
                    _file_rel_path = _file_fullpath.replace(f"{dataset_root}/", "").replace("/", "\\")    
                # ingest
                _file_rel_path = _file_rel_path.lower()
                try:
                    logger.debug(f"Removing fullpath: {_file_fullpath} rel path: {_file_rel_path}")
                    file_items.pop(_file_rel_path)
                except: 
                    pass
    logger.debug(f"Left over file items: {file_items}")
    return (len(file_items) == 0)
    
def ingest_dataset_to_clowder(db, dataset, project, logger):
    """
    Go over the files, pull it, check, 
    """
    logger.debug(f"@ingest-dataset: Start ingesting datataset {dataset.name} with {len(dataset.files)} files")
    _clowder_key = config.get('clowder', 'api_key')
    _clowder_api_url = config.get('clowder', 'api_url')
    _dataset_ingest_successful = True
    _error_message = []
    found = False
    if not dataset.space:
        logger.debug(f"finding space: {project.name}")
        res = clowderful.get_spaces(_clowder_key, _clowder_api_url, project.name, False)
        if res.ok:
            for _space in res.json():
                if _space.get('name') == project.name:
                    # update 
                    # only update datasetid
                    pdb.crud.update_dataset_space_datasetid(db, dataset.id, _space.get('id'), None)
                    dataset.space = _space.get('id')
                    logger.debug(f"@ingest-dataset: found space {dataset.space}")
        else:
            return (False, ["Fail to query Clowder space"])
    if dataset.space:
        if not dataset.datasetid:
            logger.debug(f"finding dataset: {dataset.name}")
            res = clowderful.list_dataset_in_space(_clowder_key, _clowder_api_url, dataset.space)
            if res.ok:
                _clwddatasets = res.json()
                for _clwddataset in _clwddatasets:
                    if _clwddataset.get('name') == dataset.name:
                        # only update datasetid
                        pdb.crud.update_dataset_space_datasetid(db, dataset.id, None, _clwddataset.get('id'))
                        dataset.datasetid = _clwddataset.get('id')
                        logger.debug(f"@ingest-dataset: found dataset {dataset.datasetid}")
                        found = True
                # not found, create new one
                if not found:
                    _ds_info = clowderful.create_dataset(_clowder_key, _clowder_api_url, dataset.space, dataset.name)
                    logger.debug(f"@ingest-dataset: dataset created: {_ds_info}")
                    pdb.crud.update_dataset_space_datasetid(db, dataset.id, None, _ds_info.get('id'))
                    dataset.datasetid = _ds_info.get('id')
                    found = True
                    #### add metadata
                    _dataset_booking = pdb.crud.get_booking(db, dataset.bookingid)
                    if not _dataset_booking:
                        logger.error(f"@dataset {dataset} does not have any booking.: {dataset.bookingid}")
                        return (False, ["Fail to find dataset booking"])
                    _ds_metadata = {
                        "system": dataset.origionalmachine,
                        "author": _dataset_booking.username,
                        "projectid": _dataset_booking.projectid,
                        "bookingid": _dataset_booking.id
                    }
                    clowderful.upload_dataset_metadata(_clowder_key, _clowder_api_url, _ds_info.get('id'), _ds_metadata)
                    ### add tags
                    _ds_tags = [ dataset.origionalmachine, _dataset_booking.username, str(_dataset_booking.projectid) ]
                    clowderful.add_dataset_tags(_clowder_key, _clowder_api_url, _ds_info.get('id'), _ds_tags)
            else:
                found = False
                logger.debug("@ingest-dataset: cannot find dataset, ERROR")
        else:
            found = True
    else:
        logger.debug("@ingest-dataset: dataset space is still None, ERROR")
        found = False

    ######## not found #########
    if not found:
        return (False, ["Cannot find Clouder space and dataset"])

    # all files items
    logger.debug("Space and dataset found. Now ingesting files")
    file_items = { file.path.lower():file for file in dataset.files }
    logger.debug(f"File items in db: {file_items}")
    qcollection = project.collection.strip().split("-")[-1]
    # do a walk over: /prefix/QCollection/dataset
    _relpathfromrootcollection = dataset.relpathfromrootcollection.replace("\\", "/")
    dataset_root = f"{config.get('rdm', 'prefix', default='/data')}/{qcollection}/{_relpathfromrootcollection}"
    folders = {}
    ignore_folders = []
    _ds_folders = clowderful.get_dataset_folders(_clowder_key, _clowder_api_url, dataset.datasetid)
    for root, dirs, files in os.walk(dataset_root, topdown = True):
        # go to clowder and create those
        for dir in dirs:
            _current_dir_fullpath = os.path.join(root, dir)
            if dir.startswith('.'):
                ignore_folders.append(_current_dir_fullpath)
                continue
            _current_dir_relativepath = _current_dir_fullpath.strip(dataset_root)
            _parent_folder_id = folders.get(root)
            # search for existing folders
            _exist = False
            for _ds_folder in _ds_folders:
                if _ds_folder.get('name') == _current_dir_relativepath:
                    logger.debug (f"\nFolder {_current_dir_relativepath} exists")
                    folders[_current_dir_fullpath] = _ds_folder.get('id')
                    _exist = True
                    break
            if not _exist:
                logger.debug (f"\nCreate folder {_current_dir_relativepath}")
                try:
                    _folder = clowderful.add_folder(_clowder_key, _clowder_api_url, dataset.datasetid, dir, parent_folder_id=_parent_folder_id)
                    folders[_current_dir_fullpath] = _folder['id']
                except Exception as e:
                    logger.error (f">>>Exception 2 creating folder {e}")
        ### files
        for file in files:
            _to_ignore = file.startswith('.')
            for folder in ignore_folders:
                if folder in root:
                    _to_ignore = True
            _file_fullpath = os.path.join(root, file)
            logger.debug(f"Looking into: {_file_fullpath}")
            if not _to_ignore:
                logger.debug(f"Start processing: {_file_fullpath}")
                _parent_folder_id = folders.get(root)
                # since rel path is windows
                if  dataset_root.endswith("/"):
                    _file_rel_path = _file_fullpath.replace(dataset_root, "").replace("/", "\\")
                else:
                    _file_rel_path = _file_fullpath.replace(f"{dataset_root}/", "").replace("/", "\\")    
                # ingest
                _file_rel_path = _file_rel_path.lower()
                _to_be_ingested = True
                _file_object = None
                if _file_rel_path in file_items:
                    _file_object = file_items.pop(_file_rel_path)
                    if (_file_object.mode == pdb.models.Mode.ingested and _file_object.status == pdb.models.Status.success ) or \
                       _file_object.mode == pdb.models.Mode.intransit or \
                       (_file_object.mode == pdb.models.Mode.imported and _file_object.status != pdb.models.Status.success ):
                        logger.debug(f"File {_file_fullpath} either already ingested or not ready to be ingested")
                        _to_be_ingested = False
                if _to_be_ingested:
                    try:
                        _fileinfo = clowderful.add_server_file(_clowder_key, _clowder_api_url, dataset.datasetid, _file_fullpath, check_duplicate=True, parent_folderid=_parent_folder_id)
                        logger.info(f"Done ingesting clowder file {_fileinfo}")
                        # update database
                        if _file_object:
                            # update ri
                            pdb.crud.update_file(db, _file_object.id, \
                                            {   'status': pdb.models.Status.success, \
                                                'mode': pdb.models.Mode.ingested, \
                                                'fileid':  _fileinfo.get('id'), \
                                                'finished': datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) \
                                            })
                        else:
                            logger.info(f"------>File {_file_fullpath} not in database, ingest it")
                            _newfile = pdb.crud.schemas.FileCreate(path=_file_rel_path, \
                                                                size_kb=os.stat(_file_fullpath).st_size/1024.0 ,\
                                                                status=pdb.models.Status.success, \
                                                                mode=pdb.models.Mode.ingested,\
                                                                dataset_id=dataset.id,\
                                                                fileid= _fileinfo.get('id'),\
                                                                finished=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) )
                            # new file
                            pdb.crud.create_file(db, _newfile)
                    except Exception as e:
                        logger.error(f"Problem {e}")
                        if _file_object:
                            pdb.crud.update_file_mode_status(db, _file_object.id, pdb.models.Mode.ingested, pdb.models.Status.failed)    
                        else:
                            logger.info(f"------>File {_file_fullpath} not in database, report fail")
                            _newfile = pdb.crud.schemas.FileCreate(path=_file_rel_path, \
                                                                size_kb=os.stat(_file_fullpath).st_size/1024.0 ,\
                                                                status=pdb.models.Status.failed, \
                                                                mode= pdb.models.Mode.ingested,\
                                                                dataset_id=dataset.id,\
                                                                fileid= _fileinfo.get('id'),\
                                                                finished=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) )
                            # new file
                            pdb.crud.create_file(db, _newfile)
                        _dataset_ingest_successful = False
                        _error_message.append( f"Exception when ingesting file: {e}" )
                        logger.debug (f">>>Exception at creating file {e}")
    # end for loop
    logger.debug(f"Done ingesting files, the files items left: {file_items}")
    if _dataset_ingest_successful:
        _dataset_ingest_successful = (len(file_items) == 0)
        if not _dataset_ingest_successful:
            _error_message.append( f"Not all files were ingested. Missing: {file_items}" )
    return (_dataset_ingest_successful, _error_message)



def send_email(db, datasetinfo, result, messages):
    if result:
        title = f"Successfully ingested dataset"
        to_address = datasetinfo.user.email
        # if assistant is present, then sent email to assisant
        if datasetinfo.booking and datasetinfo.booking.assistant:
            to_address = pdb.crud.get_ppms_user(db, datasetinfo.booking.assistant).email
        pitschi_url = f"{config.get('clowder', 'url')}/datasets/{datasetinfo.datasetid}?space={datasetinfo.space}"
        _relpathfromrootcollection = datasetinfo.relpathfromrootcollection.replace("\\", "/")
        cloud_rdm_url=f"https://cloud.rdm.uq.edu.au/index.php/apps/files/?dir=/{datasetinfo.project.collection}/{_relpathfromrootcollection}"
        samba_url = 'smb:' + datasetinfo.networkpath.replace('\\', '/')
        contents = f"""
        <html>
            <head></head>
            <body>
                <p>Dear {datasetinfo.user.name},<br /></p>
                <p>Pitschi has successfully ingested dataset from {datasetinfo.system.name}.</p>

                <p>You can view the dataset using the following systems (please allow time for synchronization):</p>
                    <ul>
                        <li><b>Pitschi</b> <a href="{pitschi_url}">here</a></li>
                        <li><b>Cloud RDM</b> <a href="{cloud_rdm_url}">here</a></li>
                        <li><b>Windows</b> Enter this location into File Explorer: <b>{datasetinfo.networkpath}</b>. Please use your UQ username (eg: uq\\uqxxxxxx) and password.</li>
                        <li><b>MacOS</b> Go to Finder and then on the menu Go-> Connect to Server.... Enter this text: <b>{samba_url}</b>. Please use your UQ username (eg: uq\\uqxxxxxx) and password.</li>
                        <li><b>Linux</b> Enter this location into File Manager (Caja, Nautilus, etc): <b>{samba_url}</b>. Please use your UQ username (eg: uq\\uqxxxxxx) and password.</li>
                        <li><b>CVL</b> Go to collection: <b>{datasetinfo.project.collection.strip().split("-")[-1]}</b> and then {_relpathfromrootcollection}</li>
                        <li><b>Image Processing Portal</b> <a href="https://ipp.rcc.uq.edu.au/?component=filesmanager&relpath={datasetinfo.project.collection.strip().split("-")[-1]}/{_relpathfromrootcollection}">here</a></li>
                    </ul>
                </p>
                Regards,<br />
                Pitschi Team
            </body>
        </html>
        """
    else:
        title = f"Problem ingesting dataset"
        to_address = config.get('email', 'address')
        contents = f"""
        <html>
            <head></head>
            <body>
                <p>Dear admins<br /></p>
                <p>The following dataset was failed to ingest:</p>
                <ul>
                    <li><b>Machine</b> {datasetinfo.origionalmachine}</li>
                    <li><b>Location</b> {datasetinfo.origionalpath}</li>
                    <li><b>Booking id:</b> {datasetinfo.booking.id}</li>
                    <li><b>system id:</b> {datasetinfo.booking.systemid}</li>
                    <li><b>username:</b> {datasetinfo.booking.username}</li>
                    <li><b>project id:</b> {datasetinfo.booking.projectid}</li>
                </ul>
                <p> Reasons: </p>
                <ul>
        """
        for message in messages:
            contents = f"""{contents}<li>{message}</li>"""
        contents = f"""{contents}
                        </ul>
                            </p>
                            Regards,
                        </body>
                    </html>
                    """

    mail.send_mail(to_address, title, contents)


# every half hour
@router.on_event("startup")
@repeat_every(seconds=60 * int(config.get('clowder', 'ingest_frequency')), wait_first=False, logger=logger)
def ingest() -> None:
    # first, check mount point
    if not utils.ok_for_ingest():
        logger.debug(">>> scheduled ingest: mount point is not ready")
        return
    # db = SessionLocal()
    with sessionmaker.context_session() as db:
        logger.debug(">>> Repeated ingest: querying successfully imported datasets")
        # first query datasets that are in imported mode success
        _imported_datasets = pdb.crud.get_imported_success_datasets(db)
        # for each dataset, first change it to imported - ongoing
        logger.debug(f"There are {len(_imported_datasets)} datasets successfully imported")
        for _dataset in _imported_datasets:
            logger.debug(f"Looking into dataset {_dataset.id}")
            _project = pdb.crud.get_project_from_booking(db, _dataset.bookingid)
            if _project:
                logger.debug(f"project {_project.name}")
                # then for each file,
                _dataset_ready = check_all_files_in_dataset(db, _dataset, _project, logger)
                # proceed if datasaet is ready or the booking time is over by 24 hours
                _dataset_booking =  pdb.crud.get_booking(db, _dataset.bookingid)
                # this is brisbane time
                _booking_start_time = datetime.datetime.fromisoformat(f"{_dataset_booking.bookingdate} {_dataset_booking.starttime}")
                _booking_end_time = _booking_start_time + datetime.timedelta(minutes = _dataset_booking.duration)
                # duration till booking finished
                _lapsed_time_since_finish = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) - utils.localize_time(_booking_end_time)
                # if ready, or time has passed wait_time_to_sync then start ingesting
                if _dataset_ready or _lapsed_time_since_finish.total_seconds()/3600 > int(config.get('clowder', 'wait_time_to_sync')) :
                    logger.debug(f"Processing dataset {_dataset.id}")
                    pdb.crud.update_dataset_mode_status(db, _dataset.id, pdb.models.Mode.ingested, pdb.models.Status.ongoing)
                    (result, messages) = ingest_dataset_to_clowder(db, _dataset, _project, logger)
                    logger.debug(f"Done ingsting, result: {result} \n messages: {messages}")
                    # send an email
                    _dataset_info = pdb.crud.summarize_dataset_info(db, _dataset.id)
                    if _dataset_info:
                        logger.debug(f"Datasetinto {_dataset_info}")
                        send_email(db, _dataset_info, result, messages)
                    if result:
                        # success
                        pdb.crud.update_dataset_mode_status(db, _dataset.id, pdb.models.Mode.ingested, pdb.models.Status.success)
                    else:
                        # fail
                        pdb.crud.update_dataset_mode_status(db, _dataset.id, pdb.models.Mode.ingested, pdb.models.Status.failed)
                else:
                    logger.info(f"project {_project.name} does not have all files in this cache")
            else:
                logger.error(f"schduled ingestg: Error: Cannot find project for booking {_dataset.bookingid}")
        # db.close()
