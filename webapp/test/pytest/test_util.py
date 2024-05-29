from os import environ
from db import db
from requests.auth import HTTPBasicAuth

from util import httpd_utils
from sqlalchemy import delete

import logging

GM_ADDRESS = environ['GM_ADDRESS']
CALLBACK_ADDRESS = environ['CALLBACK_ADDRESS']
CLIENT_NAME = environ['CLIENT_NAME']
TEST_PW = "TEST-PW"
TEST_AUTH=HTTPBasicAuth(CLIENT_NAME, TEST_PW)

def populate_db():
    """Before all tests: Place a sample client in the database, then give it a password """
    with db.DbSession() as session:
        session.add(db.DbClient(CLIENT_NAME))
        session.commit()

    httpd_utils.add_httpd_user(CLIENT_NAME, TEST_PW)


def reset_db():
    """ After all tests: Empty the database"""
    TABLES = [
        db.DbCommandQueueEntry,
        db.DbClientCommitAccess, 
        db.DbClientAuthChallenge, 
        db.DbClientAuthEvent, 
        db.DbClient, 
        db.DbGitCommit
    ]
    with db.DbSession() as session:
        for table in TABLES:
            session.execute(delete(table))
        session.commit()

    httpd_utils.remove_httpd_user(CLIENT_NAME)

