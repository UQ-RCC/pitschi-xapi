import logging
import pitschi.config as config
import datetime, pytz
import pitschi.db as pdb
from pitschi.ppms import get_ppms_user, get_ppms_users, get_systems, get_projects, get_rdm_collection, get_project_members
from sqlalchemy.orm import Session


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
                logger.debug(f"User :{_project_user} not exists, query ppms")
                _user_schema = pdb.schemas.User(\
                                    username = _project_user,\
                                    userid = _users_info[_project_user].get("id"),\
                                    name = _users_info[_project_user].get("name"),\
                                    email = _users_info[_project_user].get('email') )
                logger.debug(f"User :{_project_user} not exists, create new one")
                _db_user = pdb.crud.create_ppms_user(db, _user_schema)
                logger.debug(f"User :{_project_user} added to database")
            if not _db_user.userid:
                # update it
                pdb.crud.update_ppms_user_id(db, _db_user.username, _project_member.get("id"))
            # check if email needs to be updated in db
            _ppms_email = _users_info[_project_user].get('email')
            if _db_user.email != _ppms_email:
                logger.debug(f'User {_db_user.username} ppms email mismatch...')
                logger.debug(f'  updating {_db_user.email} to {_ppms_email}')
                pdb.crud.update_ppms_user_email(db, _db_user.username, _ppms_email)
                _db_user = pdb.crud.get_ppms_user(db, _db_user.username)
            _ppms_name = _users_info[_project_user].get('name')
            if _db_user.name != _ppms_name:
                logger.debug(f'User {_db_user.username} ppms name mismatch...')
                logger.debug(f'  updating {_db_user.name} to {_ppms_name}')
                pdb.crud.update_ppms_user_name(db, _db_user.username, _ppms_name)
                _db_user = pdb.crud.get_ppms_user(db, _db_user.username)
            # add to userproject if not exists           
            pdb.crud.create_user_project(  db, pdb.schemas.UserProjectBase(\
                                                username = _db_user.username,\
                                                projectid = _project_in_db.id ) )
            
    # done syncing
    logger.debug("--> Done syncing")
    pdb.crud.set_stat(db, name='syncing_projects', value='False')
    # db.close()


