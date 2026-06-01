import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from './api';
import { ProductDetail } from './models';

export interface AdminUser {
    id: number;
    username: string;
    full_name: string | null;
    is_admin: boolean;
    is_active: boolean;
}

export interface CreateUserBody {
    username: string;
    password: string;
    full_name?: string | null;
    is_admin: boolean;
    is_active: boolean;
}

export interface UpdateUserBody {
    full_name?: string | null;
    is_admin?: boolean;
    is_active?: boolean;
    password?: string;
}

export interface ProductFormData {
    supplier_id?: number | null;
    supplier_name?: string | null;
    category_id?: number | null;
    category_name?: string | null;
    code?: string | null;
    name: string;
    description?: string | null;
    price?: string | null;
    currency?: string | null;
    iva?: string | null;
    unit_per_pack?: number | null;
    barcode?: string | null;
    notes?: string | null;
    payment_condition_ids?: number[];
}

@Injectable({ providedIn: 'root' })
export class AdminService {
    constructor(private http: HttpClient) {}

    // ===== Users =====
    listUsers(): Observable<AdminUser[]> {
        return this.http.get<AdminUser[]>(`${API_BASE}/admin/users`);
    }
    createUser(body: CreateUserBody): Observable<AdminUser> {
        return this.http.post<AdminUser>(`${API_BASE}/admin/users`, body);
    }
    updateUser(id: number, body: UpdateUserBody): Observable<AdminUser> {
        return this.http.patch<AdminUser>(`${API_BASE}/admin/users/${id}`, body);
    }
    deleteUser(id: number): Observable<void> {
        return this.http.delete<void>(`${API_BASE}/admin/users/${id}`);
    }

    // ===== Products =====
    private toFormData(body: ProductFormData, files: File[] = [], extra: Record<string, string> = {}): FormData {
        const fd = new FormData();
        Object.entries(body).forEach(([k, v]) => {
            // payment_condition_ids se envía siempre como CSV (incluso vacío) para poder limpiar
            if (k === 'payment_condition_ids') {
                fd.append(k, Array.isArray(v) ? v.join(',') : '');
                return;
            }
            if (v !== null && v !== undefined && v !== '') fd.append(k, String(v));
        });
        Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
        files.forEach(f => fd.append('images', f, f.name));
        return fd;
    }

    createProduct(body: ProductFormData, files: File[]): Observable<ProductDetail> {
        return this.http.post<ProductDetail>(`${API_BASE}/admin/products`, this.toFormData(body, files));
    }
    updateProduct(id: number, body: Partial<ProductFormData>, files: File[] = [], clearImages = false): Observable<ProductDetail> {
        const fd = this.toFormData(body as ProductFormData, files, clearImages ? { clear_images: 'true' } : {});
        return this.http.patch<ProductDetail>(`${API_BASE}/admin/products/${id}`, fd);
    }
    deleteProduct(id: number): Observable<void> {
        return this.http.delete<void>(`${API_BASE}/admin/products/${id}`);
    }

    // ===== Payment conditions =====
    listConditions(): Observable<AdminPaymentCondition[]> {
        return this.http.get<AdminPaymentCondition[]>(`${API_BASE}/admin/payment-conditions`);
    }
    createCondition(body: PaymentConditionBody): Observable<AdminPaymentCondition> {
        return this.http.post<AdminPaymentCondition>(`${API_BASE}/admin/payment-conditions`, body);
    }
    updateCondition(id: number, body: PaymentConditionBody): Observable<AdminPaymentCondition> {
        return this.http.patch<AdminPaymentCondition>(`${API_BASE}/admin/payment-conditions/${id}`, body);
    }
    deleteCondition(id: number): Observable<void> {
        return this.http.delete<void>(`${API_BASE}/admin/payment-conditions/${id}`);
    }

    // ===== Settings =====
    getSettings(): Observable<AdminSettings> {
        return this.http.get<AdminSettings>(`${API_BASE}/admin/settings`);
    }
    updateSettings(body: AdminSettings): Observable<AdminSettings> {
        return this.http.put<AdminSettings>(`${API_BASE}/admin/settings`, { settings: body });
    }
}

export interface AdminPaymentCondition {
    id: number;
    name: string;
    description: string | null;
    multiplier: string | number;
    days: number | null;
    is_active: boolean;
    sort_order: number;
}

export interface PaymentConditionBody {
    name: string;
    description?: string | null;
    multiplier: number;
    days?: number | null;
    is_active: boolean;
    sort_order: number;
}

export interface AdminSettings {
    catalog_disclaimer: string | null;
    catalog_terms: string | null;
    company_name: string | null;
    company_contact: string | null;
    order_notification_email: string | null;
}

