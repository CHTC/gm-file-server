from os import environ
from pathlib import Path
from db import db
import base64

ON_DISK_SECRETS = Path(environ.get("SECRETS_DIR"))
LOCAL_SECRET_SOURCE = 'localhost'

def get_secret_value(secret: db.DbSecretSource) -> str:
    """ Given a secret source from the DB, return the base64-encoded value of that Secret
    TODO: support cases besides reading a secret stored on disk
    """
    if secret.source == LOCAL_SECRET_SOURCE:
        with open(ON_DISK_SECRETS / secret.name, 'rb') as secf:
            return base64.b64encode(secf.read())


def configure_local_secrets():
    """ Reconcile the list of secrets stored on disk with the list of secret
    sourecs in the database. Mark any secrets that are present in the db but
    absent from disk as invalid. """
    active_local_secrets = [f.name for f in ON_DISK_SECRETS.iterdir() if f.is_file()]
    db.reconcile_local_secrets(active_local_secrets)
