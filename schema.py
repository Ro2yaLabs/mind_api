from pydantic import BaseModel
from typing import List

class Message(BaseModel):
    client_id: int
    user_responses: List
    sqlite_database: str