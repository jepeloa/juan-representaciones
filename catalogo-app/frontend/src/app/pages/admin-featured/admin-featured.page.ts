import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CdkDropList, CdkDrag, CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';
import { Observable } from 'rxjs';

import { AdminService } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Product, Supplier } from '../../core/models';

type Section = 'catalog' | 'offer' | 'brand';
interface FItem { id: number; name: string; thumb: string | null; group: string; }
interface FGroup { label: string; items: FItem[]; }

@Component({
    selector: 'app-admin-featured',
    standalone: true,
    imports: [CommonModule, FormsModule, CdkDropList, CdkDrag],
    templateUrl: './admin-featured.page.html',
})
export class AdminFeaturedPage implements OnInit {
    section = signal<Section>('catalog');
    featured: Record<Section, ReturnType<typeof signal<FItem[]>>> = {
        catalog: signal<FItem[]>([]), offer: signal<FItem[]>([]), brand: signal<FItem[]>([]),
    };
    allItems: Record<Section, ReturnType<typeof signal<FItem[]>>> = {
        catalog: signal<FItem[]>([]), offer: signal<FItem[]>([]), brand: signal<FItem[]>([]),
    };

    selectedId: number | null = null;
    saving = signal(false);
    msg = signal<string | null>(null);

    constructor(private admin: AdminService, private catalog: CatalogService) {}

    private mapProduct = (p: Product): FItem => ({ id: p.id, name: p.name, thumb: p.thumbnail, group: p.supplier_name || '' });
    private mapSupplier = (s: Supplier): FItem => ({ id: s.id, name: s.name, thumb: s.image, group: '' });

    ngOnInit() {
        (['catalog', 'offer', 'brand'] as Section[]).forEach(s => { this.load(s); this.loadAll(s); });
    }

    private load(s: Section) {
        if (s === 'brand') {
            this.admin.getFeaturedBrands().subscribe(list => this.featured.brand.set(list.map(this.mapSupplier)));
        } else {
            this.admin.getFeatured(s).subscribe(list => this.featured[s].set(list.map(this.mapProduct)));
        }
    }

    private loadAll(s: Section, page = 1, acc: FItem[] = []) {
        if (s === 'brand') {
            this.catalog.suppliers().subscribe(list => this.allItems.brand.set(list.map(this.mapSupplier)));
            return;
        }
        this.catalog.list({ page_size: 200, page, sort: 'name', on_offer: s === 'offer' ? true : undefined })
            .subscribe(res => {
                const all = [...acc, ...res.items.map(this.mapProduct)];
                if (res.items.length && all.length < res.total) this.loadAll(s, page + 1, all);
                else this.allItems[s].set(all);
            });
    }

    setSection(s: Section) {
        this.section.set(s);
        this.selectedId = null;
        this.msg.set(null);
    }

    list(): FItem[] {
        return this.featured[this.section()]();
    }

    availableGroups = computed<FGroup[]>(() => {
        const s = this.section();
        const featuredIds = new Set(this.featured[s]().map(i => i.id));
        const groups: Record<string, FItem[]> = {};
        for (const it of this.allItems[s]()) {
            if (featuredIds.has(it.id)) continue;
            const key = it.group || (s === 'brand' ? 'Marcas' : 'Sin marca');
            (groups[key] ??= []).push(it);
        }
        return Object.keys(groups).sort().map(label => ({ label, items: groups[label] }));
    });

    drop(ev: CdkDragDrop<FItem[]>) {
        const arr = [...this.list()];
        moveItemInArray(arr, ev.previousIndex, ev.currentIndex);
        this.featured[this.section()].set(arr);
    }

    add() {
        const id = this.selectedId;
        if (!id) return;
        const s = this.section();
        const it = this.allItems[s]().find(x => x.id === id);
        if (!it || this.featured[s]().some(x => x.id === id)) return;
        this.featured[s].set([...this.featured[s](), it]);
        this.selectedId = null;
    }

    remove(it: FItem) {
        const s = this.section();
        this.featured[s].set(this.featured[s]().filter(x => x.id !== it.id));
    }

    save() {
        this.saving.set(true);
        this.msg.set(null);
        const s = this.section();
        const ids = this.list().map(i => i.id);
        const op: Observable<any[]> = s === 'brand' ? this.admin.setFeaturedBrands(ids) : this.admin.setFeatured(s, ids);
        op.subscribe({
            next: (list: any[]) => {
                this.featured[s].set(s === 'brand' ? list.map(this.mapSupplier) : list.map(this.mapProduct));
                this.saving.set(false);
                this.flash('Orden guardado');
            },
            error: () => { this.saving.set(false); this.flash('No se pudo guardar'); },
        });
    }

    private flash(m: string) {
        this.msg.set(m);
        setTimeout(() => this.msg.set(null), 2500);
    }
}
