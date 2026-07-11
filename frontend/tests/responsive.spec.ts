import { test, expect } from '@playwright/test'
import { mockApi } from './mockApi'

/**
 * Guards the mobile-responsive work: no page may overflow the viewport
 * horizontally at common phone widths (portrait AND landscape), and the nav
 * must collapse into a hamburger below the `sm` breakpoint while showing
 * inline links above it.
 */

// B45: '/projects/demo' IS the workbench now; the old outline/chapter URLs redirect into it,
// and the dashboard lives on at /automation.
const ROUTES = [
  '/',
  '/projects/new',
  '/settings',
  '/projects/demo',
  '/projects/demo?sel=scene:1.1',
  '/projects/demo?sel=outline',
  '/projects/demo/automation',
  '/projects/demo/lorebook',
  '/projects/demo/chapters/1',
]

// Portrait: 320 = iPhone SE (1st gen), 375 = iPhone SE/12 mini, 414 = large phones.
const PORTRAIT = [320, 375, 414].map((width) => ({ width, height: 800 }))

// Landscape: short viewports whose in-between widths cross the sm/lg breakpoints
// that portrait phone widths never hit. 667 = iPhone SE/8, 812 = iPhone X/11 Pro,
// 926 = iPhone 14 Pro Max — all rotated 90°.
const LANDSCAPE = [
  { width: 667, height: 375 },
  { width: 812, height: 375 },
  { width: 926, height: 428 },
]

const VIEWPORTS = [
  ...PORTRAIT.map((v) => ({ ...v, label: `${v.width}px portrait` })),
  ...LANDSCAPE.map((v) => ({ ...v, label: `${v.width}x${v.height} landscape` })),
]

for (const vp of VIEWPORTS) {
  test.describe(`no horizontal overflow @ ${vp.label}`, () => {
    for (const route of ROUTES) {
      test(route, async ({ page }) => {
        await mockApi(page)
        await page.setViewportSize({ width: vp.width, height: vp.height })
        await page.goto(route, { waitUntil: 'load' })
        // Let async data render and the layout settle.
        await expect(page.locator('h1, textarea').first()).toBeVisible()
        await page.waitForTimeout(250)

        const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
        expect(
          scrollWidth,
          `content is ${scrollWidth}px wide but the viewport is ${vp.width}px — something overflows on ${route} (${vp.label})`,
        ).toBeLessThanOrEqual(vp.width)
      })
    }
  })
}

test.describe('modals fit within a short landscape viewport', () => {
  test('chapter AI-context modal stays inside 812x375', async ({ page }) => {
    await mockApi(page)
    await page.setViewportSize({ width: 812, height: 375 })
    // Legacy chapter URL → workbench with the chapter selected (B45 redirect).
    await page.goto('/projects/demo/chapters/1', { waitUntil: 'load' })

    await page.getByRole('button', { name: 'AI context' }).click()
    const card = page.locator('.max-w-2xl').first()
    await expect(card).toBeVisible()

    const box = await card.boundingBox()
    expect(box, 'modal card should have a layout box').not.toBeNull()
    // The card must sit fully within the viewport height (1px tolerance),
    // so it never clips off the top/bottom on a short landscape screen.
    expect(box!.y).toBeGreaterThanOrEqual(-1)
    expect(box!.y + box!.height).toBeLessThanOrEqual(375 + 1)
  })
})

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
