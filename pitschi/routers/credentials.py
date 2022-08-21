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

@router.get("/key")
async def get_encypted_key(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    """
    get the key (encyrpted) used to decrypt credentials
    """
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return config.get('creds', 'encrypted_key')

@router.get("/key_oidc")
async def get_encypted_key_oidc(user: dict = Depends(keycloak.decode)):
    """
    get the key (encyrpted) used to decrypt credentials - using oidc
    """
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
    return config.get('creds', 'encrypted_key')


@router.get("/creds")
async def get_encypted_credentials(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Querying credentials")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return config.get('creds', 'encrypted_creds')

@router.get("/creds_oidc")
async def get_encypted_credentials_oidc(user: dict = Depends(keycloak.decode)):
    """
    get the key (encyrpted) used to decrypt credentials - using oidc
    """
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
    return config.get('creds', 'encrypted_creds')
