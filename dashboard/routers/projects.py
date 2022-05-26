
from fastapi import APIRouter, Depends

import logging

from fastapi import APIRouter, Depends, HTTPException, status
import pitschi.db as pdb
from sqlalchemy.orm import Session

from pitschi.routers import ppms_utils
import dashboard.keycloak as keycloak


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
        is_superadmin = realm_access and 'superadmin' in realm_access.get('roles')
        if not is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorised. Only superadmin can do this."
            )
    logger.debug(">>>>>>>>>>>> Manual syncing PPMS projects")
    ppms_utils.sync_ppms_projects(db, logger)


@router.get("/projects")
async def get_ppms_projects(user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorised"
        )
    else: 
        realm_access = user.get('realm_access')
        is_superadmin = realm_access and 'superadmin' in realm_access.get('roles')
        if not is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorised. Only superadmin can do this."
            )
        return pdb.crud.get_projects(db)
