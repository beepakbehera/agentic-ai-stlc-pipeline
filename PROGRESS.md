# PROGRESS / HANDOFF — Agentic AI STLC Pipeline

_Last updated: 2026-09-26. Read this first to resume work._

## Current Objective
Test **https://practicesoftwaretesting.com/** (Toolshop) end-to-end with the pipeline:
docs → RAG → test-case generation (Agent 1, real LLM) → push ALL test cases to Jira →
automation scripts (Agent 2) → execute (CI + local) → report → email report to
beepak.behera@gmail.com (same pattern as saucedemo / herokuapp runs).

## Completed So Far
- Docs fetched into `docs_practice/` (14 files). Richest source for test cases:
  `docs_practice/user-stories-v5.md` (1270 lines of ACs). Also architecture,
  features, gift-card-validation, postcode-lookup, http-query-method, etc.
- **RAG working**: 149 chunks ingested from 14 docs into `./data/vector_db`;
  retrieval verified (correct top sources). Fix in `src/nodes/rag_retrieval.py`:
  empty Chroma collection is falsy → both checks now `if self.vector_store is None:`.
  chromadb / sentence-transformers / langchain-huggingface / langchain-chroma installed.
- `pipeline_config_practicesoftwaretesting.json` created; pipeline run **pst-01**
  completed all 6 stages (10,291 tokens, 0 errors) — BUT Agent 1 hit a JSON
  control-char bug and fell back to **3 MOCK test cases**. JSON fix applied after the
  run; **Agent 1 has NOT been re-run with the real LLM yet**.
- `tests/pst_auth.spec.ts` — 9 auth/account tests; 8 pass. Sign-out fixed via
  nav-menu dropdown (fix written; full re-run pending).
- `tests/pst_catalog_checkout.spec.ts` — 12 tests; catalog tests pass;
  `openInStockProduct(page)` helper fixed quantity/favorites/cart tests.
- JSON robustness fix (`try json.loads → except: json.loads(strict=False)`) applied
  to `agent1_test_author.py`, `agent2_script_gen.py`, `agent4_defect_logger.py`
  (compiled OK). **Still pending: `agent2b_mcp_heal.py:136` and `agent3_cicd_trigger.py:201`.**
- Earlier phases done: saucedemo E2E green (run 36244620540), the-internet E2E green
  (run 36246250361), Jira issues SCRUM-5..16, emailed reports, client PDF.

## Site / Environment Facts (verified)
- Angular 20 + Bootstrap 5 SPA; Laravel 12 API at api.practicesoftwaretesting.com
  (REST/GraphQL, MariaDB/Redis/JWT).
- **`testIdAttribute: 'data-test'`** added to `playwright.config.ts` `use` block
  (site uses data-test, not data-testid).
- Accounts: admin@practicesoftwaretesting.com/welcome01;
  customer@…/welcome01 (Jane Doe); customer2@…/welcome01; customer3@…/pass123.
- Verified DOM selectors (probes in `/tmp/map_checkout2.mjs`, `/tmp/find_product.mjs`,
  `/tmp/dump_form.mjs`):
  - Login: `email, password, login-submit, login-error` ("Invalid email or password"),
    `forgot-password-link, register-link`.
  - Grid: `product-name, product-price, sort, search-query, search-submit, search-reset,
    category-{id}/brand-{id} checkboxes, pagination-next, out-of-stock, eco-friendly-filter`.
  - Detail: `product-name(h1), unit-price, product-description, quantity,
    increase-quantity, decrease-quantity, add-to-cart, add-to-favorites`.
  - **Account menu is a dropdown**: click `nav-menu` FIRST, then
    `nav-my-invoices / nav-my-favorites / nav-my-profile / nav-sign-out`.
  - Checkout: `proceed-1..4, first-name, checkout-complete`.
- Stock race: grid out-of-stock badge unreliable; stock enforced on detail page
  (add-to-cart disabled). `openInStockProduct` iterates up to 8 cards, requires
  URL `/product/` + enabled add-to-cart, else goBack. Product 0 "Combination
  Pliers" was buyable when logged in.
- Bundle intel (main-SCJRSYE5.js): `checkout-complete` set after `createInvoice`
  succeeds (cart emptied after); "Thanks for your order" NOT in main bundle
  (lazy chunk/i18n) → don't assert on that text; `payment_method` cases:
  bank-transfer (monthlyInstallments), cash-on-delivery, credit card.

## Jira / Email / CI Facts
- Jira project key **SCRUM** (PROJ doesn't exist). Issue types: 10004 Story,
  10003 Task (no Bug type). Auth via settings JIRA_EMAIL + JIRA_API_TOKEN;
  ADF description helper pattern in `create_jira_issues.py` /
  `create_jira_issues_herokuapp.py` → model the new pst script on these.
- Gmail app password in `.env` as GMAIL_APP_PASSWORD (no spaces);
  `send_execution_report.py` is parameterized (SITE_NAME, SITE_URL, RUN_ID,
  PIPELINE_ID) — update for pst run and send at the end.
- CI gap: `.github/workflows/agentic_tests.yml` never exports `NEMOTRON_MODEL`
  → CI Nemotron calls 404 → silent mock fallback (secret IS set on GH).
  **Fix: `echo "NEMOTRON_MODEL=${{ secrets.NEMOTRON_MODEL }}" >> $GITHUB_ENV`
  in Configure environment steps.**
- CI runs 36248448062 (dispatch by Agent 3 for pst-01) & 36246959695 (push)
  concluded **failure** — chromium Playwright passed 8 and Robot 1; failing job
  not yet identified. LangSmith 401 warnings in CI are harmless.
- `.env`: NEMOTRON_MODEL=nvidia/nemotron-3-ultra-550b-a55b (correct locally),
  JIRA_PROJECT_KEY=SCRUM. Never print secrets.

## Remaining Failures (2 tests)
1. **Full checkout** (`pst_catalog_checkout.spec.ts`): `checkout-complete` never
   visible. `/tmp/map_checkout2.mjs` failed clicking `proceed-1` — "element is
   not enabled". Debug: verify cart badge persists after add-to-cart, maybe
   navigate via cart UI; assert `checkout-complete` visible (NOT "Thanks for
   your order" text).
2. **Invoices overview**: needs `nav-menu` dropdown open first (same as sign-out).

## Git State (uncommitted)
- Modified: `playwright.config.ts`, `src/nodes/agent1_test_author.py`,
  `src/nodes/agent2_script_gen.py`, `src/nodes/agent4_defect_logger.py`,
  `src/nodes/rag_retrieval.py`.
- Untracked: `docs_practice/`, `pipeline_config_practicesoftwaretesting.json`,
  `practicesoftwaretesting_state.json`, `tests/pst_auth.spec.ts`,
  `tests/pst_catalog_checkout.spec.ts`.
- Last commit: 085d5c7 "Add herokuapp login suite and per-site Jira/report scripts".

## Next Steps (in order)
1. Fix invoices test (open `nav-menu` first) + full-checkout test (debug
   proceed-1 disabled; cart persistence/badge after add-to-cart). Re-run both
   pst suites until green locally.
2. Apply `strict=False` JSON fix to `agent2b_mcp_heal.py:136` and
   `agent3_cicd_trigger.py:201`.
3. Add NEMOTRON_MODEL export to `.github/workflows/agentic_tests.yml`.
4. Commit + push suites & fixes.
5. Re-run Agent 1 with real LLM (or derive test cases from
   `docs_practice/user-stories-v5.md` ACs) → push ALL test cases to Jira
   (Stories/Tasks in SCRUM).
6. Trigger CI; identify/fix the failing job from runs 36248448062 / 36246959695.
7. Send pst execution report email: SITE_NAME="Practice Software Testing
   (Toolshop)", SITE_URL=https://practicesoftwaretesting.com/, RUN_ID=<new CI run>,
   PIPELINE_ID=pst-01.
