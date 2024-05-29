from os import environ
import requests
import time
from requests.auth import HTTPBasicAuth

import logging
from pathlib import Path
from db import db
import subprocess
from models.models import CommandQueueResponse
from datetime import datetime, timedelta
import pytest
from .test_util import populate_db, reset_db, set_htpasswd, unset_htpasswd, GM_ADDRESS, CLIENT_NAME, TEST_AUTH

logger = logging.getLogger()


GM_ADDRESS = environ['GM_ADDRESS']
CLIENT_NAME = environ['CLIENT_NAME']
TEST_CMD = "Test Command!"
TEST_PW = "TEST-PW"

GET_CMD_ADDR = f"{GM_ADDRESS}/api/private/command-queue"

@pytest.fixture(autouse=True)
def setup_teardown():
    """Before all tests: Place a sample client in the database, then give it a password """
    populate_db()
    set_htpasswd()
    yield
    reset_db()
    unset_htpasswd()

def test_read_command_queue():
    """ Enqueue a sample command for the client """
    db.enqueue_command(CLIENT_NAME, TEST_CMD, 1)

    # get the status of the client's command queue
    command = CommandQueueResponse.model_validate(
        requests.get(GET_CMD_ADDR, auth=TEST_AUTH).json())
    assert command.queue_length == 1
    assert command.command == TEST_CMD

def test_read_multiple_commands():
    """ Enqueue multiple commands for the client, then ensure the first is read """
    queue_length = 3
    for i in range(queue_length):
        db.enqueue_command(CLIENT_NAME, f"{TEST_CMD} {i}", 1, datetime.now() + timedelta(minutes=i))

    # get the status of the client's command queue
    command = CommandQueueResponse.model_validate(
        requests.get(GET_CMD_ADDR, auth=HTTPBasicAuth(CLIENT_NAME, TEST_PW)).json())
    assert command.queue_length == queue_length
    assert command.command == f"{TEST_CMD} {0}"


def test_dequeue_command():
    """ Enqueue multiple commands for the client, then ensure the first is read """
    queue_length = 3
    for i in range(queue_length):
        db.enqueue_command(CLIENT_NAME, f"{TEST_CMD} {i}", 1, datetime.now() + timedelta(minutes=i))

    # get the status of the client's command queue
    command = CommandQueueResponse.model_validate(
        requests.get(GET_CMD_ADDR, auth=HTTPBasicAuth(CLIENT_NAME, TEST_PW)).json())
    assert command.queue_length == queue_length
    assert command.command == f"{TEST_CMD} {0}"
