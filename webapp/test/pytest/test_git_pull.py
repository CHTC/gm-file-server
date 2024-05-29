from os import environ
import requests
import time

import logging
from pathlib import Path
import subprocess
import pytest
from .test_util import populate_db, reset_db, GM_ADDRESS, CLIENT_NAME, TEST_PW, TEST_AUTH

logger = logging.getLogger()


@pytest.fixture(scope="module", autouse=True)
def wait_on_startup():
    time.sleep(3)

@pytest.fixture(autouse=True)
def setup_teardown():
    """Before all tests: Place a sample client in the database, then give it a password """
    populate_db()
    yield
    reset_db()

def test_auth_git_pull():
    """ Step 1: Submit an authenticated git clone request to the object server. """
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
    list_repo_addr = f"{GM_ADDRESS}/api/public/repo-status"
    repo = requests.get(list_repo_addr).json()
    subprocess.call(['git','clone',f'{GM_ADDRESS}/git/{repo["name"]}'])
    # Pass iff subprocess returns 200
    # Report back to the server that the pull was successful

def test_status_report():
    """ Step 2: Confirm via the API that the git pull was logged in the DB """
    list_repo_addr = f"{GM_ADDRESS}/api/public/repo-status"
    report_access_addr = f"{GM_ADDRESS}/api/private/log-repo-access"
    repo = requests.get(list_repo_addr).json()
    requests.post(report_access_addr, json=repo, auth=TEST_AUTH)
    status_addr = f"{GM_ADDRESS}/api/public/client-status"

    status = requests.get(status_addr).json()
    print(status)

