import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .routers import clowder, ppms, user, scheduledingest, credentials
from .routers import sync_ppms_bookings, sync_ppms_projects, notification, dailytask

from .routers.dashboard import projects, collections, cache, admin

import pitschi.config as config
from logging.handlers import TimedRotatingFileHandler

import pitschi.keycloak as keycloak

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

# notification
pitschixapi.include_router(
    notification.router, 
    tags=["notification"], 
    responses={404: {"description": "Not found"}},
)

# credentials
pitschixapi.include_router(
    credentials.router, 
    tags=["credentials"], 
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


# daily tasks
pitschixapi.include_router(
    dailytask.router, 
    tags=["dailytask"], 
    responses={404: {"description": "Not found"}},
)


# scheduledtasks
if config.get('ppms', 'syncing_ppms_project', default = "no") == "yes":
    logger.debug("Syncing project on")
    pitschixapi.include_router(
        sync_ppms_projects.router
    )
else:
    logger.debug("Syncing projects with ppms off")

if config.get('ppms', 'syncing_ppms_bookings', default = "no") == "yes":
    logger.debug("Syncing bookings on")
    pitschixapi.include_router(
        sync_ppms_bookings.router
    )
else:
    logger.debug("Syncing bookings with ppms off")
    
if config.get('clowder', 'ingesting', default = "yes") == "yes":
    logger.debug("ingsting on")
    pitschixapi.include_router(
        scheduledingest.router
    )
else:
    logger.debug("ingesting off")

###############dashboard
pitschixapi.include_router(
    projects.router,
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(keycloak.decode)],
    responses={404: {"description": "Not found"}},
)

pitschixapi.include_router(
    collections.router,
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(keycloak.decode)],
    responses={404: {"description": "Not found"}},
)


pitschixapi.include_router(
    cache.router,
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)

pitschixapi.include_router(
    admin.router,
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)



logger.info("Start xapi")
