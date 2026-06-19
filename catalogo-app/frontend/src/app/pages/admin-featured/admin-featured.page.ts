import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CdkDropList, CdkDrag, CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';

import { AdminService } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Product } from '../../core/models';

type Section = 'catalog' | 'offer';
interface ProductGroup { supplier: string; items: Product[]; }

@Component({
    selector: 'app-admin-featured',
    standalone: true,
    imports: [CommonModule, FormsModule, CdkDropList, CdkDrag],
    templateUrl: './admin-featured.page.html',
})
export class AdminFeaturedPage implements OnInit {
    section = signal<Section>('catalog');
    featured: Record<Section, ReturnType<typeof signal<Product[]>>> = {
        catalog: signal<Product[]>([]),
        offer: signal<Product[]>([]),
    };
    allProducts: Record<Section, ReturnType<typeof signal<Product[]>>> = {
        catalog: signal<Product[]>([]),
        offer: signal<Product[]>([]),
    };

    selectedId: number | null = null;
    saving = signal(false);
    msg = signal<string | null>(null);

    constructor(private admin: AdminService, private catalog: CatalogService) {}

    ngOnInit() {
        this.load('catalog');
        this.load('offer');
        this.loadAll('catalog');
        this.loadAll('offer');
    }

    private load(s: Section) {
        this.admin.getFeatured(s).subscribe(list => this.featured[s].set(list));
    }

    /** Catálogo completo (o solo ofertas) para el desplegable; pagina de a 200. */
    private loadAll(s: Section, page = 1, acc: Product[] = []) {
        this.catalog.list({
            page_size: 200, page, sort: 'name',
            on_offer: s === 'offer' ? true : undefined,
        }).subscribe(res => {
            const all = [...acc, ...res.items];
            if (res.items.length && all.length < res.total) {
                this.loadAll(s, page + 1, all);
            } else {
                this.allProducts[s].set(all);
            }
        });
    }

    setSection(s: Section) {
        this.section.set(s);
        this.selectedId = null;
        this.msg.set(null);
    }

    list(): Product[] {
        return this.featured[this.section()]();
    }

    /** Productos disponibles (no destacados aún) agrupados por marca. */
    availableGroups = computed<ProductGroup[]>(() => {
        const s = this.section();
        const featuredIds = new Set(this.featured[s]().map(p => p.id));
        const groups: Record<string, Product[]> = {};
        for (const p of this.allProducts[s]()) {
            if (featuredIds.has(p.id)) continue;
            const sup = p.supplier_name || 'Sin marca';
            (groups[sup] ??= []).push(p);
        }
        return Object.keys(groups).sort().map(sup => ({ supplier: sup, items: groups[sup] }));
    });

    drop(ev: CdkDragDrop<Product[]>) {
        const arr = [...this.list()];
        moveItemInArray(arr, ev.previousIndex, ev.currentIndex);
        this.featured[this.section()].set(arr);
    }

    add() {
        const id = this.selectedId;
        if (!id) return;
        const s = this.section();
        const p = this.allProducts[s]().find(x => x.id === id);
        if (!p || this.featured[s]().some(x => x.id === id)) return;
        this.featured[s].set([...this.featured[s](), p]);
        this.selectedId = null;
    }

    remove(p: Product) {
        const s = this.section();
        this.featured[s].set(this.featured[s]().filter(x => x.id !== p.id));
    }

    save() {
        this.saving.set(true);
        this.msg.set(null);
        const s = this.section();
        this.admin.setFeatured(s, this.list().map(p => p.id)).subscribe({
            next: list => { this.featured[s].set(list); this.saving.set(false); this.flash('Orden guardado'); },
            error: () => { this.saving.set(false); this.flash('No se pudo guardar'); },
        });
    }

    private flash(m: string) {
        this.msg.set(m);
        setTimeout(() => this.msg.set(null), 2500);
    }
}
