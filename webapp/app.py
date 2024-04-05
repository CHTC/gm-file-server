from fastapi import FastAPI, BackgroundTasks, HTTPException
from os import environ
from models import models
from db import db
from util.httpd_utils import add_httpd_user
from util.wsgi_error_logging import with_error_logging
from secrets import token_urlsafe

import logging
import requests
from contextlib import contextmanager
from datetime import datetime, timedelta

logger = logging.getLogger("default")


api_prefix = environ['API_PREFIX']
app = FastAPI()

@app.get('/public')
def get_public():
    """ Sample endpoint that's publicly accessible """
    return {"message": "This is a public route!" }

@app.get('/private')
def get_private():
    """ Sample endpoint that's gated by apache basic auth """
    return {"message": "This is a secret route!" }

@with_error_logging
def follow_up_challenge(request: models.ChallengeInitiateRequest, challenge: models.ChallengeInitiateResponse):
    """ Background task that follows up on a challenge initiated by a client. """
    logger.info(f"C/R: Sending callback to {request.callback_address}")
    credentials = models.ChallengeCompleteRequest(
        id_secret=challenge.id_secret,
        capability=token_urlsafe(24),
        expires=datetime.now() + timedelta(hours=2))

    resp = requests.post(request.callback_address, data=credentials.model_dump_json())
    completed_challenge = models.ChallengeCompleteResponse.model_validate(resp.json())
    if completed_challenge.challenge_secret == challenge.challenge_secret:
        logger.info(f"C/R: Callback response contains correct challenge secret")
        add_httpd_user(request.client_name, credentials.capability)
        # TODO There's a big opportunity for data desync if the server crashes between 
        # updating the htpassword file and updating the database
        db.complete_challenge_session(
            request.client_name, completed_challenge.challenge_secret, credentials)
    else:
        logger.error(f"C/R: Callback response contains incorrect challenge secret. Ignoring")


@app.post('/public/challenge/initiate')
@with_error_logging
async def post_initiate_challenge(request: models.ChallengeInitiateRequest, background_tasks: BackgroundTasks) -> models.ChallengeInitiateResponse:
    """ Endpoint that allows a client to initiate the challenge/response secret
    negotiation protocol.
    """
    logger.info(f"C/R: Received challenge request from {request.client_name}")
    challenge = db.create_challenge_session(request.client_name)
    background_tasks.add_task(follow_up_challenge, request, challenge)
    return challenge

#app.include_router(prefix_router)
