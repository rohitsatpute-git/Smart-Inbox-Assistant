import { Routes } from '@angular/router';
import { authGuard } from './auth.guard';
import { LoginComponent } from './login.component';
import { QueueComponent } from './queue.component';
import { DetailComponent } from './detail.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', component: QueueComponent, canActivate: [authGuard] },
  { path: 'messages/:id', component: DetailComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: '' },
];
