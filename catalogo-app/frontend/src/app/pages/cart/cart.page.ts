import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { CartService, CartItem, Order, PaymentCondition, PublicSettings } from '../../core/cart.service';

@Component({
    selector: 'app-cart',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink],
    templateUrl: './cart.page.html',
})
export class CartPage implements OnInit {
    conditions = signal<PaymentCondition[]>([]);
    settings = signal<PublicSettings | null>(null);
    selectedConditionId = signal<number | null>(null);
    customerNotes = '';
    loading = signal(false);
    error = signal<string | null>(null);
    successOrderId = signal<number | null>(null);
    lastOrder = signal<Order | null>(null);

    selectedCondition = computed<PaymentCondition | null>(() => {
        const id = this.selectedConditionId();
        return this.conditions().find(c => c.id === id) ?? null;
    });

    multiplier = computed(() => {
        const c = this.selectedCondition();
        return c ? Number(c.multiplier) : 1;
    });

    // Agrupa los ítems del carrito por su condición de pago (preservando orden)
    groupedItems = computed<{ term: string | null; items: CartItem[] }[]>(() => {
        const groups: { term: string | null; items: CartItem[] }[] = [];
        const index = new Map<string | null, number>();
        for (const it of this.cart.items()) {
            const key = it.product.payment_term || null;
            if (!index.has(key)) {
                index.set(key, groups.length);
                groups.push({ term: key, items: [] });
            }
            groups[index.get(key)!].items.push(it);
        }
        return groups;
    });

    subtotalsByCurrency = computed(() => {
        const out: Record<string, number> = { ARS: 0, USD: 0 };
        for (const it of this.cart.items()) {
            const price = Number(it.product.price ?? 0);
            const cur = it.product.currency || 'ARS';
            out[cur] = (out[cur] || 0) + price * it.quantity;
        }
        return out;
    });

    totalsByCurrency = computed(() => {
        const subs = this.subtotalsByCurrency();
        const m = this.multiplier();
        return { ARS: subs['ARS'] * m, USD: subs['USD'] * m };
    });

    constructor(public cart: CartService, private router: Router) {}

    ngOnInit() {
        this.cart.getPaymentConditions().subscribe(c => {
            this.conditions.set(c);
            const def = c.find(x => Number(x.multiplier) === 1) || c[0];
            if (def) this.selectedConditionId.set(def.id);
        });
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
            payment_condition_id: this.selectedConditionId(),
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
