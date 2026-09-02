"""Injects Google Analytics, Open Graph / Twitter Card meta tags, and a
branded cold-start loading screen into Streamlit's own static index.html at
deploy time.

Why this exists: Streamlit is a client-rendered single-page app -- the tab
title/description set via st.set_page_config, or a GA snippet dropped in via
st.markdown, only apply after the JS bundle loads and runs (and st.markdown
content gets iframe-sandboxed regardless). Link-preview crawlers (LinkedIn,
Slack, iMessage, etc.) don't execute JS at all; they read the static HTML
Streamlit ships as-is, which has no OG tags and a generic "Streamlit" title.
The reliable fix -- already proven in this project's companion, the MENASA
Risk Monitor (see its own patch_og_tags.py) -- is to patch the actual HTML
shell Streamlit ships, once, as a Render build step run right after
`pip install` installs the package, before the server ever starts.

The loading screen exists for a different problem with the same root cause
(no way to touch the shipped shell): Render's free tier spins the container
down after a few idle minutes, so the first visitor after a quiet spell hits
a genuine cold start. Until Streamlit's JS bundle loads, connects its
websocket, and runs the Python script, the browser shows a blank page --
which reads as "broken," not "loading." This block renders instantly (static
HTML/CSS, no JS bundle needed) and removes itself once the real app has
actually rendered content.

Reuses the MENASA Risk Monitor's GA4 property (G-QP9RPS41KJ) rather than a
separate one, so all of this portfolio's live projects report into one place.

Idempotent: safe to run on every build. If a managed block is already
present (e.g. a re-run without a fresh install), it's replaced rather than
duplicated.
"""
import os
import re
import streamlit

SITE_URL = os.environ.get("SITE_URL", "https://oaqjp-final-project-emb-ai-c8u6.onrender.com")
TITLE = "Gulf AI & Tech-Bloc Alignment Tracker"
DESCRIPTION = (
    "17 countries scored on US-China AI/chip alignment -- cited data, a live "
    "composite index, a chronological policy-event tracker, and a "
    "scenario-reweighting explorer."
)
IMAGE_URL = f"{SITE_URL}/app/static/og-image.png"

GA_MEASUREMENT_ID = "G-QP9RPS41KJ"

GA_BLOCK_START = "<!-- BEGIN ga-analytics (managed by patch_og_tags.py) -->"
GA_BLOCK_END = "<!-- END ga-analytics -->"

GA_BLOCK = f"""{GA_BLOCK_START}
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{ dataLayer.push(arguments); }}
      gtag('js', new Date());
      gtag('config', '{GA_MEASUREMENT_ID}');
    </script>
    {GA_BLOCK_END}"""

OG_BLOCK_START = "<!-- BEGIN og-tags (managed by patch_og_tags.py) -->"
OG_BLOCK_END = "<!-- END og-tags -->"

OG_BLOCK = f"""{OG_BLOCK_START}
    <meta name="description" content="{DESCRIPTION}" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{TITLE}" />
    <meta property="og:description" content="{DESCRIPTION}" />
    <meta property="og:image" content="{IMAGE_URL}" />
    <meta property="og:url" content="{SITE_URL}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{TITLE}" />
    <meta name="twitter:description" content="{DESCRIPTION}" />
    <meta name="twitter:image" content="{IMAGE_URL}" />
    {OG_BLOCK_END}"""

LOADER_BLOCK_START = "<!-- BEGIN cold-start-loader (managed by patch_og_tags.py) -->"
LOADER_BLOCK_END = "<!-- END cold-start-loader -->"

LOADER_BLOCK = f"""{LOADER_BLOCK_START}
  <div id="cold-start-loader" style="
      position: fixed; inset: 0; z-index: 999999;
      background: #f7f7f2; color: #1b1e22;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      font-family: -apple-system, 'Public Sans', 'Segoe UI', sans-serif;
      text-align: center; padding: 1.5rem;
      transition: opacity 0.4s ease;
    ">
    <div style="
        width: 40px; height: 40px; border-radius: 50%;
        border: 3px solid rgba(36,84,166,0.2); border-top-color: #2454a6;
        animation: cold-start-spin 0.9s linear infinite; margin-bottom: 1.5rem;
      "></div>
    <div style="font-family: 'Source Serif 4', Georgia, serif; font-size: 1.15rem; font-weight: 700;">{TITLE}</div>
    <div style="font-size: 0.88rem; color: #52585f; margin-top: 0.6rem; max-width: 340px; line-height: 1.5;">
      Waking up the live demo -- this free-tier instance sleeps when idle,
      so the first load can take up to 30 seconds.
    </div>
  </div>
  <style>
    @keyframes cold-start-spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
  <script>
    (function() {{
      var startedAt = Date.now();
      var maxWaitMs = 25000;
      var poll = setInterval(function() {{
        var appRoot = document.querySelector('[data-testid="stAppViewContainer"]');
        var hasContent = appRoot && appRoot.innerText && appRoot.innerText.trim().length > 0;
        if (hasContent || Date.now() - startedAt > maxWaitMs) {{
          clearInterval(poll);
          var loader = document.getElementById('cold-start-loader');
          if (loader) {{
            loader.style.opacity = '0';
            setTimeout(function() {{ loader.remove(); }}, 400);
          }}
        }}
      }}, 250);
    }})();
  </script>
  {LOADER_BLOCK_END}"""


def main():
    index_path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
    with open(index_path, encoding="utf-8") as f:
        html = f.read()

    # Remove any previously-injected blocks first, so re-running this script
    # (e.g. a redeploy without a clean install) replaces rather than duplicates.
    for start, end in [(OG_BLOCK_START, OG_BLOCK_END), (LOADER_BLOCK_START, LOADER_BLOCK_END), (GA_BLOCK_START, GA_BLOCK_END)]:
        html = re.sub(re.escape(start) + r".*?" + re.escape(end), "", html, flags=re.DOTALL)

    html = html.replace("<title>Streamlit</title>", f"<title>{TITLE}</title>")
    html = html.replace("</head>", OG_BLOCK + "\n  " + GA_BLOCK + "\n  </head>")
    html = html.replace("</body>", LOADER_BLOCK + "\n</body>")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Patched OG tags, GA, and cold-start loader into {index_path}")


if __name__ == "__main__":
    main()
