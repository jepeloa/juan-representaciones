import { Injectable, signal } from '@angular/core';

export interface ConfirmOptions {
    title?: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    danger?: boolean;
}

interface ConfirmState extends ConfirmOptions {
    open: boolean;
}

/**
 * Confirmación con una ventana emergente propia (reemplaza al confirm() del navegador).
 * Uso:  if (await this.confirm.ask({ message: '¿Seguro?' })) { ... }
 */
@Injectable({ providedIn: 'root' })
export class ConfirmService {
    private _state = signal<ConfirmState>({ open: false, message: '' });
    state = this._state.asReadonly();

    private resolver: ((v: boolean) => void) | null = null;

    ask(opts: ConfirmOptions): Promise<boolean> {
        this._state.set({
            open: true,
            confirmText: 'Aceptar',
            cancelText: 'Cancelar',
            danger: false,
            ...opts,
        });
        return new Promise<boolean>(res => (this.resolver = res));
    }

    resolve(value: boolean) {
        this._state.update(s => ({ ...s, open: false }));
        const r = this.resolver;
        this.resolver = null;
        r?.(value);
    }
}
