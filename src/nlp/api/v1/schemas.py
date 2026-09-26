from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    text: str = Field(default="", description="the text to search for")
    limit: int = Field(default=5, description="the number of results to return")


class AnswerSchema(BaseModel):
    answer: str
    full_prompt: str
    chat_history: list[dict]
