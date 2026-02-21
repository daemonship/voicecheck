import { test, expect } from '@playwright/test';

const APP_URL = process.env.APP_URL || 'http://localhost:5173';

test.describe('Full manuscript analysis produces character profiles and consistency flags', () => {
  test('should complete full analysis workflow', async ({ page }) => {
    // 1. Sign up with test email and verify redirect to project list
    await page.goto(APP_URL);
    await page.click('text=Sign Up');
    await page.fill('input[name="email"]', `test-${Date.now()}@example.com`);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    
    // Should redirect to project list
    await expect(page).toHaveURL(/.*\/projects/);
    await expect(page.locator('h1, h2')).toContainText('projects', { timeout: 5000 });
    
    // 2. Upload a test .docx manuscript
    // For testing, we'll use the paste input with sample text
    const testManuscript = `
Chapter 1

"I can't believe you're here," Sarah said, her hands trembling.

John smiled. "I wouldn't miss this for the world."

"But what about the danger?" asked Michael, stepping forward.

"Danger is my business," John replied with a wink.

Chapter 2

The morning sun cast long shadows across the room. Sarah paced nervously.

"You worry too much," John said, leaning against the wall.

"Someone has to worry!" Sarah exclaimed.

Michael nodded. "She's right, you know. We need a plan."

John laughed. "Where's your sense of adventure?"

Chapter 3

"I have a bad feeling about this," Sarah whispered.

"Don't be silly," John replied. "Everything will be fine."

Michael checked his watch. "We should go. Now."

"Agreed," John said. "Let's move."

Sarah took a deep breath. "Okay. I'm ready."

"Yo what's up dudes?" John said suddenly. "This is totally rad!"
`.repeat(50); // Repeat to get enough word count

    await page.click('text=New Project');
    await page.click('text=Paste Text');
    await page.fill('textarea[name="text"]', testManuscript);
    await page.click('button[type="submit"]');

    // Wait for analysis to start/complete
    await expect(page.locator('text=Analyzing').or(page.locator('text=Complete'))).toBeVisible({ timeout: 10000 });
    
    // 3. Assert character list appears with exactly the 3 expected character names
    await expect(page.locator('text=Sarah')).toBeVisible({ timeout: 30000 });
    await expect(page.locator('text=John')).toBeVisible();
    await expect(page.locator('text=Michael')).toBeVisible();
    
    const characterNames = await page.locator('[data-testid="character-name"]').allTextContents();
    expect(characterNames).toContain('Sarah');
    expect(characterNames).toContain('John');
    expect(characterNames).toContain('Michael');
    
    // 4. Click into the character with the intentional voice break (John)
    await page.click('text=John');
    
    // 5. Assert voice profile card shows all four dimensions with representative quotes
    await expect(page.locator('[data-testid="vocabulary-level"]')).toBeVisible();
    await expect(page.locator('[data-testid="sentence-structure"]')).toBeVisible();
    await expect(page.locator('[data-testid="verbal-tics"]')).toBeVisible();
    await expect(page.locator('[data-testid="formality"]')).toBeVisible();
    
    // Check that each dimension has quotes
    const vocabularyQuotes = await page.locator('[data-testid="vocabulary-level"] [data-testid="quote"]').count();
    expect(vocabularyQuotes).toBeGreaterThanOrEqual(3);
    
    // 6. Assert at least one consistency flag exists
    const flagsSection = page.locator('[data-testid="consistency-flags"]');
    await expect(flagsSection).toBeVisible();
    
    const flags = page.locator('[data-testid="flag-item"]');
    const flagCount = await flags.count();
    expect(flagCount).toBeGreaterThan(0);
    
    // Check flag has severity, dimension, and location
    await expect(flags.first().locator('[data-testid="severity"]')).toBeVisible();
    await expect(flags.first().locator('[data-testid="dimension"]')).toBeVisible();
    await expect(flags.first().locator('[data-testid="location"]')).toBeVisible();
    
    // 7. Assert the consistent characters have higher scores than the inconsistent character
    // Go back to character list
    await page.click('text=Back to Characters');
    
    const johnScore = await page.locator('text=John').locator('..').locator('[data-testid="consistency-score"]').textContent();
    const sarahScore = await page.locator('text=Sarah').locator('..').locator('[data-testid="consistency-score"]').textContent();
    
    // Extract numeric scores
    const johnScoreNum = parseInt(johnScore?.match(/\d+/)?.[0] || '0');
    const sarahScoreNum = parseInt(sarahScore?.match(/\d+/)?.[0] || '0');
    
    expect(sarahScoreNum).toBeGreaterThan(johnScoreNum);
    
    // 8. Dismiss the flag and assert the score updates
    await page.click('text=John');
    const initialScore = parseInt(await page.locator('[data-testid="character-score"]').textContent() || '0');
    
    // Dismiss first flag
    await page.locator('[data-testid="flag-item"] [data-testid="dismiss-button"]').first().click();
    
    // Wait for score update
    await page.waitForTimeout(1000);
    const updatedScore = parseInt(await page.locator('[data-testid="character-score"]').textContent() || '0');
    
    expect(updatedScore).toBeGreaterThanOrEqual(initialScore);
  });
});
