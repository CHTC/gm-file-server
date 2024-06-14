from os import environ

import logging
from pathlib import Path
from db import db
from sqlalchemy import update, select
from datetime import datetime, timedelta
import pytest
from tempfile import NamedTemporaryFile
from .test_common import populate_db, reset_db, set_htpasswd, unset_htpasswd, GM_ADDRESS, CLIENT_NAME
from util.httpd_utils import HTTPD_PASSWD_FILE, prune_auth_file
from util.config_utils import configure_active_clients

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

# httpd_utils.py
def test_prune_auth_file():
    """ Expire the sample user's auth, then ensure the prune_auth_file job removes it"""
    db.create_auth_session(CLIENT_NAME)
    with db.DbSession() as session:
        session.execute(update(db.DbClientAuthEvent).values(auth_state='SUCCESSFUL', expires=datetime.now() - timedelta(minutes=5)))
        session.commit()
    prune_auth_file()

    # Assert that the auth file is empty after removing expired entries
    with open(HTTPD_PASSWD_FILE) as htpasswd:
        lines = htpasswd.readlines()
        assert len(lines) == 0

def test_prune_preserves_active():
    """ Ensure that the prune_auth_file job doesn't remove active auth sessions"""
    db.create_auth_session(CLIENT_NAME)
    with db.DbSession() as session:
        session.execute(update(db.DbClientAuthEvent).values(auth_state='SUCCESSFUL', expires=datetime.now() + timedelta(minutes=5)))
        session.commit()
    prune_auth_file()

    # Assert that the auth file is empty after removing expired entries
    with open(HTTPD_PASSWD_FILE) as htpasswd:
        lines = htpasswd.readlines()
        assert len(lines) == 1

# config_reader.py
TEST_CONFIGS = [
"clients: []", # zero clients
"""clients:
- name: test-client
""", # one client
"""clients:
- name: test-client
- name: test-client-2
""" # two clients
]

def test_reconcile_configs():
    temp_files = [NamedTemporaryFile() for _ in TEST_CONFIGS]

    for tmpf, cfg in zip(temp_files, TEST_CONFIGS):
        with open(tmpf.name, 'w') as f:
            f.write(cfg)

    configure_active_clients(temp_files[0].name)
    with db.DbSession() as session:
        active_clients = session.scalars(select(db.DbClient).where(db.DbClient.valid == True)).all()
        assert len(active_clients) == 0
    
    configure_active_clients(temp_files[1].name)
    with db.DbSession() as session:
        active_clients = session.scalars(select(db.DbClient).where(db.DbClient.valid == True)).all()
        assert len(active_clients) == 1
    
    configure_active_clients(temp_files[2].name)
    with db.DbSession() as session:
        active_clients = session.scalars(select(db.DbClient).where(db.DbClient.valid == True)).all()
        assert len(active_clients) == 2

    configure_active_clients(temp_files[1].name)
    with db.DbSession() as session:
        active_clients = session.scalars(select(db.DbClient).where(db.DbClient.valid == True)).all()
        assert len(active_clients) == 1
    
