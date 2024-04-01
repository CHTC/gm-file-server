# Sample script that works 
from fastapi import FastAPI, HTTPException, BackgroundTasks
from os import environ
from models.models import *
import asyncio
import requests
import time
from requests.auth import HTTPBasicAuth

import logging
from contextlib import asynccontextmanager
from secrets import token_urlsafe

logger = logging.getLogger("default")


GM_ADDRESS = environ['GM_ADDRESS']
CALLBACK_ADDRESS = environ['CALLBACK_ADDRESS']
CLIENT_NAME = 'test-client'

STATE_DICT = {
    'challenge_secret': None,
    'id_secret': None
}

async def initiate_handshake():
    """ Step 1: Initiate the handshake with the object server. Send an unauthenticated request to
    the /challenge/initiate endpoint containing a callback to this server. """
    await asyncio.sleep(1)
    challenge_addr = f"{GM_ADDRESS}/api/public/challenge/initiate"
    print(f"C/R: Initiating challenge to {challenge_addr}")
    resp = requests.post(challenge_addr, data=
        ChallengeInitiateRequest(client_name=CLIENT_NAME, callback_address=CALLBACK_ADDRESS).model_dump_json())
    challenge = ChallengeInitiateResponse.model_validate(resp.json())
    STATE_DICT['id_secret'] = challenge.id_secret
    STATE_DICT['challenge_secret'] = challenge.challenge_secret
    print(f"C/R: Received challenge: {challenge.id_secret}, {challenge.challenge_secret}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(initiate_handshake())
    yield

app = FastAPI(lifespan=lifespan)

@app.post('/public/challenge/response')
async def post_initiate_challenge(request: ChallengeCompleteRequest, background_tasks: BackgroundTasks) -> ChallengeCompleteResponse:
    """ Step 2: Create a callback web address and listen for a request from the object server. Compare the 
    id token to the value retrieved in step 1, then send the challenge retrieved in step 1 and a capability
    """
    print(f"C/R: Callback initiated by {request.id_secret}")
    if request.id_secret != STATE_DICT['id_secret']:
        raise HTTPException(403, "Unexpected ID token")
    capability = token_urlsafe(16)
    print(f"C/R: id secret matches, replying with capability")
    background_tasks.add_task(test_auth, capability)
    return ChallengeCompleteResponse(challenge_secret=STATE_DICT['challenge_secret'], capability=capability)

def test_auth(capability: str):
    """ Step 3: Submit an authenticated request to the object server. """
    time.sleep(1)
    auth_addr = f"{GM_ADDRESS}/api/private"
    print(f"C/R: Sending an authenticated request to the Object Server at {auth_addr}")
    resp = requests.get(auth_addr, auth=HTTPBasicAuth(CLIENT_NAME, capability))
    print(resp.status_code)
