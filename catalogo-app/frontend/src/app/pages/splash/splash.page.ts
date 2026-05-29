import { Component, EventEmitter, OnInit, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-splash',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './splash.page.html',
})
export class SplashPage implements OnInit {
    @Output() done = new EventEmitter<void>();
    fading = signal(false);

    ngOnInit() {
        setTimeout(() => this.fading.set(true), 1700);
        setTimeout(() => this.done.emit(), 2200);
    }
}
