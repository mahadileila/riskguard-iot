import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const isLoginRequest = req.url.includes('/auth/login');
  const token = authService.getToken();

  if (token && !isLoginRequest) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
       if (error.status === 401 && !isLoginRequest) {
        authService.logout(true);
      }
      return throwError(() => error);
    })
  );
};