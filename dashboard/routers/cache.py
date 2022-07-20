
from fastapi import APIRouter, Depends
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session


router = APIRouter()
logger = logging.getLogger('pitschidashboard')


@router.get("/caches")
async def get_caches(db: Session = Depends(pdb.get_db)):
    return pdb.crud.get_caches(db)
    