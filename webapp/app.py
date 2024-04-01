from fastapi import FastAPI, BackgroundTasks, HTTPException
from os import environ
from .models.models import *
from .db import db
from .util.httpd_utils import add_httpd_user

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

def follow_up_challenge(request: ChallengeInitiateRequest, challenge: ChallengeInitiateResponse):
    with err_log_context():
        logger.info(f"C/R: Sending callback to {request.callback_address}")
        resp = requests.post(request.callback_address, data=ChallengeCompleteRequest(id_secret=challenge.id_secret).model_dump_json())
        completed_challenge = ChallengeCompleteResponse.model_validate(resp.json())
        if completed_challenge.challenge_secret == challenge.challenge_secret:
            logger.info(f"C/R: Callback response contains correct challenge secret")
            add_httpd_user(request.client_name, completed_challenge.capability)
            db.complete_challenge_session(request.client_name, completed_challenge.challenge_secret)
        else:
            logger.error(f"C/R: Callback response contains incorrect challenge secret. Ignoring")


@app.post('/public/challenge/initiate')
async def post_initiate_challenge(request: ChallengeInitiateRequest, background_tasks: BackgroundTasks) -> ChallengeInitiateResponse:
    logger.info(f"C/R: Received challenge request from {request.client_name}")
    with err_log_context():
        challenge = db.create_challenge_session(request.client_name)
        background_tasks.add_task(follow_up_challenge, request, challenge)
        return challenge

#app.include_router(prefix_router)
