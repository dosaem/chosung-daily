from pydantic import BaseModel


class GuestResponse(BaseModel):
    token: str
