from pydantic import BaseModel

class Ticket(BaseModel):
    key: str
    summary: str
    description: dict | None = None
    status: str