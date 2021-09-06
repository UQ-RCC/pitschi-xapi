import enum, datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Enum, DateTime, Date, Time, Interval, ForeignKeyConstraint
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
    received =  Column(DateTime, primary_key=False, index=False, nullable=False, default=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) )
    modified =  Column(DateTime, primary_key=False, index=False, nullable=False, default=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) )
    finished =  Column(DateTime, primary_key=False, index=False, nullable=True)
    desc = Column(String, unique=False, primary_key=False, index=False, nullable=True)
    # todo: change to enum
    mode = Column(Enum(Mode), primary_key=False, index=False, nullable=False, default=Mode.intransit) 
    status = Column(Enum(Status), primary_key=False, index=False, nullable=False, default=Status.ongoing) 
    space = Column(String, unique=False, primary_key=False, index=False, nullable=False, default="")
    datasetid = Column(String, unique=False, primary_key=False, index=False, nullable=False, default="")

    bookingid = Column(Integer, ForeignKey("booking.id"), nullable=False)
    booking = relationship("Booking", back_populates="datasets")

    files = relationship("File", back_populates="dataset")



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
    received =  Column(DateTime, primary_key=False, index=False, nullable=False, default=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) )
    modified =  Column(DateTime, primary_key=False, index=False, nullable=False, default=datetime.datetime.now(pytz.timezone(config.get('ppms', 'timezone'))) )
    finished =  Column(DateTime, primary_key=False, index=False, nullable=True)
    fileid = Column(String, unique=False, primary_key=False, index=False, nullable=False, default="")
    dataset_id = Column(Integer, ForeignKey("dataset.id"), nullable=False)
    dataset =  relationship("Dataset", back_populates="files")

class System(Base):
    __tablename__ = 'system'
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, primary_key=False, index=False, nullable=False)
    name = Column(String, primary_key=False, index=False, nullable=False)
    bookings = relationship("Booking", back_populates="system")


class UserProject(Base):
    __tablename__ = 'userproject'
    username = Column(String, ForeignKey('user.username'), primary_key=True)
    projectid = Column(Integer, ForeignKey('project.id'), primary_key=True)
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
    name = Column(String, primary_key=False, index=False, nullable=False)
    active = Column(Boolean, primary_key=False, index=False, nullable=False, default=True)
    type = Column(String, primary_key=False, index=False, nullable=False)
    phase = Column(Integer, primary_key=False, index=False, nullable=False)
    description = Column(String, primary_key=False, index=False, nullable=True)
    collection = Column(String, primary_key=False, index=False, nullable=True)
    users = relationship("UserProject", back_populates="project")

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
    projectid = Column(Integer, primary_key=False, index=False, nullable=True)
    
    userproject = relationship("UserProject", back_populates="bookings")
    __table_args__ = (
        ForeignKeyConstraint(
            ['username', 'projectid'],
            ['userproject.username', 'userproject.projectid'],
        ),
    )


class Collection(Base):
    __tablename__ = 'collection'
    name = Column(String, primary_key=True, index=True, nullable=False)
    fullname = Column(String, primary_key=False, index=False, nullable=True)