from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from .db_schema import Base, DbClient, DbClientAuthEvent, DbAuthState, DbClientCommitAccess, DbClientAuthChallenge, DbGitCommit, DbCommandQueueEntry, DbCommandStatus
from .client_state_report import query_client_states
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

def _get_client_by_name(session: Session, client_name: str) -> DbClient:
    """ Get a client by name """
    return session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))

def _get_pending_auth_session(session: Session, client_name: str, challenge_secret: str) -> DbClientAuthEvent:
    client = _get_client_by_name(session, client_name)
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


def create_auth_session(client_name: str) -> models.ChallengeInitiateResponse:
    """ Create a new challenge session in the database """
    with DbSession() as session:
        client = _get_client_by_name(session, client_name)
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        
        auth_event = DbClientAuthEvent(client.id)
        auth_challenge = DbClientAuthChallenge(auth_event.id, token_urlsafe(16), token_urlsafe(16))

        session.add(auth_event)
        session.add(auth_challenge)

        session.commit()

        return models.ChallengeInitiateResponse(
            id_secret=auth_challenge.id_secret, challenge_secret=auth_challenge.challenge_secret)
        

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
        client = _get_client_by_name(session, client_name)
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

def log_commit_fetch(commit_hash: str, commit_time: datetime):
    """ Log that a new commit has been pulled from the upstream """
    with DbSession() as session:
        exiting_commit = session.scalar(select(DbGitCommit).where(DbGitCommit.commit_hash == commit_hash))
        if exiting_commit is not None:
            return # No-op
        
        session.add(DbGitCommit(commit_hash, commit_time))
        session.commit()


def get_client_status_report(report_time: datetime = None, auth_state: models.AuthStateQuery = None, latest_commit: bool = None) -> list[models.ClientAccessStatus]:
    """ Get the current auth token status and repo access times for each client """
    with DbSession() as session:
        client_states = query_client_states(session, report_time, auth_state, latest_commit)
        return [models.ClientStatus.from_db(s) for s in client_states]


def _get_queue_info(session: Session, client_name: str) -> tuple[int, DbCommandQueueEntry]:
    """ Return the queue length and head of the command queue for a given client """
    client = _get_client_by_name(session, client_name)
    queue_length = session.scalar(select(func.count()).select_from(DbCommandQueueEntry)
        .where(DbCommandQueueEntry.client_id == client.id)
        .where(DbCommandQueueEntry.completed == None))
    next_command = session.scalar(select(DbCommandQueueEntry)
        .where(DbCommandQueueEntry.client_id == client.id)
        .where(DbCommandQueueEntry.completed == None)
        .order_by(DbCommandQueueEntry.priority.desc(), DbCommandQueueEntry.created.asc()))
    return queue_length, next_command

def enqueue_command(client_name: str, command: str, priority: int = 1, created: datetime = None):
    with DbSession() as session:
        client = _get_client_by_name(session, client_name)
        queue_entry = DbCommandQueueEntry(client.id, command, priority)
        queue_entry.created = created or datetime.now()
        session.add(queue_entry)
        session.commit()

def get_next_command(client_name: str) -> models.CommandQueueResponse:
    """ Get the next incomplete command in the client's command queue """
    with DbSession() as session:
        queue_length, next_command = _get_queue_info(session, client_name)

        # Mark the command as acknowledged if it isn't yet
        if next_command and not next_command.acknowledged:
            next_command.acknowledged = datetime.now()
            next_command.status = DbCommandStatus.IN_PROGRESS
            session.add(next_command)

        session.commit()

        return models.CommandQueueResponse(
            queue_length=queue_length, 
            command=next_command.command if next_command else None)

def dequeue_command(client_name: str, command_status: DbCommandStatus) -> models.CommandQueueResponse:
    """ Mark a command as either successful or failed, then return the count of commands left in the queue"""
    if command_status not in (DbCommandStatus.SUCCESSFUL, DbCommandStatus.FAILED):
        raise HTTPException(400, "Command status must be either SUCCESSFUL or FAILED")
    with DbSession() as session:
        queue_length, active_command = _get_queue_info(session, client_name)

        # Mark the command as acknowledged if it isn't yet
        if not active_command or not active_command.acknowledged:
            raise HTTPException(400, "Cannot dequeue an unread command")

        active_command.completed = datetime.now()
        active_command.status = command_status

        session.commit()

        return models.CommandQueueResponse(queue_length=queue_length)

