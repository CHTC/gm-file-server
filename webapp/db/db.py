from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from .db_schema import Base, DbClient, DbClientChallengeSession, DbClientRepoAccess
from os import environ
from models import models
from fastapi import HTTPException
from secrets import token_urlsafe
from datetime import datetime
import logging

logger = logging.getLogger("default")

engine = create_engine(f"sqlite:///{environ['DATA_DIR']}/db.sqlite")

Base.metadata.create_all(engine)

DbSession = sessionmaker(bind=engine)


def create_challenge_session(client_name: str) -> models.ChallengeInitiateResponse:
    """ Create a new challenge session in the database """
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        
        client_challenge = DbClientChallengeSession(client.id, token_urlsafe(16), token_urlsafe(16))

        session.add(client_challenge)

        session.commit()

        return models.ChallengeInitiateResponse(
            id_secret=client_challenge.id_secret, challenge_secret=client_challenge.challenge_secret)
        
def complete_challenge_session(client_name: str, challenge_secret: str):
    """ Resolve a challenge session in the database """
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")

        active_challenge = session.scalar(select(DbClientChallengeSession)
            .where(DbClientChallengeSession.client_id == client.id)
            .where(DbClientChallengeSession.challenge_secret == challenge_secret))
        if active_challenge is None:
            raise HTTPException(404, "No valid challenge/response session in progress")

        session.delete(active_challenge)

        return True # TODO what other information do we need here?


def log_client_repo_access(client_name: str, repo_name: str, git_hash: str):
    """ Update the state of the given client's latest access to the given repo """
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        client_access = session.scalar(select(DbClientRepoAccess)
            .where(DbClientRepoAccess.client_id == client.id)
            .where(DbClientRepoAccess.git_repo == repo_name))
        if client_access is None:
            client_access = DbClientRepoAccess(client.id, repo_name)
        
        client_access.git_hash = git_hash
        client_access.access_time = datetime.now()

        session.add(client_access)
        session.commit()





