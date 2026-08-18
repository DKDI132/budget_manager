from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base

if TYPE_CHECKING:
    from entity.elementy import Element


class Rachunek(Base):
    __tablename__ = "rachunki"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender: Mapped[Optional[str]] = mapped_column(nullable=True)
    store_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    purchase_date: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    picture_path: Mapped[Optional[str]] = mapped_column(nullable=True)

    elementy: Mapped[List["Element"]] = relationship(
        "Element",
        back_populates="rachunek",
        cascade="all, delete-orphan"
    )