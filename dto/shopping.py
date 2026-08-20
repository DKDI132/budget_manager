from pydantic import BaseModel

class ShoppingItemCreate(BaseModel):
    item_name: str
    added_by: str
