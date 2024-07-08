from os import environ
import requests

import logging
from models.models import SecretSource, SecretValue
import pytest
from .test_common import populate_db, reset_db, set_htpasswd, unset_htpasswd, GM_ADDRESS, CLIENT_NAME, TEST_AUTH
import base64 

logger = logging.getLogger()


SECRETS_ADDR = f"{GM_ADDRESS}/api/private/secrets"

EXPECTED_SECRET_NAME  = "sample-secret.txt"
EXPECTED_SECRET_VALUE =  "Hello, secret!\n"
LOCAL_SECRET_SOURCE = "localhost"

@pytest.fixture(autouse=True)
def setup_teardown():
    """Before all tests: Place a sample client in the database, then give it a password """
    populate_db()
    set_htpasswd()
    yield
    reset_db()
    unset_htpasswd()

def test_read_secrets_list():
    """ Read the list of secrets """
    # get the status of the client's command queue
    secrets_list = requests.get(SECRETS_ADDR, auth=TEST_AUTH).json()
    assert len(secrets_list) == 1

    secret_source = SecretSource.model_validate(secrets_list[0])
    assert secret_source.secret_source == LOCAL_SECRET_SOURCE
    assert secret_source.secret_name == EXPECTED_SECRET_NAME

def test_read_secrets_value():
    """ Read a specfic secret value """
    # get the status of the client's command queue
    secret_value = SecretValue.model_validate(
        requests.get(f"{SECRETS_ADDR}/{EXPECTED_SECRET_NAME}", auth=TEST_AUTH).json())

    assert secret_value.secret_name == EXPECTED_SECRET_NAME
    assert base64.b64decode(secret_value.secret_value).decode() == EXPECTED_SECRET_VALUE
