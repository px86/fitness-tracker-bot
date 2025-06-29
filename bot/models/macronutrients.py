from pydantic import BaseModel, Field


class MacroNutrients(BaseModel):
    """
    Represents the macronutrient breakdown and energy content of a food item/meal.

    Attributes:
        calories (int): Total energy content in kilocalories (kcal). Must be non-negative.
        protein (int): Protein content in grams (g). Must be non-negative.
        fat (int): Fat content in grams (g). Must be non-negative.
        carbohydrates (int): Carbohydrate content in grams (g). Must be non-negative.
    """

    calories: int = Field(..., ge=0)
    protein: int = Field(..., ge=0)
    fat: int = Field(..., ge=0)
    carbohydrates: int = Field(..., ge=0)
