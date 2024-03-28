from fastapi import FastAPI, BackgroundTasks, HTTPException
from os import environ
from .models.models import *
from .db import db

import logging
import requests
from contextlib import contextmanager

logger = logging.getLogger("default")


api_prefix = environ['API_PREFIX']
app = FastAPI()
#prefix_router = APIRouter(prefix=api_prefix)

# TODO a more elegant solution
# hack to deal with apache not logging fastAPI's exceptions by default
@contextmanager
def err_log_context():
    try:
        yield
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"{e}")
        raise HTTPException(500, f"{e}")


@app.get('/public')
def get_public():
    return {"message": "This is a public route!" }

@app.get('/private')
def get_public():
    return {"message": "This is a secret route!" }

def follow_up_challenge(callback_address:str, id_secret: str, challenge_secret:str):
    logger.info(f"Following up on challenge to {callback_address}")
    resp = requests.post(callback_address, data=ChallengeCompleteRequest(id_secret=id_secret).model_dump())
    completed_challenge = ChallengeCompleteResponse.model_validate_json(resp.json())
    logger.info(f"Challenge status: {completed_challenge.challenge_secret == challenge_secret}")


@app.post('/public/challenge/initiate')
async def post_initiate_challenge(request: ChallengeInitiateRequest, background_tasks: BackgroundTasks) -> ChallengeInitiateResponse:
    logger.info(f"Received challenge request from {request.client_name}")
    with err_log_context():
        challenge = db.create_challenge_session(request.client_name)
        background_tasks.add_task(follow_up_challenge, request.callback_address, challenge.id_secret, challenge.challenge_secret)
        return challenge

#app.include_router(prefix_router)
