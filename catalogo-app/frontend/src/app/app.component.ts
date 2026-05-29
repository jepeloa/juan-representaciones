import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

import { SplashPage } from './pages/splash/splash.page';

const SPLASH_KEY = 'splashShown';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, RouterOutlet, SplashPage],
    template: `
        <app-splash *ngIf="showSplash()" (done)="hideSplash()"></app-splash>
        <router-outlet></router-outlet>
    `,
})
export class AppComponent {
    showSplash = signal(true);

    constructor() {
        try {
            if (sessionStorage.getItem(SPLASH_KEY) === 'true') {
                this.showSplash.set(false);
            } else {
                sessionStorage.setItem(SPLASH_KEY, 'true');
            }
        } catch {
            // sessionStorage may not be available
        }
    }

    hideSplash() {
        this.showSplash.set(false);
    }
}
