from pydantic import BaseModel, Field



class ChallengeInitiateRequest(BaseModel):
    client_name: str = Field(description="Name of the client that is requesting a challenge")
    callback_address: str = Field(description="Location to respond to with a challenge")


class ChallengeInitiateResponse(BaseModel):
    id_secret: str = Field(description="Identifier token that the server will present at the callback_address")
    challenge_secret: str = Field(description="Challenge Secret that the client must return to the server")


class ChallengeCompleteRequest(BaseModel):
    id_secret: str = Field(description="Identifier token that the server presents to the callback_address")

class ChallengeCompleteResponse(BaseModel):
    challenge_secret: str = Field(description="Challenge Secret that the client returns to the server")
    capability: str = Field(description="The capability negotiated between the client and the server")
