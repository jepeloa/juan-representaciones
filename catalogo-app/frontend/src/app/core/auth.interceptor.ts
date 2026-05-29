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
            if (err.status === 401 && isApi && !req.url.endsWith('/auth/login')) {
                auth.logout();
                router.navigate(['/login']);
            }
            return throwError(() => err);
        }),
    );
};
