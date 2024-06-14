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
from .test_common import populate_db, reset_db, set_htpasswd, unset_htpasswd, GM_ADDRESS, CLIENT_NAME, TEST_AUTH

logger = logging.getLogger()


CMD_QUEUE_ADDR = f"{GM_ADDRESS}/api/private/command-queue"
TEST_CMD = "Test Command!"
SUCCESS_BODY = {'status': db.DbCommandStatus.SUCCESSFUL}

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
        requests.get(CMD_QUEUE_ADDR, auth=TEST_AUTH).json())
    assert command.queue_length == 1
    assert command.command == TEST_CMD

def test_read_multiple_commands():
    """ Enqueue multiple commands for the client, then ensure the first is read """
    queue_length = 2
    for i in range(queue_length):
        db.enqueue_command(CLIENT_NAME, f"{TEST_CMD} {i}", 1, datetime.now() + timedelta(minutes=i))

    # get the status of the client's command queue
    command = CommandQueueResponse.model_validate(
        requests.get(CMD_QUEUE_ADDR, auth=TEST_AUTH).json())
    assert command.queue_length == queue_length
    assert command.command == f"{TEST_CMD} {0}"

def test_command_priority():
    """ Enqueue multiple commands for the client, then ensure the highest priority is read """
    queue_length = 2
    for i in range(queue_length):
        db.enqueue_command(CLIENT_NAME, f"{TEST_CMD} {i}", i, datetime.now() + timedelta(minutes=i))

    # get the status of the client's command queue
    command = CommandQueueResponse.model_validate(
        requests.get(CMD_QUEUE_ADDR, auth=TEST_AUTH).json())
    assert command.queue_length == queue_length
    assert command.command == f"{TEST_CMD} {queue_length - 1}"

def test_dequeue_command():
    """ Enqueue a command for the client, then dequeue it """
    db.enqueue_command(CLIENT_NAME, TEST_CMD)

    requests.get(CMD_QUEUE_ADDR, auth=TEST_AUTH)
    success_body = {'status': db.DbCommandStatus.SUCCESSFUL}
    next_command = CommandQueueResponse.model_validate(
        requests.post(CMD_QUEUE_ADDR, auth=TEST_AUTH, json=success_body).json())
    assert next_command.queue_length == 0

    next_cmd = CommandQueueResponse.model_validate(
        requests.get(CMD_QUEUE_ADDR, auth=TEST_AUTH).json())
    assert next_cmd.queue_length == 0
    assert next_cmd.command is None

def test_dequeue_commands():
    """ Enqueue several commands for the client, then dequeue them in order """
    queue_length = 3
    for i in range(queue_length):
        db.enqueue_command(CLIENT_NAME, f"{TEST_CMD} {i}", 1, datetime.now() + timedelta(minutes=i))

    for i in range(queue_length):
        current_cmd = CommandQueueResponse.model_validate(
            requests.get(CMD_QUEUE_ADDR, auth=TEST_AUTH).json())
        assert current_cmd.queue_length == queue_length - i
        assert current_cmd.command == f"{TEST_CMD} {i}"
        CommandQueueResponse.model_validate(
            requests.post(CMD_QUEUE_ADDR, auth=TEST_AUTH, json=SUCCESS_BODY).json())

def test_dequeue_before_read():
    """ Ensure that a command can't be marked as complete before it's been read """
    db.enqueue_command(CLIENT_NAME, TEST_CMD, 1)

    # get the status of the client's command queue
    resp = requests.post(CMD_QUEUE_ADDR, auth=TEST_AUTH, json=SUCCESS_BODY)
    assert resp.status_code >= 400

def test_completion_states():
    """ Ensure that a command can only be marked as 'SUCCESSFUL' or 'FAILED' by a client"""
    db.enqueue_command(CLIENT_NAME, TEST_CMD, 1)

    for cmd_status in [db.DbCommandStatus.PENDING, db.DbCommandStatus.IN_PROGRESS]:
        resp = requests.post(CMD_QUEUE_ADDR, auth=TEST_AUTH, json={'status':cmd_status})
        assert resp.status_code >= 400
