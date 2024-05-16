from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from .db_schema import Base, DbClient, DbClientAuthEvent, DbAuthState, DbClientCommitAccess, DbClientAuthChallenge, DbGitCommit
from os import environ
from models import models
from fastapi import HTTPException
from secrets import token_urlsafe
from datetime import datetime
import logging
from datetime import datetime

logger = logging.getLogger()

engine = create_engine(f"sqlite:///{environ['DATA_DIR']}/db.sqlite")

Base.metadata.create_all(engine)

DbSession = sessionmaker(bind=engine)


def create_auth_session(client_name: str) -> models.ChallengeInitiateResponse:
    """ Create a new challenge session in the database """
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        
        auth_event = DbClientAuthEvent(client.id)
        auth_challenge = DbClientAuthChallenge(auth_event.id, token_urlsafe(16), token_urlsafe(16))

        session.add(auth_event)
        session.add(auth_challenge)

        session.commit()

        return models.ChallengeInitiateResponse(
            id_secret=auth_challenge.id_secret, challenge_secret=auth_challenge.challenge_secret)
        

def _get_pending_auth_session(session: Session, client_name: str, challenge_secret: str) -> DbClientAuthEvent:
    client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
    if client is None:
        raise HTTPException(401, "Given client name is invalid")

    auth_session : DbClientAuthEvent = session.scalar(select(DbClientAuthEvent)
        .join(DbClientAuthEvent.challenge)
        .where(DbClientAuthEvent.client_id == client.id)
        .where(DbClientAuthEvent.auth_state == DbAuthState.PENDING)
        .where(DbClientAuthChallenge.challenge_secret  == challenge_secret))
    if auth_session is None:
        raise HTTPException(401, "No valid challenge/response session in progress")
    return auth_session

def activate_auth_session(client_name: str, challenge_secret: str, expires: datetime):
    """ Activate an auth session in the database after the handshake protocol succeeds """
    with DbSession() as session:
        auth_session = _get_pending_auth_session(session, client_name, challenge_secret)
        auth_session.activate(expires)
        session.add(auth_session)
        session.delete(auth_session.challenge)
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
        session.delete(auth_session.challenge)
        session.commit()

        return True # TODO what other information do we need here?


def log_client_repo_access(client_name: str, git_hash: str):
    """ Update the state of the given client's latest access to the given repo """
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        client_access = session.scalar(select(DbClientCommitAccess)
            .where(DbClientCommitAccess.client_id == client.id)
            .where(DbClientCommitAccess.commit_hash == git_hash))
        if client_access is None:
            client_access = DbClientCommitAccess(client.id, git_hash)
        
        client_access.access_time = datetime.now()

        session.add(client_access)
        session.commit()


def get_all_client_statuses() -> list[models.ClientGitRepoStatus]:
    """ Get the current auth token status and repo access times for each client """
    with DbSession() as session:
        clients : list[DbClient] = session.scalars(select(DbClient).where(DbClient.valid == True))
        if not clients:
            raise HTTPException(404, "No valid clients found")
        results = []
        for client in clients:
            latest_auth_state = sorted(client.auth_sessions, key = lambda s: s.expires, reverse=True)[0] \
                if client.auth_sessions else None
            latest_repo_access = sorted(client.repo_access, key = lambda s: s.access_time, reverse=True)[0] \
                if client.repo_access else None
            results.append(models.ClientStatus(
                client_name = client.name, 
                auth_state = models.ClientAuthState.from_db(latest_auth_state), 
                repo_access = models.ClientGitRepoStatus.from_db(latest_repo_access))
            )
        return results

def log_commit_fetch(commit_hash: str, commit_time: datetime):
    """ Log that a new commit has been pulled from the upstream """
    with DbSession() as session:
        exiting_commit = session.scalar(select(DbGitCommit).where(DbGitCommit.commit_hash == commit_hash))
        if exiting_commit is not None:
            return # No-op
        
        session.add(DbGitCommit(commit_hash, commit_time))
        session.commit()
