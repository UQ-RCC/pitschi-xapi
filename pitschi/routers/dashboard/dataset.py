from fastapi import APIRouter, Depends

import logging

from fastapi import APIRouter, Depends, HTTPException, status
import pitschi.db as pdb
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from pitschi.routers import ppms_utils
import pitschi.keycloak as keycloak


router = APIRouter()
logger = logging.getLogger('pitschidashboard')

@router.get("/datasets/failed")
async def get_failed_datasets(user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
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
            try:
                rval = pdb.crud.get_datasets_to_reset(db)
                logger.info(f'get failed dataset {rval}')
                return rval
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={'message': str(e)},
                )
            

@router.put('/datasets/reset/{datasetid}')
async def reset_dataset(datasetid: int, user: dict = Depends(keycloak.decode), db: Session = Depends(pdb.get_db)):
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
            dataset = pdb.crud.get_dataset(db,datasetid)
            if not dataset:
                return HTTPException(status_code=400, detail='Dataset id {datasetid} does not exist')
            if dataset.mode == pdb.models.Mode.imported and dataset.status == pdb.models.Status.failed:
                return pdb.crud.update_dataset_mode_status(db, datasetid, pdb.models.Mode.imported, pdb.models.Status.ongoing)
            elif dataset.mode == pdb.models.Mode.ingested and dataset.status == pdb.models.Status.failed:   
                return pdb.crud.update_dataset_mode_status(db, datasetid, pdb.models.Mode.imported, pdb.models.Status.success)
            else:
                return HTTPException(status_code=400, detail=f'Dataset reset not allowed {dataset}')