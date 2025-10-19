from flask import Flask, request, jsonify
import asyncio
import nest_asyncio
import os
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
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save uploaded file
    csv_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(csv_path)

    try:
        # Run the async scraper
        data = asyncio.run(scrape_ebay_from_csv(csv_path))
        return jsonify({"status": "success", "results": data})
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
