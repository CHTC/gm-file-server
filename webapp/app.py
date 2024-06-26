from fastapi import FastAPI, BackgroundTasks, Request, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from typing import Annotated
from models import models
from db import db
from util import git_utils
from sys import stdout
from util.httpd_utils import add_httpd_user
from secrets import token_urlsafe
from scheduler import init_scheduler
from typing import Optional, Literal

from contextlib import asynccontextmanager

import logging
import requests
from datetime import datetime, timedelta

logging.basicConfig(stream=stdout, level=logging.INFO)
logger = logging.getLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    git_utils.trust_upstream_host()
    git_utils.clone_repo()
    init_scheduler()
    yield

app = FastAPI(lifespan=lifespan)

security = HTTPBasic()

@app.get('/public')
def get_public():
    """ Sample endpoint that's publicly accessible """
    return {"message": "This is a public route!" }

@app.get('/public/repo-status')
def get_repo_status() -> models.RepoListing:
    """ Return the name and latest commit of the git repo """
    return git_utils.get_repo_status()

@app.get('/public/client-status')
def get_client_statuses(
        report_time: Optional[datetime] = None, 
        auth_state: Optional[models.AuthStateQuery] = models.AuthStateQuery.ANY,
        latest_commit: Optional[bool] = None) -> list[models.ClientStatus]:
    """ Get the list of active clients to the server, and the sync status of their git repos """
    return db.get_client_status_report(report_time, auth_state, latest_commit)

@app.get('/private/verify-auth')
def verify_auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """ Sanity check basic-auth gated endpoint. Used by clients to confirm that
    handshake protocol succeeded. Auth is handled at the httpd layer.
    """
    return { "whoami": credentials.username }

@app.post('/private/log-repo-access')
def log_repo_access(repo: models.RepoListing, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """ Endpoints for clients to report that they successfully pulled a git repo. """
    db.log_client_repo_access(credentials.username, repo.commit_hash)
    return { "status": "acknowledged" }

@app.get('/private/command-queue')
def get_next_command(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> models.CommandQueueResponse:
    """ Get the next command in the authenticated client's command queue """
    return db.get_next_command(credentials.username)

@app.post('/private/command-queue')
def complete_command(
        completion_status: models.CommandQueueCompletionRequest,
        credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> models.CommandQueueResponse:
    """ Mark the head of the authenticated client's command queue as complete """
    return db.dequeue_command(credentials.username, completion_status.status)

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
async def post_initiate_challenge(request: models.ChallengeInitiateRequest, background_tasks: BackgroundTasks) -> models.ChallengeInitiateResponse:
    """ Endpoint that allows a client to initiate the challenge/response secret
    negotiation protocol.
    """
    logger.info(f"C/R: Received challenge request from {request.client_name}")
    challenge = db.create_auth_session(request.client_name)
    background_tasks.add_task(follow_up_challenge, request, challenge)
    return challenge
