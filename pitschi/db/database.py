from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi_utils.session import FastAPISessionMaker
import pitschi.config as config

from functools import lru_cache


SQLALCHEMY_DATABASE_URL = (f"{config.get('database', 'type')}://"
                           f"{config.get('database', 'username')}:"
                           f"{config.get('database', 'password')}@"
                           f"{config.get('database', 'host')}/"
                           f"{config.get('database', 'name')}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={}
)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

@lru_cache()
def _get_fastapi_sessionmaker() -> FastAPISessionMaker:
    """ This function could be replaced with a global variable if preferred """
    return FastAPISessionMaker(SQLALCHEMY_DATABASE_URL)
