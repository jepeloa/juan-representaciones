import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_BASE } from './api';
import { Category, Facets, Product, ProductDetail, ProductList, Supplier } from './models';

export interface ProductQuery {
    q?: string;
    supplier_id?: number;
    category_id?: number;
    currency?: string;
    max_price?: number;
    min_price?: number;
    sort?: string;
    page?: number;
    page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogService {
    constructor(private http: HttpClient) {}

    list(q: ProductQuery): Observable<ProductList> {
        let params = new HttpParams();
        for (const [k, v] of Object.entries(q)) {
            if (v !== undefined && v !== null && v !== '') {
                params = params.set(k, String(v));
            }
        }
        return this.http.get<ProductList>(`${API_BASE}/products`, { params });
    }

    get(id: number): Observable<ProductDetail> {
        return this.http.get<ProductDetail>(`${API_BASE}/products/${id}`);
    }

    facets(): Observable<Facets> {
        return this.http.get<Facets>(`${API_BASE}/products/facets`);
    }

    suppliers(): Observable<Supplier[]> {
        return this.http.get<Supplier[]>(`${API_BASE}/suppliers`);
    }

    categories(supplierId?: number): Observable<Category[]> {
        let params = new HttpParams();
        if (supplierId) params = params.set('supplier_id', supplierId);
        return this.http.get<Category[]>(`${API_BASE}/categories`, { params });
    }
}
