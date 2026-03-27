# Blogy Engine — AI Blog Generator

5-step AI-powered blog pipeline using Groq + LLaMA 3 70B.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Add your Groq API key:
   - Option A: Create a `.env` file:
     ```
     GROQ_API_KEY=your_key_here
     ```
   - Option B: Edit `engine.py` line 7 and replace `YOUR_GROQ_API_KEY_HERE`

   Get your free key at: https://console.groq.com

3. Run the server:
```bash
python app.py
```

4. Open browser: http://localhost:5000

## Pipeline

| Step | What it does |
|------|-------------|
| 1. Keyword analysis | Clusters intent, finds SERP gaps, India GEO context |
| 2. Outline | Generates H1/H2/H3 structure for featured snippets |
| 3. Draft | Writes 1400-1600 word SEO-optimised blog |
| 4. Humanise | Removes AI tells, adds natural variation |
| 5. SEO validate | Scores keyword density, structure, snippet readiness |

## Output

- Rendered blog preview
- Raw HTML (copy/download)
- SEO score breakdown
- Keyword intelligence panel

## Files

```
blogy-engine/
├── app.py          # Flask server + SSE streaming
├── engine.py       # 5-step prompt pipeline
├── templates/
│   └── index.html  # Web UI
├── requirements.txt
└── README.md
```
