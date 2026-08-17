const { test, expect } = require('@playwright/test');

for (const [name, path] of [['home','/'], ['syllabus','/syllabus.html']]) {
  test(`${name} visual baseline`, async ({ page }) => {
    await page.goto(path);
    await page.emulateMedia({ media: 'screen' });
    await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true, animations: 'disabled' });
  });
}
