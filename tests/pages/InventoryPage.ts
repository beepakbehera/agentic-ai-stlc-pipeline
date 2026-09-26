/**
 * Inventory / Products Page Object Model - saucedemo.com
 *
 * Healed by Agent 2b - Selector Self-Healing Engine.
 * Replaces the fictional DashboardPage; saucedemo's post-login page is
 * the inventory: .inventory_list, .inventory_item, .shopping_cart_link.
 */

import { Page, Locator, expect } from '@playwright/test';

export class InventoryPage {
  readonly page: Page;
  readonly url = '/inventory.html';

  // Header
  readonly appLogo: Locator;
  readonly title: Locator;
  readonly menuButton: Locator;
  readonly cartLink: Locator;
  readonly cartBadge: Locator;

  // Content
  readonly inventoryList: Locator;
  readonly inventoryItems: Locator;

  // Cart / checkout
  readonly addToCartButtons: Locator;
  readonly checkoutButton: Locator;

  // Checkout form
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly postalCodeInput: Locator;
  readonly continueButton: Locator;
  readonly finishButton: Locator;
  readonly completeHeader: Locator;

  constructor(page: Page) {
    this.page = page;

    this.appLogo = page.locator('.app_logo');
    this.title = page.locator('.title');
    this.menuButton = page.locator('#react-burger-menu-btn');
    this.cartLink = page.locator('.shopping_cart_link');
    this.cartBadge = page.locator('.shopping_cart_badge');
    this.inventoryList = page.locator('.inventory_list');
    this.inventoryItems = page.locator('.inventory_item');
    this.addToCartButtons = page.locator('.inventory_item button');
    this.checkoutButton = page.locator('[data-test=checkout]');
    this.firstNameInput = page.locator('#first-name');
    this.lastNameInput = page.locator('#last-name');
    this.postalCodeInput = page.locator('#postal-code');
    this.continueButton = page.locator('#continue');
    this.finishButton = page.locator('#finish');
    this.completeHeader = page.locator('.complete-header');
  }

  /**
   * Expect the inventory page is loaded after login
   */
  async expectLoaded(): Promise<void> {
    await expect(this.page).toHaveURL(/inventory/);
    await expect(this.inventoryList).toBeVisible();
    await expect(this.title).toHaveText('Products');
  }

  /**
   * Add the first product to the cart and expect the badge to update
   */
  async addFirstItemToCart(): Promise<void> {
    await this.addToCartButtons.first().click();
    await expect(this.cartBadge).toHaveText('1');
  }

  /**
   * Full checkout journey with the given customer details
   */
  async checkout(firstName: string, lastName: string, postalCode: string): Promise<void> {
    await this.cartLink.click();
    await this.checkoutButton.click();
    await this.firstNameInput.fill(firstName);
    await this.lastNameInput.fill(lastName);
    await this.postalCodeInput.fill(postalCode);
    await this.continueButton.click();
    await this.finishButton.click();
    await expect(this.completeHeader).toContainText('Thank you');
  }

  /**
   * Logout through the burger menu
   */
  async logout(): Promise<void> {
    await this.menuButton.click();
    await this.page.locator('#logout_sidebar_link').click();
    await expect(this.page.locator('#login-button')).toBeVisible();
  }
}
