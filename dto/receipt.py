from typing import List, Optional
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(description="Nazwa produktu z paragonu")
    quantity: Optional[float] = Field(default=1.0, description="Ilość kupionych sztuk/kg")
    unit_price: Optional[float] = Field(default=None, description="Cena jednostkowa")
    total_price: float = Field(description="Łączna cena za tę pozycję")

class ReceiptData(BaseModel):
    store_name: Optional[str] = Field(default=None, description="Nazwa sklepu / sprzedawcy")
    date: Optional[str] = Field(default=None, description="Data zakupu (YYYY-MM-DD)")
    items: List[Item] = Field(description="Lista odczytanych produktów")
    total_amount: float = Field(description="Łączna kwota do zapłaty (SUMA PLN)")

class ItemCreate(BaseModel):
    name: str
    quantity: float = 1.0
    total_price: float

class ReceiptSaveRequest(BaseModel):
    account: str
    store_name: Optional[str] = "Nieokreślony sklep"
    purchase_date: Optional[str] = ""
    picture_path: Optional[str] = ""
    cost: float
    items: List[ItemCreate]
