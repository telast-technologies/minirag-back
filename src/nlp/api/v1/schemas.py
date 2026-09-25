from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    text: str = Field(default="", description="the text to search for")
    limit: int = Field(default=5, description="the number of results to return")
