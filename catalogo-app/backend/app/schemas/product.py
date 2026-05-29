from decimal import Decimal
from pydantic import BaseModel


class SupplierOut(BaseModel):
    id: int
    name: str
    slug: str
    product_count: int | None = None

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: int
    name: str
    supplier_id: int
    product_count: int | None = None

    class Config:
        from_attributes = True


class ProductImageOut(BaseModel):
    id: int
    src: str
    position: int

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    code: str | None
    name: str
    description: str | None
    price: Decimal | None
    currency: str | None
    iva: str | None
    supplier_id: int
    supplier_name: str
    category_id: int | None
    category_name: str | None
    thumbnail: str | None

    class Config:
        from_attributes = True


class ProductDetailOut(ProductOut):
    unit_per_pack: int | None
    barcode: str | None
    notes: str | None
    source_file: str | None
    images: list[ProductImageOut]


class FacetsOut(BaseModel):
    suppliers: list[SupplierOut]
    currencies: list[str]
    min_price: Decimal | None
    max_price: Decimal | None
    total: int


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
