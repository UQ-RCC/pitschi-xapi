
from fastapi import APIRouter, Depends

import logging

from fastapi import APIRouter, Depends, HTTPException, status
import pitschi.db as pdb
from sqlalchemy.orm import Session

import dashboard.keycloak as keycloak


router = APIRouter()
logger = logging.getLogger('pitschidashboard')


@router.put("/collections/{collectionid}")
async def update_collection(collectionid: str, collectioncacheinfo: pdb.schemas.CollectionCacheBase, 
                            user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
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
    if collectioncacheinfo.collection_name != collectionid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection id and name are different"
        )
    logger.debug(">>>>>>>>>>>> Update collection")
    pdb.crud.update_collection(db, collectionid, collectioncacheinfo)
    


@router.get("/collections")
async def get_collections(user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
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
        return pdb.crud.get_collections(db)



@router.get("/collections/{collectionid}")
async def get_ppms_projects(collectionid: str, user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
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
        return pdb.crud.get_collection(db, collectionid)
