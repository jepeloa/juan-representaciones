import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { CatalogService } from '../../core/catalog.service';
import { AuthService } from '../../core/auth.service';
import { AdminService, AdminPaymentCondition } from '../../core/admin.service';
import { Supplier } from '../../core/models';

@Component({
    selector: 'app-suppliers',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './suppliers.page.html',
})
export class SuppliersPage implements OnInit {
    suppliers = signal<Supplier[]>([]);
    loading = signal(true);
    uploadingId = signal<number | null>(null);

    // Modal de condiciones de pago de una marca (cliente: ver)
    conditionsOf = signal<Supplier | null>(null);

    // Editor de condiciones por marca (admin)
    allConditions = signal<AdminPaymentCondition[]>([]);
    editCondsOf = signal<Supplier | null>(null);
    selectedCondIds: number[] = [];
    savingConds = signal(false);

    constructor(private svc: CatalogService, public auth: AuthService, private admin: AdminService) {}

    get isAdmin(): boolean {
        return !!this.auth.user()?.is_admin;
    }

    ngOnInit() {
        this.load();
        if (this.isAdmin) this.admin.listConditions().subscribe(c => this.allConditions.set(c));
    }

    openEditConds(s: Supplier, ev: Event) {
        ev.preventDefault();
        ev.stopPropagation();
        this.editCondsOf.set(s);
        this.selectedCondIds = (s.payment_conditions ?? []).map(c => c.id);
    }

    isCondSelected(id: number): boolean {
        return this.selectedCondIds.includes(id);
    }

    toggleCond(id: number) {
        this.selectedCondIds = this.selectedCondIds.includes(id)
            ? this.selectedCondIds.filter(x => x !== id)
            : [...this.selectedCondIds, id];
    }

    saveConds() {
        const s = this.editCondsOf();
        if (!s) return;
        this.savingConds.set(true);
        this.admin.setSupplierConditions(s.id, this.selectedCondIds).subscribe({
            next: updated => {
                this.suppliers.update(list => list.map(x => x.id === updated.id ? { ...x, payment_conditions: updated.payment_conditions } : x));
                this.savingConds.set(false);
                this.editCondsOf.set(null);
            },
            error: () => this.savingConds.set(false),
        });
    }

    closeEditConds() {
        this.editCondsOf.set(null);
    }

    private load() {
        this.svc.suppliers().subscribe({
            next: s => { this.suppliers.set(s); this.loading.set(false); },
            error: () => this.loading.set(false),
        });
    }

    onPick(supplier: Supplier, ev: Event) {
        const input = ev.target as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) return;
        this.uploadingId.set(supplier.id);
        this.admin.setSupplierImage(supplier.id, file).subscribe({
            next: updated => {
                this.suppliers.update(list => list.map(s => s.id === updated.id ? { ...s, image: updated.image } : s));
                this.uploadingId.set(null);
                input.value = '';
            },
            error: () => { this.uploadingId.set(null); input.value = ''; },
        });
    }

    openConditions(supplier: Supplier, ev: Event) {
        ev.preventDefault();
        ev.stopPropagation();
        this.conditionsOf.set(supplier);
    }

    closeConditions() {
        this.conditionsOf.set(null);
    }

    clearImage(supplier: Supplier, ev: Event) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!confirm(`¿Quitar la foto de "${supplier.name}"?`)) return;
        this.admin.clearSupplierImage(supplier.id).subscribe(updated => {
            this.suppliers.update(list => list.map(s => s.id === updated.id ? { ...s, image: null } : s));
        });
    }
}
