import logging
import pitschi.config as config
import datetime, pytz
from fastapi import APIRouter, Depends, status
from fastapi_utils.tasks import repeat_every
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_systems, get_projects, get_rdm_collection, get_project_members
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
@repeat_every(seconds=60 * 60 * 24 * int(config.get('ppms', 'project_sync_day')), wait_first=False, logger=logger)
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
        projects = get_projects()
        #now get projects
        for project in projects:
            if int(project.get('ProjectRef')) < int(config.get('ppms', 'project_starting_ref', default=0)):
                continue
            # exists in db already
            _project_in_db = pdb.crud.get_project(db, project.get('ProjectRef'))
            if not _project_in_db:
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
            ###### get more information
            if not _project_in_db.collection:
                _q_collection = get_rdm_collection(config.get('ppms', 'coreid'), _project_in_db.id)
                if _q_collection:
                    pdb.crud.update_project_collection(db, _project_in_db.id, _q_collection)
            # now with project users
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
                                        email = _user_info.get('email') )
                    logger.debug(f"User :{_user_info.get('login')} not exists, create new one")
                    _db_user = pdb.crud.create_ppms_user(db, _user_schema)
                    logger.debug(f"Create user project...")
                    pdb.crud.create_user_project(  db, pdb.schemas.UserProjectBase(\
                                                    username = _user_info.get('login'),\
                                                    projectid = _project_in_db.id ) )
                if not _db_user.userid:
                    # update it
                    pdb.crud.update_ppms_user_id(db, _db_user.username, _project_member.get("id"))
        # db.close()


