from os import environ
from models import models
import asyncio
import requests
import time
from requests.auth import HTTPBasicAuth
from db import db
from util import httpd_utils

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import subprocess

logger = logging.getLogger()


GM_ADDRESS = environ['GM_ADDRESS']
CALLBACK_ADDRESS = environ['CALLBACK_ADDRESS']
CLIENT_NAME = environ['CLIENT_NAME']
TEST_PW = "TEST-PW"

STATE_DICT = {
    'challenge_secret': None,
    'id_secret': None
}

def prepopulate_db():
    """Step 0: Place a sample client in the database, then give it a password """
    with db.DbSession() as session:
        session.add(db.DbClient(CLIENT_NAME))
        session.commit()

    httpd_utils.add_httpd_user(CLIENT_NAME, TEST_PW)


def do_auth_git_pull():
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
    report_access_addr = f"{GM_ADDRESS}/api/private/log-repo-access"
    repo = requests.get(list_repo_addr).json()
    subprocess.call(['git','clone',f'{GM_ADDRESS}/git/{repo["name"]}'])
    # Report back to the server that the pull was successful
    requests.post(report_access_addr, json=repo, auth=HTTPBasicAuth(CLIENT_NAME, TEST_PW))
    print(f"Git pull succeeded")

def check_status_report():
    """ Step 2: Confirm via the API that the git pull was logged in the DB """
    status_addr = f"{GM_ADDRESS}/api/public/client-status"

    status = requests.get(status_addr).json()
    print(status)

if __name__ == '__main__':
    time.sleep(5)
    prepopulate_db()
    do_auth_git_pull()
    check_status_report()
