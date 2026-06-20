import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const token = auth.token();
    const isApi = req.url.startsWith('/api');
    const cloned = isApi && token
        ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
        : req;
    return next(cloned).pipe(
        catchError((err: HttpErrorResponse) => {
            const isLogin = req.url.endsWith('/auth/login');
            // 401: token inválido o vencido.
            // 403 con sesión que se cree admin: desajuste token↔usuario (p. ej. otra
            //     pestaña inició sesión como cliente y pisó el token). Forzar re-login.
            const tokenMismatch = err.status === 403 && !!auth.user()?.is_admin;
            if (isApi && !isLogin && (err.status === 401 || tokenMismatch)) {
                auth.logout();
                router.navigate(['/login'], { queryParams: { expired: 1 } });
            }
            return throwError(() => err);
        }),
    );
};
