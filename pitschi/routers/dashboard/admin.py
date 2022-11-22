from fastapi import APIRouter, Depends

import logging

from fastapi import APIRouter, Depends, HTTPException, status
import pitschi.db as pdb
from sqlalchemy.orm import Session

from pitschi.routers import ppms_utils
import pitschi.keycloak as keycloak


router = APIRouter()
logger = logging.getLogger('pitschidashboard')

@router.get("/resetSync")
async def rest_ppms_sync_stats(user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
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
    logger.debug(">>>>>>>>>>>> Reset PPMS Sync status")
    pdb.crud.set_stat(db, name='syncing_projects', value='False')

