import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { CatalogService } from '../../core/catalog.service';
import { CartService } from '../../core/cart.service';
import { Product, ProductDetail } from '../../core/models';
import { ProductDetailModalComponent } from '../catalog/product-detail-modal.component';

@Component({
    selector: 'app-offers',
    standalone: true,
    imports: [CommonModule, RouterLink, ProductDetailModalComponent],
    templateUrl: './offers.page.html',
})
export class OffersPage implements OnInit {
    products = signal<Product[]>([]);
    loading = signal(false);
    selectedProduct = signal<ProductDetail | null>(null);

    constructor(private svc: CatalogService, public cart: CartService) {}

    ngOnInit() {
        this.loading.set(true);
        this.svc.list({ on_offer: true, page_size: 200, sort: 'name' }).subscribe({
            next: res => { this.products.set(res.items); this.loading.set(false); },
            error: () => this.loading.set(false),
        });
    }

    addToCart(p: Product, ev: Event) {
        ev.stopPropagation();
        if (p.price === null || p.price === undefined) return;
        this.cart.add(p, 1);
    }

    openDetail(p: Product) {
        this.svc.get(p.id).subscribe(detail => this.selectedProduct.set(detail));
    }

    closeDetail() {
        this.selectedProduct.set(null);
    }

    offerPct(p: Product): number {
        const list = Number(p.price ?? 0);
        const off = Number(p.offer_price ?? 0);
        if (!list || off <= 0 || off >= list) return 0;
        return Math.round((1 - off / list) * 100);
    }

    fmtPrice(p: number | string | null, mon: string | null): string {
        if (p === null || p === undefined) return '';
        const n = typeof p === 'string' ? parseFloat(p) : p;
        if (Number.isNaN(n)) return '';
        const formatted = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
        return (mon === 'USD' ? 'US$ ' : '$ ') + formatted;
    }
}
