import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { CartService, Order, PublicSettings } from '../../core/cart.service';
import { Product } from '../../core/models';

@Component({
    selector: 'app-cart',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink],
    templateUrl: './cart.page.html',
})
export class CartPage implements OnInit {
    settings = signal<PublicSettings | null>(null);
    customerNotes = '';
    loading = signal(false);
    error = signal<string | null>(null);
    successOrderId = signal<number | null>(null);
    lastOrder = signal<Order | null>(null);

    termsLabel(p: Product): string {
        return (p.payment_conditions ?? []).map(c => c.name).join(', ');
    }

    /** Precio efectivo: el de oferta si el producto está en oferta, si no el de lista. */
    effPrice(p: Product): number {
        if (p.is_offer && p.offer_price !== null && p.offer_price !== undefined) {
            return Number(p.offer_price);
        }
        return Number(p.price ?? 0);
    }

    subtotalsByCurrency = computed(() => {
        const out: Record<string, number> = { ARS: 0, USD: 0 };
        for (const it of this.cart.items()) {
            const price = this.effPrice(it.product);
            const cur = it.product.currency || 'ARS';
            out[cur] = (out[cur] || 0) + price * it.quantity;
        }
        return out;
    });

    constructor(public cart: CartService, private router: Router) {}

    ngOnInit() {
        this.cart.getPublicSettings().subscribe(s => this.settings.set(s));
    }

    fmtPrice(n: number, currency: string): string {
        const formatted = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
        return (currency === 'USD' ? 'US$ ' : '$ ') + formatted;
    }

    submit() {
        if (!this.cart.items().length) return;
        this.loading.set(true);
        this.error.set(null);
        this.cart.createOrder({
            payment_condition_id: null,
            customer_notes: this.customerNotes || null,
            items: this.cart.items().map(it => ({ product_id: it.product.id, quantity: it.quantity })),
        }).subscribe({
            next: order => {
                this.loading.set(false);
                this.successOrderId.set(order.id);
                this.lastOrder.set(order);
                this.cart.clear();
                // Refresh order status after a couple of seconds to catch the background email result
                setTimeout(() => this.refreshLastOrderStatus(), 2500);
            },
            error: err => {
                this.loading.set(false);
                this.error.set(err?.error?.detail || 'No se pudo crear la orden');
            },
        });
    }

    refreshLastOrderStatus() {
        const id = this.successOrderId();
        if (!id) return;
        this.cart.listMyOrders().subscribe(orders => {
            const found = orders.find(o => o.id === id);
            if (found) this.lastOrder.set(found);
        });
    }

    downloadPdf() {
        const id = this.successOrderId();
        if (!id) return;
        this.cart.downloadOrderPdf(id).subscribe(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `orden-${id}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    openPdf() {
        const id = this.successOrderId();
        if (!id) return;
        this.cart.downloadOrderPdf(id).subscribe(blob => {
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        });
    }

    newOrder() {
        this.successOrderId.set(null);
        this.customerNotes = '';
    }
}
