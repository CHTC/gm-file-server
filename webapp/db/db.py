from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from .db_schema import Base, DbClient, DbClientAuthSession, DbAuthState
from os import environ
from models import models
from fastapi import HTTPException
from secrets import token_urlsafe
import logging
from datetime import datetime

logger = logging.getLogger("default")

engine = create_engine(f"sqlite:///{environ['DATA_DIR']}/db.sqlite")

Base.metadata.create_all(engine)

DbSession = sessionmaker(bind=engine)


def create_auth_session(client_name: str) -> models.ChallengeInitiateResponse:
    """ Create a new challenge session in the database """
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        
        client_challenge = DbClientAuthSession(client.id, token_urlsafe(16), token_urlsafe(16))

        session.add(client_challenge)

        session.commit()

        return models.ChallengeInitiateResponse(
            id_secret=client_challenge.id_secret, challenge_secret=client_challenge.challenge_secret)
        

def _get_pending_auth_session(session: Session, client_name: str, challenge_secret: str) -> DbClientAuthSession:
    client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
    if client is None:
        raise HTTPException(401, "Given client name is invalid")

    auth_session : DbClientAuthSession = session.scalar(select(DbClientAuthSession)
        .where(DbClientAuthSession.client_id == client.id)
        .where(DbClientAuthSession.challenge_secret == challenge_secret)
        .where(DbClientAuthSession.auth_state == DbAuthState.PENDING))
    if auth_session is None:
        raise HTTPException(401, "No valid challenge/response session in progress")
    return auth_session

def activate_auth_session(client_name: str, challenge_secret: str, expires: datetime):
    """ Activate an auth session in the database after the handshake protocol succeeds """
    with DbSession() as session:
        auth_session = _get_pending_auth_session(session, client_name, challenge_secret)
        auth_session.activate(expires)
        session.add(auth_session)
        session.commit()

        return True # TODO what other information do we need here?

def fail_auth_session(client_name: str, challenge_secret: str):
    """ Fail an auth session in the database after the handshake protocol fails 
    # TODO clear these out on a regular basis
    """
    with DbSession() as session:
        auth_session = _get_pending_auth_session(session, client_name, challenge_secret)
        auth_session.fail()
        session.add(auth_session)
        session.commit()

        return True # TODO what other information do we need here?
