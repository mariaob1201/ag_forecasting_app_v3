/* Cereal rye biomass NLS model — direct port of
   features/crereal_rye_biomass.py:predict_rye_biomass.

   Currently unused at runtime (the daily build pre-computes biomass
   server-side), but kept here so future iterations can let users
   change planting date / fall precip in the browser without a rebuild.
*/

(function (root) {
  "use strict";

  // Coefficients from the original NLS fit (R implementation).
  const COEF = {
    b0:   4.231e+02,   // intercept
    b_pd: -1.031e+00,  // slope on planting DOY
    b_pf: -2.878e-01,  // slope on fall precipitation (mm)
    k:     3.663e-03,  // logistic steepness
    x0:    1.049e+03,  // logistic midpoint (GDD)
  };

  function predictRyeBiomass(plantDoy, precipFallMm, gddTotal) {
    const num = COEF.b0 + COEF.b_pd * plantDoy + COEF.b_pf * precipFallMm;
    const den = 1 + Math.exp(-COEF.k * (gddTotal - COEF.x0));
    const raw = num / den;
    return raw * raw;
  }

  function fahrenheitToCelsius(f) { return (f - 32) * 5 / 9; }
  function inchesToMm(inches)     { return inches * 25.4; }

  // Simple-average GDD (base °C) for one day, vectorized over arrays.
  function dailyGddCelsius(tavgC, base) {
    base = base || 0;
    return Math.max(0, tavgC - base);
  }

  // Classify lb/ac into Low / Moderate / High using the same thresholds
  // as features/config.py:BIOMASS_THRESHOLDS.
  function classifyBiomass(value, lowMax, highMin) {
    if (value == null || Number.isNaN(value)) return "Unknown";
    if (value < lowMax) return "Low";
    if (value < highMin) return "Moderate";
    return "High";
  }

  root.Biomass = {
    predictRyeBiomass,
    fahrenheitToCelsius,
    inchesToMm,
    dailyGddCelsius,
    classifyBiomass,
    COEF,
  };
})(window);
