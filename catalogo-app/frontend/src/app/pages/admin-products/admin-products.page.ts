import { Component, HostListener, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { debounceTime, Subject } from 'rxjs';

import { AdminService, ProductFormData, AdminPaymentTerm } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Category, Product, Supplier } from '../../core/models';

@Component({
    selector: 'app-admin-products',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-products.page.html',
})
export class AdminProductsPage implements OnInit {
    suppliers = signal<Supplier[]>([]);
    categories = signal<Category[]>([]);
    paymentTerms = signal<AdminPaymentTerm[]>([]);
    products = signal<Product[]>([]);
    total = signal(0);
    page = 1;
    pageSize = 30;

    loading = signal(false);
    saving = signal(false);
    error = signal<string | null>(null);
    successMsg = signal<string | null>(null);
    editingId = signal<number | null>(null);
    showForm = signal(false);

    // search filters
    q = '';
    filterSupplierId: number | null = null;

    // form state
    form: ProductFormData = this.emptyForm();
    existingThumbnail: string | null = null;
    selectedFiles: File[] = [];
    previewUrls: string[] = [];
    newSupplierName = '';
    newCategoryName = '';
    useNewSupplier = false;
    useNewCategory = false;
    clearExistingImages = false;

    private search$ = new Subject<void>();

    constructor(public admin: AdminService, private catalog: CatalogService) {
        this.search$.pipe(debounceTime(300)).subscribe(() => this.refresh());
    }

    ngOnInit() {
        this.catalog.suppliers().subscribe(s => this.suppliers.set(s));
        this.refresh();
    }

    onSearchInput() {
        this.page = 1;
        this.search$.next();
    }

    onFilterSupplier() {
        this.page = 1;
        this.refresh();
    }

    refresh() {
        this.loading.set(true);
        this.catalog.list({
            q: this.q || undefined,
            supplier_id: this.filterSupplierId ?? undefined,
            page: this.page,
            page_size: this.pageSize,
            sort: 'name',
        }).subscribe({
            next: r => {
                this.products.set(r.items);
                this.total.set(r.total);
                this.loading.set(false);
            },
            error: () => this.loading.set(false),
        });
    }

    pages(): number {
        return Math.max(1, Math.ceil(this.total() / this.pageSize));
    }

    nextPage() { if (this.page < this.pages()) { this.page++; this.refresh(); window.scrollTo({top: 0, behavior: 'smooth'}); } }
    prevPage() { if (this.page > 1) { this.page--; this.refresh(); window.scrollTo({top: 0, behavior: 'smooth'}); } }

    emptyForm(): ProductFormData {
        return {
            supplier_id: null,
            supplier_name: null,
            category_id: null,
            category_name: null,
            code: null,
            name: '',
            description: null,
            price: null,
            currency: 'ARS',
            iva: null,
            unit_per_pack: null,
            barcode: null,
            notes: null,
            payment_term_id: null,
        };
    }

    loadPaymentTerms(supplierId: number | null) {
        if (!supplierId) { this.paymentTerms.set([]); return; }
        this.admin.listPaymentTerms(supplierId, true).subscribe(t => this.paymentTerms.set(t));
    }

    openNew() {
        this.editingId.set(null);
        this.form = this.emptyForm();
        this.useNewSupplier = false;
        this.useNewCategory = false;
        this.newSupplierName = '';
        this.newCategoryName = '';
        this.clearExistingImages = false;
        this.existingThumbnail = null;
        this.paymentTerms.set([]);
        this.clearFiles();
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    edit(p: Product) {
        this.editingId.set(p.id);
        this.form = {
            supplier_id: p.supplier_id,
            supplier_name: null,
            category_id: p.category_id,
            category_name: null,
            code: p.code,
            name: p.name,
            description: p.description,
            price: p.price !== null && p.price !== undefined ? String(p.price) : null,
            currency: p.currency,
            iva: p.iva,
            payment_term_id: p.payment_term_id,
        };
        this.useNewSupplier = false;
        this.useNewCategory = false;
        this.newSupplierName = '';
        this.newCategoryName = '';
        this.clearExistingImages = false;
        this.existingThumbnail = p.thumbnail;
        this.clearFiles();
        if (p.supplier_id) {
            this.catalog.categories(p.supplier_id).subscribe(c => this.categories.set(c));
        }
        this.loadPaymentTerms(p.supplier_id);
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    onSupplierSelect() {
        this.form.category_id = null;
        this.form.payment_term_id = null;
        this.newCategoryName = '';
        this.useNewCategory = false;
        if (this.form.supplier_id) {
            this.catalog.categories(this.form.supplier_id).subscribe(c => this.categories.set(c));
        } else {
            this.categories.set([]);
        }
        this.loadPaymentTerms(this.form.supplier_id ?? null);
    }

    isDragging = signal(false);

    onFilesSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files) return;
        this.addFiles(Array.from(input.files));
        input.value = '';  // allow re-selecting same file
    }

    addFiles(files: File[]) {
        const images = files.filter(f => f.type.startsWith('image/'));
        if (!images.length) return;
        this.selectedFiles = [...this.selectedFiles, ...images];
        images.forEach(f => this.previewUrls = [...this.previewUrls, URL.createObjectURL(f)]);
    }

    onDragOver(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging.set(true);
    }

    onDragLeave(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging.set(false);
    }

    onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging.set(false);
        const files = event.dataTransfer?.files;
        if (files && files.length) {
            this.addFiles(Array.from(files));
        }
    }

    @HostListener('paste', ['$event'])
    onPaste(event: ClipboardEvent) {
        if (!this.showForm()) return;
        const target = event.target as HTMLElement;
        if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
        const items = event.clipboardData?.items;
        if (!items) return;
        const files: File[] = [];
        for (let i = 0; i < items.length; i++) {
            const it = items[i];
            if (it.kind === 'file' && it.type.startsWith('image/')) {
                const f = it.getAsFile();
                if (f) files.push(f);
            }
        }
        if (files.length) {
            event.preventDefault();
            this.addFiles(files);
        }
    }

    removeFile(i: number) {
        this.selectedFiles = this.selectedFiles.filter((_, idx) => idx !== i);
        URL.revokeObjectURL(this.previewUrls[i]);
        this.previewUrls = this.previewUrls.filter((_, idx) => idx !== i);
    }

    private clearFiles() {
        this.previewUrls.forEach(u => URL.revokeObjectURL(u));
        this.selectedFiles = [];
        this.previewUrls = [];
    }

    submit() {
        this.error.set(null);
        this.successMsg.set(null);
        if (!this.form.name?.trim()) { this.error.set('El nombre del producto es obligatorio'); return; }
        const body: ProductFormData = { ...this.form };
        if (this.useNewSupplier && this.newSupplierName.trim()) {
            body.supplier_id = null;
            body.supplier_name = this.newSupplierName.trim();
        }
        if (this.useNewCategory && this.newCategoryName.trim()) {
            body.category_id = null;
            body.category_name = this.newCategoryName.trim();
        }
        const editId = this.editingId();
        if (!editId && !body.supplier_id && !body.supplier_name) {
            this.error.set('Elegí o creá un proveedor');
            return;
        }
        this.saving.set(true);
        const op = editId
            ? this.admin.updateProduct(editId, body, this.selectedFiles, this.clearExistingImages)
            : this.admin.createProduct(body, this.selectedFiles);
        op.subscribe({
            next: () => {
                this.saving.set(false);
                this.successMsg.set(editId ? 'Producto actualizado' : 'Producto creado');
                this.showForm.set(false);
                this.editingId.set(null);
                this.clearFiles();
                this.refresh();
            },
            error: err => {
                this.saving.set(false);
                this.error.set(err?.error?.detail || 'Error al guardar');
            },
        });
    }

    confirmDelete(p: Product) {
        if (!confirm(`¿Eliminar "${p.name}"? Esta acción no se puede deshacer.`)) return;
        this.admin.deleteProduct(p.id).subscribe({
            next: () => { this.successMsg.set('Producto eliminado'); this.refresh(); },
            error: err => this.error.set(err?.error?.detail || 'Error al eliminar'),
        });
    }

    cancel() {
        this.showForm.set(false);
        this.editingId.set(null);
        this.clearFiles();
    }

    fmtPrice(p: number | string | null, mon: string | null): string {
        if (p === null || p === undefined) return '—';
        const n = typeof p === 'string' ? parseFloat(p) : p;
        if (Number.isNaN(n)) return '—';
        return (mon === 'USD' ? 'US$ ' : '$ ') +
            new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
    }
}
