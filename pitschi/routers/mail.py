from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging
import pitschi.db as pdb
from sqlalchemy.orm import Session
import pitschi.mail as mail

router = APIRouter()
logger = logging.getLogger('pitschixapi')
security = HTTPBasic()

class Mail(BaseModel):
    to_addr: str
    subject: str
    contents: str

@router.post("/notification/mail")
async def send_mail(msg: Mail, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    """
    Send email notification. 
    This requires authed user to send.
    """
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.info(f'mailto: {msg.to_addr}, subject: {msg.subject}, username: {credentials.username}')
    mail.send_mail(msg.to_addr, msg.subject, msg.contents)
