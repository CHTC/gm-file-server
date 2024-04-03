from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from .db_schema import Base, DbClient, DbClientChallengeSession
from ..models.models import *
from fastapi import HTTPException
from secrets import token_urlsafe
import logging

logger = logging.getLogger("default")

engine = create_engine("sqlite:///tmp/db.sqlite")

Base.metadata.create_all(engine)

DbSession = sessionmaker(bind=engine)

def populate_dummy_data():
    with DbSession() as session:
        session.add(DbClient("test-client"))
        session.commit()
populate_dummy_data()



def create_challenge_session(client_name: str) -> ChallengeInitiateResponse:
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")
        
        client_challenge = DbClientChallengeSession(client.id, token_urlsafe(16), token_urlsafe(16))

        session.add(client_challenge)

        session.commit()

        return ChallengeInitiateResponse(
            id_secret=client_challenge.id_secret, challenge_secret=client_challenge.challenge_secret)
        
def complete_challenge_session(client_name: str, challenge_secret: str):
    with DbSession() as session:
        client = session.scalar(select(DbClient).where(DbClient.name == client_name).where(DbClient.valid == True))
        if client is None:
            raise HTTPException(404, "Given client name is invalid")

        active_challenge = session.scalar(select(DbClientChallengeSession)
            .where(DbClientChallengeSession.client_id == client.id)
            .where(DbClientChallengeSession.challenge_secret == challenge_secret))
        if active_challenge is None:
            raise HTTPException(404, "No challenge/response session in progress")

        session.delete(active_challenge)

        return True # TODO what information do we need here?