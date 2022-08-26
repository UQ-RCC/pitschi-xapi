from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger('pitschixapi')
security = HTTPBasic()

@router.get("/dailytask/{systemid}")
async def get_dailytask(systemid: int, 
                    credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Querying user")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return pdb.crud.get_daily_tasks(db, systemid)


@router.post("/dailytask")
async def add_dailytask(task: pdb.schemas.DailyTaskBase, 
                        credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Add new daily tasks")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return pdb.crud.add_daily_task(db, task)



@router.put("/dailytask/{taskid}")
async def finish_dailytask(taskid: int, status: pdb.models.Status, 
                            credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    logger.debug("Complete the task")
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    pdb.crud.complete_daily_task(db, taskid, status)