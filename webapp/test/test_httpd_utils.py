from os import environ

import logging
from pathlib import Path
from db import db
from sqlalchemy import update
from datetime import datetime, timedelta
import pytest
from .test_util import populate_db, reset_db, set_htpasswd, unset_htpasswd, GM_ADDRESS
from util.httpd_utils import HTTPD_PASSWD_FILE, prune_auth_file

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

def test_prune_auth_file():
    """ Expire the sample user's auth, then ensure the prune_auth_file job removes it"""
    with db.DbSession() as session:
        session.execute(update(db.DbClientAuthEvent).values(expires=datetime.now() - timedelta(minutes=5)))
        session.commit()
    prune_auth_file()

    # Assert that the auth file is empty after removing expired entries
    with open(HTTPD_PASSWD_FILE) as htpasswd:
        lines = htpasswd.readlines()
        assert len(lines) == 0

def test_prune_preserves_active():
    """ Ensure that the prune_auth_file job doesn't remove active auth sessions"""
    prune_auth_file()

    # Assert that the auth file is empty after removing expired entries
    with open(HTTPD_PASSWD_FILE) as htpasswd:
        lines = htpasswd.readlines()
        assert len(lines) == 1
