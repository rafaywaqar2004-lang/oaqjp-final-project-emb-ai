"""Injects Google Analytics (GA4) and a real page title into Streamlit's own
static index.html at deploy time.

Why this exists: Streamlit is a client-rendered single-page app -- there is
no `<head>` a script running inside the app can reach, so `st.markdown` /
`st.components.v1.html` snippets get sandboxed in an iframe and never fire a
real top-level pageview. The reliable fix (already used by this project's
companion, the MENASA Risk Monitor -- see its `patch_og_tags.py`) is to patch
the actual HTML shell Streamlit ships, once, as a Render build step run right
after `pip install` installs the package.

Reuses the MENASA Risk Monitor's GA4 property (G-QP9RPS41KJ) rather than
spinning up a separate one, so all of this portfolio's live projects report
into the same place.

Idempotent: safe to run on every build. If the managed block is already
present (e.g. a re-run without a fresh install), it's replaced rather than
duplicated.
"""
import os
import re
import streamlit

TITLE = "Gulf AI & Tech-Bloc Alignment Tracker"

GA_MEASUREMENT_ID = "G-QP9RPS41KJ"

GA_BLOCK_START = "<!-- BEGIN ga-analytics (managed by patch_analytics.py) -->"
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


def main():
    index_path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
    with open(index_path, encoding="utf-8") as f:
        html = f.read()

    html = re.sub(re.escape(GA_BLOCK_START) + r".*?" + re.escape(GA_BLOCK_END), "", html, flags=re.DOTALL)
    html = html.replace("<title>Streamlit</title>", f"<title>{TITLE}</title>")
    html = html.replace("</head>", GA_BLOCK + "\n  </head>")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Patched Google Analytics into {index_path}")


if __name__ == "__main__":
    main()
