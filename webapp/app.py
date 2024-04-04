from fastapi import FastAPI, BackgroundTasks, HTTPException
from os import environ
from models import models
from db import db
from util.httpd_utils import add_httpd_user
from util.fs_utils import list_git_repos
from util.wsgi_error_logging import with_error_logging

import logging
import requests
from contextlib import contextmanager

logger = logging.getLogger("default")


api_prefix = environ['API_PREFIX']
app = FastAPI()

@app.get('/public')
def get_public():
    """ Sample endpoint that's publicly accessible """
    return {"message": "This is a public route!" }

@app.get('/public/git-repos')
def get_git_repos() -> list[RepoListing]:
    """ Get the list of git repositories available from the server """
    return list_git_repos()

@with_error_logging
def follow_up_challenge(request: models.ChallengeInitiateRequest, challenge: models.ChallengeInitiateResponse):
    """ Background task that follows up on a challenge initiated by a client. """
    logger.info(f"C/R: Sending callback to {request.callback_address}")
    resp = requests.post(request.callback_address, data=models.ChallengeCompleteRequest(id_secret=challenge.id_secret).model_dump_json())
    completed_challenge = models.ChallengeCompleteResponse.model_validate(resp.json())
    if completed_challenge.challenge_secret == challenge.challenge_secret:
        logger.info(f"C/R: Callback response contains correct challenge secret")
        add_httpd_user(request.client_name, completed_challenge.capability)
        db.complete_challenge_session(request.client_name, completed_challenge.challenge_secret)
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
