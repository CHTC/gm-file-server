from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from os import environ
from models import models
from db import db
from util.httpd_utils import add_httpd_user, RequestScopeInfo
from util.fs_utils import list_git_repos
from util.wsgi_error_logging import with_error_logging
from secrets import token_urlsafe

import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger("default")


api_prefix = environ['API_PREFIX']
app = FastAPI()

@app.get('/public')
def get_public():
    """ Sample endpoint that's publicly accessible """
    return {"message": "This is a public route!" }

@app.get('/public/git-repos')
@with_error_logging
def get_git_repos() -> list[models.RepoListing]:
    """ Get the list of git repositories available from the server """
    return list_git_repos()

@app.get('/public/client-status')
@with_error_logging
def get_client_statuses() -> list[models.ClientStatus]:
    """ Get the list of active clients to the server, and the sync status of their git repos """
    return db.get_all_client_statuses()

@app.get('/private/verify-auth')
def verify_auth(request: Request):
    """ Sanity check basic-auth gated endpoint. Used by clients to confirm that
    handshake protocol succeeded. Auth is handled at the httpd layer.
    """
    scope_info = RequestScopeInfo(request)
    return { "whoami": scope_info.user }

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
        db.activate_auth_session(
            request.client_name, challenge.challenge_secret, credentials.expires)
    else:
        logger.error(f"C/R: Callback response contains incorrect challenge secret. Ignoring")
        db.fail_auth_session(request.client_name, challenge.challenge_secret)


@app.post('/public/challenge/initiate')
@with_error_logging
async def post_initiate_challenge(request: models.ChallengeInitiateRequest, background_tasks: BackgroundTasks) -> models.ChallengeInitiateResponse:
    """ Endpoint that allows a client to initiate the challenge/response secret
    negotiation protocol.
    """
    logger.info(f"C/R: Received challenge request from {request.client_name}")
    challenge = db.create_auth_session(request.client_name)
    background_tasks.add_task(follow_up_challenge, request, challenge)
    return challenge

#app.include_router(prefix_router)
