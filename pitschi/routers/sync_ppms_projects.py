import logging
import pitschi.config as config
import datetime, pytz
from fastapi import APIRouter, Depends, status
from fastapi_utils.tasks import repeat_every
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_systems, get_projects, get_rdm_collection, get_project_members
from sqlalchemy.orm import Session
from pitschi.routers import ppms_utils

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
@repeat_every(seconds=15, wait_first=False, logger=logger, max_repetitions=1)
def init_admin_user() -> None:
    with sessionmaker.context_session() as db:
        logger.debug(">>>>>>>>>>>> init >>>>>>>>>>>>>>>>>>>>>>>>>>")
        pdb.crud.create_admin_if_not_exist(db)
        pdb.crud.create_caches_if_not_exist(db)
        pdb.crud.set_stat(db, name='syncing_projects', value='False', desc='is system syncing projects', isstring=False)

# every 2 days or so
# sync systems
# sync projects
@router.on_event("startup")
@repeat_every(seconds=60 * 60 * 24 * int(config.get('ppms', 'project_sync_day')), wait_first=False, logger=logger)
def sync_ppms_weekly() -> None:
    logger.debug(">>>>>>>>>>>> Start syncing PPMS projects")
    # first get systems
    # db = SessionLocal()
    with sessionmaker.context_session() as db:
        ppms_utils.sync_ppms_projects(db, logger)



