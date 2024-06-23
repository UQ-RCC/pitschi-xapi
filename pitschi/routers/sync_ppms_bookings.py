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
@router.on_event('startup')
@repeat_every(seconds=60 * int(config.get('ppms', 'booking_sync_minute')), wait_first=False, logger=logger)
def sync_ppms_bookings() -> None:
    # db = SessionLocal()
    logger.debug('<<<<<<<<<<<<<< Start syncing PPMS bookings')
    with sessionmaker.context_session() as db:
        logger.debug('query ppms bookings of today')
        _today_tz = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))).date()
        _bookings = get_daily_bookings(config.get('ppms', 'coreid'), _today_tz)
        logger.debug(f'bookings: {len(_bookings)}')
        _training_sessions_by_id = {ts['SessionID']: {k: v for k, v in ts.items() if k != 'SessionID'}
            for ts in get_daily_training(config.get('ppms', 'coreid'), _today_tz)}
        logger.debug(f'training: {len(_training_sessions_by_id)}')
        _rims_projects = None
        _rims_systems = None
        _booking_count = 0
        _validated_db_users = {} # cache of validated user info
        for _booking in _bookings:
            _booking_object = pdb.schemas.Booking(
                id = _booking.get('Ref (session)'),
                bookingdate = datetime.datetime.strptime(_booking.get('Date'), '%Y/%m/%d').date(),
                starttime = datetime.time.fromisoformat(_booking.get('Start time')),
                duration = _booking.get('Duration booked (minutes)'),
                cancelled = _booking.get('Cancelled'))
            logger.debug(f'booking id: {_booking_object.id}')
            _booking_details_list = get_booking_details(config.get('ppms', 'coreid'), _booking_object.id)
            if len(_booking_details_list) == 0:
                logger.debug(f'get booking details error: booking id {_booking_object.id}')
                continue
            _booking_details = _booking_details_list[0]
            _booking_object.systemid = _booking_details.get('systemId')
            if _booking_object.systemid:
                logger.debug(f'system name: {_booking_details.get("systemName")}')
                _system = pdb.crud.create_system(db, pdb.schemas.System(
                    id = _booking_details.get('systemId'),
                    name = _booking_details.get('systemName'),
                    type = _booking_details.get('systemType')))
            _booking_object.status = _booking.get('status')
            _training_session = _training_sessions_by_id.get(_booking_object.id)
            if _training_session:
                logger.info(f'booking {_booking_object.id} is a training session')
                _booking['userId'] = _training_session.get('UserID')
                _booking['userName'] = _training_session.get('User full Name')
                _booking['projectId'] = _training_session.get('ProjectID')
                _booking['projectName'] = _training_session.get('Project Name')
            else:
                _booking['userId'] = _booking_details.get('userId')
                _booking['userName'] = _booking_details.get('userName')
                _booking['projectId'] = _booking_details.get('projectId')
                _booking['projectName'] = _booking_details.get('projectName')
            if _booking_details.get('assisted'):
                _booking['assistantId'] = _booking_details.get('assistantId')
                _booking['assistant'] = _booking_details.get('assistant')
            if _booking.get('projectId'):
                logger.debug(f'project id: {_booking["projectId"]}')
                _booking_object.projectid = int(_booking['projectId'])
                ######### handle projectId ##############
                _project_in_db = pdb.crud.get_project(db, _booking_object.projectid)
                # if project does not exists
                if not _project_in_db:
                    logger.debug(f'create new project id: {_booking["projectId"]}')
                    if not _rims_projects:
                        _rims_projects_by_id = {p['ProjectRef']: {k: v for k, v in p.items() if k != 'ProjectRef'} for p in get_projects()}
                        logger.debug(f'rims projects: {len(_rims_projects_by_id)}')
                    _rims_project = _rims_projects_by_id.get(_booking['projectId'])
                    if _rims_project:
                        _projectSchema = pdb.schemas.Project(
                            id = _rims_project.get('ProjectRef'),
                            name = _rims_project.get('ProjectName'),
                            active = bool(_rims_project.get('Active')),
                            type = _rims_project.get('ProjectType'),
                            phase = _rims_project.get('Phase'),
                            description = _rims_project.get('Descr'))
                        _project_in_db = pdb.crud.create_project(db, _projectSchema)
                if not _project_in_db:
                    logger.debug(f'get booking project error: booking id {_booking_object.id}')
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
                logger.debug(f'project {_project_in_db.id} users: {[m["login"] for m in _project_members]}')
                _validated_project_users = []
                for _project_member in _project_members:
                    if _validated_db_users.get(_project_member.get('id'), 0) == 0:
                        _validated_db_users[_project_member.get('id')] = get_db_user(db, userid=_project_member.get('id'))
                    _user_info = _validated_db_users[_project_member.get('id')]
                    if _user_info:
                        _validated_project_users.append(_user_info.username)
                    else:
                        logger.debug(f'invalid project member - id: {_project_member.get("id")}, login: {_project_member.get("login")}')
                # add project to user projects if not already added
                pdb.crud.update_project_users(db, _project_in_db.id, _validated_project_users)
                logger.debug(f'validated project {_project_in_db.id} users: {_validated_project_users}')
                _user_id = int(_booking['userId'])
                if _validated_db_users.get(_user_id, 0) == 0:
                    _validated_db_users[_user_id] = get_db_user(db, userid=_user_id)
                _user_info = _validated_db_users[_user_id]
                if _user_info:
                    logger.debug(f'setting booking user: {_user_info.username}')
                    _booking_object.username = _user_info.username
                else:
                    logger.debug(f'invalid booking user - id: {_user_id}')
                if _booking.get('assistantId'):
                    _user_id = int(_booking['assistantId'])
                    if _validated_db_users.get(_user_id, 0) == 0:
                        _validated_db_users[_user_id] = get_db_user(db, userid=_user_id)
                    _user_info = _validated_db_users[_user_id]
                    if _user_info:
                        logger.debug(f'setting assistant: {_user_info.username}')
                        _booking_object.assistant = _user_info.username
                    else:
                        logger.debug(f'invalid booking assistant - id: {_user_id}')
                else:
                    logger.debug(f'booking has no assistant')
            _booking_count += 1
            try:
                pdb.crud.create_booking(db, _booking_object)
            except Exception as e:
                logger.error(f'problem creating booking id {_booking_object.id}', exc_info=True)

        logger.debug(f'finished syncing {_booking_count} bookings')
