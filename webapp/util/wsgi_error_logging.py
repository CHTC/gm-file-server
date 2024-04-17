from fastapi import HTTPException
from os import environ

import logging
from inspect import iscoroutinefunction
from functools import wraps

logger = logging.getLogger()


def _sync_wrapper(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        try:
            return func(*args,**kwargs)
        except HTTPException as e:
            logger.error(f"{e}")
            raise e
        except Exception as e:
            logger.error(f"{e}", e)
            raise HTTPException(500, f"{e}")
    return wrapper

def _async_wrapper(func):
    @wraps(func)
    async def wrapper(*args,**kwargs):
        try:
            return await func(*args,**kwargs)
        except HTTPException as e:
            logger.error(f"{e}")
            raise e
        except Exception as e:
            logger.error(f"{e}", e)
            raise HTTPException(500, f"{e}")
    return wrapper

# TODO a more elegant solution
# hack to deal with apache not logging fastAPI's exceptions by default
def with_error_logging(func):
    if iscoroutinefunction(func):
        return _async_wrapper(func)
    else:
        return _sync_wrapper(func)
