from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
import dashboard.keycloak as keycloak
import logging

router = APIRouter()
logger = logging.getLogger('pitschidashboard')

@router.get("/user")
async def get_user(user: dict = Depends(keycloak.decode)):
    logger.debug("Querying user")
    return user

@router.get("/token")
async def get_token(token: str = Depends(keycloak.oauth2_scheme)):
    return token