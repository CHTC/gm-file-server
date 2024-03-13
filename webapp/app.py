from fastapi import FastAPI, APIRouter
from os import environ


api_prefix = environ['API_PREFIX']
app = FastAPI()
#prefix_router = APIRouter(prefix=api_prefix)


@app.get('/public')
def get_public():
    return {"message": "This is a public route!" }

@app.get('/private')
def get_public():
    return {"message": "This is a secret route!" }

#app.include_router(prefix_router)
