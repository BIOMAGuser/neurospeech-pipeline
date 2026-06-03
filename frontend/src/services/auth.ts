import { jwtDecode } from 'jwt-decode';
import { apiPublicFetch } from '@/lib/api';

interface DecodedToken {
  exp: number;
  sub: string;
  is_admin?: boolean;
}

export class AuthService {
  private static TOKEN_KEY = 'auth_token';

  static async login(username: string, password: string): Promise<void> {
    const response = await apiPublicFetch('/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `Login failed with status ${response.status}`);
    }

    const data = await response.json();
    if (!data.access_token) {
      throw new Error('No access token received');
    }

    localStorage.setItem(this.TOKEN_KEY, data.access_token);
  }

  static logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
  }

  static getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(this.TOKEN_KEY);
  }

  static isTokenValid(): boolean {
    const token = this.getToken();
    if (!token) return false;

    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return decoded.exp > Date.now() / 1000;
    } catch {
      return false;
    }
  }

  static isAdmin(): boolean {
    const token = this.getToken();
    if (!token) return false;
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return decoded.is_admin === true;
    } catch {
      return false;
    }
  }

  static getUsername(): string | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return decoded.sub;
    } catch {
      return null;
    }
  }

  static getTokenExpiry(): number | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return decoded.exp;
    } catch {
      return null;
    }
  }

  static getAuthHeader(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

}
