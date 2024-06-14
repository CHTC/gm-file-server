from os import environ
from pydantic import BaseModel
from db import db
import yaml

CONFIG_FILE = f"{environ.get('CONFIG_DIR')}/config.yaml"


class ConfigClient(BaseModel):
    name: str

class GlideinManagerConfig(BaseModel):
    clients: list[ConfigClient]


def parse_config(config_file:str = CONFIG_FILE) -> GlideinManagerConfig:
    with open(config_file) as cfg:
        return GlideinManagerConfig.model_validate(yaml.load(cfg.read(), Loader=yaml.FullLoader))


def configure_active_clients(config_file:str = CONFIG_FILE):
    """ Reconcile the list of active clients in the database with that provided in the config file.
    Mark any clients in the db but not the config file as invalid to prevent them from authenticating,
    then add any clients that are in the config but not the database.
    """
    active_clients = parse_config(config_file).clients
    db.reconcile_active_clients([a.name for a in active_clients])
