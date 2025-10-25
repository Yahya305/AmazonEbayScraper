import asyncio
from typing import List
from playwright.async_api import async_playwright, Page
from utils.setup_browser import get_chromium_path
import re
import random

# --- Reusable single-URL scraper ---
async def scrape_ebay(item_url: str):
    chromium_path = get_chromium_path()
    try:
        # if random.random() < 0.4:
        #     raise Exception("Simulated random error for testing")
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=chromium_path,
                                              args=["--headless=new"],
                                            # headless=False
                                              )
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

async def scrape_ebay_from_list(urls: List[str]):
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

async def scrape_ebay_with_progress(urls: List[str]):
    """
    Async generator that yields progress updates and results as scraping happens.
    Yields dict objects with different 'type' fields for progress tracking.
    """
    results = []
    failed_urls = []
    total = len(urls)
    
    for index, url in enumerate(urls, 1):
        # Yield progress update
        yield {
            'type': 'progress',
            'current': index,
            'total': total,
            'url': url,
            'percentage': round((index / total) * 100, 1)
        }
        
        # Scrape the URL
        print(f"🔍 Scraping: {url}")
        result = await scrape_ebay(url)
        
        if result.get("success"):
            results.append(result["data"])
            # Yield success update
            yield {
                'type': 'item_success',
                'data': result['data']
            }
        else:
            failed_urls.append(result.get("url", url))
            # Yield failure update
            yield {
                'type': 'item_failed',
                'url': url,
                'error': result.get('error', 'Unknown error')
            }
    
    # Yield final results
    yield {
        'type': 'complete',
        'results': results,
        'totalUrls': total,
        'successfulScrapes': len(results),
        'failedScrapes': len(failed_urls),
        'failedUrls': failed_urls
    }
    
async def set_amazon_zip_code(page: Page, zip_code: str = "75007"):
    """Set the delivery zip code on Amazon product page"""
    try:
        print(f"Setting zip code to {zip_code}...")
        
        # Click the "Deliver to" link in the header
        deliver_button = page.locator('#nav-global-location-popover-link')
        await deliver_button.click(timeout=5000)
        await asyncio.sleep(2)  # Wait for modal to fully load
        print("Clicked deliver button, modal opening...")
        
        # Wait for the zip input field to appear
        zip_input = page.locator('#GLUXZipUpdateInput')
        await zip_input.wait_for(timeout=5000, state="visible")
        print("Modal opened, found zip input")
        
        # Clear and enter the zip code
        await zip_input.fill(zip_code)
        await asyncio.sleep(0.5)
        print(f"Entered zip code: {zip_code}")
        
        # Click Apply button
        apply_button = page.locator('#GLUXZipUpdate')
        await apply_button.click(timeout=5000)
        await asyncio.sleep(3)  # Wait longer for confirmation/response
        print("Applied zip code")
        
        # Check for the confirmation modal "You're now shopping for delivery to:"
        # Look for the header text to confirm modal is visible
        try:
            print("Checking for confirmation modal...")
            confirmation_header = page.locator('h4:has-text("You\'re now shopping for delivery to:")')
            await confirmation_header.wait_for(timeout=5000, state="visible")
            print("Found confirmation modal header")
            
            # Click the actual input button, not the span
            confirmation_button = page.locator('.a-popover-footer input#GLUXConfirmClose').first
            await confirmation_button.click(timeout=5000, force=True)
            await asyncio.sleep(2)  # Wait for page to update
            print("Clicked Continue on confirmation modal")
            return True
        except Exception as e:
            print(f"No confirmation modal found: {e}, trying Done button...")
        
        # If no confirmation modal, try to close with Done button
        done_button = page.locator('button[name="glowDoneButton"]')
        try:
            await done_button.click(timeout=5000)
            await asyncio.sleep(2)  # Wait for modal to close and page to update
            print("Closed modal with Done button")
        except Exception as e:
            print(f"⚠️ Could not find Done button, trying close icon: {e}")
            # Try clicking the close icon as fallback
            close_button = page.locator('button[aria-label="Close"]').first
            try:
                await close_button.click(timeout=5000)
                await asyncio.sleep(2)
                print("Closed modal with close icon")
            except:
                print("⚠️ Could not close modal, it may have auto-closed")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error setting zip code: {e}")
        return False


async def handle_captcha_or_continue(page: Page):
    """Handle Amazon's 'Continue shopping' button if it appears"""
    try:
        print("Checking for captcha/continue shopping button...")
        
        # Check if the continue shopping button exists
        continue_button = page.locator('button.a-button-text:has-text("Continue shopping")')
        
        # Wait a short time to see if it appears
        try:
            await continue_button.wait_for(timeout=3000, state="visible")
            print("Found 'Continue shopping' button, clicking...")
            await continue_button.click()
            await asyncio.sleep(2)  # Wait for navigation
            print("Clicked 'Continue shopping' successfully")
            return True
        except:
            print("No captcha/continue button found, proceeding normally")
            return False
            
    except Exception as e:
        print(f"⚠️ Error checking for continue button: {e}")
        return False

async def scrape_amazon(product_url: str, zip_code: str = "75007"):
    chromium_path = get_chromium_path()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                executable_path=chromium_path,
                args=["--headless=new"],
            )
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
            await page.goto(product_url, wait_until="load", timeout=60000)
            await asyncio.sleep(2)
            
            # === HANDLE CAPTCHA/CONTINUE BUTTON ===
            await handle_captcha_or_continue(page)
            
            # === SET ZIP CODE ===
            zip_set = await set_amazon_zip_code(page, zip_code)
            if not zip_set:
                await browser.close()
                return {"success": False, "url": product_url, "error": "Failed to set zip code"}
            
            # === SCRAPE DATA ===
            await asyncio.sleep(2)  # Extra wait for content to load
            
            amazon_data = await page.evaluate(
                """() => {
                    // Extract ASIN from URL
                    const urlMatch = window.location.href.match(/\\/dp\\/([A-Z0-9]+)/);
                    const itemNumber = urlMatch ? urlMatch[1] : null;
                    
                    // Extract title from the specific productTitle span
                    let title = null;
                    const titleElement = document.querySelector("#productTitle");
                    if (titleElement) {
                        title = titleElement.textContent?.trim() || null;
                    }
                    
                    // Extract price - get the offscreen text which has the full price
                    let discountedPrice = null;
                    const priceContainer = document.querySelector(".a-price.aok-align-center.reinventPricePriceToPayMargin");
                    if (!priceContainer) {
                        // Fallback for different price structure
                        const altPriceContainer = document.querySelector(".a-price[data-a-size='xl']");
                        if (altPriceContainer) {
                            const offscreenPrice = altPriceContainer.querySelector(".a-offscreen");
                            if (offscreenPrice) {
                                const priceText = offscreenPrice.textContent?.trim() || "";
                                const priceMatch = priceText.match(/\\$(\\d+[.,]?\\d*)/);
                                if (priceMatch) {
                                    discountedPrice = parseFloat(priceMatch[1].replace(/,/g, ""));
                                }
                            }
                        }
                    } else {
                        const offscreenPrice = priceContainer.querySelector(".a-offscreen");
                        if (offscreenPrice) {
                            const priceText = offscreenPrice.textContent?.trim() || "";
                            const priceMatch = priceText.match(/\\$(\\d+[.,]?\\d*)/);
                            if (priceMatch) {
                                discountedPrice = parseFloat(priceMatch[1].replace(/,/g, ""));
                            }
                        }
                    }
                    
                    // Extract actual price - look for list/typical price
                    let actualPrice = null;
                    const allText = document.body.innerText;
                    const typicalPriceMatch = allText.match(/Typical price[:\\s]+\\$(\\d+[.,]?\\d*)/i);
                    if (typicalPriceMatch) {
                        actualPrice = parseFloat(typicalPriceMatch[1].replace(/,/g, ""));
                    }
                    
                    // If no typical price found, use discounted price
                    if (!actualPrice) {
                        actualPrice = discountedPrice;
                    }
                    
                    // === Extract stock info from availability-string div ===
                    let inStock = false;
                    let numberInStock = null;
                    
                    const availabilityDiv = document.querySelector("#availability-string");
                    if (availabilityDiv) {
                        const availText = availabilityDiv.textContent?.trim() || "";
                        
                        // Check if "In Stock" text is present
                        if (availText.toLowerCase().includes("in stock")) {
                            inStock = true;
                            numberInStock = 999; // In stock, quantity not specified
                        }
                        
                        // Check for "Only X left in stock"
                        const onlyMatch = availText.match(/only\\s+(\\d+)\\s+left/i);
                        if (onlyMatch) {
                            inStock = true;
                            numberInStock = parseInt(onlyMatch[1]);
                        }
                    }
                    
                    return { 
                        itemNumber, 
                        title, 
                        discountedPrice, 
                        actualPrice, 
                        inStock,
                        numberInStock,
                        locationZipCode: "75007"
                    };
                }"""
            )
            
            await browser.close()
            amazon_data["url"] = product_url
            return {"success": True, "data": amazon_data}
            
    except Exception as e:
        print(f"❌ Error scraping {product_url}: {e}")
        return {"success": False, "url": product_url, "error": str(e)}

async def scrape_amazon_from_csv(urls: List[str], zip_code: str = "75007"):
    results = []
    failed_urls = []
    
    # Scrape sequentially (safer for Amazon — avoids blocking)
    for url in urls:
        print(f"🔍 Scraping: {url}")
        result = await scrape_amazon(url, zip_code)
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