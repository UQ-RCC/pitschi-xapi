import enum, datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Enum, DateTime, func, Date, Time, Interval, ForeignKeyConstraint, null
from sqlalchemy.orm import relationship

from sqlalchemy.ext.mutable import MutableList
from sqlalchemy_json import mutable_json_type
from sqlalchemy import PickleType
import pytz
import pitschi.config as config
from sqlalchemy.dialects.postgresql import JSONB
# from sqlalchemy_json import NestedMutable, MutableDict


from .database import Base

class Mode(enum.Enum):
    intransit = 'intransit' # being copied
    imported = 'imported' # copied
    ingested = 'ingested' # ingested/indexed in repo
    
class Status(enum.Enum):
    ongoing = 'ongoing'
    success = 'success'
    failed = 'failed'


class RepoType(enum.Enum):
    clowder = 'clowder'

class SystemStats(Base):
    __tablename__ = 'systemstats'
    name = Column(String, unique=True, primary_key=True, index=True, nullable=False)
    value = Column(String, unique=False, primary_key=False, index=False, nullable=True)
    isstring = Column(Boolean, nullable=False, default=True)
    description = Column(String, unique=False, primary_key=False, index=False, nullable=True)


class PUser(Base):
    __tablename__ = 'puser'
    username = Column(String, unique=True, primary_key=True, index=True, nullable=False)
    password = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    desc = Column(String, unique=False, primary_key=False, index=False, nullable=True)

class Dataset(Base):
    __tablename__ = 'dataset'
    id = Column(Integer, primary_key=True, index=True)
    origionalmachine = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    origionalpath = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    networkpath = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    relpathfromrootcollection = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    name = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    received =  Column(DateTime(timezone=True), primary_key=False, index=False, nullable=False, server_default=func.timezone('UTC', func.now()))
    modified =  Column(DateTime(timezone=True), primary_key=False, index=False, nullable=False, default=func.timezone('UTC', func.now()), onupdate=func.timezone('UTC', func.now()))
    finished =  Column(DateTime(timezone=True), primary_key=False, index=False, nullable=True)
    desc = Column(String, unique=False, primary_key=False, index=False, nullable=True)
    # todo: change to enum
    mode = Column(Enum(Mode), primary_key=False, index=False, nullable=False, default=Mode.intransit) 
    status = Column(Enum(Status), primary_key=False, index=False, nullable=False, default=Status.ongoing) 
    space = Column(String, unique=False, primary_key=False, index=False, nullable=False, default="")
    datasetid = Column(String, unique=False, primary_key=False, index=False, nullable=False, default="")

    bookingid = Column(Integer, ForeignKey("booking.id"), nullable=False)

    repo_name = Column(String, ForeignKey("repo.name"), nullable=False)
    repo =  relationship("Repo", back_populates="datasets")
    
    booking = relationship("Booking", back_populates="datasets")

    files = relationship("File", back_populates="dataset")

# not being used atm
class Repo(Base):
    __tablename__ = 'repo'
    name = Column(String, primary_key=True, index=True)
    type = Column(Enum(RepoType), primary_key=False, index=False, nullable=False, default=RepoType.clowder)
    url = Column(String, primary_key=False, index=False, nullable=False)
    apiurl = Column(String, primary_key=False, index=False, nullable=False)
    apikey = Column(String, primary_key=False, index=False, nullable=False)
    
    datasets = relationship("Dataset", back_populates="repo")

class File(Base):
    __tablename__ = 'file'
    id = Column(Integer, primary_key=True, index=True)
    # this path is the relative path from the folder
    path = Column(String, unique=False, primary_key=False, index=False, nullable=False)
    hashvalue = Column(String, unique=False, primary_key=False, index=False, nullable=True)
    size_kb = Column(Float, unique=False, primary_key=False, index=False, nullable=False)
    # todo: change to enum
    mode = Column(Enum(Mode), primary_key=False, index=False, nullable=False, default=Mode.intransit) 
    status = Column(Enum(Status), primary_key=False, index=False, nullable=False, default=Status.ongoing)
    received =  Column(DateTime(timezone=True), primary_key=False, index=False, nullable=False, server_default=func.timezone('UTC', func.now()))
    modified =  Column(DateTime(timezone=True), primary_key=False, index=False, nullable=False, default=func.timezone('UTC', func.now()), onupdate=func.timezone('UTC', func.now()))
    finished =  Column(DateTime(timezone=True), primary_key=False, index=False, nullable=True)
    fileid = Column(String, unique=False, primary_key=False, index=False, nullable=False, default="")
    dataset_id = Column(Integer, ForeignKey("dataset.id"), nullable=False)
    dataset =  relationship("Dataset", back_populates="files")

class System(Base):
    __tablename__ = 'system'
    id = Column(Integer, primary_key=True, index=True)
    coreid = Column(Integer, primary_key=False, index=False, nullable=False)
    type = Column(String, primary_key=False, index=False, nullable=False)
    name = Column(String, primary_key=False, index=False, nullable=False)
    bookings = relationship("Booking", back_populates="system")
    dailytasks = relationship("DailyTask", back_populates="system")

class DailyTask(Base):
    __tablename__ = 'dailytask'
    id = Column(Integer, primary_key=True, index=True)
    systemid = Column(Integer, ForeignKey("system.id"), nullable=True)
    system = relationship("System", back_populates="dailytasks")
    status = Column(Enum(Status), primary_key=False, index=False, nullable=False, default=Status.ongoing)
    start = Column(DateTime(timezone=True), primary_key=False, index=False, nullable=False, server_default=func.timezone('UTC', func.now()) )
    finished = Column(DateTime(timezone=True), primary_key=False, index=False, nullable=True)
    
class UserProject(Base):
    __tablename__ = 'userproject'
    username = Column(String, ForeignKey('user.username'), primary_key=True)
    projectid = Column(Integer, ForeignKey('project.id'), primary_key=True)
    enabled = Column(Boolean, primary_key=False, index=False, nullable=False, default=True)
    project = relationship("Project", back_populates="users")
    user = relationship("User", back_populates="projects")
    bookings = relationship("Booking", back_populates="userproject") 
    
class User(Base):
    __tablename__ = 'user'
    username = Column(String, primary_key=True, index=True)
    userid = Column(Integer, primary_key=False, index=False, nullable=True)
    name = Column(String, primary_key=False, index=False, nullable=False)
    email = Column(String, primary_key=False, index=False, nullable=False)
    projects = relationship("UserProject", back_populates="user")    


class Project(Base):
    __tablename__ = 'project'
    id = Column(Integer, primary_key=True, index=True)
    coreid = Column(Integer, primary_key=False, index=False, nullable=False)
    name = Column(String, primary_key=False, index=False, nullable=False)
    active = Column(Boolean, primary_key=False, index=False, nullable=False, default=True)
    type = Column(String, primary_key=False, index=False, nullable=False)
    phase = Column(Integer, primary_key=False, index=False, nullable=False)
    description = Column(String, primary_key=False, index=False, nullable=True)
    collection = Column(String, ForeignKey("collection.name"), index=False, nullable=True)
    users = relationship("UserProject", back_populates="project")
    collectionobj = relationship("Collection", back_populates="projects")

class CollectionCache(Base):
    __tablename__ = 'collectioncache'
    collection_name = Column(String, ForeignKey('collection.name'), primary_key=True)
    cache_name = Column(String, ForeignKey('cache.name'), primary_key=True)
    priority =  Column(Integer, default=0, nullable=False) # the higher the better, its cache = 0
    # limit
    inodeslimit = Column(Integer, primary_key=False, index=False, nullable=True)
    inodesused = Column(Integer, primary_key=False, index=False, nullable=True)
    blocklimitgb = Column(Float, primary_key=False, index=False, nullable=True)
    blockusedgb = Column(Float, primary_key=False, index=False, nullable=True)
    lastupdated = Column(DateTime(timezone=True), primary_key=False, index=False, nullable=True, default=func.timezone('UTC', func.now())) 
    cache = relationship("Cache", back_populates="collections")
    collection = relationship("Collection", back_populates="caches")

class Cache(Base):
    __tablename__ = 'cache'
    name = Column(String, primary_key=True, index=True)
    path = Column(String, primary_key=False, index=False, nullable=False)
    collections = relationship("CollectionCache", back_populates="cache")



class Collection(Base):
    __tablename__ = 'collection'
    name = Column(String, primary_key=True, index=True)
    # information at home
    inodeslimit = Column(Integer, primary_key=False, index=False, nullable=True)
    inodesused = Column(Integer, primary_key=False, index=False, nullable=True)
    blocklimitgb = Column(Float, primary_key=False, index=False, nullable=True)
    blockusedgb = Column(Float, primary_key=False, index=False, nullable=True)
    capacitygb = Column(Float, primary_key=False, index=False, nullable=True)
    lastupdated = Column(DateTime(timezone=True), primary_key=False, index=False, nullable=True, default=func.timezone('UTC', func.now()))
    projects = relationship("Project", back_populates="collectionobj")
    caches = relationship("CollectionCache", back_populates="collection")


class Booking(Base):
    __tablename__ = 'booking'
    id = Column(Integer, primary_key=True, index=True)
    bookingdate =  Column(Date, primary_key=False, index=False, nullable=False)
    starttime = Column(Time, primary_key=False, index=False, nullable=False)
    duration = Column(Integer, primary_key=False, index=False, nullable=False)
    status = Column(String, primary_key=False, index=False, nullable=True)
    cancelled = Column(Boolean, primary_key=False, index=False, nullable=False, default=False)
    systemid = Column(Integer, ForeignKey("system.id"), nullable=True)
    system = relationship("System", back_populates="bookings")

    datasets = relationship("Dataset", back_populates="booking")

    username = Column(String, primary_key=False, index=False, nullable=True)
    assistant = Column(String, primary_key=False, index=False, nullable=True)
    projectid = Column(Integer, primary_key=False, index=False, nullable=True)
    
    userproject = relationship("UserProject", back_populates="bookings")
    __table_args__ = (
        ForeignKeyConstraint(
            ['username', 'projectid'],
            ['userproject.username', 'userproject.projectid'],
        ),
    )
