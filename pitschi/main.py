import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .routers import clowder, ppms, user, scheduledtasks, scheduledingest
import pitschi.config as config
from logging.handlers import TimedRotatingFileHandler


logger = logging.getLogger('pitschixapi')
logger.setLevel(logging.DEBUG)

log_file = config.get('logging', 'log_file', default = "/var/log/pitschi/pitschi-xapi.log")
fh = TimedRotatingFileHandler(log_file, when='midnight',backupCount=7)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logging.getLogger("uvicorn.access").addHandler(fh)
# logging.getLogger("uvicorn.error").addHandler(fh)
logging.getLogger("uvicorn").addHandler(fh)


pitschixapi = FastAPI()

pitschixapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# user
pitschixapi.include_router(
    user.router, 
    tags=["user"], 
    responses={404: {"description": "Not found"}},
)


# ppms
pitschixapi.include_router(
    ppms.router, 
    tags=["ppms"], 
    prefix="/ppms",
    responses={404: {"description": "Not found"}},
)
# clowder
pitschixapi.include_router(
    clowder.router,
    prefix="/clowder",
    tags=["clowder"],
    responses={404: {"description": "Not found"}},
)

# scheduledtasks
if config.get('ppms', 'syncing_ppms', default = "no") == "yes":
    logger.debug("Syncing on")
    pitschixapi.include_router(
        scheduledtasks.router
    )
else:
    logger.debug("Syncing with ppms off")
    
if config.get('clowder', 'ingesting', default = "yes") == "yes":
    logger.debug("ingsting on")
    pitschixapi.include_router(
        scheduledingest.router
    )
else:
    logger.debug("ingesting off")

logger.info("Start ippuserinfo")
