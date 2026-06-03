/**
 * Centralized API client.
 * Single place for base URL, auth headers, and error handling.
 */

import { AuthService } from '@/services/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Make an authenticated fetch request to the backend API.
 * Automatically prepends the base URL and attaches the JWT token.
 */
export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = {
    ...AuthService.getAuthHeader(),
    ...(options.body && typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers as Record<string, string> ?? {}),
  };

  const response = await fetch(url, { ...options, headers });
  return response;
}

/**
 * Unauthenticated fetch (e.g. for /token login endpoint).
 */
export async function apiPublicFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const url = `${API_URL}${path}`;
  return fetch(url, options);
}

export { API_URL };
