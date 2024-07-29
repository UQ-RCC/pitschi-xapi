from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session
import pitschi.config as config
import pitschi.keycloak as keycloak

router = APIRouter()
logger = logging.getLogger('pitschixapi')
security = HTTPBasic()


@router.get("/creds/{field}")
async def get_encypted_creds(field: str, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Get creds field")
    if field not in config.config.options('creds'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect field",
            headers={"WWW-Authenticate": "Basic"},
        )
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return config.get('creds', field)

@router.get("/creds_oidc/{field}")
async def get_encypted_creds_oidc(field: str, user: dict = Depends(keycloak.decode)):
    """
    get the key (encyrpted) used to decrypt credentials - using oidc
    """
    if field not in config.config.options('creds'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect field",
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorised"
        )
    else: 
        realm_access = user.get('realm_access')
        has_superadmin_access = realm_access and 'superadmin' in realm_access.get('roles')
        if not has_superadmin_access:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorised. Only superadmin can do this."
            )
    return config.get('creds', field)

@router.get("/clowder_api_url")
async def get_clowder_api_url():
    return config.get('clowder', 'api_url')

@router.get("/ppms_api_config")
async def get_ppms_api_config(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Get ppms api config")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    # allowed unencrypted field list excludes keys
    allowed_fields = ['booking_query', 'coreids', 'ppms_url', 'project_starting_ref',
        'q_collection_field', 'qcollection_action', 'timezone']
    return { f: config.get('ppms', f) for f in allowed_fields }
