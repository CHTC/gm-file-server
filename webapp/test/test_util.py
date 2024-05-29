from os import environ
from db import db, db_schema
from requests.auth import HTTPBasicAuth

from util import httpd_utils
from sqlalchemy import delete

import logging

GM_ADDRESS = environ['GM_ADDRESS']
CALLBACK_ADDRESS = environ['CALLBACK_ADDRESS']
CLIENT_NAME = environ['CLIENT_NAME']
CLIENT_ID = db_schema._gen_uuid()
TEST_PW = "TEST-PW"
TEST_AUTH=HTTPBasicAuth(CLIENT_NAME, TEST_PW)

def set_htpasswd():
    httpd_utils.add_httpd_user(CLIENT_NAME, TEST_PW)

def unset_htpasswd():
    httpd_utils.remove_httpd_user(CLIENT_NAME)

def populate_db():
    """Before all tests: Place a sample client in the database, then give it a password """
    with db.DbSession() as session:
        client = db.DbClient(CLIENT_NAME)
        client.id = CLIENT_ID
        session.add(client)
        session.commit()

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
