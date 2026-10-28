import { ensureIndexed, expect, expectNoSeriousA11yIssues, test } from "./fixtures";

test.beforeAll(async ({ request }) => ensureIndexed(request));

test("search shows grouped results with a highlighted preview", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("searchbox", { name: "Search your files" }).fill("starter flour water");
  const first = page.getByRole("option").first();
  await expect(first).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("article", { name: "Preview" }).locator("mark").first()).toBeVisible();
  await expect(page).toHaveURL(/\?q=starter/);

  await page.getByRole("searchbox").press("ArrowDown");
  await expect(page.getByRole("option").nth(1)).toHaveAttribute("aria-selected", "true");

  await page.getByRole("radio", { name: "Keyword" }).click();
  await expect(page.getByRole("option").first()).toContainText("keyword");
  await expectNoSeriousA11yIssues(page);
});

test("no results and empty states", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Search your files", { exact: true })).toBeVisible();
  await page.getByRole("radio", { name: "Keyword" }).click();
  await page.getByRole("searchbox").fill("zzqxjv_nothing_matches");
  await expect(page.getByText("No results")).toBeVisible();
});

test("⌘K palette jumps to a result and offers Ask", async ({ page }) => {
  await page.goto("/sources/");
  await page.keyboard.press("ControlOrMeta+k");
  const input = page.getByPlaceholder("Search files or ask…");
  await input.fill("sourdough");
  await expect(page.getByRole("option", { name: /Ask Behique about “sourdough”/ })).toBeVisible();
  await page.getByRole("option", { name: /sourdough\.md/ }).first().click();
  await expect(page).toHaveURL(/\/\?q=sourdough/);
  await expect(page.getByRole("article", { name: "Preview" })).toBeVisible();
});

test("sources lists the fixture and its counts", async ({ page }) => {
  await page.goto("/sources/");
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("button", { name: /Index .* now/ }).first()).toBeEnabled();
  await page.getByRole("button", { name: "Add source" }).click();
  await expect(page.getByRole("dialog", { name: "Add source" })).toContainText("docker-compose.yml");
  await expectNoSeriousA11yIssues(page);
});

test("settings shows server info and theme switching works", async ({ page }) => {
  await page.goto("/settings/");
  await expect(page.getByText("Embedding model")).toBeVisible();
  await page.getByRole("radio", { name: "Dark" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expectNoSeriousA11yIssues(page);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("radio", { name: "System" }).click();
});

test("panes resize, clamp, reset and persist", async ({ page }) => {
  await page.goto("/");
  const sep = page.getByRole("separator", { name: "Resize sidebar" });
  const sidebar = page.getByRole("complementary", { name: "Sidebar" });
  await sep.focus();
  await sep.press("Home");
  await expect(sep).toHaveAttribute("aria-valuenow", "48");
  await expect(sidebar.getByText("Behique")).toHaveCount(0); // icons only
  await page.reload();
  await expect(page.getByRole("separator", { name: "Resize sidebar" })).toHaveAttribute(
    "aria-valuenow",
    "48",
  );
  await page.getByRole("separator", { name: "Resize sidebar" }).dblclick();
  await expect(page.getByRole("separator", { name: "Resize sidebar" })).toHaveAttribute(
    "aria-valuenow",
    "140",
  );

  await page.getByRole("searchbox").fill("starter");
  const split = page.getByRole("separator", { name: "Resize results and preview" });
  await split.focus();
  await split.press("Home");
  await expect(split).toHaveAttribute("aria-valuenow", "150");
});

test("narrow screens use icon sidebar and a preview sheet", async ({ page }) => {
  await page.setViewportSize({ width: 600, height: 800 });
  await page.goto("/?q=starter");
  await expect(page.getByRole("separator", { name: "Resize sidebar" })).toHaveCount(0);
  await page.getByRole("option").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("article", { name: "Preview" })).toBeVisible();
});

test("reduced motion disables transitions", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/settings/");
  const d = await page
    .getByRole("radio", { name: "Light" })
    .evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(parseFloat(d)).toBeLessThan(0.01);
});
