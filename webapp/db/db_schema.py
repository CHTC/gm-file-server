from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column
from uuid import uuid4
from datetime import datetime
from enum import Enum

def _gen_uuid():
    return str(uuid4())

class Base(DeclarativeBase):
    pass

class DbClient(Base):
    """ Table for clients with permission to connect to the Object Server """
    __tablename__ = "client"

    id = Column(String, primary_key=True, default = _gen_uuid)
    name = Column(String, unique=True, nullable=False)
    valid = Column(Boolean, default=True)

    auth_sessions: Mapped[list["DbClientAuthSession"]] = relationship(cascade="delete")

    repo_access: Mapped[list["DbClientRepoAccess"]] = relationship(cascade="delete")

    def __init__(self, name):
        self.name = name
        self.valid = True

class DbAuthState(str, Enum):
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'
    FAILED = 'FAILED'

class DbClientAuthSession(Base):
    """ Table for tracking in-progress challenge/response sessions with a client """
    __tablename__ = "client_auth_sessions"
    id = Column(String, primary_key=True, default = _gen_uuid)
    client_id: Mapped[String] = mapped_column(ForeignKey('client.id'))
    auth_state = Column(String, nullable=False)

    id_secret = Column(String, unique=True)
    challenge_secret = Column(String, unique=True)

    initiated = Column(DateTime, default=datetime.now())
    expires   = Column(DateTime, default=datetime.now())

    def __init__(self, client_id, id_secret, challenge_secret):
        self.id = _gen_uuid()
        self.client_id = client_id
        self.id_secret = id_secret
        self.auth_state = DbAuthState.PENDING
        self.challenge_secret = challenge_secret

    def activate(self, expires):
        self.auth_state = DbAuthState.ACTIVE
        self.expires = expires
        self.challenge_secret = None
        self.id_secret = None
    
    def fail(self):
        self.auth_state = DbAuthState.FAILED
        self.challenge_secret = None
        self.id_secret = None

class DbClientRepoAccess(Base):
    """ Table for tracking the latest version of a git repo accessed by a client """
    __tablename__ = "client_git_access"
    
    id = Column(String, primary_key=True, default = _gen_uuid)
    client_id: Mapped[String] = mapped_column(ForeignKey('client.id'))
    
    git_repo = Column(String, nullable=False)
    git_hash = Column(String)
    access_time = Column(TIMESTAMP)

    def __init__(self, client_id, git_repo):
        self.id = _gen_uuid()
        self.client_id = client_id
        self.git_repo = git_repo

