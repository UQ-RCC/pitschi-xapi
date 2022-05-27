import logging
import pitschi.config as config
import datetime, pytz
from fastapi import APIRouter, Depends, status
from fastapi_utils.tasks import repeat_every
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_daily_bookings_one_system, get_daily_bookings, get_systems, get_projects, get_ppms_user_by_id, get_rdm_collection, get_project_members, get_booking_details
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
    logger.debug("<<<<<<<<<<<<<< Start syncing PPMS projects")
    with sessionmaker.context_session() as db:
        logger.debug("query ppms bookings of today")
        _today_tz = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))).date()
        _bookings = get_daily_bookings(config.get('ppms', 'coreid'), _today_tz)
        logger.debug(f"bookings: {_bookings}")
        ### handle cancelled bookings
        ### also if this is the same as in database, then ignore the rest
        _today_tz = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))).date()
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
            _booking_objects[str(_booking.get("Ref (session)"))]  = _a_booking_object
            _system_name = _booking.get("System")
            _system = pdb.crud.get_system_byname(db, _system_name)
            if not _system:
                # if no system exists --> maybe weekly task does not update yet
                systems = get_systems()
                if _system_name in systems:
                    _system = pdb.crud.create_system(db, pdb.schemas.System( \
                                                    id=systems.get(_system_name).get('systemid'), \
                                                    name=systems.get(_system_name).get('systemname'), \
                                                    type=systems.get(_system_name).get('systemtype') \
                                                ))
            logger.debug(f"systemid:{_system.id}")
            _a_booking_object.systemid = _system.id
            _systems_with_bookings.add(_system.id)
        logger.debug(f"\nbooking objects: {_booking_objects}\n")
        for _sys_id in _systems_with_bookings:
            _today_tz = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))).date()
            _system_bookings = get_daily_bookings_one_system(config.get('ppms', 'coreid'), _sys_id, _today_tz)
            logger.debug(f"daily booking of system:{_system_bookings}" )
            for _system_booking in _system_bookings:
                _system_booking_id = str(_system_booking.get('id'))
                logger.debug(f"system booking id:{_system_booking_id}" )
                if _system_booking_id in _booking_objects:
                    # if this booking does not belong to any project, ignore
                    # if projectId == 0 --> highly likely a training
                    _booking_objects[_system_booking_id].status = _system_booking.get('status')
                    _booking_objects[_system_booking_id].assistant = _system_booking.get('assistant')
                    if _booking_objects[_system_booking_id].assistant:
                        _booking_objects[_system_booking_id].assistant = _booking_objects[_system_booking_id].assistant.strip()
                    if _system_booking.get('projectId') == '0' or _system_booking.get('projectId') == 0:
                        if _system_booking.get('userName') == 'Training' and _system_booking.get('assistant').strip() != '':
                            _a_booking_details = get_booking_details(config.get('ppms', 'coreid'), _system_booking_id)
                            if len(_a_booking_details) > 0:
                                _assistance_id = int(_a_booking_details[0].get("assistantId"))
                                # now translate this id to user
                                _assistant_in_db = pdb.crud.get_ppms_user_by_uid(db, _assistance_id)
                                if _assistant_in_db:
                                    _booking_objects[_system_booking_id].username = _assistant_in_db.username
                                else:
                                    ### look in ppms
                                    logger.debug(f">>>>>>>>>>>>>Need to find user with id: {_assistance_id}")                
                    else:
                        _booking_objects[_system_booking_id].projectid = int(_system_booking.get('projectId'))
                        ######### handle projectId ##############
                        _project_in_db = pdb.crud.get_project(db, _system_booking.get('projectId'))
                        logger.debug(f"project id:{_system_booking.get('projectId')}")
                        logger.debug(f"project in db:{_project_in_db}")
                        # if project does not exists
                        if not _project_in_db:
                            logger.debug(f"Not exists, create new project")
                            projects = get_projects()
                            for project in projects:
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
                            logger.debug(f"project id:{_system_booking.get('projectId')} still not in database. ignore this booking")
                            continue
                        # first collection
                        if not _project_in_db.collection:
                            _q_collection = get_rdm_collection(config.get('ppms', 'coreid'), _project_in_db.id)
                            # update it
                            if _q_collection:
                                # create collection and collectioncache
                                pdb.crud.create_collection(db, pdb.schemas.CollectionBase(name=_q_collection))
                                # create one its, one imb by default
                                pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name='its'))
                                pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name='qbi', priority=1))    
                                pdb.crud.update_project_collection(db, _project_in_db.id, _q_collection)
                        # now with project users
                        # _project_users = get_project_user(_project_in_db.id)
                        _project_members = get_project_members(_project_in_db.id)
                        logger.debug(f"project {_project_in_db.id} users:{_project_members}")
                        for _project_member in _project_members:
                            _project_user = _project_member.get("login").strip()
                            logger.debug(f"Checking project user:{_project_user}")
                            if not _project_user:
                                logger.debug(f"{_project_user} is empty. ignore")
                                continue
                            _db_user = pdb.crud.get_ppms_user(db, _project_user)
                            if not _db_user:
                                _user_info = get_ppms_user(_project_user)
                                _user_schema = pdb.schemas.User(\
                                                username = _user_info.get('login'),\
                                                userid = _project_member.get("id"),\
                                                name = f"{_user_info.get('lname')} {_user_info.get('fname')}",\
                                                email = _user_info.get('email') \
                                            )
                                logger.debug(f"User :{_user_info.get('login')} not exists, create new one")
                                _db_user = pdb.crud.create_ppms_user(db, _user_schema)
                                logger.debug(f"Create user project...")
                                pdb.crud.create_user_project(  db, pdb.schemas.UserProjectBase(\
                                                                username = _user_info.get('login'),\
                                                                projectid = _project_in_db.id ) )
                            if not _db_user.userid:
                                pdb.crud.update_ppms_user_id(db, _db_user.username, _project_member.get("id"))
                            if _db_user.email == _system_booking.get('userEmail'):
                                logger.debug(f">>>>{_booking_objects[_system_booking_id]}")
                                logger.debug(f">>>>assistance: {_booking_objects[_system_booking_id].assistant}")
                                if not _booking_objects[_system_booking_id].assistant:
                                    logger.debug(f"This booking has no assistant, username: {_db_user.username}")
                                    _booking_objects[_system_booking_id].username = _db_user.username
                                else:
                                    logger.debug("This booking has assistant")
                                    ### this session requires assistance
                                    # check if this user can operate the machine 
                                    # _system_rights = get_system_rights(_sys_id)
                                    # _user_system_right = _system_rights.get(_db_user.username)
                                    #TODO: if _user_system_right is A, create 2 booking objects, one for user, one for assistant person
                                    # if _user_system_right in ("A", "S"):
                                        # _booking_objects[_system_booking_id].username = _db_user.username
                                    _booking_objects[_system_booking_id].username = _db_user.username
                                    #### get the assistance login
                                    logger.debug("Querying booking details@ppms_booking syncing")
                                    _booking_details = get_booking_details(config.get('ppms', 'coreid'), _system_booking_id)
                                    logger.debug(f"Booking details>>>: {_booking_details}")
                                    if len(_booking_details) > 0:
                                        _a_booking_details = _booking_details[0]
                                        logger.debug(f"Booking: {_a_booking_details}")
                                        _assistance_id = int(_a_booking_details.get("assistantId"))
                                        logger.debug(f"assistant: {_assistance_id}")
                                        # now translate this id to user
                                        _assistant_in_db = pdb.crud.get_ppms_user_by_uid(db, _assistance_id)
                                        if _assistant_in_db:
                                            _booking_objects[_system_booking_id].assistant = _assistant_in_db.username
                                            logger.debug(f"Setting assistant: {_assistant_in_db.username}")
                                        else:
                                            ### look in ppms
                                            logger.debug(f">>>>>>>>>>>>>Need to find user with id: {_assistance_id}")
                                            _users = get_ppms_user_by_id(_assistance_id, config.get('ppms', 'coreid'))
                                            if len(_users) > 0:
                                                _user_info = _users[0]
                                                _user_schema = pdb.schemas.User(\
                                                    username = _user_info.get('login'),\
                                                    userid = _assistance_id,\
                                                    name = f"{_user_info.get('lname')} {_user_info.get('fname')}",\
                                                    email = _user_info.get('email') \
                                                )
                                                logger.debug(f"User :{_user_info.get('login')} not exists, create new one")
                                                _db_user = pdb.crud.create_ppms_user(db, _user_schema)
                                                _booking_objects[_system_booking_id].assistant = _user_info.get('login')
                                    else:
                                        logger.error(f"Booking details of booking {_system_booking_id} returns nothing. Username of this booking is null")

        # create bookings
        [ pdb.crud.create_booking(db, _booking_object) for _booking_object in _booking_objects.values() ]
        # db.close()
    
    
