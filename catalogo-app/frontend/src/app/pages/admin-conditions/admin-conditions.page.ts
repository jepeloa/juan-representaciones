import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AdminService, AdminPaymentCondition, AdminSettings, PaymentConditionBody } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Supplier } from '../../core/models';

@Component({
    selector: 'app-admin-conditions',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-conditions.page.html',
})
export class AdminConditionsPage implements OnInit {
    conditions = signal<AdminPaymentCondition[]>([]);
    suppliers = signal<Supplier[]>([]);
    settings = signal<AdminSettings>({
        catalog_disclaimer: null,
        catalog_terms: null,
        company_name: null,
        company_contact: null,
        order_notification_email: null,
    });

    loading = signal(true);
    savingCondition = signal(false);
    savingSettings = signal(false);
    error = signal<string | null>(null);
    successMsg = signal<string | null>(null);

    editingId = signal<number | null>(null);
    showForm = signal(false);
    form: PaymentConditionBody = this.emptyForm();

    constructor(public admin: AdminService, private catalog: CatalogService) {}

    ngOnInit() {
        this.refresh();
        this.catalog.suppliers().subscribe(s => this.suppliers.set(s));
    }

    refresh() {
        this.loading.set(true);
        this.admin.listConditions().subscribe(c => {
            this.conditions.set(c);
            this.loading.set(false);
        });
        this.admin.getSettings().subscribe(s => this.settings.set(s));
    }

    emptyForm(): PaymentConditionBody {
        return { text: '' };
    }

    supplierNames(c: AdminPaymentCondition): string {
        const byId = new Map(this.suppliers().map(s => [s.id, s.name]));
        return (c.supplier_ids ?? []).map(id => byId.get(id)).filter(Boolean).join(', ');
    }

    openNew() {
        this.editingId.set(null);
        this.form = this.emptyForm();
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    edit(c: AdminPaymentCondition) {
        this.editingId.set(c.id);
        this.form = { text: c.description || c.name };
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    saveCondition() {
        if (!this.form.text?.trim()) { this.error.set('Escribí la condición'); return; }
        this.savingCondition.set(true);
        this.error.set(null);
        const body: PaymentConditionBody = { text: this.form.text.trim() };
        const editId = this.editingId();
        const op = editId
            ? this.admin.updateCondition(editId, body)
            : this.admin.createCondition(body);
        op.subscribe({
            next: () => {
                this.savingCondition.set(false);
                this.successMsg.set(editId ? 'Condición actualizada' : 'Condición creada');
                this.showForm.set(false);
                this.refresh();
            },
            error: err => {
                this.savingCondition.set(false);
                this.error.set(err?.error?.detail || 'Error al guardar');
            },
        });
    }

    confirmDelete(c: AdminPaymentCondition) {
        if (!confirm(`¿Eliminar "${c.name}"?`)) return;
        this.admin.deleteCondition(c.id).subscribe({
            next: () => { this.successMsg.set('Condición eliminada'); this.refresh(); },
            error: err => this.error.set(err?.error?.detail || 'Error'),
        });
    }

    saveSettings() {
        this.savingSettings.set(true);
        this.error.set(null);
        this.admin.updateSettings(this.settings()).subscribe({
            next: s => { this.savingSettings.set(false); this.settings.set(s); this.successMsg.set('Términos guardados'); },
            error: err => { this.savingSettings.set(false); this.error.set(err?.error?.detail || 'Error'); },
        });
    }

    pctLabel(mult: number | string): string {
        const m = Number(mult);
        if (m === 1) return 'lista';
        if (m > 1) return `+${((m - 1) * 100).toFixed(1)}%`;
        return `−${((1 - m) * 100).toFixed(1)}%`;
    }

    setSetting(key: keyof AdminSettings, value: string | null) {
        const next = { ...this.settings(), [key]: value };
        this.settings.set(next);
    }
}
