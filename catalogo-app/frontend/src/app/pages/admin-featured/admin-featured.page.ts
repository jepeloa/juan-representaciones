import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CdkDropList, CdkDrag, CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';
import { Subject, debounceTime } from 'rxjs';

import { AdminService } from '../../core/admin.service';
import { CatalogService } from '../../core/catalog.service';
import { Product } from '../../core/models';

type Section = 'catalog' | 'offer';

@Component({
    selector: 'app-admin-featured',
    standalone: true,
    imports: [CommonModule, FormsModule, CdkDropList, CdkDrag],
    templateUrl: './admin-featured.page.html',
})
export class AdminFeaturedPage implements OnInit {
    section: Section = 'catalog';
    featured: Record<Section, Product[]> = { catalog: [], offer: [] };

    q = '';
    results = signal<Product[]>([]);
    searching = signal(false);
    saving = signal(false);
    msg = signal<string | null>(null);

    private search$ = new Subject<void>();

    constructor(private admin: AdminService, private catalog: CatalogService) {
        this.search$.pipe(debounceTime(300)).subscribe(() => this.runSearch());
    }

    ngOnInit() {
        this.load('catalog');
        this.load('offer');
    }

    private load(s: Section) {
        this.admin.getFeatured(s).subscribe(list => (this.featured[s] = list));
    }

    setSection(s: Section) {
        this.section = s;
        this.q = '';
        this.results.set([]);
        this.msg.set(null);
    }

    get list(): Product[] {
        return this.featured[this.section];
    }

    drop(ev: CdkDragDrop<Product[]>) {
        moveItemInArray(this.list, ev.previousIndex, ev.currentIndex);
    }

    onSearch() {
        this.search$.next();
    }

    private runSearch() {
        const term = this.q.trim();
        if (!term) { this.results.set([]); return; }
        this.searching.set(true);
        this.catalog.list({
            q: term,
            page_size: 20,
            sort: 'name',
            on_offer: this.section === 'offer' ? true : undefined,
        }).subscribe({
            next: res => {
                const ids = new Set(this.list.map(p => p.id));
                this.results.set(res.items.filter(p => !ids.has(p.id)));
                this.searching.set(false);
            },
            error: () => this.searching.set(false),
        });
    }

    add(p: Product) {
        if (this.list.some(x => x.id === p.id)) return;
        this.featured[this.section] = [...this.list, p];
        this.q = '';
        this.results.set([]);
    }

    remove(p: Product) {
        this.featured[this.section] = this.list.filter(x => x.id !== p.id);
    }

    save() {
        this.saving.set(true);
        this.msg.set(null);
        const s = this.section;
        this.admin.setFeatured(s, this.list.map(p => p.id)).subscribe({
            next: list => { this.featured[s] = list; this.saving.set(false); this.flash('Orden guardado'); },
            error: () => { this.saving.set(false); this.flash('No se pudo guardar'); },
        });
    }

    private flash(m: string) {
        this.msg.set(m);
        setTimeout(() => this.msg.set(null), 2500);
    }
}
