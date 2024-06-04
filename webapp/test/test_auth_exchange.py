
# Sample script that acts as a client to the object server.

from fastapi import FastAPI, HTTPException, BackgroundTasks
from os import environ
from models import models
import requests
import time
from requests.auth import HTTPBasicAuth
from db import db

import logging
from multiprocessing import Process, Queue
import pytest
import uvicorn
from .test_util import populate_db, reset_db, unset_htpasswd, GM_ADDRESS, CALLBACK_ADDRESS, CLIENT_NAME, CLIENT_ID

logger = logging.getLogger()


#
# Subprocess: A FastAPI app that listens for the GM-initiated request during the auth exchange handshake
#

STATE_DICT = {
    'challenge_secret': None,
    'id_secret': None
}

# Queue for sending messages from pytest to fastapi app
fastapi_queue = Queue()
# Queue for sending messages from fastapi to pytest
pytest_queue = Queue()

app = FastAPI()

@app.post('/public/challenge/response')
def post_initiate_challenge(request: models.ChallengeCompleteRequest) -> models.ChallengeCompleteResponse:
    """ Step 2: Create a callback web address and listen for a request from the object server. Compare the 
    id token to the value retrieved in step 1, then send the challenge retrieved in step 1 back
    """
    id_secret = fastapi_queue.get()
    challenge_secret = fastapi_queue.get()
    print(f"C/R: Callback initiated by {request.id_secret}")
    if request.id_secret != id_secret:
        raise HTTPException(403, "Unexpected ID token")
    print(f"C/R: id secret matches, replying with challenge secret")
    pytest_queue.put(request.capability)
    return models.ChallengeCompleteResponse(challenge_secret=challenge_secret)

#
# Main process: A pytest that initiates the handshake request and then validates the ability to submit
# an authenticated request after the handshake completes
#

@pytest.fixture(autouse=True)
def setup_teardown():
    """ Test setup/teardown: Create a client with no setup, then delete that client """
    populate_db()
    # Make sure no password entry exists before the test
    unset_htpasswd()
    yield
    reset_db()
    unset_htpasswd()

def initiate_handshake():
    """ Step 1: Initiate the handshake with the object server. Send an unauthenticated request to
    the /challenge/initiate endpoint containing a callback to this server. """
    challenge_addr = f"{GM_ADDRESS}/api/public/challenge/initiate"
    print(f"C/R: Initiating challenge to {challenge_addr}")
    resp = requests.post(challenge_addr, data=
        models.ChallengeInitiateRequest(client_name=CLIENT_NAME, callback_address=CALLBACK_ADDRESS).model_dump_json())
    challenge = models.ChallengeInitiateResponse.model_validate(resp.json())
    fastapi_queue.put(challenge.id_secret)
    fastapi_queue.put(challenge.challenge_secret)
    print(f"C/R: Received challenge: {challenge.id_secret}, {challenge.challenge_secret}")


def verify_auth(capability: str):
    """ Step 3: Confirm with the object server that the auth exchange succeeded. """
    # Confirm that auth succeeded in previous step
    auth_addr = f"{GM_ADDRESS}/api/private/verify-auth"
    print(f"C/R: Sending an authenticated request to the Object Server at {auth_addr}")
    resp = requests.get(auth_addr, auth=HTTPBasicAuth(CLIENT_NAME, capability))
    assert resp.status_code == 200
    user = resp.json()['whoami']
    assert user == CLIENT_NAME
    print(f"C/R: Authenticated to Object Server as {user}", flush=True)

def test_auth_exchange():
    proc = Process(target=uvicorn.run, args=(app,), kwargs={'host':'0.0.0.0','port':8089})
    proc.start()
    time.sleep(1) # Wait for the fastapi app to start
    initiate_handshake()
    capability = pytest_queue.get()
    time.sleep(1) # Wait for the fastapi app to finish its response
    proc.terminate()

    verify_auth(capability)

    with db.DbSession() as session:
        auth_events = session.scalars(db.select(db.DbClientAuthEvent)).all()
        assert len(auth_events) == 1
        assert auth_events[0].client_id == CLIENT_ID
        assert auth_events[0].auth_state == db.DbAuthState.SUCCESSFUL
