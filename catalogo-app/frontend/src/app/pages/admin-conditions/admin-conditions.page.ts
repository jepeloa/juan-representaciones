import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AdminService, AdminPaymentCondition, AdminSettings, PaymentConditionBody } from '../../core/admin.service';

@Component({
    selector: 'app-admin-conditions',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-conditions.page.html',
})
export class AdminConditionsPage implements OnInit {
    conditions = signal<AdminPaymentCondition[]>([]);
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

    constructor(public admin: AdminService) {}

    ngOnInit() {
        this.refresh();
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
        return { name: '', description: '', multiplier: 1.0, days: null, is_active: true, sort_order: 0 };
    }

    openNew() {
        this.editingId.set(null);
        this.form = this.emptyForm();
        const maxOrder = this.conditions().reduce((m, c) => Math.max(m, c.sort_order), 0);
        this.form.sort_order = maxOrder + 1;
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    edit(c: AdminPaymentCondition) {
        this.editingId.set(c.id);
        this.form = {
            name: c.name,
            description: c.description || '',
            multiplier: Number(c.multiplier),
            days: c.days,
            is_active: c.is_active,
            sort_order: c.sort_order,
        };
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    saveCondition() {
        if (!this.form.name?.trim()) { this.error.set('El nombre es obligatorio'); return; }
        if (this.form.multiplier === null || this.form.multiplier === undefined) { this.error.set('El multiplicador es obligatorio'); return; }
        this.savingCondition.set(true);
        this.error.set(null);
        const body: PaymentConditionBody = {
            name: this.form.name.trim(),
            description: this.form.description || null,
            multiplier: Number(this.form.multiplier),
            days: this.form.days,
            is_active: this.form.is_active,
            sort_order: this.form.sort_order,
        };
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
