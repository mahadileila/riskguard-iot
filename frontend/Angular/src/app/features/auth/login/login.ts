import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html'
})
export class Login {
  username = '';
  password = '';
  error: string | null = null;
  loading = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef
  ) {
    if (this.route.snapshot.queryParamMap.get('expired')) {
      this.error = 'Your session has expired. Please log in again.';
    }
  }

  submit() {
    if (!this.username.trim() || !this.password.trim()) {
      this.error = 'Username and password are required.';
      return;
    }

    this.loading = true;
    this.error = null;

    this.authService.login(this.username, this.password).subscribe({
      next: () => {
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.loading = false;
        this.error = 'Invalid username or password.';
        this.cdr.detectChanges();
      }
    });
  }
}