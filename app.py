"""Streamlit entrypoint for the WI crop disease risk dashboard.

The actual UI lives in the ``streamlit_app`` package — this file just
wires the pieces together so ``streamlit run app.py`` Just Works.

Layout:
    streamlit_app/
        analytics.py    — gtag.js injection (reads GA_MEASUREMENT_ID)
        page.py         — st.set_page_config + logo + title
        sidebar.py      — sidebar controls + white-mold sub-radio
        ui.py           — reusable metric tile + footer
        main.py         — top-level page composition
        tabs/
            forecast.py — Disease Forecast tab
            trends.py   — Risk Trends tab
            weather.py  — Weather Data tab
            biomass.py  — Cereal Rye Biomass tab

The order below matters: Streamlit only accepts ``st.set_page_config``
as the first Streamlit call, and the analytics patch must touch
``index.html`` before the browser fetches it.
"""

from streamlit_app.analytics import inject_google_analytics
from streamlit_app.main import main
from streamlit_app.page import configure_page

inject_google_analytics()
configure_page()
main()
