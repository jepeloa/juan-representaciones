from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Setting(Base):
    """Simple key/value store for catalog-wide configuration.

    Keys used:
        - 'catalog_disclaimer': text shown at bottom of order PDFs
        - 'catalog_terms': longer terms & conditions text
        - 'company_name': displayed on order PDFs
        - 'company_contact': phone / email line on order PDFs
    """
    __tablename__ = 'settings'

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
