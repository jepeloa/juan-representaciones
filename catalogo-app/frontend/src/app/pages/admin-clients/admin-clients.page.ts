import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import {
    AdminService, ClientListItem, ClientDetail, ClientProfileBody, ClientOrder,
} from '../../core/admin.service';

type Tab = 'datos' | 'actividad' | 'compras';

@Component({
    selector: 'app-admin-clients',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-clients.page.html',
})
export class AdminClientsPage implements OnInit {
    clients = signal<ClientListItem[]>([]);
    loading = signal(true);

    selected = signal<ClientDetail | null>(null);
    loadingDetail = signal(false);
    tab = signal<Tab>('datos');

    form: ClientProfileBody = {};
    saving = signal(false);
    saved = signal(false);

    openOrders = new Set<number>();

    constructor(private admin: AdminService) {}

    ngOnInit() {
        this.load();
    }

    load() {
        this.loading.set(true);
        this.admin.listClients().subscribe({
            next: c => { this.clients.set(c); this.loading.set(false); },
            error: () => this.loading.set(false),
        });
    }

    open(c: ClientListItem) {
        this.loadingDetail.set(true);
        this.tab.set('datos');
        this.saved.set(false);
        this.openOrders.clear();
        this.admin.getClient(c.id).subscribe({
            next: d => {
                this.selected.set(d);
                this.form = { ...(d.profile ?? {}) };
                this.loadingDetail.set(false);
            },
            error: () => this.loadingDetail.set(false),
        });
    }

    back() {
        this.selected.set(null);
    }

    save() {
        const s = this.selected();
        if (!s) return;
        this.saving.set(true);
        this.saved.set(false);
        this.admin.saveClientProfile(s.id, this.form).subscribe({
            next: p => {
                this.selected.update(cur => cur ? { ...cur, profile: p } : cur);
                // Reflejar company_name en la lista
                this.clients.update(list => list.map(c =>
                    c.id === s.id ? { ...c, company_name: p.company_name ?? null } : c));
                this.saving.set(false);
                this.saved.set(true);
            },
            error: () => this.saving.set(false),
        });
    }

    toggleOrder(id: number) {
        if (this.openOrders.has(id)) this.openOrders.delete(id);
        else this.openOrders.add(id);
    }

    // ===== Helpers de presentación =====

    countOf(type: string): number {
        const s = this.selected();
        if (!s) return 0;
        return s.stats.by_type.find(b => b.event_type === type)?.count ?? 0;
    }

    fmtMoney(n: string | number | null | undefined, currency = 'ARS'): string {
        if (n === null || n === undefined) return '—';
        const v = typeof n === 'string' ? parseFloat(n) : n;
        if (Number.isNaN(v)) return '—';
        const f = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(v);
        return (currency === 'USD' ? 'US$ ' : '$ ') + f;
    }

    hasMoney(n: string | number | null | undefined): boolean {
        if (n === null || n === undefined) return false;
        const v = typeof n === 'string' ? parseFloat(n) : n;
        return !Number.isNaN(v) && v > 0;
    }

    fmtDate(s: string | null | undefined): string {
        if (!s) return '—';
        const d = new Date(s.endsWith('Z') || s.includes('+') ? s : s + 'Z');
        if (Number.isNaN(d.getTime())) return '—';
        return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    fmtDay(s: string | null | undefined): string {
        if (!s) return '—';
        const d = new Date(s.endsWith('Z') || s.includes('+') ? s : s + 'Z');
        if (Number.isNaN(d.getTime())) return '—';
        return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    /** Texto legible de un evento de actividad. */
    eventText(type: string, label: string | null): string {
        switch (type) {
            case 'login': return 'Inició sesión';
            case 'page_view': return 'Entró a ' + (label || 'una sección');
            case 'product_view': return 'Miró el producto ' + (label || '');
            case 'add_to_cart': return 'Agregó al carrito ' + (label || '');
            case 'view_conditions': return 'Vio condiciones de ' + (label || '');
            case 'view_stock': return 'Consultó stock de ' + (label || '');
            case 'search': return 'Buscó: ' + (label || '');
            case 'order': return label || 'Realizó una compra';
            default: return type;
        }
    }

    /** Color del puntito según el tipo de evento. */
    eventColor(type: string): string {
        switch (type) {
            case 'login': return 'bg-slate-400';
            case 'order': return 'bg-sage-500';
            case 'add_to_cart': return 'bg-brand-500';
            case 'product_view': return 'bg-brand-300';
            case 'search': return 'bg-gold-400';
            case 'view_conditions':
            case 'view_stock': return 'bg-cream-400';
            default: return 'bg-slate-300';
        }
    }

    orderTotalLabel(o: ClientOrder): string {
        const parts: string[] = [];
        if (this.hasMoney(o.total_ars)) parts.push(this.fmtMoney(o.total_ars, 'ARS'));
        if (this.hasMoney(o.total_usd)) parts.push(this.fmtMoney(o.total_usd, 'USD'));
        return parts.length ? parts.join(' + ') : this.fmtMoney(0, 'ARS');
    }
}
