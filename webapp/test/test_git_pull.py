import os
import requests
import time

import logging
from pathlib import Path
import subprocess
import pytest
from db import db
from models.models import ClientStatus
from datetime import datetime, timedelta
from .test_util import populate_db, reset_db, set_htpasswd, unset_htpasswd, GM_ADDRESS, CLIENT_NAME, TEST_PW, TEST_AUTH, CLIENT_ID

LIST_REPO_ADDR = f"{GM_ADDRESS}/api/public/repo-status"
STATUS_ADDR = f"{GM_ADDRESS}/api/public/client-status"

logger = logging.getLogger()


@pytest.fixture(autouse=True)
def setup_teardown():
    """ Test setup/teardown: Create a client and give it a password, then delete that client """
    populate_db()
    set_htpasswd()
    yield
    reset_db()
    unset_htpasswd()

def test_auth_git_pull():
    """ Submit an authenticated git clone request to the object server. """
    #user: apache
    # cache git credentials
    credentials_file = Path.home() / '.git-credentials'
    auth_git_url = GM_ADDRESS.replace('http://',f'http://{CLIENT_NAME}:{TEST_PW}@')
    with open(credentials_file, 'w') as f:
        f.write(auth_git_url)
    
    # set git to use cached credentials
    print(f"Performing git pull")
    subprocess.call(['git', 'config', '--global', 'credential.helper', 'store'])

    # get the status of the server's git repository
    repo = requests.get(LIST_REPO_ADDR).json()
    result = subprocess.call(['git','clone',f'{GM_ADDRESS}/git/{repo["name"]}'])
    assert result == 0
    
def test_no_auth_git_pull():
    """ Submit an unauthenticated git clone request to the object server, assert it fails. """
    credentials_file = Path.home() / '.git-credentials'
    if credentials_file.exists():
        credentials_file.unlink()
    
    # set git to use cached credentials
    print(f"Performing git pull")
    # get the status of the server's git repository
    repo = requests.get(LIST_REPO_ADDR).json()
    result = subprocess.call(['git','clone',f'{GM_ADDRESS}/git/{repo["name"]}'])
    assert result != 0

def test_status_report_db():
    """ Confirm via DB query that the git pull was logged in the DB """
    list_repo_addr = f"{GM_ADDRESS}/api/public/repo-status"
    report_access_addr = f"{GM_ADDRESS}/api/private/log-repo-access"
    repo = requests.get(list_repo_addr).json()
    requests.post(report_access_addr, json=repo, auth=TEST_AUTH)
    with db.DbSession() as session:
        reports = session.scalars(db.select(db.DbClientCommitAccess)
            .where(db.DbClientCommitAccess.client_id == CLIENT_ID)).all()

        assert len(reports) == 1
        assert reports[0].commit_hash == repo['commit_hash']
        assert abs(datetime.now() - reports[0].access_time) < timedelta(seconds=5)


def test_status_report_endpoint():
    """ Confirm via the API that the git pull was logged in the DB """
    list_repo_addr = f"{GM_ADDRESS}/api/public/repo-status"
    report_access_addr = f"{GM_ADDRESS}/api/private/log-repo-access"
    repo = requests.get(list_repo_addr).json()
    requests.post(report_access_addr, json=repo, auth=TEST_AUTH)

    status = requests.get(STATUS_ADDR).json()
    assert len(status) == 1
    data = ClientStatus.model_validate(status[0])
    assert data.client_name == CLIENT_NAME
    assert data.repo_access.commit_hash == repo['commit_hash']
    assert abs(datetime.now() - data.repo_access.access_time) < timedelta(seconds=5)

