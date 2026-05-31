import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AdminService, AdminPaymentTerm, PaymentTermBody } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Supplier } from '../../core/models';

@Component({
    selector: 'app-admin-payment-terms',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-payment-terms.page.html',
})
export class AdminPaymentTermsPage implements OnInit {
    terms = signal<AdminPaymentTerm[]>([]);
    suppliers = signal<Supplier[]>([]);
    loading = signal(true);
    saving = signal(false);
    error = signal<string | null>(null);
    successMsg = signal<string | null>(null);
    editingId = signal<number | null>(null);
    showForm = signal(false);
    form: PaymentTermBody = this.emptyForm();

    constructor(public admin: AdminService, private catalog: CatalogService) {}

    ngOnInit() {
        this.refresh();
        this.catalog.suppliers().subscribe(s => this.suppliers.set(s));
    }

    refresh() {
        this.loading.set(true);
        this.admin.listPaymentTerms().subscribe({
            next: t => { this.terms.set(t); this.loading.set(false); },
            error: () => this.loading.set(false),
        });
    }

    emptyForm(): PaymentTermBody {
        return { text: '', supplier_id: null, is_active: true, sort_order: 0 };
    }

    openNew() {
        this.editingId.set(null);
        this.form = this.emptyForm();
        const maxOrder = this.terms().reduce((m, c) => Math.max(m, c.sort_order), 0);
        this.form.sort_order = maxOrder + 1;
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    edit(t: AdminPaymentTerm) {
        this.editingId.set(t.id);
        this.form = { text: t.text, supplier_id: t.supplier_id, is_active: t.is_active, sort_order: t.sort_order };
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    save() {
        if (!this.form.text?.trim()) { this.error.set('El texto de la condición es obligatorio'); return; }
        this.saving.set(true);
        this.error.set(null);
        const body: PaymentTermBody = {
            text: this.form.text.trim(),
            supplier_id: this.form.supplier_id ?? null,
            is_active: this.form.is_active,
            sort_order: this.form.sort_order,
        };
        const id = this.editingId();
        const op = id ? this.admin.updatePaymentTerm(id, body) : this.admin.createPaymentTerm(body);
        op.subscribe({
            next: () => {
                this.saving.set(false);
                this.successMsg.set(id ? 'Condición actualizada' : 'Condición creada');
                this.showForm.set(false);
                this.refresh();
            },
            error: err => {
                this.saving.set(false);
                this.error.set(err?.error?.detail || 'Error al guardar');
            },
        });
    }

    confirmDelete(t: AdminPaymentTerm) {
        if (!confirm(`¿Eliminar esta condición?\n\n"${t.text}"\n\nLos productos que la usen quedarán sin condición.`)) return;
        this.admin.deletePaymentTerm(t.id).subscribe({
            next: () => { this.successMsg.set('Condición eliminada'); this.refresh(); },
            error: err => this.error.set(err?.error?.detail || 'Error'),
        });
    }

    supplierLabel(id: number | null): string {
        if (id === null || id === undefined) return 'Todos los proveedores';
        return this.suppliers().find(s => s.id === id)?.name ?? '—';
    }
}
