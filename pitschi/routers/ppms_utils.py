import json
import logging
import pitschi.config as config
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_ppms_user_by_id, get_ppms_users, get_cores, get_system_pids, get_systems, get_projects, get_rdm_collections, get_project_members
import pitschi.mail as mail
from sqlalchemy.orm import Session

logger = logging.getLogger('pitschixapi')


def de_dup_userid(db: Session, login: str, userid: int, users_info: dict, alert: bool = False):
    # user name was changed in rims, try to find and fix users with wrong id
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
                logger.warning(msg)
                pdb.crud.update_ppms_user_id(db, _fix_user.username, _usr.get('id'))
                if (alert):
                    contents = msg[:1].upper() + msg[1:] + ', was username changed in RIMS?'
                    mail.send_mail(config.get('email', 'address'), '[WARNING] RIMS sync duplicate userid', contents)
            else:
                msg = f'User {_fix_user.username} has duplicate id {userid}'
                logger.error(msg)
                if (alert):
                    contents = msg + ', was username deleted in RIMS?'
                    mail.send_mail(config.get('email', 'address'), '[ERROR] RIMS sync duplicate userid', contents)


def get_db_user(db: Session, login: str = None, userid: int = None, coreid: int = None, users_info: dict = None, alert: bool = False):
    '''
    get user info by login or userid from db
    use users_info to add missing user to db, or update db user if needed
    query rims if users_info not provided
    '''
    _usr = {}
    if userid:
        _usrs = get_ppms_user_by_id(userid, coreid)
        if _usrs:
            _usr = _usrs[0]
    else:
        if users_info:
            _usr = { 'login': login, **users_info.get(login) }
        else:
            _usr_info = get_ppms_user(login)
            if _usr_info:
                _usr = _usr_info
    if not _usr:
        # don't have any user info from RIMS
        return None
    _user_schema = pdb.schemas.User(username=_usr.get('login'), userid=_usr.get('id'), name=_usr.get('name'), email=_usr.get('email'))
    _db_user = pdb.crud.create_ppms_user(db, _user_schema)
    de_dup_userid(db, _db_user.username, _usr.get('id'), users_info, alert=alert)
    return _db_user


def notify_failed_datasets(db: Session, alert: bool = False):
    days = int(config.get('ppms', 'project_sync_day'))
    results = pdb.crud.get_datasets_to_reset(db, since_days=days)
    all_fails = [{'name': rs.Dataset.name, 'booking': rs.Dataset.bookingid, 'machine': rs.Dataset.originalmachine, 'mode': rs.Dataset.mode} for rs in results]
    if len(all_fails) > 0:
        import_fails = [ds for ds in all_fails if ds['mode'] == pdb.models.Mode.imported]
        ingest_fails = [ds for ds in all_fails if ds['mode'] == pdb.models.Mode.ingested]
        msg = f'{len(all_fails)} datasets failed in past {days} day/s: {len(import_fails)} imports, {len(ingest_fails)} ingests'
        logger.warning(msg)
        if (alert):
            contents = '<p>' + msg + '</p>'
            contents += '<p>imports failed</p>'
            contents += '<ul>'
            for ds in import_fails:
                contents += f'<li>{ds["name"]}: booking {ds["booking"]}, on {ds["machine"]}</li>'
            contents += '</ul>'
            contents += '<p>ingests failed</p>'
            contents += '<ul>'
            for ds in ingest_fails:
                contents += f'<li>{ds["name"]}: booking {ds["booking"]}, on {ds["machine"]}</li>'
            contents += '</ul>'
            mail.send_mail(config.get('email', 'address'), '[WARNING] Dataset import/ingest fails', contents)
    else:
        logger.info(f'No datasets failed in past {days} day/s')

def sync_cores(db: Session):
    cores = get_cores()
    for core in cores:
        pdb.crud.create_core(db, pdb.schemas.Core(
            id = core.get('Core ID'),
            institution = core.get('Institution'),
            shortname = core.get('Facility Short Name'),
            longname = core.get('Facility Long Name'),
            rorid = core.get('ROR ID'))
        )


def sync_projects(db: Session, project_ids: dict = {}, alogger: logging.Logger = logger, alert: bool = False):
    '''
    sync projects from rims
    - sync all projects from rims if projects_ids is empty list
    - otherwise just sync the projects in projects_ids
    '''
    users = get_ppms_users()
    _rdms_by_pid = { r['projectid']: r['rdm'] for r in get_rdm_collections() }
    # convert to dict to allow easy lookup by login
    _users_info = { u["login"]: { "id": u["id"], "email": u["email"], "name": u["name"] } for u in users }
    _users_info_by_id = { u["id"]: { "login": u["login"], "email": u["email"], "name": u["name"] } for u in users }
    _projects_by_id = {p['ProjectRef']: {k: v for k, v in p.items() if k != 'ProjectRef'} for p in get_projects()}
    if len(project_ids) > 0:
        # partial project sync
        _project_ids = list(project_ids.keys())
    else:
        # full project sync
        _project_ids = list(_projects_by_id.keys())
    #now get projects
    _validated_db_users = [] # list of validated users
    for _project_id in _project_ids:
        if _project_id < int(config.get('ppms', 'project_starting_ref', default=0)):
            continue
        project = _projects_by_id.get(_project_id)
        if project is None:
            alogger.error(f'project id {_project_id} not found - is it inactive?')
            continue
        # note that this information is already available in the get projects query --> quick
        ### add project
        _projectSchema = pdb.schemas.Project(
                id = _project_id,
                coreid = project.get('CoreFacilityRef'),
                name = project.get('ProjectName'),
                active = bool(project.get('Active')),
                type = project.get('ProjectType'),
                phase = project.get('Phase'),
                description = project.get('Descr')
            )
        _project_in_db = pdb.crud.create_project(db, _projectSchema)
        ###### get more information
        _q_collection = _rdms_by_pid.get(_project_id)
        if (_q_collection and '-' in _q_collection) or _q_collection == '':
            if _q_collection == '':
                _q_collection = None
            if _q_collection and not pdb.crud.get_collection(db, _q_collection):
                # create collection and default collection caches
                pdb.crud.create_collection(db, pdb.schemas.CollectionBase(name=_q_collection))
                for cn, cp in json.loads(config.get('rdm', 'cache_defaults')).items():
                    pdb.crud.create_collection_cache(db, pdb.schemas.CollectionCacheBase(collection_name=_q_collection, cache_name=cn, priority=cp))
            if _project_in_db.collection != _q_collection:
                pdb.crud.update_project_collection(db, _project_in_db.id, _q_collection)

        # now with project users
        _project_users = [n for n in [m['login'] for m in get_project_members(_project_id) if m.get('login')] if n.strip()]
        # and extra users listed with project id, ie. booking users/assistants
        for usrid in project_ids.get(_project_id, []):
            usrname = _users_info_by_id[usrid]['login']
            if usrname not in _project_users:
                _project_users.append(usrname)
        alogger.debug(f'project {_project_id} users: {_project_users}')
        _validated_project_users = []
        for _project_user in _project_users:
            if _project_user not in _validated_db_users:
                alogger.debug(f"checking project user: {_project_user}")
                if not _project_user:
                    alogger.debug(f"{_project_user} is empty. ignore")
                    continue
                _db_user = get_db_user(db, login=_project_user, coreid=_project_in_db.coreid, users_info=_users_info, alert=alert)
                _validated_db_users.append(_project_user)
            else:
                alogger.debug(f"already checked project user: {_project_user}")
            _validated_project_users.append(_project_user)
        pdb.crud.update_project_users(db, _project_id, _validated_project_users)

    alogger.debug(f'projects: {len(_project_ids)}, unique project users {len(_validated_db_users)}')

    # done syncing
    alogger.debug('--> done syncing')
    # db.close()

def sync_ppms_projects(db: Session, alogger: logging.Logger = logger):
    _syncing_stat = pdb.crud.get_stat(db, 'syncing_projects')
    if not _syncing_stat:
        alogger.debug("--> syncing_projects not exist, create it")
        pdb.crud.set_stat(db, name='syncing_projects', value='True', desc='is system syncing projects', isstring=False)
    else:
        ### in the middle of a sync
        if eval(_syncing_stat.value):
            alogger.debug("--> the system is in the middle of a project sync")
            return
        else:
            pdb.crud.set_stat(db, name='syncing_projects', value='True')
    alogger.debug("--> sync PPMS info: checking for import/ingest fails")
    notify_failed_datasets(db, alert=True)
    alogger.debug("--> sync PPMS info: cores, systems, projects, users")
    sync_cores(db)
    pids = {p['System ID']: p['PID'] for p in get_system_pids() if p.get('PID')}
    systems = get_systems()
    for system in systems:
        _id = system.get('systemid')
        pdb.crud.create_system(db, pdb.schemas.System(
            id = _id,
            coreid = system.get('coreid'),
            type = system.get('systemtype'),
            name = system.get('systemname'),
            pid = pids.get(_id, ''))
        )
    sync_projects(db, alogger=alogger, alert=True)
    pdb.crud.set_stat(db, name='syncing_projects', value='False')
