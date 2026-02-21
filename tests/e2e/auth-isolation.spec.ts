import { test, expect } from '@playwright/test';

const APP_URL = process.env.APP_URL || 'http://localhost:5173';

test.describe('Authenticated user cannot access another user\'s project', () => {
  test('should return 403 when accessing another user\'s project', async ({ context, page }) => {
    // 1. Sign up as user A with email testA@example.com, upload a manuscript
    const pageA = await context.newPage();
    await pageA.goto(APP_URL);
    await pageA.click('text=Sign Up');
    await pageA.fill('input[name="email"]', `testA-${Date.now()}@example.com`);
    await pageA.fill('input[name="password"]', 'TestPassword123!');
    await pageA.click('button[type="submit"]');
    
    await pageA.click('text=New Project');
    await pageA.click('text=Paste Text');
    await pageA.fill('textarea[name="text"]', '"Test dialogue," said CharacterA.');
    await pageA.click('button[type="submit"]');
    
    // Wait for project creation and get project URL
    await pageA.waitForURL(/.*\/projects\/.*/);
    const projectUrl = pageA.url();
    const projectId = projectUrl.split('/').pop();
    
    // 2. Log out of user A's session
    await pageA.click('text=Logout').or(pageA.locator('[aria-label="Logout"]'));
    await pageA.waitForURL(/.*\/(login|signup)/);
    
    // 3. Sign up as user B
    const pageB = await context.newPage();
    await pageB.goto(APP_URL);
    await pageB.click('text=Sign Up');
    await pageB.fill('input[name="email"]', `testB-${Date.now()}@example.com`);
    await pageB.fill('input[name="password"]', 'TestPassword123!');
    await pageB.click('button[type="submit"]');
    
    // 4. Navigate directly to user A's project URL
    await pageB.goto(projectUrl);
    
    // 5. Assert a 403 error page or redirect to user B's own project list
    await expect(pageB.locator('text=403').or(pageB.locator('text=Forbidden').or(pageB.locator('text=Access Denied')))).toBeVisible({ timeout: 5000 });
    
    // Or might redirect to user's own projects
    const isRedirected = pageB.url().includes('/projects') && !pageB.url().includes(projectId || '');
    if (isRedirected) {
      await expect(pageB.locator('text=projects')).toBeVisible();
      // Should not show user A's project
      await expect(pageB.locator(`text=${projectId}`)).not.toBeVisible();
    }
  });
});
