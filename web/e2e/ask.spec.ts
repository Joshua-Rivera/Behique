import { ensureIndexed, expect, expectNoSeriousA11yIssues, test } from "./fixtures";

test.beforeAll(async ({ request }) => ensureIndexed(request));

test("without a key, Ask shows setup instructions", async ({ page, request }) => {
  const health = await (await request.get("/api/health")).json();
  test.skip(health.ask_enabled, "server has a key");
  await page.goto("/ask/");
  await expect(page.getByText("Ask is turned off")).toBeVisible();
  await expectNoSeriousA11yIssues(page);
});

test("streams steps, answer, citations and usage (mocked, no paid calls)", async ({
  page,
  request,
}) => {
  const hits = await (
    await request.post("/api/search", { data: { query: "starter", mode: "bm25", k: 1 } })
  ).json();
  const h = hits[0];
  await page.route("**/api/health", async (route) => {
    const res = await route.fetch();
    await route.fulfill({ response: res, json: { ...(await res.json()), ask_enabled: true, web_allowed: true } });
  });
  const sse = [
    ["step", { kind: "search", label: "Searching files: starter" }],
    ["step", { kind: "read", label: `Reading ${h.path}` }],
    ["delta", { text: `Feed it twice a day [chunk:${h.chunk_id}].` }],
    [
      "citations",
      {
        citations: [
          { type: "local", chunk_id: h.chunk_id, file_id: h.file_id, path: h.path },
          { type: "web", url: "https://example.com/guide", title: "A guide" },
        ],
      },
    ],
    ["usage", { input: 900, output: 40, cache_read: 800, cache_write: 0, web_searches: 0, web_fetches: 0, steps: 2 }],
    ["done", { refused: false, step_cap_reached: false, web_enabled: false }],
  ]
    .map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`)
    .join("");
  await page.route("**/api/ask/stream", (route) =>
    route.fulfill({ status: 200, contentType: "text/event-stream", body: sse }),
  );

  await page.goto("/ask/");
  await page.getByRole("textbox", { name: "Question" }).fill("How often do I feed it?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText(`Reading ${h.path}`)).toBeVisible();
  await expect(page.getByText("Feed it twice a day")).toBeVisible();
  await expect(page.getByLabel("Token usage")).toContainText("800 cache read");

  const web = page.getByRole("link", { name: "A guide" });
  await expect(web).toHaveAttribute("rel", "noopener noreferrer");
  await page.getByRole("button", { name: new RegExp(`Source 1: ${h.path}`) }).click();
  await expect(page.getByRole("dialog").getByRole("article", { name: "Preview" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expectNoSeriousA11yIssues(page);
});

test("Stop aborts a running answer", async ({ page }) => {
  await page.route("**/api/health", async (route) => {
    const res = await route.fetch();
    await route.fulfill({ response: res, json: { ...(await res.json()), ask_enabled: true } });
  });
  await page.route("**/api/ask/stream", () => {
    /* never answers */
  });
  await page.goto("/ask/");
  await page.getByRole("textbox", { name: "Question" }).fill("slow question");
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.getByText("Stopped.")).toBeVisible();
});

test("an API key on the server sends the UI to Settings", async ({ page }) => {
  await page.route("**/api/sources", (route) =>
    route.fulfill({ status: 401, json: { detail: "invalid or missing API key" } }),
  );
  await page.goto("/sources/");
  await expect(page).toHaveURL(/\/settings\/\?reason=auth/);
  await expect(page.getByText("This server needs an API key")).toBeVisible();
});
