"""
Scraper for tow.whfb.app using async Playwright.
Collects all rule, army, unit, magic, and FAQ pages.

Checkpoint mechanism:
  Every successfully scraped page is immediately appended to a JSONL checkpoint
  file (one JSON object per line). On restart the checkpoint is read first and
  already-scraped paths are skipped, so a crash never means starting over.

  Use force=True to wipe the checkpoint and start fresh.

Final cache:
  When all pages are done the results are also written to tow_pages.json so the
  rest of the pipeline can load them with a single json.loads() call.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright
from tqdm import tqdm

BASE_URL = "https://tow.whfb.app"
CACHE_FILE = Path("pipeline/cache/tow_pages.json")
CHECKPOINT_FILE = Path("pipeline/cache/checkpoint.jsonl")
SITEMAP_PATHS = ["/sitemap/rules", "/sitemap/armies", "/sitemap/magic", "/sitemap/magic-items"]
SKIP_PATHS = {"/", "/sitemap", "/links", "/credit", "/metrics"}
MAX_CONCURRENT = 8


# ── Checkpoint helpers ────────────────────────────────────────────────────────

def load_checkpoint() -> tuple[set[str], list[dict]]:
    """
    Read the JSONL checkpoint file and return:
      - a set of already-scraped paths  (used to skip them)
      - a list of their page dicts       (used to seed results)

    JSONL format means we append one line per page, so a crash mid-write
    at worst corrupts the last line — we skip blank/invalid lines defensively.
    If the same path appears more than once we keep the last occurrence.
    """
    if not CHECKPOINT_FILE.exists():
        return set(), []

    pages_by_path: dict[str, dict] = {}
    for line in CHECKPOINT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            page = json.loads(line)
            pages_by_path[page["path"]] = page
        except (json.JSONDecodeError, KeyError):
            pass  # corrupted last line — safely ignored

    return set(pages_by_path.keys()), list(pages_by_path.values())


async def append_checkpoint(lock: asyncio.Lock, page: dict) -> None:
    """
    Append a single scraped page to the checkpoint file.
    Protected by an asyncio.Lock so concurrent coroutines don't interleave writes.
    """
    async with lock:
        with CHECKPOINT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")


# ── Browser helpers ───────────────────────────────────────────────────────────

async def collect_urls(browser) -> list[str]:
    """Visit each sitemap page and collect all rule/army/unit URLs."""
    urls: set[str] = set()
    page = await browser.new_page()
    for sitemap in SITEMAP_PATHS:
        try:
            print(f"  Collecting URLs from {sitemap}...")
            await page.goto(f"{BASE_URL}{sitemap}", wait_until="networkidle", timeout=30000)
            await page.wait_for_selector("a[href]", timeout=10000)
            links = await page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.getAttribute('href'))"
            )
            for link in links:
                if (
                    link
                    and link.startswith("/")
                    and link not in SKIP_PATHS
                    and not link.startswith("/sitemap")
                ):
                    urls.add(link)
        except Exception as e:
            print(f"  Warning: failed to collect from {sitemap}: {e}")
    await page.close()
    return sorted(urls)


async def scrape_page(browser, path: str) -> dict | None:
    """Scrape a single page, returning structured text content."""
    url = f"{BASE_URL}{path}"
    context = await browser.new_context()
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("h1, h2, main, article", timeout=15000)

        result = await page.evaluate("""() => {
            const h1 = document.querySelector('h1');
            const title = h1 ? h1.innerText.trim() : document.title;

            const clone = (document.querySelector('main') || document.querySelector('article') || document.body).cloneNode(true);
            ['nav', 'header', 'footer', 'script', 'style', '[aria-label="navigation"]'].forEach(sel => {
                clone.querySelectorAll(sel).forEach(el => el.remove());
            });

            const sections = [];
            let currentHeading = title;
            let currentText = [];

            const walk = (node) => {
                if (node.nodeType === Node.TEXT_NODE) {
                    const text = node.textContent.trim();
                    if (text) currentText.push(text);
                } else if (node.nodeType === Node.ELEMENT_NODE) {
                    const tag = node.tagName.toLowerCase();
                    if (['h1','h2','h3','h4'].includes(tag)) {
                        if (currentText.length > 0) {
                            sections.push({ heading: currentHeading, text: currentText.join(' ') });
                            currentText = [];
                        }
                        currentHeading = node.innerText.trim();
                    } else if (['p','li','td','dd','dt'].includes(tag)) {
                        const text = node.innerText.trim();
                        if (text) currentText.push(text);
                    } else {
                        for (const child of node.childNodes) walk(child);
                    }
                }
            };

            for (const child of clone.childNodes) walk(child);
            if (currentText.length > 0) {
                sections.push({ heading: currentHeading, text: currentText.join(' ') });
            }

            return { title, sections, fullText: clone.innerText.trim() };
        }""")

        return {
            "url": url,
            "path": path,
            "title": result["title"],
            "sections": result["sections"],
            "full_text": result["fullText"],
        }
    except Exception as e:
        print(f"\n  Error scraping {path}: {e}")
        return None
    finally:
        await context.close()


# ── Main entry point ──────────────────────────────────────────────────────────

async def scrape_all(force: bool = False) -> list[dict]:
    """
    Scrape all pages from tow.whfb.app with checkpoint-based resume support.

    Flow:
      1. Load checkpoint  → already-done pages pre-populate results, their
         paths are skipped in the scrape loop.
      2. Collect all URLs from sitemaps.
      3. Filter to only the URLs not yet in the checkpoint.
      4. Scrape remaining pages concurrently (max MAX_CONCURRENT at a time),
         appending each success to the checkpoint immediately.
      5. Write the final combined list to tow_pages.json (flat cache for the
         rest of the pipeline).

    force=True wipes both the checkpoint and the cache so everything reruns.
    """
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Wipe state on force-rescrape
    if force:
        CHECKPOINT_FILE.unlink(missing_ok=True)
        CACHE_FILE.unlink(missing_ok=True)

    # Fast path: full cache already written (all pages done on a previous run)
    if CACHE_FILE.exists():
        print(f"Loading tow.whfb.app data from cache ({CACHE_FILE})")
        return json.loads(CACHE_FILE.read_text())

    # Load whatever was completed in a previous (possibly crashed) run
    done_paths, results = load_checkpoint()
    if done_paths:
        print(f"Resuming from checkpoint: {len(done_paths)} pages already scraped.")

    print("Starting tow.whfb.app scrape...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        print("Step 1/2: Collecting URLs from sitemaps...")
        all_urls = await collect_urls(browser)
        remaining = [u for u in all_urls if u not in done_paths]
        print(f"  Total pages: {len(all_urls)} | Already done: {len(done_paths)} | Remaining: {len(remaining)}")

        if remaining:
            print("Step 2/2: Scraping pages...")
            semaphore = asyncio.Semaphore(MAX_CONCURRENT)
            checkpoint_lock = asyncio.Lock()

            progress = tqdm(
                total=len(all_urls),
                initial=len(done_paths),
                desc="Scraping tow.whfb.app",
                unit="page",
                dynamic_ncols=True,
            )

            async def scrape_with_limit(path: str):
                async with semaphore:
                    page_data = await scrape_page(browser, path)
                    if page_data and page_data["full_text"]:
                        await append_checkpoint(checkpoint_lock, page_data)
                        progress.set_postfix_str(page_data["title"][:40])
                    progress.update(1)
                    return page_data

            tasks = [scrape_with_limit(u) for u in remaining]
            for coro in asyncio.as_completed(tasks):
                page_data = await coro
                if page_data and page_data["full_text"]:
                    results.append(page_data)

            progress.close()
        else:
            print("  All pages already in checkpoint — nothing left to scrape.")

        await browser.close()

    # Write consolidated cache so next run skips straight to json.loads()
    CACHE_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Scraped {len(results)} pages total → cached to {CACHE_FILE}")
    return results


if __name__ == "__main__":
    import asyncio
    pages = asyncio.run(scrape_all(force=True))
    print(f"Done. Total pages: {len(pages)}")
