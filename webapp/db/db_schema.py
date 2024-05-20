from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey
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

    auth_sessions: Mapped[list["DbClientAuthEvent"]] = relationship(cascade="delete")

    repo_access: Mapped[list["DbClientCommitAccess"]] = relationship(cascade="delete")

    def __init__(self, name):
        self.id = _gen_uuid()
        self.name = name
        self.valid = True

class DbAuthState(str, Enum):
    PENDING = 'PENDING'
    SUCCESSFUL = 'SUCCESSFUL'
    FAILED = 'FAILED'

class DbClientAuthEvent(Base):
    """ Table for tracking in-progress challenge/response sessions with a client """
    __tablename__ = "client_auth_sessions"
    id = Column(String, primary_key=True, default = _gen_uuid)
    client_id: Mapped[String] = mapped_column(ForeignKey('client.id'))
    auth_state = Column(String, nullable=False)

    initiated = Column(DateTime, default=datetime.now(), index=True)
    expires   = Column(DateTime, default=datetime.now())

    challenge: Mapped["DbClientAuthChallenge"] = relationship(cascade="delete")

    def __init__(self, client_id):
        self.id = _gen_uuid()
        self.client_id = client_id
        self.auth_state = DbAuthState.PENDING
        self.initiated = datetime.now()

    def activate(self, expires):
        self.auth_state = DbAuthState.SUCCESSFUL
        self.expires = expires
    
    def fail(self):
        self.auth_state = DbAuthState.FAILED

class DbClientAuthChallenge(Base):
    __tablename__ = "client_auth_challenges"

    auth_event_id: Mapped[String] = mapped_column(ForeignKey('client_auth_sessions.id'), primary_key=True)

    id_secret = Column(String, unique=True)
    challenge_secret = Column(String, unique=True)

    def __init__(self, auth_event_id, id_secret, challenge_secret):
        self.auth_event_id = auth_event_id
        self.id_secret = id_secret
        self.challenge_secret = challenge_secret


class DbGitCommit(Base):
    """ Table for tracking the Git Commits that have been the HEAD """

    __tablename__ = "repo_commits"

    commit_hash = Column(String, primary_key=True)

    commit_time = Column(DateTime)

    sync_time = Column(DateTime)

    def __init__(self, commit_hash, commit_time):
        self.commit_hash = commit_hash
        self.commit_time = commit_time
        self.sync_time = datetime.now()

class DbClientCommitAccess(Base):
    """ Table for tracking the latest version of the git repo accessed by a client """
    __tablename__ = "client_commit_access"
    
    id = Column(String, primary_key=True, default = _gen_uuid)
    client_id: Mapped[String] = mapped_column(ForeignKey('client.id'))
    
    commit_hash: Mapped[String] = mapped_column(ForeignKey('repo_commits.commit_hash'))
    access_time = Column(DateTime)

    def __init__(self, client_id, commit_hash, access_time = None):
        self.id = _gen_uuid()
        self.client_id = client_id
        self.commit_hash = commit_hash
        self.access_time = access_time


class DbClientStateView(Base):
    __tablename__ = "__client_latest_state"

    id = Column(String, primary_key=True, default = _gen_uuid)
    name = Column(String, unique=True, nullable=False)

    auth_state = Column(String, nullable=False)

    initiated = Column(DateTime, default=datetime.now(), index=True)
    expires   = Column(DateTime, default=datetime.now())

    commit_hash = Column(String)
    access_time = Column(DateTime)


