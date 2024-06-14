from subprocess import Popen, PIPE, run
from os import environ
from fastapi import Request
from db import db
from models.models import AuthStateQuery

import logging
logger = logging.getLogger()

HTTPD_PASSWD_FILE = f"{environ['DATA_DIR']}/.htpasswd"

def add_httpd_user(username:str, password:str):
    """ Add a new user + password to the httpd password file """
    httpd_call = Popen(['htpasswd', '-i', HTTPD_PASSWD_FILE, username], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = httpd_call.communicate(input=password.encode())

    if httpd_call.returncode:
        raise RuntimeError(f"htpasswd -i returned nonzero exit code: {httpd_call.returncode}: {err}")

def remove_httpd_user(username:str):
    """ Remove a user's current password from the httpd password file """
    httpd_code = run(['htpasswd', '-D', HTTPD_PASSWD_FILE, username])
    if httpd_code.returncode:
        raise RuntimeError(f"htpasswd -D returned nonzero exit code: {httpd_code}")

def prune_auth_file():
    """ Remove all users' whose auth session has expired from the httpd password file """
    active_clients = db.get_client_status_report(auth_state=AuthStateQuery.SUCCESSFUL)
    active_client_names = [cl.client_name for cl in active_clients]
    
    # Read the whole htpasswd file line by line
    with open(HTTPD_PASSWD_FILE, 'r') as htpasswd:
        auth_lines = htpasswd.readlines()

    # Re-write the file, including only the clients who are currently authenticated
    active_auth_lines = [l for l in auth_lines if any(l.startswith(f"{c}:") for c in active_client_names)]
    with open(HTTPD_PASSWD_FILE, 'w') as htpasswd:
        htpasswd.writelines(active_auth_lines)



    
