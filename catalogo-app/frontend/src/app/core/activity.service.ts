import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { API_BASE } from './api';
import { AuthService } from './auth.service';

export type ActivityType =
    | 'page_view' | 'product_view' | 'add_to_cart'
    | 'view_conditions' | 'view_stock' | 'search';

/**
 * Registra actividad del usuario para el dashboard de Clientes (admin).
 * Es best-effort: si falla, no rompe nada ni molesta al usuario.
 */
@Injectable({ providedIn: 'root' })
export class ActivityService {
    constructor(private http: HttpClient, private auth: AuthService) {}

    track(eventType: ActivityType, opts: { label?: string | null; path?: string | null; refId?: number | null } = {}) {
        // Solo si está logueado (todas las rutas del back exigen token).
        if (!this.auth.token()) return;
        const body = {
            event_type: eventType,
            label: opts.label ?? null,
            path: opts.path ?? null,
            ref_id: opts.refId ?? null,
        };
        this.http.post(`${API_BASE}/activity`, body).subscribe({ next: () => {}, error: () => {} });
    }
}
