from os import environ
import requests
import time
from requests.auth import HTTPBasicAuth

import logging
from pathlib import Path
from db import db
import subprocess
from models.models import CommandQueueResponse
import pytest
from .test_util import populate_db, reset_db

logger = logging.getLogger()


GM_ADDRESS = environ['GM_ADDRESS']
CLIENT_NAME = environ['CLIENT_NAME']
TEST_CMD = "Test Command!"
TEST_PW = "TEST-PW"

@pytest.fixture(scope="module", autouse=True)
def wait_on_startup():
    time.sleep(3)

@pytest.fixture(autouse=True)
def setup_teardown():
    """Before all tests: Place a sample client in the database, then give it a password """
    populate_db()
    yield
    reset_db()

def test_read_command_queue():
    """ Enqueue a sample command for the client """
    db.enqueue_command(CLIENT_NAME, TEST_CMD, 1)

    # get the status of the server's git repository
    get_cmd_addr = f"{GM_ADDRESS}/api/private/command-queue"
    command = CommandQueueResponse.model_validate(
        requests.get(get_cmd_addr, auth=HTTPBasicAuth(CLIENT_NAME, TEST_PW)).json())
    assert command.queue_length == 1
    assert command.command == TEST_CMD
