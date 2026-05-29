import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

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

    constructor(private auth: AuthService, private router: Router) {
        if (this.auth.isAuthenticated()) this.router.navigate(['/catalogo']);
    }

    submit() {
        if (!this.username || !this.password) return;
        this.loading.set(true);
        this.error.set(null);
        this.auth.login(this.username.trim(), this.password).subscribe({
            next: () => {
                this.loading.set(false);
                this.router.navigate(['/catalogo']);
            },
            error: err => {
                this.loading.set(false);
                this.error.set(err?.error?.detail || 'No se pudo iniciar sesión');
            },
        });
    }
}
