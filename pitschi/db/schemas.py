from typing import List, Optional

from pydantic import BaseModel, Json
from . import models
import pytz, datetime
import pitschi.config as config

#################################
### system stats
#################################
class SystemStats(BaseModel):
    name: str
    value: Optional[str] = None
    description: Optional[str] = None
    isstring: bool = True
    class Config:
        orm_mode = True

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
### repo type
#################################
class Repo(BaseModel):
    name: str
    type: models.RepoType = models.RepoType.clowder
    url: str
    apiurl: str
    apikey: str
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
    received: Optional[datetime.datetime]
    modified: Optional[datetime.datetime]
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
    originalmachine: str
    originalpath: str   # C:\dekstop\folder1\folder2
    networkpath: str     # \\data.qbi.uq.edu.au\CMM4CEED-Q3504\folder1\folder2
    name: str
    received: Optional[datetime.datetime]
    modified: Optional[datetime.datetime]
    finished: datetime.datetime = None
    desc: Optional[str] = None
    status: models.Status = models.Status.ongoing
    mode: models.Mode = models.Mode.intransit
    space: Optional[str] = None
    datasetid: Optional[str] = None
    bookingid: Optional[int] = None
    repo_name: str = "pitschi"
    
class DatasetCreate(DatasetBase):
    files: List[FileBase] = []

class Dataset(DatasetBase):
    id: int
    files: List[File] = []
    repo: Optional[Repo] = None
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

class DailyTaskBase(BaseModel):
    systemid: Optional[int] = None
    start: Optional[datetime.datetime]
    finished: datetime.datetime = None
    status: models.Status = models.Status.ongoing

class DailyTask(DailyTaskBase):
    id: int
    class Config:
        orm_mode = True

class Core(BaseModel):
    id: int
    institution: str
    shortname: str
    longname: str
    rorid: str
    class Config:
        orm_mode = True

class System(BaseModel):
    id: int
    coreid: int
    type: str
    name: str
    pid: str
    bookings: List[Booking] = []
    dailytasks: List[DailyTask] = []
    class Config:
        orm_mode = True

class UserProjectBase(BaseModel):
    username: str
    projectid: int
    enabled: bool = True
    
class User(BaseModel):
    username: str
    name: str
    userid: Optional[int] = None
    email: str
    projects: List[UserProjectBase] = []
    class Config:
        orm_mode = True

class CollectionCacheBase(BaseModel):
    collection_name: str
    cache_name: str
    inodeslimit: Optional[int] = None
    inodesused: Optional[int] = None
    blocklimitgb: Optional[float] = None
    blockusedgb: Optional[float] = None
    lastupdated: Optional[datetime.datetime] = None
    priority: Optional[int] = 0
    

class Project(BaseModel):
    id: int
    coreid: int
    name: str
    active: bool = True
    type: str
    phase: int
    description: Optional[str] = None
    collection: Optional[str] = None
    users: List[UserProjectBase] = []
    class Config:
        orm_mode = True

class CacheBase(BaseModel):
    name: str
    path: str

class CollectionBase(BaseModel):
    name: str
    inodeslimit: Optional[int] = None
    inodesused: Optional[int] = None
    blocklimitgb: Optional[float] = None
    blockusedgb: Optional[float] = None
    capacitygb: Optional[float] = None
    lastupdated: Optional[datetime.datetime] = None


class CollectionCache(CollectionCacheBase):
    collection: CollectionBase
    cache: CacheBase
    class Config:
        orm_mode = True

class Cache(CacheBase):
    collections: List[CollectionCache] = []
    class Config:
        orm_mode = True

class Collection(CollectionBase):
    projects: List[Project] = []
    caches: List[CollectionCache] = []
    class Config:
        orm_mode = True

class UserProject(UserProjectBase):
    user: User
    project: Project
    bookings: List[Booking] = []
    datasets: List[Dataset] = [] 
    class Config:
        orm_mode = True

