from . import crud, database, models, schemas

# from .database import SessionLocal, engine
from .database import engine
from .database import _get_fastapi_sessionmaker
from typing import Iterator
from sqlalchemy.orm import Session

models.Base.metadata.create_all(bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def get_db() -> Iterator[Session]:
    """ FastAPI dependency that provides a sqlalchemy session """
    yield from _get_fastapi_sessionmaker().get_db()


