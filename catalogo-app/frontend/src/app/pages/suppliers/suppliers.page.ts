import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { CatalogService } from '../../core/catalog.service';
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

    constructor(private svc: CatalogService) {}

    ngOnInit() {
        this.svc.suppliers().subscribe({
            next: s => {
                this.suppliers.set(s);
                this.loading.set(false);
            },
            error: () => this.loading.set(false),
        });
    }
}
