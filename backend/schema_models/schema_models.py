from typing import List
from pydantic import BaseModel, Field

# Pydantic models for request/response
class PromptCreate(BaseModel):
    title: str
    body: str
    favorite: str
    type: str
    tags: List[str] = Field(default_factory=list)


class DerivedPrompt(BaseModel):
    """A prompt selected for an agent/system context."""
    id: int
    title: str
    body: str
    date: str
    type: str
    tags: List[str] = Field(default_factory=list)
    criticality: str
    updated_at: str

class Prompt(PromptCreate):
    id: int
    date: str
    criticality: str = "normal"
    updated_at: str = ""

# Pydantic model for update request
class PromptUpdate(BaseModel):
    body: str
    type: str | None = None
    tags: list[str] | None = None


class TagCreate(BaseModel):
    name: str
    color: str | None = None


class TagUpdate(BaseModel):
    new_name: str | None = None
    color: str | None = None
