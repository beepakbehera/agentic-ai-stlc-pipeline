/**
 * Test Data Fixtures
 * 
 * Centralized test data for data-driven testing.
 * Agent 2 will generate similar fixtures for generated tests.
 */

export interface TestUser {
  email: string;
  password: string;
  name: string;
  shouldSucceed: boolean;
  expectedError?: string;
}

export const testUsers: Record<string, TestUser> = {
  validUser: {
    email: 'testuser@example.com',
    password: 'ValidPass123!',
    name: 'Test User',
    shouldSucceed: true,
  },
  invalidPassword: {
    email: 'testuser@example.com',
    password: 'WrongPassword',
    name: 'Test User',
    shouldSucceed: false,
    expectedError: 'Invalid credentials',
  },
  invalidEmail: {
    email: 'not-an-email',
    password: 'ValidPass123!',
    name: 'Test User',
    shouldSucceed: false,
    expectedError: 'Please enter a valid email address',
  },
  emptyEmail: {
    email: '',
    password: 'ValidPass123!',
    name: '',
    shouldSucceed: false,
    expectedError: 'Email is required',
  },
  emptyPassword: {
    email: 'testuser@example.com',
    password: '',
    name: 'Test User',
    shouldSucceed: false,
    expectedError: 'Password is required',
  },
  lockedAccount: {
    email: 'locked@example.com',
    password: 'ValidPass123!',
    name: 'Locked User',
    shouldSucceed: false,
    expectedError: 'Account is locked',
  },
};

export const testProducts = [
  { id: 'PROD-001', name: 'Basic Plan', price: 9.99, currency: 'USD' },
  { id: 'PROD-002', name: 'Pro Plan', price: 29.99, currency: 'USD' },
  { id: 'PROD-003', name: 'Enterprise Plan', price: 99.99, currency: 'USD' },
];

export const testEnvironments = {
  staging: {
    baseUrl: 'https://staging.example.com',
    apiUrl: 'https://api-staging.example.com',
  },
  production: {
    baseUrl: 'https://app.example.com',
    apiUrl: 'https://api.example.com',
  },
  development: {
    baseUrl: 'http://localhost:3000',
    apiUrl: 'http://localhost:8000',
  },
};

export const browsers = ['chromium', 'firefox', 'webkit'] as const;
export type BrowserType = typeof browsers[number];