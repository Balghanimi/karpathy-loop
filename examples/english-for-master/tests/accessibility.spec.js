const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('accessibility', () => {
  for (const path of ['/', '/syllabus.html']) {
    test(`${path} has no serious accessibility violations`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator('body')).toBeVisible();
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      const serious = results.violations.filter(v => ['critical', 'serious'].includes(v.impact));
      expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
    });
  }
});
