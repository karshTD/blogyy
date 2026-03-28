import os
import re
from dotenv import load_dotenv
from groq import Groq



_INJECTION_PHRASES = [
    "ignore all", "ignore previous", "act as", "jailbreak",
    "system prompt", "forget everything", "forget all",
    "disregard", "dan mode", "pretend you are", "pretend to be",
    "new persona", "prompt injection", "reveal your prompt",
    "reveal your instructions", "what are your instructions",
]

def sanitize_keyword(keyword: str):
    if re.search(r"<[^>]+>", keyword):
        return keyword, True
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", keyword).strip()
    if any(phrase in cleaned.lower() for phrase in _INJECTION_PHRASES):
        return cleaned, True
    if "<" in cleaned or ">" in cleaned or cleaned.count("\n") > 2:
        return cleaned, True
    return cleaned, False


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

def chat(system, user, temperature=0.7):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return response.choices[0].message.content.strip()


# ── STEP 1: Keyword clustering & intent analysis ──────────────────────────────
def analyse_keyword(keyword):
    system = """You are an expert SEO strategist specialising in the Indian digital market.
Your job is to analyse a seed keyword and return structured SEO intelligence.
Respond ONLY in this exact format, no extra text:

PRIMARY_INTENT: [informational|transactional|navigational|commercial]
SEARCH_VOLUME: [low|medium|high]
COMPETITION: [low|medium|high]
CLUSTER_KEYWORDS: [5 closely related LSI keywords, comma separated]
LONG_TAIL: [3 long-tail variants, comma separated]
SERP_GAP: [one sentence describing what existing results are missing]
GEO_CONTEXT: [one sentence on India-specific angle for this keyword]
META_TITLE: [SEO meta title under 60 chars]
META_DESC: [SEO meta description under 155 chars]"""

    user = f"Analyse this keyword for the Indian market: {keyword}"
    raw = chat(system, user, temperature=0.3)
    
    result = {}
    for line in raw.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


# ── STEP 2: Generate structured outline ──────────────────────────────────────
def generate_outline(keyword, analysis):
    cluster = analysis.get("CLUSTER_KEYWORDS", "")
    gap = analysis.get("SERP_GAP", "")
    geo = analysis.get("GEO_CONTEXT", "")

    system = """You are a senior content strategist. Create a detailed blog outline optimised for:
- Featured snippet eligibility (direct answers, lists, tables)
- Google's E-E-A-T guidelines (Experience, Expertise, Authority, Trust)
- Indian reader context
- Conversion: move reader from awareness → action

Output ONLY a clean outline in this format:
TITLE: [exact H1]
H2: [section name]
  H3: [subsection]
  H3: [subsection]
H2: [section name]
...
CTA: [call to action text]"""

    user = f"""Keyword: {keyword}
Related keywords: {cluster}
SERP gap to exploit: {gap}
India context: {geo}

Create a 6-8 section outline for a 1500-word blog."""
    
    return chat(system, user, temperature=0.5)


# ── STEP 3: Write the full blog draft ────────────────────────────────────────
def write_draft(keyword, outline, analysis):
    meta_title = analysis.get("META_TITLE", keyword)
    meta_desc = analysis.get("META_DESC", "")
    long_tail = analysis.get("LONG_TAIL", "")
    geo = analysis.get("GEO_CONTEXT", "")

    system = """You are a senior content writer who writes for Indian B2B and SaaS audiences.
Your writing style is:
- Conversational but authoritative
- Uses real examples, numbers, and specifics (not vague claims)
- Varies sentence length — mix short punchy sentences with longer analytical ones
- Never starts consecutive sentences the same way
- Includes India-specific context, pricing in INR where relevant
- Naturally weaves in keywords (never stuffed)
- Structures content for skimmability: short paragraphs, bold key phrases inline
- Writes like a knowledgeable human, not a content mill

Format the blog in clean HTML using only: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>, <table>, <tr>, <td>, <th>
Include the meta title and description as HTML comments at the top."""

    user = f"""Write a complete 1400-1600 word SEO blog using this outline:

{outline}

Requirements:
- Primary keyword: {keyword}
- Secondary keywords to include naturally: {long_tail}
- India-specific angle: {geo}
- Meta title: {meta_title}
- Meta description: {meta_desc}
- Include one comparison table if relevant
- End with a strong CTA paragraph
- Keyword density: 1–1.5% for primary keyword"""

    return chat(system, user, temperature=0.75)


# ── STEP 4: Humanisation pass ─────────────────────────────────────────────────
def humanise(draft):
    system = """You are an editor who makes AI-written content undetectable.
Your edits:
- Replace formal/robotic phrases with natural conversational equivalents
- Add occasional first-person observations ("In my experience...", "Honestly,...")
- Insert mild imperfections: rhetorical questions, incomplete thoughts fixed mid-sentence
- Vary paragraph rhythm — some very short (1 sentence), some longer
- Remove any AI tells: avoid "In conclusion", "It's worth noting", "Furthermore", "Moreover", "In today's digital landscape", "game-changer", "revolutionary", "leverage"
- Add specific Indian examples, cities, brand names where natural
- Keep all HTML formatting intact
- Do NOT change factual content or structure

Return ONLY the edited HTML, no commentary."""

    return chat(system, draft, temperature=0.85)


# ── STEP 5: SEO validation ─────────────────────────────────────────────────────
def validate_seo(blog_html, keyword):
    plain = re.sub(r'<[^>]+>', ' ', blog_html)
    plain = re.sub(r'\s+', ' ', plain).strip()
    word_count = len(plain.split())
    
    kw_lower = keyword.lower()
    words_lower = plain.lower()
    kw_count = words_lower.count(kw_lower)
    density = round((kw_count / word_count) * 100, 2) if word_count else 0

    h1 = len(re.findall(r'<h1[^>]*>', blog_html))
    h2 = len(re.findall(r'<h2[^>]*>', blog_html))
    h3 = len(re.findall(r'<h3[^>]*>', blog_html))
    has_table = 1 if '<table' in blog_html else 0
    has_list = 1 if '<ul' in blog_html or '<ol' in blog_html else 0
    has_meta = 1 if '<!-- META' in blog_html or 'meta' in blog_html.lower()[:200] else 0

    density_ok = 0.8 <= density <= 1.8
    length_ok = 1200 <= word_count <= 1800
    structure_ok = h1 >= 1 and h2 >= 4

    score = 0
    if density_ok: score += 25
    if length_ok: score += 20
    if structure_ok: score += 20
    if has_table: score += 10
    if has_list: score += 10
    if h3 >= 2: score += 10
    if has_meta: score += 5

    snippet_ready = has_list and h2 >= 4 and density_ok

    return {
        "seo_score": score,
        "word_count": word_count,
        "keyword_density": density,
        "density_ok": density_ok,
        "h1_count": h1,
        "h2_count": h2,
        "h3_count": h3,
        "has_table": bool(has_table),
        "has_list": bool(has_list),
        "snippet_ready": snippet_ready,
        "length_ok": length_ok,
        "structure_ok": structure_ok,
    }




# ── STEP 6: Platform-Specific Adaptation ───────────────────────────────────
PLATFORM_CONFIGS = {
    "LinkedIn": {
        "style": "High-engagement, professional social post. Use punchy one-sentence paragraphs, 5-7 bullet points, and a 'hook' at the top to stop the scroll. No HTML tags, use plain text with emojis for bullet points.",
        "length": "Shortened (approx 400-600 words highlights)",
        "format": "Plain Text"
    },
    "Medium": {
        "style": "Story-driven, authoritative long-form article. Keep high-quality H2/H3 headers. Focus on reader empathy and deep insights. Include a 'Read Time' estimate at the top.",
        "length": "Full length",
        "format": "Markdown/HTML"
    },
    "Dev.to": {
        "style": "Technical, builder-focused guide. Use code-block formatting where relevant. Direct, no-fluff tone. Must be in clean GitHub-Flavored Markdown.",
        "length": "Full length",
        "format": "Markdown"
    },
    "WordPress": {
        "style": "Standard SEO-optimized blog. Include meta-tags, image alt-text suggestions in brackets, and clear table of contents. Focus on keyword placement for snippet eligibility.",
        "length": "Full length",
        "format": "Clean HTML"
    },
    "Substack": {
        "style": "Newsletter style. Personal, direct address to the reader ('You'). Bold the most important takeaways. Clear, centered CTA buttons.",
        "length": "Full length",
        "format": "Markdown"
    }
}

def adapt_for_platform(blog_html, platform_name):
    config = PLATFORM_CONFIGS.get(platform_name)
    if not config:
        return blog_html

    system = f"""You are a platform-optimization expert. Convert the provided blog into a version specifically for {platform_name}.
    Rules:
    - Target Style: {config['style']}
    - Target Length: {config['length']}
    - Output Format: {config['format']}
    - Ensure 'Platform Adaptation Quality' is 100%.
    - Maintain the primary SEO intent but change the 'vibe' to fit the platform.
    Return ONLY the adapted content."""

    user = f"Adapt this blog content for {platform_name}:\n\n{blog_html}"
    return chat(system, user, temperature=0.6)



# ── MASTER PIPELINE ────────────────────────────────────────────────────────────
def run_pipeline(keyword, progress_callback=None):
    def progress(step, msg):
        if progress_callback:
            progress_callback(step, msg)

    progress(1, "Analysing keyword intent and clustering...")
    analysis = analyse_keyword(keyword)

    progress(2, "Generating SEO-optimised outline...")
    outline = generate_outline(keyword, analysis)

    progress(3, "Writing full blog draft...")
    draft = write_draft(keyword, outline, analysis)

    progress(4, "Running humanisation pass...")
    humanised = humanise(draft)

    progress(5, "Validating SEO metrics...")
    seo = validate_seo(humanised, keyword)

    progress(6, "Adapting content for 5 Approved Platforms...")
    variants = {}
    platforms = ["LinkedIn", "Medium", "Dev.to", "WordPress", "Substack"]
    
    for p in platforms:
        progress(6, f"Creating {p} version...")
        variants[p] = adapt_for_platform(humanised, p)

    return {
        "keyword": keyword,
        "analysis": analysis,
        "outline": outline,
        "blog_html": humanised,
        "seo": seo,
        "platform_variants": variants,
    }
