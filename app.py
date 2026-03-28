import json
import queue
import threading
from flask import Flask, render_template, request, Response, stream_with_context
from engine import run_pipeline
from collections import defaultdict
import time

REQUEST_LOG = defaultdict(list)

def is_rate_limited(ip):
    now = time.time()
    REQUEST_LOG[ip] = [t for t in REQUEST_LOG[ip] if now - t < 60]
    if len(REQUEST_LOG[ip]) >= 5:
        return True
    REQUEST_LOG[ip].append(now)
    return False


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    if is_rate_limited(request.remote_addr):
        return {"error": "Rate limit exceeded"}, 429

    data = request.json # Get full json body
    keyword = data.get("keyword", "").strip()
    
    if not keyword:
        return {"error": "No keyword provided"}, 400
    if len(keyword) > 120:
        return {"error": "Keyword too long. Keep it under 120 characters."}, 400

    clean_keyword, flagged = sanitize_keyword(keyword)
    if flagged:
        return {"error": "Invalid input. Please enter a plain SEO keyword."}, 400


    q = queue.Queue()

    def pipeline_thread():
        # Step and msg are used for the progress bar in index.html
        def progress(step, msg):
            q.put({"type": "progress", "step": step, "msg": msg})
        try:
            # This now returns the variants thanks to our engine.py update
            result = run_pipeline(keyword, progress_callback=progress)
            
            # Ensure analysis is a dict for JSON serialization
            result["analysis"] = dict(result["analysis"])
            
            # The 'result' dict now contains 'platform_variants'
            q.put({"type": "done", "data": result})
        except Exception as e:
            import traceback
            print(traceback.format_exc()) # Log for debugging during hackathon
            q.put({"type": "error", "msg": str(e)})

    # Threading allows the UI to stay responsive during generation
    threading.Thread(target=pipeline_thread, daemon=True).start()

    def stream():
        while True:
            item = q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item["type"] in ("done", "error"):
                break

    return Response(stream_with_context(stream()), mimetype="text/event-stream")

if __name__ == "__main__":
    # Threaded=True is important for the streaming response
    app.run(debug=True, port=5000, threaded=True)
