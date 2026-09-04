import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-login',
  imports: [FormsModule],
  template: `
    <div class="login-wrap">
      <div class="card">
        <h1>Smart Inbox Assistant</h1>
        <p class="muted">Reviewer sign-in (HTTP Basic). Default: reviewer / reviewer123</p>
        <label>Username <input [(ngModel)]="user" name="user" /></label>
        <label>Password <input [(ngModel)]="password" name="password" type="password" /></label>
        <button (click)="submit()">Continue</button>
      </div>
    </div>
  `,
})
export class LoginComponent {
  user = 'reviewer';
  password = 'reviewer123';

  constructor(
    private auth: AuthService,
    private router: Router,
  ) {}

  submit(): void {
    this.auth.login(this.user, this.password);
    this.router.navigateByUrl('/');
  }
}
