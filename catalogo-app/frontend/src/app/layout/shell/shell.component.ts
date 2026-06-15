import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../../core/auth.service';
import { CartService } from '../../core/cart.service';

interface NavItem {
    label: string;
    icon: string;
    route: string;
    adminOnly?: boolean;
    showBadge?: boolean;
}

@Component({
    selector: 'app-shell',
    standalone: true,
    imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
    templateUrl: './shell.component.html',
})
export class ShellComponent {
    /** Desktop: collapsed vs expanded width. */
    sidebarCollapsed = signal(false);
    /** Mobile: drawer open (slides in from left). */
    mobileOpen = signal(false);
    userMenuOpen = signal(false);

    private allNav: NavItem[] = [
        {
            label: 'Catálogo',
            route: '/catalogo',
            icon: 'M3.75 6.75A2.25 2.25 0 0 1 6 4.5h12a2.25 2.25 0 0 1 2.25 2.25v10.5A2.25 2.25 0 0 1 18 19.5H6a2.25 2.25 0 0 1-2.25-2.25Zm3 0v.75h10.5v-.75H6.75ZM6.75 11.25h10.5v6H6.75Z',
        },
        {
            label: 'Ofertas',
            route: '/ofertas',
            icon: 'M11.7 2.8a2 2 0 0 1 .6 0l7 1.2a1 1 0 0 1 .8.8l1.2 7a2 2 0 0 1-.55 1.74l-8.2 8.2a2 2 0 0 1-2.83 0l-6.5-6.5a2 2 0 0 1 0-2.83l8.2-8.2a2 2 0 0 1 1.07-.55Zm4.3 4.2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z',
        },
        {
            label: 'Mi orden',
            route: '/carrito',
            icon: 'M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z',
            showBadge: true,
        },
        {
            label: 'Proveedores',
            route: '/proveedores',
            icon: 'M3 4.5h18v3H3zm2 5h14v10H5zM9 12h6v4H9z',
        },
        {
            label: 'Cargar productos',
            route: '/admin/productos',
            icon: 'M12 4v16m-8-8h16',
            adminOnly: true,
        },
        {
            label: 'Gestionar ofertas',
            route: '/admin/ofertas',
            icon: 'M11.7 2.8a2 2 0 0 1 .6 0l7 1.2a1 1 0 0 1 .8.8l1.2 7a2 2 0 0 1-.55 1.74l-8.2 8.2a2 2 0 0 1-2.83 0l-6.5-6.5a2 2 0 0 1 0-2.83l8.2-8.2a2 2 0 0 1 1.07-.55Zm4.3 4.2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z',
            adminOnly: true,
        },
        {
            label: 'Condiciones',
            route: '/admin/condiciones',
            icon: 'M3 5.25a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 5.25v13.5A2.25 2.25 0 0 1 18.75 21H5.25A2.25 2.25 0 0 1 3 18.75Zm4.5 4.5h9v1.5h-9zm0 4.5h6v1.5h-6z',
            adminOnly: true,
        },
        {
            label: 'Usuarios',
            route: '/admin/usuarios',
            icon: 'M15 8a3 3 0 1 0-6 0 3 3 0 0 0 6 0Zm6 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm-3 5a5 5 0 0 0-5 5v1h10v-1a5 5 0 0 0-5-5Zm-9 6v-1a5 5 0 0 1 5-5h0a4.99 4.99 0 0 0-2 4v2H9Z',
            adminOnly: true,
        },
    ];

    nav = computed<NavItem[]>(() =>
        this.allNav.filter(item => !item.adminOnly || this.auth.user()?.is_admin),
    );

    get isAdmin(): boolean {
        return !!this.auth.user()?.is_admin;
    }

    constructor(public auth: AuthService, public cart: CartService, private router: Router) {
        // Auto-close mobile drawer on navigation.
        this.router.events
            .pipe(filter(e => e instanceof NavigationEnd))
            .subscribe(() => this.mobileOpen.set(false));
    }

    toggleSidebar() {
        this.sidebarCollapsed.update(v => !v);
    }

    toggleMobile() {
        this.mobileOpen.update(v => !v);
    }

    toggleUserMenu() {
        this.userMenuOpen.update(v => !v);
    }

    logout() {
        this.auth.logout();
        this.router.navigate(['/login']);
    }
}
