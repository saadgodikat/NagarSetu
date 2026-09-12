from typing import Any

from pydantic import BaseModel, Field


class AssistantQueryIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AssistantAnswerOut(BaseModel):
    question: str
    intent: str
    answer: str
    data: dict[str, Any]
    provider: str = "sql_rules"
    supported_questions: list[str]
