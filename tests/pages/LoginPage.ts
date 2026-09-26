/**
 * Login Page Object Model - saucedemo.com
 *
 * Healed by Agent 2b - Selector Self-Healing Engine.
 * Original data-testid selectors did not exist on the target app;
 * healed to the real DOM: #user-name, #password, #login-button,
 * [data-test=error], .login_credentials.
 */

import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly url = '/';

  // Form fields - healed selectors (saucedemo real DOM)
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;

  // Messages
  readonly errorMessage: Locator;
  readonly errorCloseButton: Locator;

  // Page elements
  readonly loginLogo: Locator;
  readonly credentialsInfo: Locator;

  constructor(page: Page) {
    this.page = page;

    this.usernameInput = page.locator('#user-name');
    this.passwordInput = page.locator('#password');
    this.loginButton = page.locator('#login-button');
    this.errorMessage = page.locator('[data-test=error]');
    this.errorCloseButton = page.locator('[data-test=error] button');
    this.loginLogo = page.locator('.login_logo');
    this.credentialsInfo = page.locator('.login_credentials');
  }

  /**
   * Navigate to login page and wait for load
   */
  async goto(): Promise<void> {
    await this.page.goto('/');
    await expect(this.loginLogo).toBeVisible();
    await expect(this.loginButton).toBeVisible();
  }

  /**
   * Fill login form
   */
  async fillForm(username: string, password: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
  }

  /**
   * Submit login form
   */
  async submit(): Promise<void> {
    await this.loginButton.click();
  }

  /**
   * Complete login flow
   */
  async login(username: string, password: string): Promise<void> {
    await this.fillForm(username, password);
    await this.submit();
  }

  /**
   * Expect the error banner with (partial) expected text
   */
  async expectErrorMessage(expectedText: string): Promise<void> {
    await expect(this.errorMessage).toBeVisible();
    if (expectedText) {
      await expect(this.errorMessage).toContainText(expectedText);
    }
  }

  /**
   * Dismiss the error banner via the close (X) button
   */
  async dismissError(): Promise<void> {
    await this.errorCloseButton.click();
    await expect(this.errorMessage).not.toBeVisible();
  }
}
