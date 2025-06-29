from typing import Literal
from pydantic import BaseModel, Field


class User(BaseModel):
    """
    Represents a user with basic demographic and physical information.

    Attributes:
        userid (int): User's telegram userid.
        name (str): Full name of the user. Required. Max length: 100 characters.
        gender (Literal["male", "female", "other"]): Gender identity of the user. Must be one of: "male", "female", or "other".
        age (int): Age of the user in years. Must be greater than 0 and less than 120.
        height (int): Height of the user in centimeters. Must be greater than 0.
        weight (int): Weight of the user in kilograms. Must be greater than 0.
    """

    userid: int = (Field(...),)
    name: str = Field(..., max_length=100)
    gender: Literal["male", "female", "other"]
    age: int = Field(..., gt=0, lt=120)
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
