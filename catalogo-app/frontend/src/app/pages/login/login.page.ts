import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';

@Component({
    selector: 'app-login',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './login.page.html',
})
export class LoginPage {
    username = '';
    password = '';
    loading = signal(false);
    error = signal<string | null>(null);
    notice = signal<string | null>(null);

    constructor(private auth: AuthService, private router: Router, private route: ActivatedRoute) {
        if (this.auth.isAuthenticated()) this.router.navigate([this.home()]);
        if (this.route.snapshot.queryParamMap.get('expired')) {
            this.notice.set('Tu sesión expiró o se inició sesión con otra cuenta. Volvé a ingresar.');
        }
    }

    /** Cliente arranca en Marcas; admin en Productos. */
    private home(): string {
        return this.auth.user()?.is_admin ? '/catalogo' : '/proveedores';
    }

    submit() {
        if (!this.username || !this.password) return;
        this.loading.set(true);
        this.error.set(null);
        this.auth.login(this.username.trim(), this.password).subscribe({
            next: () => {
                this.loading.set(false);
                this.router.navigate([this.home()]);
            },
            error: err => {
                this.loading.set(false);
                this.error.set(err?.error?.detail || 'No se pudo iniciar sesión');
            },
        });
    }
}
