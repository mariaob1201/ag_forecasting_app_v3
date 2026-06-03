/* DOM rendering helpers — metric tiles, model info expander, station table.
   All inputs are plain station objects with a ``_value`` and ``_class``
   field already attached by app.js. */

(function (root) {
  "use strict";

  const NEUTRAL = "#34495e";

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function tile(color, label, value) {
    return `
      <div class="metric-tile">
        <div class="metric-label" style="color:${color}">${escapeHtml(label)}</div>
        <div class="metric-value">${escapeHtml(value)}</div>
      </div>
    `;
  }

  function renderMetrics(stations, model, colors) {
    const total = stations.length;
    const hasValue = stations.filter(
      (s) => s._value != null && s._value !== -1 && s._class !== "Inactive"
    ).length;
    const high = stations.filter((s) => s._class === "High").length;
    const moderate = stations.filter((s) => s._class === "Moderate").length;
    const low = stations.filter((s) => s._class === "Low").length;

    const activeLabel = model.type === "biomass" ? "With prediction" : "Active stations";

    document.getElementById("metrics").innerHTML =
      tile(NEUTRAL, "Total stations", total) +
      tile(NEUTRAL, activeLabel, hasValue) +
      tile(colors.High || "#e74c3c", "High", high) +
      tile(colors.Moderate || "#f39c12", "Moderate", moderate) +
      tile(colors.Low || "#2ecc71", "Low", low);
  }

  function renderModelInfo(model, modelInfo) {
    const el = document.getElementById("model-info");
    const slug = model.model_name;
    const info = slug && modelInfo ? modelInfo[slug] : null;

    if (!info) {
      el.innerHTML = `
        <details>
          <summary>📖 About this model — ${escapeHtml(model.label)}</summary>
          <p class="muted">No metadata available for <code>${escapeHtml(slug || "")}</code>.</p>
        </details>
      `;
      return;
    }

    const variables = (info.variables || [])
      .map((v) => `<code>${escapeHtml(v)}</code>`)
      .join(", ");

    el.innerHTML = `
      <details>
        <summary>📖 About this model — ${escapeHtml(model.label)}</summary>
        <p><strong>${escapeHtml(info.name || slug)}</strong>
          ${info.crop ? `· crop: <em>${escapeHtml(info.crop)}</em>` : ""}
          ${info.version ? `· v${escapeHtml(info.version)}` : ""}
        </p>
        ${info.description ? `<p>${escapeHtml(info.description)}</p>` : ""}
        ${info.model_type ? `<p><strong>Model type:</strong> ${escapeHtml(info.model_type)}</p>` : ""}
        ${info.risk_output ? `<p><strong>Risk output:</strong> ${escapeHtml(info.risk_output)}</p>` : ""}
        ${info.inactive_rule ? `<p><strong>Inactive rule:</strong> ${escapeHtml(info.inactive_rule)}</p>` : ""}
        ${variables ? `<p><strong>Input variables:</strong> ${variables}</p>` : ""}
      </details>
    `;
  }

  function formatValue(value, model) {
    if (value == null || value === -1) return "n/a";
    if (model.type === "biomass") return `${Math.round(value).toLocaleString()} ${model.unit || "lb/ac"}`;
    return Number(value).toFixed(2);
  }

  function renderTable(stations, model, colors) {
    const valueHeader = model.type === "biomass" ? "Biomass" : "Risk value";
    const classOrder = { High: 0, Moderate: 1, Low: 2, Inactive: 3, Unknown: 4, "No Risk": 2 };

    const sorted = stations.slice().sort((a, b) => {
      // Primary: by class severity; secondary: by value desc.
      const aClass = classOrder[a._class] ?? 9;
      const bClass = classOrder[b._class] ?? 9;
      if (aClass !== bClass) return aClass - bClass;
      const av = a._value == null ? -Infinity : a._value;
      const bv = b._value == null ? -Infinity : b._value;
      return bv - av;
    });

    const rows = sorted
      .map((s) => {
        const color = colors[s._class] || "#95a5a6";
        return `
          <tr>
            <td><strong>${escapeHtml(s.name)}</strong>
                <small style="color:#6B7280">(${escapeHtml(s.id)})</small></td>
            <td>${escapeHtml(s.city || "")}</td>
            <td>${escapeHtml(s.county || "")}</td>
            <td>${escapeHtml(s.region || "")}</td>
            <td>${formatValue(s._value, model)}</td>
            <td><span class="class-pill" style="background:${color}">
              ${escapeHtml(s._class)}
            </span></td>
          </tr>`;
      })
      .join("");

    document.getElementById("station-table").innerHTML = `
      <thead>
        <tr>
          <th>Station</th>
          <th>City</th>
          <th>County</th>
          <th>Region</th>
          <th>${valueHeader}</th>
          <th>Class</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    `;
  }

  root.WIRender = { renderMetrics, renderModelInfo, renderTable };
})(window);
