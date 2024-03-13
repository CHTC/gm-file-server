import sys
import os
from logging.config import dictConfig

HERE = os.path.dirname(__file__)
sys.path.append(HERE)

logdir = "/var/log/"
dictConfig({
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] %(module)s:%(lineno)s ~ %(message)s",
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "default",
            "filename": os.path.join(logdir, "wsgi.log"),
            "maxBytes": 10485760,
            "backupCount": 5
        }
    },
    "root": {"level": "DEBUG", "handlers": ["file"]}
})

from app import app
from a2wsgi import ASGIMiddleware


application = ASGIMiddleware(app.app)
