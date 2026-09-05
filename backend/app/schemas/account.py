"""Account data lifecycle request contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class AccountDeleteRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirmation: Literal["DELETE"]
