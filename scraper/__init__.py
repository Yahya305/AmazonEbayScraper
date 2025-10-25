"""
scraper package

Contains modular scraping utilities for different e-commerce websites.
Each scraper module should expose an async function named `scrape_<site>()`
that accepts a URL and returns a dictionary of scraped data.
"""

from .ebay_scraper import scrape_ebay_from_list, scrape_amazon_from_csv, scrape_ebay_with_progress

__all__ = [
    "scrape_ebay_from_list",
    "scrape_amazon_from_csv",
    "scrape_ebay_with_progress",
]
