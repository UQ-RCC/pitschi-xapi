import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pitschi.db as pdb
from sqlalchemy.orm import Session
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(pdb.get_db)):
    user = pdb.crud.get_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

