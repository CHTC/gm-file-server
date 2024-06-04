from subprocess import Popen, PIPE, run
from os import environ
from fastapi import Request

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
