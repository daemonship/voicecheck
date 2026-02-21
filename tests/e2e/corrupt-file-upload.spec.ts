import { test, expect } from '@playwright/test';

const APP_URL = process.env.APP_URL || 'http://localhost:5173';
import { writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

test.describe('Corrupt file upload shows error gracefully', () => {
  test('should reject non-.docx files renamed to .docx', async ({ page }) => {
    // 1. Sign up and log in
    await page.goto(APP_URL);
    await page.click('text=Sign Up');
    await page.fill('input[name="email"]', `corrupttest-${Date.now()}@example.com`);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    
    // 2. Upload a file renamed to .docx that is actually a PNG image
    // Create a fake .docx (PNG bytes with .docx extension)
    const fakeDocxPath = join(tmpdir(), 'fake.docx');
    writeFileSync(fakeDocxPath, Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])); // PNG magic bytes
    
    await page.click('text=New Project');
    await page.click('text=Upload File');
    
    // Set up file input handler
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(fakeDocxPath);
    
    await page.click('button[type="submit"]');
    
    // 3. Assert an error message is displayed indicating the file is not valid
    await expect(page.locator('text=invalid file').or(page.locator('text=not a valid').or(page.locator('text=corrupt')))).toBeVisible({ timeout: 5000 });
    
    // 4. Assert no project is created in the project list
    await page.click('text=Cancel').or(page.locator('text=Back').or(page.locator('text=Projects')));
    
    // Should not see the newly uploaded project in list
    await expect(page.locator('text=fake.docx')).not.toBeVisible();
  });
  
  test('should reject password-protected .docx files', async ({ page }) => {
    // 1. Sign up and log in
    await page.goto(APP_URL);
    await page.click('text=Sign Up');
    await page.fill('input[name="email"]', `protectedtest-${Date.now()}@example.com`);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    
    // 5. Upload a password-protected .docx file
    // Create a file that simulates password protection
    const protectedDocxPath = join(tmpdir(), 'protected.docx');
    writeFileSync(protectedDocxPath, Buffer.from('encrypted-content'));
    
    await page.click('text=New Project');
    await page.click('text=Upload File');
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(protectedDocxPath);
    
    await page.click('button[type="submit"]');
    
    // 6. Assert a clear error message about password protection, not a generic 500
    await expect(page.locator('text=password').or(page.locator('text=protected'))).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=500 Error').or(page.locator('text=Internal Server Error'))).not.toBeVisible();
  });
});
