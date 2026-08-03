from typing import Literal

from pydantic import BaseModel


class Ticket(BaseModel):
    key: str
    summary: str
    description: dict | None = None
    status: str

class ReviewResult(BaseModel):
    verdict: Literal["approve", "request_changes"]
    summary: str
    comments: list[str]