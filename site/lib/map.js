/* Leaflet map setup + marker rendering for the static dashboard.
   Mirrors the Streamlit map (carto-positron-ish basemap + emoji
   station markers colored by risk class). */

(function (root) {
  "use strict";

  const WI_CENTER = [44.6, -89.7];
  const WI_ZOOM = 6.5;

  function initMap(elementId) {
    const map = L.map(elementId, { zoomControl: true, scrollWheelZoom: true })
      .setView(WI_CENTER, WI_ZOOM);

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · ' +
          '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 19,
      }
    ).addTo(map);

    return map;
  }

  // Single layer group we replace on every model switch — keeps GC
  // from collecting orphan markers and avoids stacking.
  let markersLayer = null;

  function makeIcon(color) {
    return L.divIcon({
      className: "station-marker",
      html:
        `<div style="
           background:${color};
           border:2px solid white;
           border-radius:50%;
           width:24px;height:24px;
           display:flex;align-items:center;justify-content:center;
           font-size:12px;
           box-shadow:0 1px 3px rgba(0,0,0,0.35);">
           📡
         </div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12],
    });
  }

  function popupHtml(station, model) {
    const valueLabel =
      model.type === "biomass" ? "Predicted biomass" : "Risk";
    const valueText =
      station._value == null || station._value === -1
        ? "n/a"
        : model.type === "biomass"
        ? `${Math.round(station._value).toLocaleString()} ${model.unit || "lb/ac"}`
        : station._value.toFixed(2);

    return `
      <div class="popup-name">${escapeHtml(station.name)}
        <small style="color:#6B7280">(${escapeHtml(station.id)})</small>
      </div>
      <div class="popup-meta">
        ${escapeHtml(station.city || "")},
        ${escapeHtml(station.county || "")}
        — ${escapeHtml(station.region || "")}
      </div>
      <div class="popup-class">
        ${escapeHtml(station._class)}
      </div>
      <div>${valueLabel}: <strong>${valueText}</strong></div>
    `;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderStations(map, stations, model, colors) {
    if (markersLayer) {
      markersLayer.remove();
      markersLayer = null;
    }
    markersLayer = L.layerGroup();

    stations.forEach((s) => {
      if (s.lat == null || s.lon == null) return;
      const color = colors[s._class] || colors.Unknown || "#bdc3c7";
      const marker = L.marker([s.lat, s.lon], { icon: makeIcon(color) });
      marker.bindPopup(popupHtml(s, model));
      markersLayer.addLayer(marker);
    });

    markersLayer.addTo(map);
  }

  root.WIMap = { initMap, renderStations };
})(window);
