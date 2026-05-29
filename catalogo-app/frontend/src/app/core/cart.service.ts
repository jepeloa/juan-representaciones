import { Injectable, computed, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from './api';
import { Product } from './models';

export interface CartItem {
    product: Product;
    quantity: number;
}

export interface PaymentCondition {
    id: number;
    name: string;
    description: string | null;
    multiplier: string | number;
    days: number | null;
    is_active: boolean;
    sort_order: number;
}

export interface PublicSettings {
    catalog_disclaimer: string | null;
    catalog_terms: string | null;
    company_name: string | null;
    company_contact: string | null;
}

export interface OrderItem {
    id: number;
    product_id: number | null;
    quantity: number;
    unit_price_list: string;
    unit_price_final: string;
    currency: string;
    line_total: string;
    product_name: string;
    product_code: string | null;
    supplier_name: string | null;
}

export interface Order {
    id: number;
    user_id: number | null;
    payment_condition_id: number | null;
    payment_name: string | null;
    payment_multiplier: string;
    subtotal_ars: string;
    total_ars: string;
    subtotal_usd: string;
    total_usd: string;
    customer_notes: string | null;
    status: string;
    created_at: string;
    email_to: string | null;
    email_status: 'pending' | 'sent' | 'failed' | 'disabled';
    email_sent_at: string | null;
    email_error: string | null;
    items: OrderItem[];
}

const CART_KEY = 'catalogo_cart_v1';

@Injectable({ providedIn: 'root' })
export class CartService {
    private _items = signal<CartItem[]>(this.restore());
    items = computed(() => this._items());
    count = computed(() => this._items().reduce((acc, it) => acc + it.quantity, 0));

    constructor(private http: HttpClient) {}

    add(product: Product, qty = 1) {
        if (product.price === null || product.price === undefined) return;
        const existing = this._items().find(it => it.product.id === product.id);
        if (existing) {
            this.update(product.id, existing.quantity + qty);
        } else {
            this._items.set([...this._items(), { product, quantity: qty }]);
            this.persist();
        }
    }

    update(productId: number, qty: number) {
        if (qty < 1) { this.remove(productId); return; }
        this._items.set(this._items().map(it =>
            it.product.id === productId ? { ...it, quantity: qty } : it
        ));
        this.persist();
    }

    remove(productId: number) {
        this._items.set(this._items().filter(it => it.product.id !== productId));
        this.persist();
    }

    clear() {
        this._items.set([]);
        this.persist();
    }

    has(productId: number): boolean {
        return this._items().some(it => it.product.id === productId);
    }

    quantityOf(productId: number): number {
        return this._items().find(it => it.product.id === productId)?.quantity ?? 0;
    }

    private persist() {
        try {
            const raw = this._items().map(it => ({ id: it.product.id, qty: it.quantity, snapshot: it.product }));
            localStorage.setItem(CART_KEY, JSON.stringify(raw));
        } catch {}
    }

    private restore(): CartItem[] {
        try {
            const raw = localStorage.getItem(CART_KEY);
            if (!raw) return [];
            const parsed = JSON.parse(raw) as { id: number; qty: number; snapshot: Product }[];
            return parsed.map(r => ({ product: r.snapshot, quantity: r.qty }));
        } catch { return []; }
    }

    // ===== API calls =====
    getPaymentConditions(): Observable<PaymentCondition[]> {
        return this.http.get<PaymentCondition[]>(`${API_BASE}/payment-conditions`);
    }

    getPublicSettings(): Observable<PublicSettings> {
        return this.http.get<PublicSettings>(`${API_BASE}/settings/public`);
    }

    createOrder(payload: { payment_condition_id: number | null; customer_notes: string | null; items: { product_id: number; quantity: number }[] }): Observable<Order> {
        return this.http.post<Order>(`${API_BASE}/orders`, payload);
    }

    downloadOrderPdf(orderId: number): Observable<Blob> {
        return this.http.get(`${API_BASE}/orders/${orderId}/pdf`, { responseType: 'blob' });
    }

    listMyOrders(): Observable<Order[]> {
        return this.http.get<Order[]>(`${API_BASE}/orders`);
    }
}
