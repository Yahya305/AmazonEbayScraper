import csv
from playwright.async_api import async_playwright
import asyncio
import re

async def scrape_ebay_single_url(page, item_url: str):
    page.on("console", lambda msg: print("PAGE LOG:", msg.text))

    await page.context.set_extra_http_headers({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })

    await page.goto(item_url, wait_until="networkidle", timeout=60000)
    print(f"✅ eBay page loaded: {item_url}")

    await asyncio.sleep(3)

    ebay_data = await page.evaluate(
        """() => {
            const urlMatch = window.location.href.match(/\\/itm\\/(\\d+)/);
            const itemNumber = urlMatch ? urlMatch[1] : null;

            let titleElement =
                document.querySelector('h1[data-testid="vi-VR-cvipPrice-title"]') ||
                document.querySelector("h1") ||
                document.querySelector('[role="heading"]');
            const title = titleElement?.textContent?.trim() || null;

            let price = null;
            const priceElement =
                document.querySelector('[data-testid="x-price-primary"]') ||
                document.querySelector(".x-price-primary") ||
                document.querySelector(".x-bin-price__content");
            if (priceElement) {
                const priceText = priceElement.textContent?.trim() || "";
                const priceMatch = priceText.match(/[\\d,.]+/);
                if (priceMatch) {
                    price = parseFloat(priceMatch[0].replace(/,/g, ""));
                }
            }

            let stockCount = null;
            const stockElements = document.querySelectorAll("span");
            for (const element of stockElements) {
                const text = element.textContent?.toLowerCase() || "";
                if (text.includes("in stock") || text.includes("available")) {
                    const match = text.match(/(\\d+)\\s*(in stock|available)/i);
                    if (match) {
                        stockCount = parseInt(match[1]);
                        break;
                    }
                }
            }

            if (!stockCount) {
                const allText = document.body.textContent || "";
                const stockMatch = allText.match(/only\\s+(\\d+)\\s+left/i);
                if (stockMatch) {
                    stockCount = parseInt(stockMatch[1]);
                }
            }

            return { title, price, stockCount, itemNumber };
        }"""
    )

    print("✅ eBay data extracted:", ebay_data)
    return ebay_data

async def scrape_ebay_from_csv(csv_path: str):
    results = []

    # Read URLs from CSV file
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        urls = [row[0] for row in reader if row]  # assuming 1st column contains URLs

    print(f"📄 Found {len(urls)} URLs to scrape.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for i, url in enumerate(urls, 1):
            try:
                print(f"\n🔹 Scraping ({i}/{len(urls)}): {url}")
                data = await scrape_ebay_single_url(page, url)
                results.append({ "url": url, **data })
            except Exception as e:
                print(f"❌ Failed to scrape {url}: {e}")
                results.append({ "url": url, "error": str(e) })

        await browser.close()

    print("\n✅ Scraping completed.")
    return results
