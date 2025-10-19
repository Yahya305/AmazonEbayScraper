from flask import Flask, request, jsonify
import asyncio
import nest_asyncio
import io
import os
import csv
from scraper import scrape_ebay_from_csv
from utils.config_manager import get_chromium_path

# Allow nested event loops (Flask + asyncio compatibility)
nest_asyncio.apply()

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

chromium_path = get_chromium_path()
print("Chromium path is:", chromium_path)


@app.route("/")
def home():
    return jsonify({"message": "✅ eBay Scraper API is running!"})


@app.route("/scrape-ebay", methods=["POST"])
def scrape_ebay():
    """
    Accepts a CSV file (containing eBay item URLs).
    Scrapes them one by one and returns the results as JSON.
    Processes the file in memory (not saved to disk).
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        # Read CSV content in memory
        content = file.read().decode("utf-8")
        csv_data = io.StringIO(content)
        reader = csv.reader(csv_data)
        urls = [row[0].strip() for row in reader if row]  # assumes one URL per line

        # Run the async scraper directly with URLs
        data = asyncio.run(scrape_ebay_from_csv(urls))

        return jsonify({"status": "success", "results": data})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
