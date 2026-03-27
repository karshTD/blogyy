import json
import queue
import threading
from flask import Flask, render_template, request, Response, stream_with_context
from engine import run_pipeline

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json # Get full json body
    keyword = data.get("keyword", "").strip()
    
    if not keyword:
        return {"error": "No keyword provided"}, 400

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
