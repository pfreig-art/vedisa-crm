import { test, expect } from '@playwright/test'

test.describe('Auth', () => {
  test('redirige a /login si no hay token', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/login/)
  })

  test('login con credenciales validas redirige al dashboard', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="email"]', 'admin@vedisa.com')
    await page.fill('input[name="password"]', 'admin123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
    await expect(page.locator('h1')).toContainText('Dashboard')
  })

  test('login con credenciales invalidas muestra error', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="email"]', 'wrong@example.com')
    await page.fill('input[name="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')
    await expect(page.locator('[role="alert"], .text-red-500, .error')).toBeVisible()
  })
})
