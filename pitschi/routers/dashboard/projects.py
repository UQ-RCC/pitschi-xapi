
from fastapi import APIRouter, Depends

import logging

from fastapi import APIRouter, Depends, HTTPException, status
import pitschi.db as pdb
from sqlalchemy.orm import Session

from pitschi.routers import ppms_utils
import pitschi.keycloak as keycloak


router = APIRouter()
logger = logging.getLogger('pitschidashboard')


@router.post("/projects")
async def sync_ppms_projects(user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorised"
        )
    else: 
        realm_access = user.get('realm_access')
        has_dashboard_access = realm_access and 'dashboard' in realm_access.get('roles')
        if not has_dashboard_access:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorised. Only dashboard can do this."
            )
    logger.debug(">>>>>>>>>>>> Manual syncing PPMS projects")
    ppms_utils.sync_ppms_projects(db, logger)


@router.get("/projects")
async def get_ppms_projects(full: bool = False, user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorised"
        )
    else: 
        realm_access = user.get('realm_access')
        has_dashboard_access = realm_access and 'dashboard' in realm_access.get('roles')
        if full and has_dashboard_access:
            return pdb.crud.get_projects_full(db)
        else:
            return pdb.crud.get_projects(db)


@router.get("/projects/{projectid}")
async def get_ppms_projects(projectid: int, user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorised"
        )
    else: 
        realm_access = user.get('realm_access')
        has_dashboard_access = realm_access and 'dashboard' in realm_access.get('roles')
        if not has_dashboard_access:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorised. Only dashboard can do this."
            )
        else:
            _project = pdb.crud.get_project(db, projectid)
            _user_projects = pdb.crud.get_project_users(db, projectid)
            if _project:
                _users = []
                for _user_proj in _user_projects:
                    _anuser = pdb.crud.row2dict(pdb.crud.get_ppms_user(db, _user_proj.username))
                    if _anuser:
                        _users.append(_anuser)
                _project.userslist = _users
                logger.debug (str(_users))
            return _project