export interface User {
    id: number;
    username: string;
    full_name: string | null;
    is_admin: boolean;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface Supplier {
    id: number;
    name: string;
    slug: string;
    product_count: number;
}

export interface Category {
    id: number;
    name: string;
    supplier_id: number;
    product_count: number;
}

export interface Product {
    id: number;
    code: string | null;
    name: string;
    description: string | null;
    price: number | string | null;
    currency: string | null;
    iva: string | null;
    supplier_id: number;
    supplier_name: string;
    category_id: number | null;
    category_name: string | null;
    payment_conditions: { id: number; name: string; description?: string | null }[];
    thumbnail: string | null;
}

export interface ProductImage {
    id: number;
    src: string;
    position: number;
}

export interface ProductDetail extends Product {
    unit_per_pack: number | null;
    barcode: string | null;
    notes: string | null;
    source_file: string | null;
    images: ProductImage[];
}

export interface ProductList {
    items: Product[];
    total: number;
    page: number;
    page_size: number;
}

export interface Facets {
    suppliers: Supplier[];
    currencies: string[];
    min_price: number | null;
    max_price: number | null;
    total: number;
}
