import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

interface LoginResponse {
  token: string;
  username: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'auth_token';
  private logoutTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private http: HttpClient, private router: Router) {
    // If the page is reloaded with a still-valid token, keep the automatic
    // logout scheduled for the moment it expires.
    const token = this.getToken();
    if (token) {
      if (this.isTokenExpired(token)) {
        this.clearToken();
      } else {
        this.scheduleAutoLogout(token);
      }
    }
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>('/api/auth/login', { username, password }).pipe(
      tap(response => {
        try {
          localStorage.setItem(this.TOKEN_KEY, response.token);
        } catch {
          // storage unavailable: the user will simply have to log in again
        }
        this.scheduleAutoLogout(response.token);
      })
    );
  }

   logout(sessionExpired = false) {
    this.clearToken();
    this.router.navigate(
      ['/login'],
      sessionExpired ? { queryParams: { expired: '1' } } : undefined
    );
  }

  getToken(): string | null {
    try {
      return localStorage.getItem(this.TOKEN_KEY);
    } catch {
      return null;
    }
  }

  /** True only if a token exists AND has not expired yet. */
  isAuthenticated(): boolean {
    const token = this.getToken();
    if (!token) return false;

    if (this.isTokenExpired(token)) {
      this.clearToken();
      return false;
    }
    return true;
  }

  private clearToken() {
    if (this.logoutTimer) {
      clearTimeout(this.logoutTimer);
      this.logoutTimer = null;
    }
    try {
      localStorage.removeItem(this.TOKEN_KEY);
    } catch {
      // ignore
    }
  }

  /** Reads the "exp" claim (seconds since epoch) from the JWT payload. */
  private getExpiryMs(token: string): number | null {
    try {
      const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      const exp = JSON.parse(atob(payload)).exp;
      return typeof exp === 'number' ? exp * 1000 : null;
    } catch {
      return null;
    }
  }

  private isTokenExpired(token: string): boolean {
    const expiryMs = this.getExpiryMs(token);
    return expiryMs === null || expiryMs <= Date.now();
  }

    private scheduleAutoLogout(token: string) {
    if (this.logoutTimer) {
      clearTimeout(this.logoutTimer);
      this.logoutTimer = null;
    }

    const expiryMs = this.getExpiryMs(token);
    if (expiryMs === null) return;

    // setTimeout cannot exceed ~24.8 days; our tokens last 24 hours.
    const delay = Math.min(Math.max(expiryMs - Date.now(), 0), 2_147_483_647);
    this.logoutTimer = setTimeout(() => this.logout(true), delay);
  }
}