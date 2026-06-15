import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ProductDetail } from '../../core/models';
import { CartService } from '../../core/cart.service';

@Component({
    selector: 'app-product-detail-modal',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './product-detail-modal.component.html',
})
export class ProductDetailModalComponent {
    @Input() product: ProductDetail | null = null;
    @Output() close = new EventEmitter<void>();

    zoomed = signal<string | null>(null);

    constructor(public cart: CartService) {}

    onClose() {
        this.zoomed.set(null);
        this.close.emit();
    }

    addToCart() {
        if (!this.product || this.product.price === null || this.product.price === undefined) return;
        // ProductDetail has more fields but the cart only needs the Product shape; cast is safe.
        this.cart.add(this.product as any, 1);
    }

    incQty() {
        if (!this.product) return;
        this.cart.update(this.product.id, this.cart.quantityOf(this.product.id) + 1);
    }

    decQty() {
        if (!this.product) return;
        this.cart.update(this.product.id, this.cart.quantityOf(this.product.id) - 1);
    }

    fmtPrice(p: number | string | null, mon: string | null): string {
        if (p === null || p === undefined) return '—';
        const n = typeof p === 'string' ? parseFloat(p) : p;
        if (Number.isNaN(n)) return '—';
        const fmt = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
        return (mon === 'USD' ? 'US$ ' : '$ ') + fmt;
    }

    get onOffer(): boolean {
        const p = this.product;
        return !!p && !!p.is_offer && p.offer_price !== null && p.offer_price !== undefined;
    }

    get offerPct(): number {
        const p = this.product;
        if (!p) return 0;
        const list = Number(p.price ?? 0);
        const off = Number(p.offer_price ?? 0);
        if (!list || off <= 0 || off >= list) return 0;
        return Math.round((1 - off / list) * 100);
    }
}
