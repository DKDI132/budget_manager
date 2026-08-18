from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base

if TYPE_CHECKING:
    from entity.rachunek import Rachunek


class Element(Base):
    __tablename__ = "elementy"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(nullable=True)

    rachunek_id: Mapped[int] = mapped_column(ForeignKey("rachunki.id", ondelete="CASCADE"))

    rachunek: Mapped["Rachunek"] = relationship("Rachunek", back_populates="elementy")