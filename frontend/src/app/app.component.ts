import { Component } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink],
  template: `
    <header class="top">
      <a routerLink="/" class="brand">Smart Inbox Assistant</a>
      <span class="tag">Synthetic data only</span>
      @if (auth.isLoggedIn()) {
        <button class="ghost" (click)="logout()">Sign out</button>
      }
    </header>
    <router-outlet />
  `,
})
export class AppComponent {
  constructor(
    public auth: AuthService,
    private router: Router,
  ) {}

  logout(): void {
    this.auth.logout();
    this.router.navigateByUrl('/login');
  }
}
