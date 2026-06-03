# Single-container image — same pattern as the COA-builder deploy.
#
#   • Python base (we need it for the FastAPI backend + build_site.py)
#   • nginx installed alongside, fronts the static site at /
#   • uvicorn runs the proxy on 127.0.0.1:8000; nginx forwards /proxy/*
#   • start.sh boots both processes; tini reaps zombies as PID 1
#
# IMPORTANT: built from the REPO ROOT (see web/docker-compose.yml's
# `context: ..`), so COPY paths reference repo-root locations. Shared
# code (features/, assets/) lives alongside the Streamlit app at the
# root; website-only files live under web/.
#
# Daily refresh: `cd web && docker compose up -d --build`.

FROM python:3.11-slim

# nginx + tini (signal handling) + curl (healthcheck).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nginx tini curl gcc \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

WORKDIR /app

# Python deps first so this layer caches well.
COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -r requirements.txt

# Source tree. Shared code (features/, assets/) stays at /app top-level
# so the existing imports (`from features.api import ...`) keep working
# without any sys.path manipulation inside the container.
COPY features/         ./features/
COPY assets/           ./assets/
COPY web/backend/      ./backend/
COPY web/site/         ./site/
COPY web/build_site.py web/start.sh ./

# nginx config (the only server block we want).
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

# Build the bundled snapshot for fast first-load. If wiscopy can't
# reach Wisconet from inside the container, weather + biomass are
# skipped automatically — disease still loads, and the live /proxy/
# endpoints handle dynamic queries at runtime anyway.
RUN python build_site.py \
 || echo "[warn] build_site.py exited non-zero — continuing without a full bundle"

RUN chmod +x /app/start.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/start.sh"]
