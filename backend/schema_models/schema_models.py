from typing import List
from pydantic import BaseModel, Field

# Pydantic models for request/response
class PromptCreate(BaseModel):
    title: str
    body: str
    favorite: str
    type: str
    tags: List[str] = Field(default_factory=list)

class Prompt(PromptCreate):
    id: int
    date: str

# Pydantic model for update request
class PromptUpdate(BaseModel):
    body: str
