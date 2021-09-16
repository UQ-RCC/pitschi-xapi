import logging
import pitschi.config as config
import datetime, pytz
from fastapi import APIRouter, Depends, status
from fastapi_utils.tasks import repeat_every
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_daily_bookings_one_system, get_daily_bookings, get_systems, get_projects, get_project_user, get_rdm_collection
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


@router.on_event("startup")
@repeat_every(seconds=15, wait_first=True, logger=logger, max_repetitions=1)
async def init_admin_user() -> None:
    with sessionmaker.context_session() as db:
        pdb.crud.create_admin_if_not_exist(db)


# every 2 days or so
# sync systems
# sync projects
@router.on_event("startup")
@repeat_every(seconds=60 * 60 * 24 * 2, wait_first=False, logger=logger)
async def sync_ppms_weekly() -> None:
    # first get systems
    # db = SessionLocal()
    with sessionmaker.context_session() as db:
        logger.debug("--> Sync PPMS weekly info: systems, projects, users")
        systems = get_systems()
        for system in systems:
            pdb.crud.create_system(db, pdb.schemas.System( \
                                                    id=systems.get(system).get('systemid'), \
                                                    name=systems.get(system).get('systemname'), \
                                                    type=systems.get(system).get('systemtype') \
                                                ))
        #now get projects
        projects = get_projects()
        for project in projects:
            # exists in db already
            if pdb.crud.get_project(db, project.get('ProjectRef')):
                continue
            # note that this informatio nis already available in the get projects query --> quick
            ### add project
            _projectSchema = pdb.schemas.Project(\
                                id = project.get('ProjectRef'),\
                                name = project.get('ProjectName'),\
                                active = bool(project.get('Active')),\
                                type = project.get('ProjectType'),\
                                phase = project.get('Phase'),\
                                description = project.get('Descr'))
            pdb.crud.create_project(db, _projectSchema)
        # db.close()


# every half hour
@router.on_event("startup")
@repeat_every(seconds=60 * int(config.get('ppms', 'booking_query_frequency')), wait_first=False, logger=logger)
async def sync_ppms_bookings() -> None:
    # db = SessionLocal()
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
                for system in systems:
                    if system == _system_name:
                        _system = pdb.crud.create_system(db, pdb.schemas.System( \
                                                        id=systems.get(system).get('systemid'), \
                                                        name=systems.get(system).get('systemname'), \
                                                        type=systems.get(system).get('systemtype') \
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
                    if int(_system_booking.get('projectId')) <=0:
                        continue
                    _booking_objects[_system_booking_id].status = _system_booking.get('status')
                    _booking_objects[_system_booking_id].projectid = _system_booking.get('projectId')
                    ######### handle projectId ##############
                    _project_in_db = pdb.crud.get_project(db, _system_booking.get('projectId'))
                    logger.debug(f"project id:{_system_booking.get('projectId')}")
                    logger.debug(f"project in db:{_project_in_db}")
                    # if project does not exists
                    if not _project_in_db:
                        logger.debug(f"Not eixsts, create new project")
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
                    # first collection
                    if not _project_in_db.collection:
                        _q_collection = get_rdm_collection(config.get('ppms', 'coreid'), _project_in_db.id)
                        # update it
                        if _q_collection:
                            pdb.crud.update_project_collection(db, _project_in_db.id, _q_collection)
                    # now with project users
                    _project_users = get_project_user(_project_in_db.id)
                    for _project_user in _project_users:
                        _db_user = pdb.crud.get_ppms_user(db, _project_user)
                        if not _db_user:
                            _user_info = get_ppms_user(_project_user)
                            _user_schema = pdb.schemas.User(\
                                            username = _user_info.get('login'),\
                                            name = f"{_user_info.get('lname')} {_user_info.get('fname')}",\
                                            email = _user_info.get('email') \
                                        )
                            _db_user = pdb.crud.create_ppms_user(db, _user_schema)
                            pdb.crud.create_user_project(  db, pdb.schemas.UserProjectBase(\
                                                            username = _user_info.get('login'),\
                                                            projectid = _project_in_db.id ) )
                        if _db_user.email == _system_booking.get('userEmail'):
                            _booking_objects[_system_booking_id].username = _db_user.username

        # create bookings
        [ pdb.crud.create_booking(db, _booking_object) for _booking_object in _booking_objects.values() ]
        # db.close()
    
    