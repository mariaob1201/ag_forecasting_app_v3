"""Google Analytics bootstrap for the Streamlit app.

Reads ``GA_MEASUREMENT_ID`` from the process env on every cold start, so
the measurement id is never committed to source. Set it however suits
the deploy target — a shell ``export``, a systemd unit, a Posit Connect
content env var, a CI secret, etc.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


def inject_google_analytics() -> None:
    """Patch Streamlit's bundled ``index.html`` to load gtag.js once.

    Streamlit serves the same ``index.html`` from its install directory
    for every page load, so the injection persists for the life of the
    process. The ``"googletagmanager" not in html`` guard makes the
    patch idempotent across re-runs.

    No-op when ``GA_MEASUREMENT_ID`` is unset / empty.
    Silently no-op when the install dir is read-only (e.g. sandboxed
    serverless deploys).
    """
    ga_id = os.environ.get("GA_MEASUREMENT_ID", "").strip()
    if not ga_id:
        return

    index_path = Path(st.__file__).parent / "static" / "index.html"
    try:
        html = index_path.read_text(encoding="utf-8")
    except OSError:
        return
    if "googletagmanager" in html:
        return

    snippet = (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>'
        '<script>'
        'window.dataLayer = window.dataLayer || [];'
        'function gtag(){dataLayer.push(arguments);}'
        "gtag('js', new Date());"
        f"gtag('config', '{ga_id}');"
        '</script>'
    )
    try:
        index_path.write_text(html.replace("<head>", "<head>" + snippet, 1), encoding="utf-8")
    except OSError:
        pass
