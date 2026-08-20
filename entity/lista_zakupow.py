from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from config.database import Base

class ProduktDoZakupu(Base):
    __tablename__ = "lista_zakupow"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    added_by: Mapped[str] = mapped_column(String, nullable=False)  # "T", "O", "K"
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Dane ze skanu paragonu
    completed_in_store: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completed_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)