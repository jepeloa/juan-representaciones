import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AdminService, AdminUser, CreateUserBody } from '../../core/admin.service';
import { AuthService } from '../../core/auth.service';

@Component({
    selector: 'app-admin-users',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-users.page.html',
})
export class AdminUsersPage implements OnInit {
    users = signal<AdminUser[]>([]);
    loading = signal(true);
    saving = signal(false);
    error = signal<string | null>(null);
    successMsg = signal<string | null>(null);

    showForm = signal(false);
    form: CreateUserBody = this.emptyForm();
    editingId = signal<number | null>(null);

    constructor(public admin: AdminService, public auth: AuthService) {}

    ngOnInit() {
        this.refresh();
    }

    refresh() {
        this.loading.set(true);
        this.admin.listUsers().subscribe({
            next: u => { this.users.set(u); this.loading.set(false); },
            error: () => this.loading.set(false),
        });
    }

    emptyForm(): CreateUserBody {
        return { username: '', password: '', full_name: '', is_admin: false, is_active: true };
    }

    openNew() {
        this.editingId.set(null);
        this.form = this.emptyForm();
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    editUser(u: AdminUser) {
        this.editingId.set(u.id);
        this.form = {
            username: u.username,
            password: '',
            full_name: u.full_name || '',
            is_admin: u.is_admin,
            is_active: u.is_active,
        };
        this.showForm.set(true);
        this.error.set(null);
        this.successMsg.set(null);
    }

    submit() {
        this.error.set(null);
        const editId = this.editingId();
        if (!this.form.username.trim()) { this.error.set('Usuario obligatorio'); return; }
        if (!editId && !this.form.password) { this.error.set('Contraseña obligatoria'); return; }
        this.saving.set(true);
        if (editId) {
            const body: any = {
                full_name: this.form.full_name || null,
                is_admin: this.form.is_admin,
                is_active: this.form.is_active,
            };
            if (this.form.password) body.password = this.form.password;
            this.admin.updateUser(editId, body).subscribe({
                next: () => { this.saving.set(false); this.successMsg.set('Usuario actualizado'); this.showForm.set(false); this.refresh(); },
                error: err => { this.saving.set(false); this.error.set(err?.error?.detail || 'Error'); },
            });
        } else {
            this.admin.createUser({
                username: this.form.username.trim(),
                password: this.form.password,
                full_name: this.form.full_name || null,
                is_admin: this.form.is_admin,
                is_active: this.form.is_active,
            }).subscribe({
                next: () => { this.saving.set(false); this.successMsg.set('Usuario creado'); this.showForm.set(false); this.refresh(); },
                error: err => { this.saving.set(false); this.error.set(err?.error?.detail || 'Error'); },
            });
        }
    }

    confirmDelete(u: AdminUser) {
        if (u.id === this.auth.user()?.id) { this.error.set('No podés eliminar tu propio usuario'); return; }
        if (!confirm(`¿Eliminar el usuario "${u.username}"?`)) return;
        this.admin.deleteUser(u.id).subscribe({
            next: () => { this.successMsg.set('Usuario eliminado'); this.refresh(); },
            error: err => this.error.set(err?.error?.detail || 'Error'),
        });
    }

    toggleActive(u: AdminUser) {
        this.admin.updateUser(u.id, { is_active: !u.is_active }).subscribe({
            next: updated => {
                this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
            },
            error: err => this.error.set(err?.error?.detail || 'Error'),
        });
    }
}
