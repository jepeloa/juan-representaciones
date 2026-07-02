import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ConfirmService } from '../core/confirm.service';

@Component({
    selector: 'app-confirm-dialog',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div *ngIf="confirm.state() as s">
      <div *ngIf="s.open"
           class="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
           (click)="confirm.resolve(false)">
        <div class="card max-w-md w-full overflow-hidden animate-[fadeIn_.15s_ease]" (click)="$event.stopPropagation()">
          <div class="px-5 py-4 border-b border-cream-200">
            <h3 class="font-display text-lg font-bold text-slate-800">{{ s.title || 'Confirmar' }}</h3>
          </div>
          <div class="px-5 py-4 text-sm text-slate-600 whitespace-pre-line">{{ s.message }}</div>
          <div class="flex justify-end gap-2 p-4 border-t border-cream-200 bg-cream-50">
            <button class="btn-ghost" (click)="confirm.resolve(false)">{{ s.cancelText || 'Cancelar' }}</button>
            <button (click)="confirm.resolve(true)"
                    class="inline-flex items-center justify-center rounded-lg px-4 py-2 font-medium text-white shadow-soft transition"
                    [class.bg-blush-500]="s.danger" [class.hover:bg-blush-600]="s.danger"
                    [class.bg-brand-500]="!s.danger" [class.hover:bg-brand-600]="!s.danger">
              {{ s.confirmText || 'Aceptar' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class ConfirmDialogComponent {
    constructor(public confirm: ConfirmService) {}
}
