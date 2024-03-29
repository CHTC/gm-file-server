from fastapi import FastAPI, HTTPException
from os import environ
from models.models import *
import asyncio
import requests

import logging
from contextlib import asynccontextmanager
from secrets import token_urlsafe

logger = logging.getLogger("default")


gm_address = environ['GM_ADDRESS']
callback_address = environ['CALLBACK_ADDRESS']

STATE_DICT = {
    'challenge_secret': None,
    'id_secret': None
}

async def send_query():
    global STATE_DICT
    print("Background task created")
    await asyncio.sleep(1)
    resp = requests.post(gm_address, data=
        ChallengeInitiateRequest(client_name='test-client', callback_address=callback_address).model_dump_json())
    challenge = ChallengeInitiateResponse.model_validate(resp.json())
    STATE_DICT['id_secret'] = challenge.id_secret
    STATE_DICT['challenge_secret'] = challenge.challenge_secret
    print(f"Got challenge {challenge.id_secret}, {challenge.challenge_secret}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(send_query())
    yield

app = FastAPI(lifespan=lifespan)

@app.post('/public/challenge/response')
async def post_initiate_challenge(request: ChallengeCompleteRequest) -> ChallengeCompleteResponse:
    global STATE_DICT
    print(f"Received challenge request from {request.id_secret}")
    if request.id_secret != STATE_DICT['id_secret']:
        raise HTTPException(403, "Unexpected ID token")
    return ChallengeCompleteResponse(challenge_secret=STATE_DICT['challenge_secret'], capability=token_urlsafe(16))
