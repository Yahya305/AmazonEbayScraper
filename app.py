from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import asyncio
import nest_asyncio
import sys
import time
import os
from scraper import scrape_ebay_from_list, scrape_amazon_with_progress, scrape_ebay_with_progress
from utils.config_manager import get_chromium_path
import json

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

EXPIRY_TIMESTAMP = 1762206093

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


@app.route("/scrape-ebay-stream", methods=["POST"])
def scrape_ebay_stream():
    """
    Accepts a JSON body with a 'urls' field containing a list of eBay URLs.
    Scrapes them using SSE for real-time progress updates.
    """
    try:
        data = request.get_json()
        if not data or "urls" not in data:
            return jsonify({"status": "error", "message": "No URLs provided"}), 400
        
        urls = [u.strip() for u in data["urls"] if u.strip()]
        if not urls:
            return jsonify({"status": "error", "message": "URL list is empty"}), 400
        
        def generate():
            """Synchronous generator that runs async scraper"""
            import asyncio
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the async generator
                async def stream_updates():
                    async for update in scrape_ebay_with_progress(urls):
                        yield update
                
                # Process each update synchronously
                async_gen = stream_updates()
                
                while True:
                    try:
                        # Get next update from async generator
                        update = loop.run_until_complete(async_gen.__anext__())
                        # Format as SSE and yield immediately
                        yield f"data: {json.dumps(update)}\n\n"
                    except StopAsyncIteration:
                        break
                        
            finally:
                loop.close()
        
        # Return response with proper headers for SSE
        response = Response(generate(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response
        
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route("/scrape-amazon-stream", methods=["POST"])
def scrape_amazon_stream():
    """
    Accepts a JSON body with 'urls' and optional 'zip_code'.
    Scrapes Amazon URLs using SSE for real-time progress updates.
    """
    try:
        data = request.get_json()
        if not data or "urls" not in data:
            return jsonify({"status": "error", "message": "No URLs provided"}), 400
        
        urls = [u.strip() for u in data["urls"] if u.strip()]
        if not urls:
            return jsonify({"status": "error", "message": "URL list is empty"}), 400
        
        max_concurrent = data.get("max_concurrent", 3)  # Lower for Amazon
        
        def generate():
            """Synchronous generator that runs async scraper"""
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                async def stream_updates():
                    async for update in scrape_amazon_with_progress(urls, max_concurrent):
                        yield update
                
                async_gen = stream_updates()
                
                while True:
                    try:
                        update = loop.run_until_complete(async_gen.__anext__())
                        yield f"data: {json.dumps(update)}\n\n"
                    except StopAsyncIteration:
                        break
                        
            finally:
                loop.close()
        
        response = Response(generate(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response
        
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
    
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
        results = asyncio.run(scrape_ebay_from_list(urls))

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
    # url = "http://127.0.0.1:5000"

    # # Open browser shortly after server starts
    # Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(debug=True)