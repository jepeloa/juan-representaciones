import { Component, OnInit, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, Subject } from 'rxjs';

import { CatalogService, ProductQuery } from '../../core/catalog.service';
import { CartService } from '../../core/cart.service';
import { AuthService } from '../../core/auth.service';
import { SearchService } from '../../core/search.service';
import { ActivityService } from '../../core/activity.service';
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

    // Popup de ofertas del día (se muestra una vez por sesión si hay ofertas activas).
    offerPreview = signal<Product[]>([]);
    showOffersPopup = signal(false);

    // Aviso de consulta de stock (por producto)
    showStock = signal(false);
    stockProduct = signal<Product | null>(null);

    stockWhatsapp = computed(() => {
        const p = this.stockProduct();
        const msg = p
            ? `Hola, quería consultar el stock de "${p.name}"${p.code ? ' (cód. ' + p.code + ')' : ''}.`
            : 'Hola, quería consultar disponibilidad de stock.';
        return 'https://wa.me/5493416747476?text=' + encodeURIComponent(msg);
    });

    openStock(p: Product, ev?: Event) {
        ev?.stopPropagation();
        this.stockProduct.set(p);
        this.showStock.set(true);
        this.activity.track('view_stock', { label: p.name, refId: p.id });
    }

    // Condiciones comerciales (de la marca del producto)
    showConditions = signal(false);
    conditionsProduct = signal<Product | null>(null);

    openConditions(p: Product, ev?: Event) {
        ev?.stopPropagation();
        this.conditionsProduct.set(p);
        this.showConditions.set(true);
        this.activity.track('view_conditions', { label: p.supplier_name, refId: p.id });
    }

    hasConditions(p: Product): boolean {
        return !!p.payment_conditions && p.payment_conditions.length > 0;
    }

    supplierId: number | null = null;
    categoryName: string | null = null;
    currency = '';
    maxPrice: number | null = null;
    sort = 'name';
    page = 1;
    pageSize = 60;
    view = signal<ViewMode>('grid');

    priceSlider = 100;
    maxPriceLimit = 5_000_000;

    pages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize)));

    private search$ = new Subject<void>();

    private firstQueryEffect = true;

    constructor(
        private svc: CatalogService,
        public cart: CartService,
        public auth: AuthService,
        public search: SearchService,
        private route: ActivatedRoute,
        private router: Router,
        private activity: ActivityService,
    ) {
        this.search$.pipe(debounceTime(300)).subscribe(() => this.fetch());
        // El texto de búsqueda es global (shell + página): al cambiar, recargar.
        effect(() => {
            this.search.query();
            if (this.firstQueryEffect) { this.firstQueryEffect = false; return; }
            this.page = 1;
            this.search$.next();
        });
    }

    get isAdmin(): boolean {
        return !!this.auth.user()?.is_admin;
    }

    addToCart(p: Product, ev: Event) {
        ev.stopPropagation();
        if (p.price === null || p.price === undefined) return;
        this.cart.add(p, 1);
        this.activity.track('add_to_cart', { label: p.name, refId: p.id });
    }

    ngOnInit() {
        const qp = this.route.snapshot.queryParamMap;
        this.search.query.set(qp.get('q') ?? '');
        this.supplierId = qp.get('supplier') ? Number(qp.get('supplier')) : null;
        this.categoryName = qp.get('cat') || null;
        this.currency = qp.get('mon') ?? '';
        // Todos (cliente y admin) arrancan en grilla y pueden cambiar a tabla (persistido vía ?view=)
        this.view.set((qp.get('view') as ViewMode) || 'grid');
        this.page = Number(qp.get('page')) || 1;

        this.svc.facets().subscribe(f => {
            this.facets.set(f);
            if (f.max_price) this.maxPriceLimit = Number(f.max_price);
        });
        if (this.supplierId) this.loadCategories(this.supplierId);
        else this.svc.categories().subscribe(c => this.categories.set(c));

        this.fetch();
        this.maybeShowOffers();
    }

    private static readonly OFFERS_SEEN_KEY = 'ofertas_popup_seen_v1';

    /** Trae las ofertas activas y abre el popup una vez por sesión si hay alguna. */
    private maybeShowOffers() {
        const seen = sessionStorage.getItem(CatalogPage.OFFERS_SEEN_KEY);
        this.svc.list({ on_offer: true, page_size: 8, sort: 'name' }).subscribe(res => {
            this.offerPreview.set(res.items);
            if (res.items.length && !seen) {
                this.showOffersPopup.set(true);
                sessionStorage.setItem(CatalogPage.OFFERS_SEEN_KEY, '1');
            }
        });
    }

    closeOffersPopup() {
        this.showOffersPopup.set(false);
    }

    goToOffers() {
        this.showOffersPopup.set(false);
        this.router.navigate(['/ofertas']);
    }

    fetch() {
        this.loading.set(true);
        const query: ProductQuery = {
            q: this.search.query() || undefined,
            supplier_id: this.supplierId ?? undefined,
            category_name: this.categoryName ?? undefined,
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
        this.categoryName = null;
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
        this.search.query.set('');
        this.supplierId = null;
        this.categoryName = null;
        this.currency = '';
        this.maxPrice = null;
        this.priceSlider = 100;
        this.page = 1;
        this.svc.categories().subscribe(c => this.categories.set(c));
        this.fetch();
    }

    openDetail(p: Product) {
        this.activity.track('product_view', { label: p.name, refId: p.id });
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

    isOnOffer(p: Product): boolean {
        return !!p.is_offer && p.offer_price !== null && p.offer_price !== undefined;
    }

    /** % de descuento (entero) de la oferta respecto del precio de lista. */
    offerPct(p: Product): number {
        const list = Number(p.price ?? 0);
        const off = Number(p.offer_price ?? 0);
        if (!list || off <= 0 || off >= list) return 0;
        return Math.round((1 - off / list) * 100);
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
        if (this.search.query()) qp.q = this.search.query();
        if (this.supplierId) qp.supplier = this.supplierId;
        if (this.categoryName) qp.cat = this.categoryName;
        if (this.currency) qp.mon = this.currency;
        if (this.view() !== 'grid') qp.view = this.view();
        if (this.page > 1) qp.page = this.page;
        this.router.navigate([], { relativeTo: this.route, queryParams: qp, replaceUrl: true });
    }
}
