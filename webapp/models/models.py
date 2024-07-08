from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime
from db.db_schema import DbClientCommitAccess, DbClientAuthEvent, DbClientStateView, DbCommandStatus, DbSecretSource



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
    name: Optional[str] = Field(description="Name of the repository on disk")
    upstream: Optional[str] = Field(description="URL of the upstream for the repository")
    commit_hash: str = Field(description="Hash of the latest commit for the repository")


class ClientAccessStatus(BaseModel):
    access_time: datetime
    commit_hash: str

    @classmethod
    def from_db(cls, entity: DbClientCommitAccess):
        if entity is None:
            return None
        
        return ClientAccessStatus(
            access_time=entity.access_time,
            commit_hash=entity.commit_hash
        )

class ClientAuthState(BaseModel):
    state: str
    initiated: Optional[datetime]
    expires: Optional[datetime]

    @classmethod
    def from_db(cls, entity: DbClientAuthEvent):
        if entity is None:
            return None
        
        return ClientAuthState(
            state=entity.auth_state,
            initiated=entity.initiated,
            expires=entity.expires)

class ClientStatus(BaseModel):
    client_name: str
    auth_state: Optional[ClientAuthState]
    repo_access: Optional[ClientAccessStatus]

    @classmethod
    def from_db(cls, entity: DbClientStateView):
        return ClientStatus(
            client_name=entity.name,
            auth_state=ClientAuthState(
                state=entity.auth_state,
                initiated=entity.initiated,
                expires=entity.expires) if entity.auth_state else None,
            repo_access=ClientAccessStatus(
                access_time=entity.access_time,
                commit_hash=entity.commit_hash) if entity.commit_hash else None)



class SecretVersion(BaseModel):
    """ TODO this might just be a JWT in the future """
    secret: str
    iat: datetime
    exp: datetime


class AuthStateQuery(Enum):
    """ Query parameter enum for  """
    # Auth states that are recorded in the DB
    PENDING = 'PENDING'
    SUCCESSFUL = 'SUCCESSFUL'
    FAILED = 'FAILED'
    # A successful auth entry whose expiration has passed
    EXPIRED = 'EXPIRED'
    # Do not filter on auth state in the query
    ANY = 'ANY'
    # Has not yet attempted to authenticate
    NONE = 'NONE'


class CommandQueueResponse(BaseModel):
    """ Response containing the queue length of a client's command queue,
    and the next command in the queue if present
    """
    queue_length: int
    command: Optional[str]

class CommandQueueCompletionRequest(BaseModel):
    """ Request sent by a client indicating the completion status of the 
    first command in its queue """
    status: DbCommandStatus

class SecretSource(BaseModel):
    """ Listing for a secret source provided by the GMOS to clients"""
    secret_name: str
    secret_source: str
    secret_version: str

    @classmethod
    def from_db(cls, entity: DbSecretSource):
        return SecretSource(secret_name=entity.name, secret_source=entity.source, secret_version=entity.version)

class SecretValue(BaseModel):
    """ The active value of a secret version """
    secret_name: str
    secret_value: str
