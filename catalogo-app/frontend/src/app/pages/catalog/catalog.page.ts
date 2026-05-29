import { Component, OnInit, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, Subject } from 'rxjs';

import { CatalogService, ProductQuery } from '../../core/catalog.service';
import { CartService } from '../../core/cart.service';
import { AuthService } from '../../core/auth.service';
import { Category, Facets, Product, ProductDetail, Supplier } from '../../core/models';
import { ProductDetailModalComponent } from './product-detail-modal.component';

type ViewMode = 'table' | 'grid';

@Component({
    selector: 'app-catalog',
    standalone: true,
    imports: [CommonModule, FormsModule, ProductDetailModalComponent],
    templateUrl: './catalog.page.html',
})
export class CatalogPage implements OnInit {
    products = signal<Product[]>([]);
    total = signal(0);
    loading = signal(false);
    facets = signal<Facets | null>(null);
    categories = signal<Category[]>([]);
    selectedProduct = signal<ProductDetail | null>(null);

    q = '';
    supplierId: number | null = null;
    categoryId: number | null = null;
    currency = '';
    maxPrice: number | null = null;
    sort = 'name';
    page = 1;
    pageSize = 60;
    view = signal<ViewMode>('table');

    priceSlider = 100;
    maxPriceLimit = 5_000_000;

    pages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize)));

    private search$ = new Subject<void>();

    constructor(
        private svc: CatalogService,
        public cart: CartService,
        public auth: AuthService,
        private route: ActivatedRoute,
        private router: Router,
    ) {
        this.search$.pipe(debounceTime(300)).subscribe(() => this.fetch());
    }

    get isAdmin(): boolean {
        return !!this.auth.user()?.is_admin;
    }

    addToCart(p: Product, ev: Event) {
        ev.stopPropagation();
        if (p.price === null || p.price === undefined) return;
        this.cart.add(p, 1);
    }

    ngOnInit() {
        const qp = this.route.snapshot.queryParamMap;
        this.q = qp.get('q') ?? '';
        this.supplierId = qp.get('supplier') ? Number(qp.get('supplier')) : null;
        this.categoryId = qp.get('cat') ? Number(qp.get('cat')) : null;
        this.currency = qp.get('mon') ?? '';
        // Clients always see grid; admins default to table unless they switched it
        const defaultView: ViewMode = this.isAdmin ? 'table' : 'grid';
        this.view.set(this.isAdmin ? ((qp.get('view') as ViewMode) || defaultView) : 'grid');
        this.page = Number(qp.get('page')) || 1;

        this.svc.facets().subscribe(f => {
            this.facets.set(f);
            if (f.max_price) this.maxPriceLimit = Number(f.max_price);
        });
        if (this.supplierId) this.loadCategories(this.supplierId);
        else this.svc.categories().subscribe(c => this.categories.set(c));

        this.fetch();
    }

    fetch() {
        this.loading.set(true);
        const query: ProductQuery = {
            q: this.q || undefined,
            supplier_id: this.supplierId ?? undefined,
            category_id: this.categoryId ?? undefined,
            currency: this.currency || undefined,
            max_price: this.maxPrice ?? undefined,
            sort: this.sort,
            page: this.page,
            page_size: this.pageSize,
        };
        this.svc.list(query).subscribe({
            next: res => {
                this.products.set(res.items);
                this.total.set(res.total);
                this.loading.set(false);
                this.syncUrl();
            },
            error: () => this.loading.set(false),
        });
    }

    onSearchInput() {
        this.page = 1;
        this.search$.next();
    }

    onSupplierChange() {
        this.categoryId = null;
        this.page = 1;
        if (this.supplierId) this.loadCategories(this.supplierId);
        else this.svc.categories().subscribe(c => this.categories.set(c));
        this.fetch();
    }

    onCategoryChange() {
        this.page = 1;
        this.fetch();
    }

    onCurrencyChange() {
        this.page = 1;
        this.fetch();
    }

    onPriceSlider() {
        if (this.priceSlider >= 100) this.maxPrice = null;
        else {
            const v = Math.pow(this.priceSlider / 100, 2.5) * this.maxPriceLimit;
            this.maxPrice = Math.round(v);
        }
        this.page = 1;
        this.search$.next();
    }

    onSort(col: string) {
        this.sort = this.sort === col ? `-${col}` : col;
        this.page = 1;
        this.fetch();
    }

    sortIcon(col: string): string {
        if (this.sort === col) return '▲';
        if (this.sort === `-${col}`) return '▼';
        return '⇅';
    }

    setView(v: ViewMode) {
        this.view.set(v);
        this.syncUrl();
    }

    nextPage() { if (this.page < this.pages()) { this.page++; this.fetch(); window.scrollTo({top: 0, behavior: 'smooth'}); } }
    prevPage() { if (this.page > 1) { this.page--; this.fetch(); window.scrollTo({top: 0, behavior: 'smooth'}); } }

    reset() {
        this.q = '';
        this.supplierId = null;
        this.categoryId = null;
        this.currency = '';
        this.maxPrice = null;
        this.priceSlider = 100;
        this.page = 1;
        this.svc.categories().subscribe(c => this.categories.set(c));
        this.fetch();
    }

    openDetail(p: Product) {
        this.svc.get(p.id).subscribe(detail => this.selectedProduct.set(detail));
    }

    closeDetail() {
        this.selectedProduct.set(null);
    }

    fmtPrice(p: number | string | null, mon: string | null): string {
        if (p === null || p === undefined) return '';
        const n = typeof p === 'string' ? parseFloat(p) : p;
        if (Number.isNaN(n)) return '';
        const formatted = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
        return (mon === 'USD' ? 'US$ ' : '$ ') + formatted;
    }

    fmtPriceShort(p: number | null): string {
        if (p === null) return 'Sin límite';
        return new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 }).format(p);
    }

    private loadCategories(supplierId: number) {
        this.svc.categories(supplierId).subscribe(c => this.categories.set(c));
    }

    private syncUrl() {
        const qp: any = {};
        if (this.q) qp.q = this.q;
        if (this.supplierId) qp.supplier = this.supplierId;
        if (this.categoryId) qp.cat = this.categoryId;
        if (this.currency) qp.mon = this.currency;
        if (this.view() !== 'table') qp.view = this.view();
        if (this.page > 1) qp.page = this.page;
        this.router.navigate([], { relativeTo: this.route, queryParams: qp, replaceUrl: true });
    }
}
