"""Optional LLM helper — "Ask about this forecast" for the Disease tab.

Adds a chat box that lets a user ask plain-language questions about the
current forecast (e.g. "why is Arlington High this week?", "what does
this model actually measure?"). The model is fed ONLY the data already
on screen plus the disease's encyclopedia URL — never advice prompts —
and is instructed to refuse treatment recommendations and refer users
to a certified agronomist or UW Extension.

Configuration (env vars, read on each call):
    OPENAI_API_KEY  — required. When unset, the expander renders a
                       short setup hint instead of the chat UI.
    OPENAI_MODEL    — optional. Defaults to "gpt-4o-mini" — small,
                       fast, ~$0.0001 per typical query here.

Nothing in this module is imported by `app.py` or `streamlit_app.main`
unless the chat is actually rendered, so missing the `openai` package
does NOT break the rest of the app.
"""

from __future__ import annotations

import os
from typing import Iterable

import pandas as pd
import streamlit as st

# Map disease label → authoritative reference URL. Mirrors the
# "Crop risk models" section of README.md so the model can cite the
# same source the user reads.
DISEASE_REFERENCES: dict[str, str] = {
    "Tar Spot (corn)":
        "https://cropprotectionnetwork.org/encyclopedia/tar-spot-of-corn",
    "Gray Leaf Spot (corn)":
        "https://cropprotectionnetwork.org/encyclopedia/gray-leaf-spot-of-corn",
    "Frogeye Leaf Spot (soybean)":
        "https://cropprotectionnetwork.org/encyclopedia/frogeye-leaf-spot-of-soybean",
    "White Mold — Non-irrigated (soybean)":
        "https://cropprotectionnetwork.org/encyclopedia/white-mold-of-soybean",
    "White Mold — Irrigated 30in (soybean)":
        "https://cropprotectionnetwork.org/encyclopedia/white-mold-of-soybean",
    "White Mold — Irrigated 15in (soybean)":
        "https://cropprotectionnetwork.org/encyclopedia/white-mold-of-soybean",
}

SYSTEM_PROMPT = """\
You are an assistant that explains daily crop-disease risk forecasts to
farmers, extension agents, and students using the Wisconsin Agricultural
Forecasting Advisory System (UW–Madison).

Your job is ONLY to:
  • Explain what the data on screen shows — risk values, classes, station
    locations, distributions.
  • Describe what the disease model is and cite the encyclopedia URL
    when one is provided in the context.
  • Translate technical terms (GDD, sentinel -1, "Inactive" model state,
    etc.) into plain language.

You MUST NOT:
  • Recommend whether or when to spray, treat, or apply fungicides.
  • Recommend specific products, application rates, or agronomic actions.
  • Predict yield or financial outcomes.

When asked about treatment, respond with: "For management decisions,
please consult a certified agronomist or your local UW–Madison
Extension office (https://extension.wisc.edu/)."

Be concise — 3-5 sentences unless asked for detail. Cite the
encyclopedia URL the user is already viewing whenever it's relevant.
"""

DEFAULT_MODEL = "gpt-4o-mini"

# Hard caps so a runaway prompt can't quietly burn tokens.
MAX_STATIONS_IN_CONTEXT = 25
MAX_QUESTION_CHARS = 500


# ---------------------------------------------------------------------------
# Pure helpers — tested in tests/test_llm.py
# ---------------------------------------------------------------------------

def reference_url_for(disease_label: str) -> str | None:
    """Authoritative reference URL for a disease label, or None."""
    return DISEASE_REFERENCES.get(disease_label)


def summarize_class_counts(class_series: Iterable[str]) -> dict[str, int]:
    """Tally `{class_label: count}` for the model's class column."""
    counts: dict[str, int] = {}
    for c in class_series:
        key = str(c) if c is not None else "Unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_forecast_context(
    forecast_date: str,
    disease_label: str,
    df: pd.DataFrame,
    risk_field: str,
    class_field: str,
) -> str:
    """Render the on-screen forecast into a compact context block.

    The LLM sees: the date, the disease, the class-distribution summary,
    and the top-N stations by risk value (descending). This keeps the
    prompt under ~1k tokens even for a full 78-station forecast.
    """
    parts: list[str] = []
    parts.append(f"Forecast date: {forecast_date}")
    parts.append(f"Disease model: {disease_label}")
    ref = reference_url_for(disease_label)
    if ref:
        parts.append(f"Reference (cite this URL when relevant): {ref}")

    if df.empty:
        parts.append("(No station data returned for this date.)")
        return "\n".join(parts)

    parts.append(f"Total stations: {len(df)}")

    if class_field in df.columns:
        counts = summarize_class_counts(df[class_field].astype(str))
        nice = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        parts.append(f"Class distribution: {nice}")

    # Top-N stations by risk value (descending), excluding -1 / NaN.
    cols = [c for c in ("station_name", "city", "county", risk_field, class_field)
            if c in df.columns]
    if cols and risk_field in df.columns:
        sortable = df[cols].copy()
        sortable[risk_field] = pd.to_numeric(sortable[risk_field], errors="coerce")
        active = sortable[sortable[risk_field].notna() & (sortable[risk_field] != -1)]
        if not active.empty:
            top = active.sort_values(risk_field, ascending=False).head(MAX_STATIONS_IN_CONTEXT)
            parts.append("Top stations by risk:")
            for _, row in top.iterrows():
                line = f"  - {row.get('station_name', '?')}"
                loc = ", ".join(str(row.get(k)) for k in ("city", "county") if row.get(k))
                if loc:
                    line += f" ({loc})"
                line += f": {row[risk_field]:.3f} [{row.get(class_field, '?')}]"
                parts.append(line)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def _get_client():
    """Lazy import + construct the OpenAI client so missing `openai` doesn't
    block the rest of the app from loading."""
    try:
        from openai import OpenAI
    except ImportError as err:
        raise RuntimeError(
            "The `openai` package is not installed. "
            "Run `pip install openai` to enable the chat feature."
        ) from err
    return OpenAI()  # reads OPENAI_API_KEY from env automatically


def ask_about_forecast(question: str, context: str, model: str | None = None) -> str:
    """Send (question + context) to the LLM and return the plain-text reply.

    Raises if the call fails — caller decides how to surface the error.
    """
    if not question.strip():
        return ""
    question = question[:MAX_QUESTION_CHARS]

    client = _get_client()
    chosen_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)

    resp = client.chat.completions.create(
        model=chosen_model,
        temperature=0.2,  # factual, no creative drift
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Current forecast context:\n\n{context}\n\n"
                f"User question:\n{question}"
            },
        ],
    )
    return (resp.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Streamlit fragment
# ---------------------------------------------------------------------------

def render_chat_expander(
    forecast_date: str,
    disease_label: str,
    df: pd.DataFrame,
    risk_field: str,
    class_field: str,
) -> None:
    """Render the "Ask about this forecast" expander on the Disease tab."""
    with st.expander("💬 Ask about this forecast (AI)", expanded=False):
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            st.info(
                "Set the `OPENAI_API_KEY` environment variable before launching "
                "Streamlit to enable AI-assisted explanations. "
                "Leave it unset to hide this feature entirely."
            )
            return

        st.caption(
            "Ask a plain-language question about the data on screen — *why is "
            "Arlington High this week?*, *what does GDD mean?*, *which counties "
            "have the most stations at risk?*"
        )

        question = st.text_area(
            "Your question",
            key=f"llm_q_{disease_label}",
            max_chars=MAX_QUESTION_CHARS,
            placeholder="Why is the risk Inactive at every station this week?",
            label_visibility="collapsed",
        )
        col_btn, _ = st.columns([1, 5])
        with col_btn:
            asked = st.button("Ask", key=f"llm_ask_{disease_label}", type="primary")

        if asked and question.strip():
            context = build_forecast_context(
                forecast_date, disease_label, df, risk_field, class_field
            )
            try:
                with st.spinner("Thinking…"):
                    answer = ask_about_forecast(question, context)
            except Exception as err:  # noqa: BLE001
                st.error(f"LLM call failed: **{type(err).__name__}** — {err}")
                return
            if answer:
                st.markdown(answer)
            else:
                st.warning("The model returned an empty response.")

        st.caption(
            "_This feature summarizes the forecast data only — it does not "
            "provide management recommendations. For treatment decisions, "
            "consult a certified agronomist or your local "
            "[UW–Madison Extension office](https://extension.wisc.edu/)._"
        )
