from fastapi import FastAPI, BackgroundTasks, HTTPException
from os import environ

import logging
import requests
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger("default")


# TODO a more elegant solution
# hack to deal with apache not logging fastAPI's exceptions by default
def with_error_logging(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        try:
            return func(*args,**kwargs)
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"{e}", e)
            raise HTTPException(500, f"{e}")
    return wrapper

def with_async_error_logging(func):
    @wraps(func)
    async def wrapper(*args,**kwargs):
        try:
            return await func(*args,**kwargs)
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"{e}", e)
            raise HTTPException(500, f"{e}")
    return wrapper
