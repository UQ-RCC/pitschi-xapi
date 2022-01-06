from typing import List, Optional

from pydantic import BaseModel, Json
from . import models
import pytz, datetime
import pitschi.config as config
#################################
### user
#################################
class PUser(BaseModel):
    username: str
    password: str
    desc: str

    class Config:
        orm_mode = True

#################################
### files
#################################
class FileBase(BaseModel):
    path: str
    hashvalue: Optional[str] = None
    size_kb: float
    status: models.Status = models.Status.ongoing
    mode: models.Mode = models.Mode.intransit
    received: datetime.datetime = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone')))
    modified: datetime.datetime = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone')))
    finished: datetime.datetime = None
    fileid: Optional[str] = None

class FileCreate(FileBase):
    dataset_id: int

class File(FileBase):
    id: int
    class Config:
        orm_mode = True


#################################
### dataset
#################################
class DatasetBase(BaseModel):
    relpathfromrootcollection: str # /folder1/folder2 # get q collectio nfrom project
    origionalmachine: str 
    origionalpath: str   # C:\dekstop\folder1\folder2
    networkpath: str     # \\data.qbi.uq.edu.au\CMM4CEED-Q3504\folder1\folder2
    name: str
    received: datetime.datetime = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone')))
    modified: datetime.datetime = datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone')))
    finished: datetime.datetime = None
    desc: Optional[str] = None
    status: models.Status = models.Status.ongoing
    mode: models.Mode = models.Mode.intransit
    space: Optional[str] = None
    datasetid: Optional[str] = None
    bookingid: Optional[int] = None
    
class DatasetCreate(DatasetBase):
    files: List[FileBase] = []

class Dataset(DatasetBase):
    id: int
    files: List[File] = []
    class Config:
        orm_mode = True

###################################################
############### PPMS ############################
##### booking
class Booking(BaseModel):
    id: int
    bookingdate: datetime.date
    starttime: datetime.time
    duration: int 
    cancelled: bool = False
    status: Optional[str] = None
    username: Optional[str] = None
    assistant: Optional[str] = None
    projectid: Optional[int] = None
    systemid: Optional[int] = None
    class Config:
        orm_mode = True

        
class System(BaseModel):
    id: int
    type: str
    name: str
    bookings: List[Booking] = []
    class Config:
        orm_mode = True

class UserProjectBase(BaseModel):
    username: str
    projectid: int
    
class User(BaseModel):
    username: str
    name: str
    userid: Optional[int] = None
    email: str
    projects: List[UserProjectBase] = []
    class Config:
        orm_mode = True

class Project(BaseModel):
    id: int
    name: str
    active: bool = True
    type: str
    phase: int
    description: Optional[str] = None
    collection: Optional[str] = None
    users: List[UserProjectBase] = []
    class Config:
        orm_mode = True

class UserProject(UserProjectBase):
    user: User
    project: Project
    bookings: List[Booking] = []
    datasets: List[Dataset] = [] 
    class Config:
        orm_mode = True

