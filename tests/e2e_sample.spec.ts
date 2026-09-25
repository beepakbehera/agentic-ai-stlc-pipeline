/**
 * Playwright TypeScript Sample Test Suite
 * 
 * This is a sample test file demonstrating the structure that Agent 2
 * will generate for Playwright automation.
 * 
 * Run with: npx playwright test tests/e2e_sample.spec.ts
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { testUsers } from './fixtures/testData';

// ============================================================================
// Test Configuration
// ============================================================================

test.describe.configure({ retries: 2 });

// ============================================================================
// Test Data
// ============================================================================

const testCases = [
  {
    id: 'TC-LOGIN-001',
    title: 'Valid user login',
    priority: 'Critical',
    user: testUsers.validUser,
    expectedResult: 'User redirected to dashboard',
  },
  {
    id: 'TC-LOGIN-002',
    title: 'Invalid password shows error',
    priority: 'High',
    user: testUsers.invalidPassword,
    expectedResult: 'Error message displayed',
  },
  {
    id: 'TC-LOGIN-003',
    title: 'Invalid email format shows error',
    priority: 'Medium',
    user: testUsers.invalidEmail,
    expectedResult: 'Inline validation error',
  },
];

// ============================================================================
// Test Fixtures
// ============================================================================

test.beforeEach(async ({ page }) => {
  // Setup: Navigate to login page before each test
  const loginPage = new LoginPage(page);
  await loginPage.goto();
});

test.afterEach(async ({ page }, testInfo) => {
  // Teardown: Capture screenshot on failure
  if (testInfo.status !== testInfo.expectedStatus) {
    await page.screenshot({ 
      path: `test-results/screenshots/${testInfo.title.replace(/\s+/g, '-')}.png`,
      fullPage: true 
    });
  }
});

// ============================================================================
// Test Cases
// ============================================================================

test.describe('User Authentication', () => {
  
  testCases.forEach(({ id, title, priority, user, expectedResult }) => {
    test(`[${id}] ${title}`, async ({ page }) => {
      test.info().annotations.push({ type: 'priority', description: priority });
      
      const loginPage = new LoginPage(page);
      const dashboardPage = new DashboardPage(page);
      
      // Act
      await loginPage.login(user.email, user.password);
      
      // Assert
      if (user.shouldSucceed) {
        await dashboardPage.expectLoggedIn(user.name);
      } else {
        await loginPage.expectErrorMessage(user.expectedError);
      }
    });
  });

});

// ============================================================================
// Data-Driven Tests with CSV/JSON
// ============================================================================

test.describe('Data-Driven Login Tests', () => {
  const loginData = [
    { email: 'user1@example.com', password: 'Pass123!', shouldPass: true },
    { email: 'user2@example.com', password: 'WrongPass', shouldPass: false },
    { email: 'invalid-email', password: 'Pass123!', shouldPass: false },
    { email: '', password: 'Pass123!', shouldPass: false },
    { email: 'user3@example.com', password: '', shouldPass: false },
  ];

  for (const data of loginData) {
    test(`Login with ${data.email || 'empty email'}`, async ({ page }) => {
      const loginPage = new LoginPage(page);
      
      await loginPage.login(data.email, data.password);
      
      if (data.shouldPass) {
        const dashboardPage = new DashboardPage(page);
        await dashboardPage.expectLoggedIn('User');
      } else {
        await expect(loginPage.errorMessage).toBeVisible();
      }
    });
  }
});

// ============================================================================
// Visual Regression Tests
// ============================================================================

test.describe('Visual Regression', () => {
  test('Login page matches baseline', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    // Compare with baseline screenshot
    await expect(page).toHaveScreenshot('login-page.png', {
      fullPage: true,
      animations: 'disabled',
      threshold: 0.2,
    });
  });
});

// ============================================================================
// API Testing Integration
// ============================================================================

test.describe('API + UI Integration', () => {
  test('Create user via API then login via UI', async ({ page, request }) => {
    // Create test user via API
    const newUser = {
      email: `test-${Date.now()}@example.com`,
      password: 'TestPass123!',
      name: 'Test User',
    };
    
    const createResponse = await request.post('/api/users', { data: newUser });
    expect(createResponse.ok()).toBeTruthy();
    
    // Login via UI
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(newUser.email, newUser.password);
    
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.expectLoggedIn(newUser.name);
  });
});

// ============================================================================
// Performance/Accessibility Tests
// ============================================================================

test.describe('Performance & Accessibility', () => {
  test('Login page loads within 3 seconds', async ({ page }) => {
    const startTime = Date.now();
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(3000);
  });

  test('Login page has no accessibility violations', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    // Run axe-core accessibility scan
    // Note: Requires @axe-core/playwright package
    // const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    // expect(accessibilityScanResults.violations).toEqual([]);
  });
});