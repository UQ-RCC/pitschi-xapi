import logging
import pitschi.config as config
import datetime, pytz
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_ppms_user_by_id, get_ppms_users, get_systems, get_projects, get_rdm_collection, get_project_members
from pitschi.notifications import send_teams_warning, send_teams_error
from sqlalchemy.orm import Session

logger = logging.getLogger('pitschixapi')


def de_dup_userid(db: Session, login: str, userid: int, users_info: dict):
    # user name was changed in rims, try to find and fix users with wrong id
    logger.debug(f'checking for duplicate userids: {userid}')
    for _fix_user in pdb.crud.get_ppms_user_by_uid(db, userid):
        # look for user with same id and different login
        if _fix_user.username != login:
            # check if their id needs to be updated
            _usr = {}
            if users_info:
                if users_info.get(_fix_user.username):
                    _usr = { 'login': _fix_user.username, **users_info[_fix_user.username] }
            else:
                try:
                    _usr_info = get_ppms_user(_fix_user.username)
                    if _usr_info:
                        _usr = _usr_info
                except:
                    pass
            if _usr and _fix_user.userid != _usr.get('id'):
                msg = f'fixing user {_fix_user.username} id - updating {_fix_user.userid} to {_usr.get("id")}'
                logger.warning('  ' + msg)
                pdb.crud.update_ppms_user_id(db, _fix_user.username, _usr.get('id'))
                if config.get('miscs', 'xapi_alerts_enabled', default='yes') == 'yes':
                    send_teams_warning('RIMS sync duplicate userid', msg[:1].upper() + msg[1:] + ', was username changed in RIMS?')
            else:
                msg = f'User {_fix_user.username} has duplicate id {userid}'
                logger.error(msg)
                if config.get('miscs', 'xapi_alerts_enabled', default='yes') == 'yes':
                    send_teams_error('RIMS sync duplicate userid', msg + ', was username deleted in RIMS?')


def get_db_user(db: Session, login: str = None, userid: int = None, users_info: dict = None):
    '''
    get user info by login or userid from db
    use users_info to add missing user to db, or update db user if needed
    query rims if users_info not provided
    '''
    _usr = {}
    if userid:
        _usrs = get_ppms_user_by_id(userid, config.get('ppms', 'coreid'))
        if _usrs:
            _usr = _usrs[0]
    else:
        if users_info:
            _usr = { 'login': login, **users_info.get(login) }
        else:
            _usr_info = get_ppms_user(login)
            if _usr_info:
                _usr = _usr_info
    _db_user = pdb.crud.get_ppms_user(db, _usr.get('login'))
    if not _usr:
        # don't have any user info from RIMS
        return _db_user
    if _db_user:
        # user exists in db - check if id, name, email need to be updated
        if not _db_user.userid:
            logger.debug(f'User {_db_user.username} rims id not set...')
            logger.debug(f'  updating {_db_user.name} to {_usr.get("id")}')
            pdb.crud.update_ppms_user_id(db, _db_user.username, _usr.get('id'))
        if _db_user.userid != _usr.get('id'):
            logger.debug(f'User {_db_user.username} rims id is wrong...')
            logger.debug(f'  updating {_db_user.userid} to {_usr.get("id")}')
            pdb.crud.update_ppms_user_id(db, _db_user.username, _usr.get('id'))
        de_dup_userid(db, _db_user.username, _usr.get('id'), users_info)
        if _db_user.name != _usr.get('name'):
            logger.debug(f'User {_db_user.username} rims name mismatch...')
            logger.debug(f'  updating {_db_user.name} to {_usr.get("name")}')
            pdb.crud.update_ppms_user_name(db, _db_user.username, _usr.get('name'))
        if _db_user.email != _usr.get('email'):
            logger.debug(f'User {_db_user.username} rims email mismatch...')
            logger.debug(f'  updating {_db_user.email} to {_usr.get("email")}')
            pdb.crud.update_ppms_user_email(db, _db_user.username, _usr.get('email'))
        # reload user from db so we have any updates
        _db_user = pdb.crud.get_ppms_user(db, _usr.get('login'))
    else:
        logger.debug(f'User {_usr.get("login")} does not exist, adding to database')
        _user_schema = pdb.schemas.User(username=_usr.get('login'), userid=_usr.get('id'), name=_usr.get('name'), email=_usr.get('email'))
        _db_user = pdb.crud.create_ppms_user(db, _user_schema)
    return _db_user


def sync_ppms_projects(db: Session, logger: logging.Logger):
    _syncing_stat = pdb.crud.get_stat(db, 'syncing_projects')
    if not _syncing_stat:
        logger.debug("--> syncing_projects not exist, create it")
        pdb.crud.set_stat(db, name='syncing_projects', value='True', desc='is system syncing projects', isstring=False)
    else:
        ### in the middle of a sync
        if eval(_syncing_stat.value):
            logger.debug("--> The system is in the middle of a syncing project")
            return
        else:
            pdb.crud.set_stat(db, name='syncing_projects', value='True')
    logger.debug("--> Sync PPMS weekly info: systems, projects, users")
    systems = get_systems()
    for system in systems:
        pdb.crud.create_system(db, pdb.schemas.System( \
                                                id=systems.get(system).get('systemid'), \
                                                name=systems.get(system).get('systemname'), \
                                                type=systems.get(system).get('systemtype') \
                                            ))
    users = get_ppms_users(config.get('ppms', 'coreid'))
    # convert to dict to allow easy lookup by login
    _users_info = { u["login"]: { "id": u["id"], "email": u["email"], "name": u["name"] } for u in users }
    _validated_db_users = [] # list of validated users
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
            _project_in_db = pdb.crud.create_project(db, _projectSchema)
        ###### get more information
        if not _project_in_db.collection:
            _q_collection = get_rdm_collection(config.get('ppms', 'coreid'), _project_in_db.id)
        else:
            _q_collection = _project_in_db.collection
        if _q_collection and '-' in _q_collection:
            # create collection and collectioncache
            pdb.crud.create_collection(db, pdb.schemas.CollectionBase(name=_q_collection))
            # create one its, one imb by default
            pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name='its'))
            pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name='imb', priority=1))
            if not _project_in_db.collection:        
                pdb.crud.update_project_collection(db, _project_in_db.id, _q_collection)

        # check for project name update
        _project_name = project.get('ProjectName')
        if _project_in_db.name != _project_name:
            logger.debug(f'Project id {_project_in_db.id} name mismatch...')
            logger.debug(f'  updating "{_project_in_db.name}" to "{_project_name}"')
            pdb.crud.update_project_name(db, _project_in_db.id, _project_name)
            _project_in_db = pdb.crud.get_project(db, _project_in_db.id)

        # now with project users
        _project_users = [n for n in [m['login'] for m in get_project_members(_project_in_db.id) if m.get('login')] if n.strip()]
        logger.debug(f'project {_project_in_db.id} users: {_project_users}')
        _validated_project_users = []
        for _project_user in _project_users:
            if _project_user not in _validated_db_users:
                logger.debug(f"Checking project user: {_project_user}")
                if not _project_user:
                    logger.debug(f"{_project_user} is empty. ignore")
                    continue
                _db_user = get_db_user(db, login=_project_user, users_info=_users_info)
                _validated_db_users.append(_project_user)
            else:
                logger.debug(f"Already checked project user: {_project_user}")
            _validated_project_users.append(_project_user)
        pdb.crud.update_project_users(db, _project_in_db.id, _validated_project_users)

    # done syncing
    logger.debug('--> Done syncing')
    logger.debug(f'Projects: {len(projects)}, Unique project users {len(_validated_db_users)}')
    pdb.crud.set_stat(db, name='syncing_projects', value='False')
    # db.close()


