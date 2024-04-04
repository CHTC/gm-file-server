from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column
from uuid import uuid4

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

    challenge_sessions: Mapped[list["DbClientChallengeSession"]] = relationship(cascade="delete")

    def __init__(self, name):
        self.name = name
        self.valid = True

class DbClientChallengeSession(Base):
    """ Table for tracking in-progress challenge/response sessions with a client """
    __tablename__ = "client_challenge_sessions"
    id = Column(String, primary_key=True, default = _gen_uuid)
    client_id: Mapped[String] = mapped_column(ForeignKey('client.id'))

    id_secret = Column(String, unique=True, nullable=False)
    challenge_secret = Column(String, unique=True, nullable=False)

    def __init__(self, client_id, id_secret, challenge_secret):
        self.id = _gen_uuid()
        self.client_id = client_id
        self.id_secret = id_secret
        self.challenge_secret = challenge_secret
