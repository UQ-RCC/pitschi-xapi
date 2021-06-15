from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger('pitschixapi')
security = HTTPBasic()

@router.get("/user")
async def get_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Querying user")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"username": credentials.username}


@router.post("/user")
async def create_user(newuser: pdb.schemas.PUser, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Create a new user, only admin can do this")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    if credentials.username == 'admin':
        pdb.crud.create_user(db, newuser.username, newuser.password, newuser.desc)
        return {"username": newuser.username}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only admin can add new users",
            headers={"WWW-Authenticate": "Basic"},
        )
