from fastapi import APIRouter, Depends

import logging
import datetime 
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pitschi.db as pdb
from sqlalchemy.orm import Session


router = APIRouter()
logger = logging.getLogger('pitschixapi')
security = HTTPBasic()


@router.get("/rdmcollection")
async def get_project_rdmcollection(projectid: int, \
                                    credentials: HTTPBasicCredentials = Depends(security),\
                                    db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.debug("Querying rdm collection")
    project = pdb.crud.get_project(db, projectid)
    _collection = ""
    if project:
        _collection = project.collection
    return {"rdmcollection": _collection}


@router.get("/bookings")
async def get_bookings_in_one_day(  systemid: int, date: datetime.date, login: str="", \
                                    credentials: HTTPBasicCredentials = Depends(security),\
                                    db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.debug("Querying booking of a certain date")
    if login:
        booking_info = pdb.crud.get_bookings_filter_system_and_user(db, systemid, date, login)
    else:
        booking_info = pdb.crud.get_bookings_filter_system(db, systemid, date)
    logger.debug(f"{booking_info}")
    return booking_info

@router.get("/bookings/{bookingid}")
async def get_bookings_in_one_day(  bookingid: int, \
                                    credentials: HTTPBasicCredentials = Depends(security),\
                                    db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.debug(f"Querying booking {bookingid}")
    return pdb.crud.get_booking(db, bookingid)
    



@router.get("/projects")
async def get_projects(credentials: HTTPBasicCredentials = Depends(security),\
                       db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.debug(f"Querying all projects and its information")
    return pdb.crud.get_projects_full(db)

