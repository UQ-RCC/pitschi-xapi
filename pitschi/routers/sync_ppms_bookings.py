import logging
import pitschi.config as config
import datetime, pytz
from fastapi import APIRouter, Depends, status
from fastapi_utils.tasks import repeat_every
import pitschi.db as pdb
from pitschi.ppms import get_system_pids, get_daily_bookings, get_daily_training, get_booking_details
from pitschi.routers import ppms_utils
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
        _bookings = get_daily_bookings(_today_tz)
        pids = {p['System ID']: p['PID'] for p in get_system_pids() if p.get('PID')}
        logger.debug(f'bookings: {len(_bookings)}')
        # training sessions can have multiple records -- use the record with
        # 'Training organised by' == 'User full Name' to set booking project/user
        _training_sessions_by_id = {ts['SessionID']: {k: v for k, v in ts.items() if k != 'SessionID'}
            for ts in get_daily_training(_today_tz) if ts['Training organised by'] == ts['User full Name']}
        _training_count = 0
        _booking_project_ids = {}
        for _booking in _bookings:
            _booking_id = _booking.get('Ref (session)')
            _booking_details_list = get_booking_details(_booking.get('coreid'), _booking_id)
            if len(_booking_details_list) == 0:
                logger.debug(f'get booking details error: booking id {_booking_id}')
                continue
            _booking_details = _booking_details_list[0]
            _booking['systemId'] = None
            _id = _booking_details.get('systemId')
            if _id:
                try:
                    _system = pdb.crud.create_system(db, pdb.schemas.System(
                        id = _id,
                        coreid = _booking.get('coreid'),
                        type = _booking_details.get('systemType'),
                        name = _booking_details.get('systemName'),
                        pid = pids.get(_id, ''))
                    )
                    _booking['systemId'] = _system.id
                except:
                    logger.warning(f'get booking system error: booking id {_booking_id}', exc_info=True)
            _booking['status'] = _booking_details.get('status')
            _training_session = _training_sessions_by_id.get(_booking_id)
            if _training_session:
                _training_count += 1
                logger.info(f'booking {_booking_id} is a training session')
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
                _project_id = _booking['projectId']
                if _project_id not in _booking_project_ids:
                    _booking_project_ids[_project_id] = []
                if _booking['userId'] not in _booking_project_ids[_project_id]:
                    _booking_project_ids[_project_id].append(_booking['userId'])
                if _booking.get('assistantId') and _booking['assistantId'] not in _booking_project_ids[_project_id]:
                    _booking_project_ids[_project_id].append(_booking['assistantId'])
            else:
                _booking['projectId'] = None
        logger.debug(f'get project and user details for {len(_bookings)} bookings ({_training_count} training)')
        # sync project and user info for the daily bookings
        ppms_utils.sync_projects(db, alogger=logger, project_ids=_booking_project_ids)
        # create/update daily db bookings now the related project and user data is up to date
        for _booking in _bookings:
            logger.debug(f'_booking: {_booking}')
            try:
                _booking_user = pdb.crud.get_ppms_user_by_uid(db, _booking.get('userId'))
                _booking_object = pdb.schemas.Booking(
                        id = _booking.get('Ref (session)'),
                        bookingdate = datetime.datetime.strptime(_booking.get('Date'), '%Y/%m/%d').date(),
                        starttime = datetime.time.fromisoformat(_booking.get('Start time')),
                        duration = _booking.get('Duration booked (minutes)'),
                        cancelled = _booking.get('Cancelled'),
                        systemid = _booking.get('systemId'),
                        status = _booking.get('status'),
                        projectid = _booking.get('projectId'),
                        username = _booking_user[0].username if len(_booking_user) else None
                    )
                if _booking.get('assistantId'):
                    _assistant = pdb.crud.get_ppms_user_by_uid(db, _booking['assistantId'])
                    _booking_object.assistant = _assistant[0].username if len(_assistant) else None
                    logger.debug(f'booking assistant: {_booking_object.assistant}')
                pdb.crud.create_booking(db, _booking_object)
            except Exception as e:
                logger.error(f'problem creating booking id {_booking.get("Ref (session)")}', exc_info=True)

        logger.debug(f'finished syncing {len(_bookings)} bookings')
