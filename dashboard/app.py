import logging
from logging.handlers import TimedRotatingFileHandler
import dashboard.keycloak as keycloak

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pitschi import config

from dashboard.routers import user, projects, collections
from fastapi.staticfiles import StaticFiles


logger = logging.getLogger('datamover')
logger.setLevel(logging.DEBUG)

log_file = config.get_config().get('logging', 'log_file')
fh = TimedRotatingFileHandler(log_file, when='midnight',backupCount=7)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logging.getLogger("uvicorn.access").addHandler(fh)
logging.getLogger("uvicorn.error").addHandler(fh)
logging.getLogger("uvicorn").addHandler(fh)


dashboard = FastAPI(title="Pitschi data mover",
              description="Manage data movement from camera machine to preprocessing to RDM")
dashboard.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dashboard.include_router(
    user.router,
    prefix="/api",
    tags=["user"],
    dependencies=[Depends(keycloak.decode)],
    responses={404: {"description": "Not found"}},
)


dashboard.include_router(
    projects.router,
    prefix="/api",
    tags=["projects"],
    dependencies=[Depends(keycloak.decode)],
    responses={404: {"description": "Not found"}},
)

dashboard.include_router(
    collections.router,
    prefix="/api",
    tags=["collections"],
    dependencies=[Depends(keycloak.decode)],
    responses={404: {"description": "Not found"}},
)


dashboard.mount('/', StaticFiles(directory=config.get_config().get("miscs", "staticfolder"), html=True, check_dir=False))

logger.info("Start the server")



