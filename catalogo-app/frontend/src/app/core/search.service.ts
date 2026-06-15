import { Injectable, signal } from '@angular/core';

/** Texto de búsqueda del catálogo, compartido entre el buscador del shell y la página. */
@Injectable({ providedIn: 'root' })
export class SearchService {
    query = signal('');
}
