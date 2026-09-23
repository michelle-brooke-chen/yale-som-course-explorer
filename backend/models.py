from pydantic import BaseModel, Field
from typing import Optional


class Course(BaseModel):
    """Yale SOM course model."""
    title: str
    number: str
    faculty: Optional[str] = None
    category: Optional[str] = None
    day: Optional[str] = None
    time: Optional[str] = None
    description: Optional[str] = None
    faculty_bio: Optional[str] = None
    credits: Optional[float] = None
    term: Optional[str] = None


class AgentResult(BaseModel):
    """Result from the agent."""
    reply: str = Field(description="The agent's response")
    tools_used: list[str] = Field(default_factory=list, description="Tools used")
