import asyncio
from typing import List
from playwright.async_api import async_playwright
from utils.setup_browser import get_chromium_path
import re

# --- Reusable single-URL scraper ---
async def scrape_ebay(item_url: str):
    chromium_path = get_chromium_path()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=chromium_path,args=["--headless=new"],)
            page = await browser.new_page()

            # Log browser console messages
            page.on("console", lambda msg: print("PAGE LOG:", msg.text))

            # Set realistic user-agent
            await page.context.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            # Navigate and wait for network to be idle
            await page.goto(item_url, wait_until="load", timeout=60000)
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

            await browser.close()

            ebay_data["url"] = item_url
            return {"success": True, "data": ebay_data}

    except Exception as e:
        print(f"❌ Error scraping {item_url}: {e}")
        return {"success": False, "url": item_url, "error": str(e)}


async def scrape_ebay_from_csv(urls: List[str]):
    results = []
    failed_urls = []

    # Scrape sequentially (safer for eBay — avoids blocking)
    for url in urls:
        print(f"🔍 Scraping: {url}")
        result = await scrape_ebay(url)

        if result.get("success"):
            results.append(result["data"])
        else:
            failed_urls.append(result.get("url", url))

    return {
        "results": results,
        "totalUrls": len(urls),
        "successfulScrapes": len(results),
        "failedScrapes": len(failed_urls),
        "failedUrls": failed_urls,
    }