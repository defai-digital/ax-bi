# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: sqllab/sqllab.spec.ts >> executes a simple SELECT query and displays results
- Location: playwright/tests/sqllab/sqllab.spec.ts:54:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: expect(locator).toBeEnabled() failed

Locator:  locator('[role="tabpanel"]:not([aria-hidden="true"])').filter({ has: locator('.ace_editor') }).locator('[data-test="run-query-action"]')
Expected: enabled
Received: disabled

Call log:
  - Expect "toBeEnabled" with timeout 60000ms
  - waiting for locator('[role="tabpanel"]:not([aria-hidden="true"])').filter({ has: locator('.ace_editor') }).locator('[data-test="run-query-action"]')
    120 × locator resolved to <button disabled type="button" data-test="run-query-action" class="ant-btn css-1pi45l5 css-var-r0 ant-btn-primary ant-btn-color-primary ant-btn-variant-solid superset-button superset-button-primary cta superset-14w0f1e">…</button>
        - unexpected value "disabled"

```

```yaml
- button "caret-right Run" [disabled]:
  - img "caret-right"
  - text: Run
```

# Test source

```ts
  226 | 
  227 |   // ── Editor Convenience ──
  228 | 
  229 |   async setQuery(sql: string): Promise<void> {
  230 |     await this.editor.setText(sql);
  231 |   }
  232 | 
  233 |   async getQuery(): Promise<string> {
  234 |     return this.editor.getText();
  235 |   }
  236 | 
  237 |   // ── Tab Management ──
  238 | 
  239 |   async getTabCount(): Promise<number> {
  240 |     return this.editorTabs.getTabCount();
  241 |   }
  242 | 
  243 |   async getTabNames(): Promise<string[]> {
  244 |     return this.editorTabs.getTabNames();
  245 |   }
  246 | 
  247 |   async getActiveTabName(): Promise<string> {
  248 |     return this.editorTabs.getActiveTabName();
  249 |   }
  250 | 
  251 |   async addTab(): Promise<void> {
  252 |     await this.editorTabs.addTab();
  253 |   }
  254 | 
  255 |   async addTabByShortcut(): Promise<void> {
  256 |     const modifier = process.platform === 'win32' ? 'Control+q' : 'Control+t';
  257 |     await this.page.keyboard.press(modifier);
  258 |   }
  259 | 
  260 |   async closeLastTab(): Promise<void> {
  261 |     const countBefore = await this.getTabCount();
  262 |     await this.editorTabs.removeLastTab();
  263 |     // Wait for tab count to decrease
  264 |     await this.page.waitForFunction(
  265 |       ([selector, expected]) => {
  266 |         const container = document.querySelector(selector);
  267 |         if (!container) return false;
  268 |         const nav = container.querySelector(':scope > .ant-tabs-nav');
  269 |         if (!nav) return false;
  270 |         return nav.querySelectorAll('.ant-tabs-tab').length === expected;
  271 |       },
  272 |       [SqlLabPage.SELECTORS.SQL_EDITOR_TABS, countBefore - 1] as const,
  273 |       { timeout: TIMEOUT.UI_TRANSITION },
  274 |     );
  275 |   }
  276 | 
  277 |   getTab(name: string): Locator {
  278 |     return this.editorTabs.getTab(name);
  279 |   }
  280 | 
  281 |   // ── Database Selection (Left Sidebar) ──
  282 | 
  283 |   async selectDatabase(dbName: string): Promise<void> {
  284 |     await this.databaseSelector.click();
  285 | 
  286 |     const popover = new Popover(this.page);
  287 |     await popover.waitForVisible();
  288 | 
  289 |     // Target the .ant-select wrapper (not the combobox input) because the
  290 |     // selection-item overlay intercepts pointer events on the input.
  291 |     const dbSelect = popover.element
  292 |       .locator(SqlLabPage.SELECTORS.DATABASE_SELECTOR)
  293 |       .locator('.ant-select')
  294 |       .first();
  295 |     const select = new Select(this.page, dbSelect);
  296 |     await select.selectOption(dbName);
  297 | 
  298 |     await popover.getButton('Select').click();
  299 |     await popover
  300 |       .waitForHidden({ timeout: TIMEOUT.UI_TRANSITION })
  301 |       .catch(error => {
  302 |         if (!(error instanceof Error) || error.name !== 'TimeoutError') {
  303 |           throw error;
  304 |         }
  305 |       });
  306 |   }
  307 | 
  308 |   // ── Query Execution ──
  309 | 
  310 |   /**
  311 |    * Sets SQL, runs the query, and waits for the API response.
  312 |    * Also observes the QueryStatusBar (.ant-steps) loading indicator to
  313 |    * confirm the UI entered the execution cycle — this unmounts the old
  314 |    * results grid, so waitForQueryResults() can trust that any grid it
  315 |    * finds afterward contains data from THIS execution.
  316 |    */
  317 |   async executeQuery(sql: string): Promise<Response> {
  318 |     await this.setQuery(sql);
  319 |     // Run Query is disabled until BOTH sql is set (just done) AND a
  320 |     // database is selected. On fresh CI users the default database may
  321 |     // not be populated when ensureEditorReady() returns, so block here
  322 |     // until the button is actually clickable before kicking off the
  323 |     // response/loading watchers — otherwise their 15 s timers run out
  324 |     // before the click can even fire. Use SLOW_TEST: under werkzeug
  325 |     // load default-db bootstrap can take >15 s.
> 326 |     await expect(this.runQueryButton.element).toBeEnabled({
      |                                               ^ Error: expect(locator).toBeEnabled() failed
  327 |       timeout: TIMEOUT.SLOW_TEST,
  328 |     });
  329 |     // Use SLOW_TEST for /sqllab/execute/ — under werkzeug stress the
  330 |     // round-trip can exceed 15 s even for trivial queries because the
  331 |     // dev server time-shares a single Python thread across all workers.
  332 |     const responsePromise = waitForPost(this.page, 'api/v1/sqllab/execute/', {
  333 |       timeout: TIMEOUT.SLOW_TEST,
  334 |     });
  335 |     // Start observing the loading indicator BEFORE clicking Run so we
  336 |     // catch it even for fast queries. QueryStatusBar (.ant-steps) appears
  337 |     // when SQL Lab enters the running state and unmounts the results grid.
  338 |     const loadingStarted = this.resultsPane
  339 |       .locator('.ant-steps')
  340 |       .waitFor({ state: 'visible', timeout: TIMEOUT.SLOW_TEST });
  341 |     await this.runQueryButton.click();
  342 |     const [, response] = await Promise.all([loadingStarted, responsePromise]);
  343 |     return response;
  344 |   }
  345 | 
  346 |   /**
  347 |    * Wait for fresh query results to render in the AG Grid.
  348 |    * Waits for the QueryStatusBar to disappear first, proving the execution
  349 |    * cycle completed and React rendered the post-query grid.
  350 |    * @param expectHeader - A column header that must be visible before returning.
  351 |    * @param options.timeout - How long to wait (default: TIMEOUT.QUERY_EXECUTION)
  352 |    */
  353 |   async waitForQueryResults(
  354 |     expectHeader: string,
  355 |     options?: { timeout?: number },
  356 |   ): Promise<void> {
  357 |     // AG Grid is heavy and lazy-rendered. Under werkzeug stress the FE
  358 |     // sometimes takes >15 s to hydrate results after the query returns.
  359 |     // Default to SLOW_TEST so a slow grid mount doesn't masquerade as a
  360 |     // query failure (the response status was already asserted upstream).
  361 |     const timeout = options?.timeout ?? TIMEOUT.SLOW_TEST;
  362 |     // Wait for QueryStatusBar to disappear — proves the loading → ready
  363 |     // transition completed. If already hidden (fast query finished before
  364 |     // this call), resolves immediately since executeQuery() already observed
  365 |     // the loading state appear.
  366 |     await this.resultsPane
  367 |       .locator('.ant-steps')
  368 |       .waitFor({ state: 'hidden', timeout });
  369 |     const grid = this.resultsGrid.element;
  370 |     await grid.waitFor({ state: 'visible', timeout });
  371 |     await grid
  372 |       .locator('.ag-header-cell', { hasText: expectHeader })
  373 |       .first()
  374 |       .waitFor({ state: 'visible', timeout });
  375 |   }
  376 | 
  377 |   // ── Row Limit ──
  378 | 
  379 |   async getRowLimit(): Promise<string> {
  380 |     const text = await this.activePanel
  381 |       .locator(SqlLabPage.SELECTORS.LIMIT_DROPDOWN)
  382 |       .textContent();
  383 |     return text?.trim() ?? '';
  384 |   }
  385 | 
  386 |   /**
  387 |    * Set the row limit via the Limit dropdown in the active panel.
  388 |    * @param limit - The menu item label to select (e.g., "10", "100")
  389 |    */
  390 |   async setRowLimit(limit: string): Promise<void> {
  391 |     await this.activePanel.locator(SqlLabPage.SELECTORS.LIMIT_DROPDOWN).click();
  392 |     await this.page.getByRole('menuitem', { name: limit, exact: true }).click();
  393 |   }
  394 | }
  395 | 
```