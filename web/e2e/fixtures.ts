import AxeBuilder from "@axe-core/playwright";
import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";

/** Register the mounted fixture folder (once) and wait for it to be indexed. */
export async function ensureIndexed(request: APIRequestContext) {
  const sources = await (await request.get("/api/sources")).json();
  if (!sources.length) {
    const mounts = await (await request.get("/api/mounts")).json();
    expect(mounts.length, "mount a fixture folder under /data").toBeGreaterThan(0);
    const mount = mounts.find((m: { name: string }) => m.name === "notes") ?? mounts[0];
    await request.post("/api/sources", { data: { path: mount.path } });
    await request.post("/api/index");
  }
  await expect
    .poll(async () => {
      const [st, health] = await Promise.all([
        (await request.get("/api/index/status")).json(),
        (await request.get("/api/health")).json(),
      ]);
      return !st.running && health.chunks > 0;
    }, { timeout: 60_000 })
    .toBe(true);
}

export async function expectNoSeriousA11yIssues(page: Page) {
  // Let enter animations finish, or axe measures half-faded text.
  await page.evaluate(() => Promise.allSettled(document.getAnimations().map((a) => a.finished)));
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const serious = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(
    serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
  ).toEqual([]);
}

/** Fails the test if the page talks to anything but its own origin. */
export const test = base.extend<{ sameOriginOnly: void }>({
  sameOriginOnly: [
    async ({ page, baseURL }, use) => {
      const external: string[] = [];
      const origin = new URL(baseURL!).origin;
      page.on("request", (r) => {
        const u = new URL(r.url());
        if (u.protocol.startsWith("http") && u.origin !== origin) external.push(r.url());
      });
      await use();
      expect(external, "external requests").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
