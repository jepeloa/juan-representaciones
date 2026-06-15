import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AdminService } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Product } from '../../core/models';

interface ProductGroup {
    supplier: string;
    items: Product[];
}

@Component({
    selector: 'app-admin-offers',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-offers.page.html',
})
export class AdminOffersPage implements OnInit {
    offers = signal<Product[]>([]);
    allProducts = signal<Product[]>([]);
    loading = signal(false);
    error = signal<string | null>(null);
    successMsg = signal<string | null>(null);

    // Alta de oferta vía desplegable
    selectedId: number | null = null;
    addPrice = '';

    // Edición inline del precio de oferta { productId: valor }
    priceInput: Record<number, string> = {};

    constructor(private admin: AdminService, private catalog: CatalogService) {}

    ngOnInit() {
        // Catálogo completo para poblar el desplegable
        this.catalog.list({ page_size: 1000, sort: 'name' }).subscribe(res => this.allProducts.set(res.items));
        this.loadOffers();
    }

    /** Productos que todavía no están en oferta, agrupados por proveedor. */
    availableGroups = computed<ProductGroup[]>(() => {
        const offerIds = new Set(this.offers().map(o => o.id));
        const groups: Record<string, Product[]> = {};
        for (const p of this.allProducts()) {
            if (offerIds.has(p.id)) continue;
            const sup = p.supplier_name || 'Sin proveedor';
            (groups[sup] ??= []).push(p);
        }
        return Object.keys(groups).sort().map(sup => ({ supplier: sup, items: groups[sup] }));
    });

    selectedProduct = computed<Product | null>(() =>
        this.allProducts().find(p => p.id === this.selectedId) ?? null,
    );

    loadOffers() {
        this.loading.set(true);
        this.admin.listOffers().subscribe({
            next: list => {
                this.offers.set(list);
                for (const p of list) {
                    this.priceInput[p.id] = p.offer_price != null ? String(p.offer_price) : '';
                }
                this.loading.set(false);
            },
            error: () => { this.loading.set(false); this.error.set('No se pudieron cargar las ofertas'); },
        });
    }

    private parsePrice(raw: string | undefined): number | null {
        if (!raw) return null;
        const n = parseFloat(raw.replace(',', '.'));
        return Number.isFinite(n) ? n : null;
    }

    /** Pone el producto elegido en el desplegable en oferta. */
    addOffer() {
        if (!this.selectedId) { this.flashError('Elegí un producto'); return; }
        const price = this.parsePrice(this.addPrice);
        if (price === null || price <= 0) { this.flashError('Ingresá un precio de oferta válido'); return; }
        const name = this.selectedProduct()?.name ?? 'Producto';
        this.admin.setOffer(this.selectedId, { offer_price: price, is_offer: true }).subscribe({
            next: () => {
                this.flashSuccess(`"${name}" puesto en oferta`);
                this.selectedId = null;
                this.addPrice = '';
                this.loadOffers();
            },
            error: err => this.flashError(err?.error?.detail || 'No se pudo guardar la oferta'),
        });
    }

    /** Guarda un nuevo precio para una oferta existente. */
    updatePrice(p: Product) {
        const price = this.parsePrice(this.priceInput[p.id]);
        if (price === null || price <= 0) { this.flashError('Precio de oferta inválido'); return; }
        this.admin.setOffer(p.id, { offer_price: price, is_offer: p.is_offer }).subscribe({
            next: () => { this.flashSuccess('Precio actualizado'); this.loadOffers(); },
            error: err => this.flashError(err?.error?.detail || 'No se pudo actualizar'),
        });
    }

    /** Activa/desactiva una oferta sin perder el precio cargado. */
    toggleActive(p: Product) {
        const price = this.parsePrice(this.priceInput[p.id]) ?? Number(p.offer_price ?? 0);
        this.admin.setOffer(p.id, { offer_price: price, is_offer: !p.is_offer }).subscribe({
            next: () => { this.flashSuccess(!p.is_offer ? 'Oferta activada' : 'Oferta pausada'); this.loadOffers(); },
            error: err => this.flashError(err?.error?.detail || 'No se pudo cambiar el estado'),
        });
    }

    removeOffer(p: Product) {
        if (!confirm(`¿Quitar "${p.name}" de ofertas?`)) return;
        this.admin.clearOffer(p.id).subscribe({
            next: () => { this.flashSuccess('Oferta eliminada'); this.loadOffers(); },
            error: () => this.flashError('No se pudo eliminar'),
        });
    }

    offerPct(p: Product, raw?: string): number {
        const list = Number(p.price ?? 0);
        const off = this.parsePrice(raw) ?? Number(p.offer_price ?? 0);
        if (!list || off <= 0 || off >= list) return 0;
        return Math.round((1 - off / list) * 100);
    }

    fmtPrice(p: number | string | null, mon: string | null): string {
        if (p === null || p === undefined) return '—';
        const n = typeof p === 'string' ? parseFloat(p) : p;
        if (Number.isNaN(n)) return '—';
        const fmt = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
        return (mon === 'USD' ? 'US$ ' : '$ ') + fmt;
    }

    private flashSuccess(msg: string) {
        this.successMsg.set(msg);
        this.error.set(null);
        setTimeout(() => this.successMsg.set(null), 2500);
    }
    private flashError(msg: string) {
        this.error.set(msg);
        setTimeout(() => this.error.set(null), 3500);
    }
}
