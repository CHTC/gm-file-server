from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from db.db_schema import DbClientRepoAccess, DbClientAuthSession



class ChallengeInitiateRequest(BaseModel):
    client_name: str = Field(description="Name of the client that is requesting a challenge")
    callback_address: str = Field(description="Location to respond to with a challenge")


class ChallengeInitiateResponse(BaseModel):
    id_secret: str = Field(description="Identifier token that the server will present at the callback_address")
    challenge_secret: str = Field(description="Challenge Secret that the client must return to the server")


class ChallengeCompleteRequest(BaseModel):
    id_secret: str = Field(description="Identifier token that the server presents to the callback_address")
    capability: str = Field(description="The capability negotiated between the client and the server")
    expires: datetime = Field(description="The expiry time of the negotiated capability")

class ChallengeCompleteResponse(BaseModel):
    challenge_secret: str = Field(description="Challenge Secret that the client returns to the server")

class RepoListing(BaseModel):
    name: str = Field(description="The name of the git repository")


class ClientGitRepoStatus(BaseModel):
    repo_name: str
    access_time: datetime
    commit_hash: str

    @classmethod
    def from_db(cls, entity: DbClientRepoAccess):
        if entity is None:
            return None
        
        return ClientGitRepoStatus(
            repo_name=entity.git_repo,
            access_time=entity.access_time,
            commit_hash=entity.commit_hash
        )

class ClientAuthState(BaseModel):
    state: str
    expires: Optional[datetime]

    @classmethod
    def from_db(cls, entity: DbClientAuthSession):
        if entity is None:
            return None
        
        return ClientAuthState(
            state=entity.auth_state,
            expires=entity.expires)

class ClientStatus(BaseModel):
    client_name: str
    auth_state: Optional[ClientAuthState]
    repo_access: list[ClientGitRepoStatus]
