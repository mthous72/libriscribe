import { test, expect } from '@playwright/test'
import { mockApi } from './mockApi'

/**
 * Guards the mobile-responsive work: no page may overflow the viewport
 * horizontally at common phone widths, and the nav must collapse into a
 * hamburger below the `sm` breakpoint while showing inline links above it.
 */

const ROUTES = [
  '/',
  '/projects/new',
  '/settings',
  '/projects/demo',
  '/projects/demo/outline',
  '/projects/demo/lorebook',
  '/projects/demo/chapters/1',
]

// 320 = iPhone SE (1st gen), 375 = iPhone SE/12 mini, 414 = large phones.
const WIDTHS = [320, 375, 414]

for (const width of WIDTHS) {
  test.describe(`no horizontal overflow @ ${width}px`, () => {
    for (const route of ROUTES) {
      test(route, async ({ page }) => {
        await mockApi(page)
        await page.setViewportSize({ width, height: 800 })
        await page.goto(route, { waitUntil: 'load' })
        // Let async data render and the layout settle.
        await expect(page.locator('h1, textarea').first()).toBeVisible()
        await page.waitForTimeout(250)

        const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
        expect(
          scrollWidth,
          `content is ${scrollWidth}px wide but the viewport is ${width}px — something overflows on ${route}`,
        ).toBeLessThanOrEqual(width)
      })
    }
  })
}

test.describe('navigation collapses responsively', () => {
  test('hamburger on mobile, inline links on desktop', async ({ page }) => {
    await mockApi(page)

    await page.setViewportSize({ width: 375, height: 800 })
    await page.goto('/', { waitUntil: 'load' })
    const menu = page.getByRole('button', { name: 'Menu' })
    await expect(menu).toBeVisible()

    // Opening the menu reveals the navigation links.
    await menu.click()
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible()

    // At desktop width the hamburger is gone and links are inline.
    await page.setViewportSize({ width: 1280, height: 800 })
    await expect(page.getByRole('button', { name: 'Menu' })).toBeHidden()
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible()
  })
})
