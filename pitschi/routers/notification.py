from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pitschi.db as pdb
from sqlalchemy.orm import Session
import pitschi.notifications as notifications
import pitschi.keycloak as keycloak

router = APIRouter()
security = HTTPBasic()

@router.post("/notificationpw")
async def send_notification(type: str, title: str, message: str, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    """
    Send notification to teams. 
    This requires authed user to send.
    """
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    notifications.send_teams_notification(type, title, message)


@router.post("/notification_oidc")
async def send_notification_oidc(type: str, title: str, message: str, user: dict = Depends(keycloak.decode)):
    """
    Same as send_notification, but required oidc auth flow. Prob there is better way to do this. 
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
    notifications.send_teams_notification(type, title, message)
