from flask import Flask, request, jsonify, render_template
import asyncio
import nest_asyncio
import sys
import time
import os
from scraper import scrape_ebay_from_csv, scrape_amazon_from_csv
from utils.config_manager import get_chromium_path

# Allow nested event loops (Flask + asyncio compatibility)
nest_asyncio.apply()

# Determine base path for templates and static files
if getattr(sys, 'frozen', False):  # Running as compiled EXE
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

app = Flask(
    __name__,
    template_folder=os.path.join(base_path, "templates"),
    static_folder=os.path.join(base_path, "static")
)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

chromium_path = get_chromium_path()
print("Chromium path is:", chromium_path)

EXPIRY_TIMESTAMP = 1761183552

@app.before_request
def check_expiry():
    current_time = int(time.time())
    if current_time > EXPIRY_TIMESTAMP:
        return jsonify({"error": "This app has expired."}), 403

@app.route("/")
def index():
    """Serve home page with eBay and Amazon buttons."""
    return render_template("index.html")


@app.route("/ebay")
def ebay_page():
    """Serve the eBay-specific page."""
    return render_template("ebay.html")


@app.route("/amazon")
def amazon_page():
    """Serve the Amazon-specific page."""
    return render_template("amazon.html")

@app.route("/health")
def health_check():
    return jsonify({"message": "✅ eBay Scraper API is running!"})


@app.route("/scrape-ebay", methods=["POST"])
def scrape_ebay():
    """
    Accepts a JSON body with a 'urls' field containing a list of eBay URLs.
    Scrapes them one by one and returns the results as JSON.
    """
    try:
        data = request.get_json()
        if not data or "urls" not in data:
            return jsonify({"status": "error", "message": "No URLs provided"}), 400

        urls = [u.strip() for u in data["urls"] if u.strip()]
        if not urls:
            return jsonify({"status": "error", "message": "URL list is empty"}), 400

        # Run the async scraper directly with URLs
        results = asyncio.run(scrape_ebay_from_csv(urls))

        return jsonify({"status": "success", "results": results})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/scrape-amazon", methods=["POST"])
def scrape_amazon():
    """
    Accepts JSON body with a list of URLs.
    Example: { "urls": ["https://amazon.com/dp/B00FR6XR9S", ...] }
    Scrapes them asynchronously and returns the results as JSON.
    """
    try:
        data = request.get_json()
        if not data or "urls" not in data:
            return jsonify({"status": "error", "message": "No URLs provided"}), 400

        urls = [u.strip() for u in data["urls"] if u.strip()]
        if not urls:
            return jsonify({"status": "error", "message": "URL list is empty"}), 400

        # Run the async scraper directly
        results = asyncio.run(scrape_amazon_from_csv(urls))

        return jsonify({"status": "success", "data": results})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



if __name__ == "__main__":
    import webbrowser
    from threading import Timer

    # Define the URL you want to open
    url = "http://127.0.0.1:5000"

    # Open browser shortly after server starts
    Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(debug=True)