import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { adminGuard } from './core/admin.guard';

export const routes: Routes = [
    {
        path: 'login',
        loadComponent: () => import('./pages/login/login.page').then(m => m.LoginPage),
    },
    {
        path: '',
        loadComponent: () => import('./layout/shell/shell.component').then(m => m.ShellComponent),
        canActivate: [authGuard],
        children: [
            { path: '', pathMatch: 'full', redirectTo: 'catalogo' },
            {
                path: 'catalogo',
                loadComponent: () => import('./pages/catalog/catalog.page').then(m => m.CatalogPage),
            },
            {
                path: 'ofertas',
                loadComponent: () => import('./pages/offers/offers.page').then(m => m.OffersPage),
            },
            {
                path: 'proveedores',
                loadComponent: () => import('./pages/suppliers/suppliers.page').then(m => m.SuppliersPage),
            },
            {
                path: 'carrito',
                loadComponent: () => import('./pages/cart/cart.page').then(m => m.CartPage),
            },
            {
                path: 'admin/ofertas',
                canActivate: [adminGuard],
                loadComponent: () => import('./pages/admin-offers/admin-offers.page').then(m => m.AdminOffersPage),
            },
            {
                path: 'admin/condiciones',
                canActivate: [adminGuard],
                loadComponent: () => import('./pages/admin-conditions/admin-conditions.page').then(m => m.AdminConditionsPage),
            },
            {
                path: 'admin/productos',
                canActivate: [adminGuard],
                loadComponent: () => import('./pages/admin-products/admin-products.page').then(m => m.AdminProductsPage),
            },
            {
                path: 'admin/usuarios',
                canActivate: [adminGuard],
                loadComponent: () => import('./pages/admin-users/admin-users.page').then(m => m.AdminUsersPage),
            },
        ],
    },
    { path: '**', redirectTo: 'catalogo' },
];
