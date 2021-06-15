from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pytz
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session
import datetime
import pitschi.config as config
import pitschi.utils as utils
import pitschi.clowder_rest as clowderful
import os, json

router = APIRouter()
logger = logging.getLogger('pitschixapi')
security = HTTPBasic()
    
# look at background asks: https://fastapi.tiangolo.com/tutorial/background-tasks/
# to be replaced by a call to clowder - needs to be implemented
@router.post("/datasets")
async def ingest(dataset: pdb.schemas.DatasetCreate, \
                credentials: HTTPBasicCredentials = Depends(security), \
                db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    newds = pdb.crud.create_dataset(db, dataset)
    return newds



@router.get("/datasets")
async def get_datasets(login: str, machine: str="", localpath: str="", \
                        date: datetime.date=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))).date(), \
                        credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    if login.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="login must not be empty",
            headers={"WWW-Authenticate": "Basic"},
        )
    datasets = []
    if  machine.strip()!="" and localpath.strip()=="":
        datasets =  pdb.crud.get_datasets_from_one_machine(db, login, machine, date)
    elif machine.strip()!="" and localpath.strip()!="":
        datasets =  pdb.crud.get_datasets_from_original(db, login, machine, localpath)
    else:
        datasets =  pdb.crud.get_datasets(db, login)
    for dataset in datasets:
        if dataset.received:
            dataset.received = utils.convert_to_xapi_tz(dataset.received)
        if dataset.finished:
            dataset.finished = utils.convert_to_xapi_tz(dataset.finished)    
        if dataset.modified:
            dataset.modified = utils.convert_to_xapi_tz(dataset.modified)
    return datasets
    
# Technically, an update to dataset should trigger reindexing as well
# But this needs to be implemented later
@router.put("/datasets/{datasetid}")
async def update_dataset(datasetid: int, dataset: pdb.schemas.DatasetCreate, \
                        credentials: HTTPBasicCredentials = Depends(security), \
                        db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return pdb.crud.update_dataset(db, datasetid, dataset)    


@router.get("/files/{fileid}")
async def update_file(fileid: int, \
                    credentials: HTTPBasicCredentials = Depends(security), \
                    db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    _afile =  pdb.crud.get_file(db, fileid)
    if _afile.received:
        _afile.received = utils.convert_to_xapi_tz(_afile.received)
    if _afile.finished:
        _afile.finished = utils.convert_to_xapi_tz(_afile.finished)
    if _afile.modified:
        _afile.modified = utils.convert_to_xapi_tz(_afile.modified)
    return _afile
    

@router.get("/datasets/{datasetid}")
async def get_dataset(datasetid: int, \
                    credentials: HTTPBasicCredentials = Depends(security), \
                    db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    _adataset =  pdb.crud.get_dataset(db, datasetid)
    if _adataset:
        if _adataset.received:
            _adataset.received = utils.convert_to_xapi_tz(_adataset.received)
        if _adataset.finished:
            _adataset.finished = utils.convert_to_xapi_tz(_adataset.finished)
        if _adataset.modified:
            _adataset.modified = utils.convert_to_xapi_tz(_adataset.modified)
        files =  pdb.crud.get_files_in_dataset(db, _adataset.id)
        for file in files:
            if file.received:
                file.received = utils.convert_to_xapi_tz(file.received)
            if file.finished:
                file.finished = utils.convert_to_xapi_tz(file.finished)    
            if file.modified:
                file.modified = utils.convert_to_xapi_tz(file.modified)
        _adataset.files = files
    return _adataset
    

@router.get("/bookings/{bookingid}/datasets")
async def get_booking_datasets(bookingid: int, \
                            credentials: HTTPBasicCredentials = Depends(security), \
                            db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    datasets = pdb.crud.get_booking_datasets(db, bookingid)
    for dataset in datasets:
        if dataset.received:
            dataset.received = utils.convert_to_xapi_tz(dataset.received)
        if dataset.finished:
            dataset.finished = utils.convert_to_xapi_tz(dataset.finished)    
        if dataset.modified:
            dataset.modified = utils.convert_to_xapi_tz(dataset.modified)
    return datasets