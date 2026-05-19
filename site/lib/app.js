/* Main controller for the static dashboard.

   Loads data/latest.json (built nightly by build_site.py), wires up the
   model selector, and re-renders the metric tiles + map + table + model
   info every time the user picks a different model.
*/

(function () {
  "use strict";

  const DATA_URL = "data/latest.json";

  function attachModelView(station, model) {
    // Decorate every station with `_value` / `_class` for the chosen model
    // so the renderers don't need to know which fields to read.
    const out = Object.assign({}, station);
    if (model.type === "biomass") {
      out._value = station[model.value_field] ?? null;
      out._class = station[model.class_field] || "Unknown";
    } else {
      const raw = station[model.risk_field];
      out._value = raw === -1 || raw == null ? null : raw;
      out._class = station[model.class_field] || "Unknown";
    }
    return out;
  }

  function populateModelSelect(models) {
    const sel = document.getElementById("model-select");
    sel.innerHTML = "";
    models.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.label;
      opt.textContent = m.label;
      sel.appendChild(opt);
    });
  }

  function setMeta(snapshot) {
    document.getElementById("forecast-date").textContent =
      "Forecast for " + snapshot.forecasting_date;
    document.getElementById("generated-at").textContent =
      "Updated " + new Date(snapshot.generated_at).toLocaleString();
  }

  function rerender(snapshot, model, map) {
    const stations = snapshot.stations.map((s) => attachModelView(s, model));
    WIMap.renderStations(map, stations, model, snapshot.class_colors);
    WIRender.renderMetrics(stations, model, snapshot.class_colors);
    WIRender.renderModelInfo(model, snapshot.model_info);
    WIRender.renderTable(stations, model, snapshot.class_colors);
  }

  async function boot() {
    let snapshot;
    try {
      const resp = await fetch(DATA_URL, { cache: "no-store" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      snapshot = await resp.json();
    } catch (err) {
      document.getElementById("metrics").innerHTML =
        `<div class="metric-tile" style="grid-column:1/-1;color:#9B0000">
           <div class="metric-label" style="color:#9B0000">Could not load data</div>
           <div class="metric-value">${err.message || err}</div>
           <p class="muted">
             Run <code>python build_site.py</code> from the project root
             to generate <code>${DATA_URL}</code>.
           </p>
         </div>`;
      return;
    }

    setMeta(snapshot);
    populateModelSelect(snapshot.models);

    const map = WIMap.initMap("map");
    let currentModel = snapshot.models[0];
    rerender(snapshot, currentModel, map);

    document
      .getElementById("model-select")
      .addEventListener("change", (e) => {
        currentModel = snapshot.models.find((m) => m.label === e.target.value);
        if (currentModel) rerender(snapshot, currentModel, map);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
