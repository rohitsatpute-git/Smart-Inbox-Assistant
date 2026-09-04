import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const header = auth.header();
  if (header) {
    req = req.clone({ setHeaders: { Authorization: header } });
  }
  return next(req);
};
