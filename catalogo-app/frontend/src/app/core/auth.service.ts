import { Injectable, computed, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import { API_BASE } from './api';
import { AuthResponse, User } from './models';

const TOKEN_KEY = 'catalogo_token';
const USER_KEY = 'catalogo_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
    private _user = signal<User | null>(this.restoreUser());
    user = computed(() => this._user());
    isAuthenticated = computed(() => !!this._user() && !!this.token());

    constructor(private http: HttpClient) {}

    login(username: string, password: string): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(`${API_BASE}/auth/login`, { username, password }).pipe(
            tap(res => {
                localStorage.setItem(TOKEN_KEY, res.access_token);
                localStorage.setItem(USER_KEY, JSON.stringify(res.user));
                this._user.set(res.user);
            }),
        );
    }

    logout(): void {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        this._user.set(null);
    }

    token(): string | null {
        return localStorage.getItem(TOKEN_KEY);
    }

    private restoreUser(): User | null {
        const raw = localStorage.getItem(USER_KEY);
        if (!raw) return null;
        try { return JSON.parse(raw); } catch { return null; }
    }
}
