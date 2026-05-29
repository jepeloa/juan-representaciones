import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';

import { AuthService } from './auth.service';

export const adminGuard: CanActivateFn = () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (auth.isAuthenticated() && auth.user()?.is_admin) return true;
    router.navigate(['/catalogo']);
    return false;
};
