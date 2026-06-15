import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { CatalogService } from '../../core/catalog.service';
import { AuthService } from '../../core/auth.service';
import { AdminService } from '../../core/admin.service';
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

    constructor(private svc: CatalogService, public auth: AuthService, private admin: AdminService) {}

    get isAdmin(): boolean {
        return !!this.auth.user()?.is_admin;
    }

    ngOnInit() {
        this.load();
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

    clearImage(supplier: Supplier, ev: Event) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!confirm(`¿Quitar la foto de "${supplier.name}"?`)) return;
        this.admin.clearSupplierImage(supplier.id).subscribe(updated => {
            this.suppliers.update(list => list.map(s => s.id === updated.id ? { ...s, image: null } : s));
        });
    }
}
