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
    keyword = request.json.get("keyword", "").strip()
    if not keyword:
        return {"error": "No keyword provided"}, 400

    q = queue.Queue()

    def pipeline_thread():
        def progress(step, msg):
            q.put({"type": "progress", "step": step, "msg": msg})
        try:
            result = run_pipeline(keyword, progress_callback=progress)
            result["analysis"] = dict(result["analysis"])
            q.put({"type": "done", "data": result})
        except Exception as e:
            q.put({"type": "error", "msg": str(e)})

    threading.Thread(target=pipeline_thread, daemon=True).start()

    def stream():
        while True:
            item = q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item["type"] in ("done", "error"):
                break

    return Response(stream_with_context(stream()), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
