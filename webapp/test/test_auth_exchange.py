# Sample script that acts as a client to the object server.

from fastapi import FastAPI, HTTPException, BackgroundTasks
from os import environ
from models import models
import asyncio
import requests
import time
from requests.auth import HTTPBasicAuth
from db import db

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import subprocess

logger = logging.getLogger()


GM_ADDRESS = environ['GM_ADDRESS']
CALLBACK_ADDRESS = environ['CALLBACK_ADDRESS']
CLIENT_NAME = environ['CLIENT_NAME']

STATE_DICT = {
    'challenge_secret': None,
    'id_secret': None
}

def prepopulate_db():
    """Step 0: Place a sample client in the database """
    with db.DbSession() as session:
        session.add(db.DbClient(CLIENT_NAME))
        session.commit()

async def initiate_handshake():
    """ Step 1: Initiate the handshake with the object server. Send an unauthenticated request to
    the /challenge/initiate endpoint containing a callback to this server. """
    await asyncio.sleep(3)
    challenge_addr = f"{GM_ADDRESS}/api/public/challenge/initiate"
    print(f"C/R: Initiating challenge to {challenge_addr}")
    resp = requests.post(challenge_addr, data=
        models.ChallengeInitiateRequest(client_name=CLIENT_NAME, callback_address=CALLBACK_ADDRESS).model_dump_json())
    challenge = models.ChallengeInitiateResponse.model_validate(resp.json())
    STATE_DICT['id_secret'] = challenge.id_secret
    STATE_DICT['challenge_secret'] = challenge.challenge_secret
    print(f"C/R: Received challenge: {challenge.id_secret}, {challenge.challenge_secret}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    prepopulate_db()
    asyncio.create_task(initiate_handshake())
    yield

app = FastAPI(lifespan=lifespan)

@app.post('/public/challenge/response')
async def post_initiate_challenge(request: models.ChallengeCompleteRequest, background_tasks: BackgroundTasks) -> models.ChallengeCompleteResponse:
    """ Step 2: Create a callback web address and listen for a request from the object server. Compare the 
    id token to the value retrieved in step 1, then send the challenge retrieved in step 1 and a capability
    """
    print(f"C/R: Callback initiated by {request.id_secret}")
    if request.id_secret != STATE_DICT['id_secret']:
        raise HTTPException(403, "Unexpected ID token")
    print(f"C/R: id secret matches, replying with challenge secret")
    background_tasks.add_task(verify_auth, request.capability)
    return models.ChallengeCompleteResponse(challenge_secret=STATE_DICT['challenge_secret'])

def verify_auth(capability: str):
    """ Step 3: Confirm with the object server that the auth exchange succeeded. """
    time.sleep(1)
    # Confirm that auth succeeded in previous step
    auth_addr = f"{GM_ADDRESS}/api/private/verify-auth"
    print(f"C/R: Sending an authenticated request to the Object Server at {auth_addr}")
    resp = requests.get(auth_addr, auth=HTTPBasicAuth(CLIENT_NAME, capability))
    print(f"C/R: Authenticated to Object Server as {resp.json()['whoami']}", flush=True)
