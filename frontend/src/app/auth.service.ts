import { Injectable } from '@angular/core';

const KEY = 'sia-auth';

@Injectable({ providedIn: 'root' })
export class AuthService {
  login(user: string, password: string): void {
    sessionStorage.setItem(KEY, btoa(`${user}:${password}`));
  }

  logout(): void {
    sessionStorage.removeItem(KEY);
  }

  isLoggedIn(): boolean {
    return !!sessionStorage.getItem(KEY);
  }

  header(): string | null {
    const raw = sessionStorage.getItem(KEY);
    return raw ? `Basic ${raw}` : null;
  }
}
