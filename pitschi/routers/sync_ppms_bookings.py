import logging
import pitschi.config as config
import datetime, pytz
from fastapi import APIRouter, Depends, status
from fastapi_utils.tasks import repeat_every
import pitschi.db as pdb
from pitschi.ppms import get_daily_bookings_one_system, get_daily_bookings, get_daily_training, get_systems, get_projects, get_rdm_collection, get_project_members, get_booking_details
from pitschi.routers.ppms_utils import get_db_user
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger('pitschixapi')

#from pitschi.db.database import SessionLocal
from fastapi_utils.session import FastAPISessionMaker
database_uri = (f"{config.get('database', 'type')}://"
                f"{config.get('database', 'username')}:"
                f"{config.get('database', 'password')}@"
                f"{config.get('database', 'host')}/"
                f"{config.get('database', 'name')}")
sessionmaker = FastAPISessionMaker(database_uri)


# every half hour
@router.on_event("startup")
@repeat_every(seconds=60 * int(config.get('ppms', 'booking_sync_minute')), wait_first=False, logger=logger)
def sync_ppms_bookings() -> None:
    # db = SessionLocal()
    logger.debug("<<<<<<<<<<<<<< Start syncing PPMS bookings")
    with sessionmaker.context_session() as db:
        logger.debug("query ppms bookings of today")
        _today_tz = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))).date()
        _bookings = get_daily_bookings(config.get('ppms', 'coreid'), _today_tz)
        logger.debug(f"bookings: {len(_bookings)}")
        _training_sessions = get_daily_training(config.get('ppms', 'coreid'), _today_tz)
        logger.debug(f"training: {len(_training_sessions)}")
        _rims_projects = None
        _rims_systems = None
        ### handle cancelled bookings
        ### also if this is the same as in database, then ignore the rest
        _bookings_in_db = pdb.crud.get_bookings(db, _today_tz)
        _booking_ids_in_db = {_booking_in_db.id for _booking_in_db in _bookings_in_db}
        _booking_ids_now = {int(_booking.get("Ref (session)")) for _booking in _bookings if not _booking.get("Cancelled")} 
        _cancelled_booking_ids = _booking_ids_in_db - _booking_ids_now
        _new_booking_ids = _booking_ids_now - _booking_ids_in_db
        logger.debug(f"Cancelled bookings: {_cancelled_booking_ids}")
        logger.debug(f"New bookings: {_new_booking_ids}")
        # now go and cancel those in database
        [ pdb.crud.cancel_booking(db, int(_cancelled_booking_id)) for _cancelled_booking_id in _cancelled_booking_ids]
        # in case there is no new booking
        # it is still worth going over one more time, in case of updates in the bookings themselve
        _booking_objects = {}
        _systems_with_bookings = set()
        _validated_db_users = {} # cache of validated user info
        for _booking in _bookings:
            # ignore old ones
            if not int(_booking.get("Ref (session)")) in _new_booking_ids:
                continue
            # continue as usual
            _a_booking_object = pdb.schemas.Booking(\
                                    id = int(_booking.get("Ref (session)")),\
                                    bookingdate = datetime.datetime.strptime(_booking.get("Date"), '%Y/%m/%d').date(),\
                                    starttime = datetime.time.fromisoformat(_booking.get("Start time")),\
                                    duration = int(_booking.get("Duration booked (minutes)")) ,\
                                    cancelled=bool(_booking.get("Cancelled")) )
            _system_name = _booking.get("System")
            _system = pdb.crud.get_system_byname(db, _system_name)
            if not _system:
                # if no system exists --> maybe weekly task does not update yet
                if not _rims_systems:
                    _rims_systems = get_systems()
                _sys = _rims_systems.get(_system_name)
                if _sys:
                    _system = pdb.crud.create_system(db, pdb.schemas.System(
                        id=_sys.get('systemid'), name=_sys.get('systemname'), type=_sys.get('systemtype')))
            if _system:
                logger.debug(f"systemid: {_system.id}")
                _a_booking_object.systemid = _system.id
                _systems_with_bookings.add(_system.id)
            _booking_objects[str(_booking.get("Ref (session)"))] = _a_booking_object
        for _sys_id in _systems_with_bookings:
            _system_bookings = get_daily_bookings_one_system(config.get('ppms', 'coreid'), _sys_id, _today_tz)
            logger.debug(f"daily booking of system: {len(_system_bookings)}" )
            for _system_booking in _system_bookings:
                _is_training_session = False
                _booking_details = None
                _system_booking_id = str(_system_booking.get('id'))
                logger.debug(f"system booking id: {_system_booking_id}" )
                if _system_booking_id in _booking_objects:
                    # if this booking does not belong to any project, ignore
                    # if projectId == 0 --> highly likely a training
                    _booking_objects[_system_booking_id].status = _system_booking.get('status')
                    _booking_objects[_system_booking_id].assistant = _system_booking.get('assistant')

                    # TODO: check if userId is there 
                    if _booking_objects[_system_booking_id].assistant:
                        _booking_objects[_system_booking_id].assistant = _booking_objects[_system_booking_id].assistant.strip()
                    if _system_booking.get('projectId') == '0' or not _system_booking.get('projectId'):
                        logger.info(f">>>booking {_system_booking} is a training")
                        if ( _system_booking.get('userName') == 'Training' or _system_booking.get('User') == 'Training') and _system_booking.get('assistant') != '':
                            logger.debug(f'Get project info for training booking id {_system_booking_id}')
                            _booking_details = get_booking_details(config.get('ppms', 'coreid'), _system_booking_id)
                            logger.info(f"training details {_booking_details}")
                            if len(_booking_details) > 0:
                                _assistance_id = int(_booking_details[0].get("assistantId"))
                                # now translate this id to user
                                if _validated_db_users.get(_assistance_id, 0) == 0:
                                    _validated_db_users[_assistance_id] = get_db_user(db, userid=_assistance_id)
                                else:
                                    logger.debug(f'Already checked booking user: {_assistance_id}')
                                _assistant_in_db = _validated_db_users[_assistance_id]
                                if _assistant_in_db:
                                    _booking_objects[_system_booking_id].assistant = _assistant_in_db.username
                            for _training_session in _training_sessions:
                                if _system_booking['id'] == _training_session['SessionID']:
                                    _system_booking['userId'] = _training_session['UserID']
                                    _system_booking['projectId'] = _training_session['ProjectID']
                                    _system_booking['projectName'] = _training_session['Project Name']
                                    _is_training_session = True
                                    break
                    if _system_booking.get('projectId'):
                        _booking_objects[_system_booking_id].projectid = int(_system_booking.get('projectId'))
                        ######### handle projectId ##############
                        _project_in_db = pdb.crud.get_project(db, _system_booking.get('projectId'))
                        logger.debug(f"project id: {_system_booking.get('projectId')}")
                        # if project does not exists
                        if not _project_in_db:
                            logger.debug(f"Not exists, create new project")
                            if not _rims_projects:
                                _rims_projects = get_projects()
                            for project in _rims_projects:
                                # logger.debug(f"project ref=:{project.get('ProjectRef')} projectid={_system_booking.get('projectId')}")
                                if project.get('ProjectRef') == _system_booking.get('projectId'):
                                    _projectSchema = pdb.schemas.Project(\
                                                    id = project.get('ProjectRef'),\
                                                    name = project.get('ProjectName'),\
                                                    active = bool(project.get('Active')),\
                                                    type = project.get('ProjectType'),\
                                                    phase = project.get('Phase'),\
                                                    description = project.get('Descr'))
                                    _project_in_db = pdb.crud.create_project(db, _projectSchema)
                        if not _project_in_db:
                            logger.debug(f"project id: {_system_booking.get('projectId')} still not in database. ignore this booking")
                            continue
                        # first collection
                        if not _project_in_db.collection:
                            _q_collection = get_rdm_collection(config.get('ppms', 'coreid'), _project_in_db.id)
                            # update it
                            if _q_collection and '-' in _q_collection:
                                # create collection and collectioncache
                                pdb.crud.create_collection(db, pdb.schemas.CollectionBase(name=_q_collection))
                                # create one its, one imb by default
                                pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name='its'))
                                pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name='imb', priority=1))
                                pdb.crud.update_project_collection(db, _project_in_db.id, _q_collection)
                        # now with project users
                        # _project_users = get_project_user(_project_in_db.id)
                        _project_members = get_project_members(_project_in_db.id)
                        logger.debug(f"project {_project_in_db.id} users: {_project_members}")
                        _validated_project_users = []
                        for _project_member in _project_members:
                            if _validated_db_users.get(_project_member.get('id'), 0) == 0:
                                _validated_db_users[_project_member.get('id')] = get_db_user(db, userid=_project_member.get('id'))
                            _user_info = _validated_db_users[_project_member.get('id')]
                            if not _user_info:
                                logger.debug(f'invalid user - id: {_project_member.get("id")}, login: {_project_member.get("login")}')
                                continue
                            # add project to user projects if not already added
                            _validated_project_users.append(_user_info.username)
                            if _user_info.userid == _system_booking.get('userId'):
                                _booking_objects[_system_booking_id].username = _user_info.username
                                logger.debug(f">>>>{_booking_objects[_system_booking_id]}")
                                logger.debug(f">>>>assistance: {_booking_objects[_system_booking_id].assistant}")
                                if not _is_training_session:
                                    if _booking_objects[_system_booking_id].assistant:
                                        logger.debug("This booking has assistant")
                                        logger.debug("Querying booking details@ppms_booking syncing")
                                        if not _booking_details:
                                            _booking_details = get_booking_details(config.get('ppms', 'coreid'), _system_booking_id)
                                        logger.debug(f"Booking details>>>: {_booking_details}")
                                        if len(_booking_details) > 0:
                                            _assistance_id = int(_booking_details[0].get("assistantId"))
                                            # now translate this id to user
                                            if _validated_db_users.get(_assistance_id, 0) == 0:
                                                _validated_db_users[_assistance_id] = get_db_user(db, userid=_assistance_id)
                                            _assistant_in_db = _validated_db_users[_assistance_id]
                                            if _assistant_in_db:
                                                logger.debug(f"Setting assistant: {_assistant_in_db.username}")
                                                _booking_objects[_system_booking_id].assistant = _assistant_in_db.username
                                            else:
                                                continue
                                        else:
                                            logger.error(f"Booking details of booking {_system_booking_id} returns nothing")
                                    else:
                                        logger.debug(f"This booking has no assistant, username: {_user_info.username}")
                        pdb.crud.update_project_users(db, _project_in_db.id, _validated_project_users)
                        # end for loop
                        # get user details
                        if _system_booking.get('userId'):
                            _user_id = int(_system_booking.get('userId'))
                            logger.debug(f"checking userId: {_user_id}")
                            if _validated_db_users.get(_user_id, 0) == 0:
                                _validated_db_users[_user_id] = get_db_user(db, userid=_user_id)
                            _user_in_db = _validated_db_users[_user_id]
                            if _user_in_db:
                                _booking_objects[_system_booking_id].username = _user_in_db.username
                            else:
                                logger.error(f">>>> Booking {_booking_objects[_system_booking_id]} userId specified {_system_booking.get('userId')}, but could not find it") 
                        else:
                            logger.error(f">>>> Booking {_booking_objects[_system_booking_id]} has no userId specified") 
                                        


        logger.debug(f"booking objects: {len(_booking_objects)}\n")
        # create bookings
        # [ pdb.crud.create_booking(db, _booking_object) for _booking_object in _booking_objects.values() ]
        for _booking_object in _booking_objects.values():
            try:
                pdb.crud.create_booking(db, _booking_object)
            except Exception as e:
                logger.error(f"Problem creating booking {_booking_object}. >>>Error: {e}")
        # db.close()
    
    
