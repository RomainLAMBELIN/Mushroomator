// Index computation shared by the map and the point details (mirror of mushroomator/predict.py).
export const LAPSE_RATE = -0.0065;          // °C per metre
export const R_EARTH = 6378137;

export const isTemperature = (name) => name.startsWith("T") && name !== "dT7";

/** Linear interpolation in a table {x: [...], y: [...]} with evenly spaced x (clamped at both ends). */
export function tableInterp(tab, x) {
  const xs = tab.x, ys = tab.y, n = xs.length;
  if (!(x > xs[0])) return ys[0];
  if (x >= xs[n - 1]) return ys[n - 1];
  const pos = (x - xs[0]) / (xs[n - 1] - xs[0]) * (n - 1);
  const i = Math.min(n - 2, Math.floor(pos));
  const f = pos - i;
  return ys[i] * (1 - f) + ys[i + 1] * f;
}

/** Percentile (0-1) of a decision value among ordinary days of the season (quantiles q0..q100). */
export function percentile(quantiles, v) {
  const n = quantiles.length;
  if (!(v > quantiles[0])) return 0;
  if (v >= quantiles[n - 1]) return 1;
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (quantiles[mid] <= v) lo = mid; else hi = mid;
  }
  const span = quantiles[hi] - quantiles[lo];
  return (lo + (span > 0 ? (v - quantiles[lo]) / span : 0)) / (n - 1);
}

export function hostFactor(sp, group) {
  return sp.hotes[group] ?? 0;
}

export function elevationFactor(sp, z) {
  if (!Number.isFinite(z)) return 0;
  const [z0, z1, z2, z3] = sp.altitude;
  const up = Math.min(1, Math.max(0, (z - z0) / Math.max(z1 - z0, 1)));
  const down = Math.min(1, Math.max(0, (z3 - z) / Math.max(z3 - z2, 1)));
  return sp.altitude_plancher + (1 - sp.altitude_plancher) * Math.min(up, down);
}

export function phFactor(sp, ph) {
  if (!Number.isFinite(ph)) return 1;
  const [a, b] = sp.ph;
  const frac = Math.min(1, Math.max(0, (ph - a) / (b - a)));
  return sp.ph_bas + (1 - sp.ph_bas) * frac;
}

export function dayOfYear(iso) {
  const d = new Date(iso + "T12:00:00Z");
  return Math.round((d - Date.UTC(d.getUTCFullYear(), 0, 1, 12)) / 86400000) + 1;
}

/** Coarse weather-grid fields for one species and day. Non-temperature variables are turned into
 *  contributions on the coarse grid (then interpolated); temperatures are kept at sea level and moved to each
 *  pixel's elevation before applying their table. */
export function coarseFields(sp, weather, day) {
  const m = sp.modele, ny = weather.lats.length, nx = weather.lons.length;
  const doy = dayOfYear(weather.dates[day]);
  const base = new Float32Array(ny * nx).fill(m.intercept + tableInterp(m.tables.doy, doy));
  const contrib = {}, values = {}, temps = {};
  for (const f of m.features) {
    if (f === "doy") continue;
    const src = weather.features[isTemperature(f) ? f + "_sl" : f][day];
    const val = new Float32Array(ny * nx);
    for (let i = 0; i < ny; i++) for (let j = 0; j < nx; j++) val[i * nx + j] = src[i][j];
    values[f] = val;
    if (isTemperature(f)) { temps[f] = val; continue; }
    const eff = new Float32Array(ny * nx);
    for (let k = 0; k < eff.length; k++) { eff[k] = tableInterp(m.tables[f], val[k]); base[k] += eff[k]; }
    contrib[f] = eff;
  }
  return { day, doy, nx, ny, base, contrib, values, temps };
}

/** Interpolation index and weight of each value on a regular increasing axis. */
export function axisWeights(axis, values) {
  const step = axis[1] - axis[0], n = axis.length;
  const idx = new Int32Array(values.length), w = new Float32Array(values.length);
  values.forEach((v, k) => {
    const pos = Math.min(n - 1 - 1e-9, Math.max(0, (v - axis[0]) / step));
    idx[k] = Math.floor(pos);
    w[k] = pos - idx[k];
  });
  return { idx, w };
}

export function bilinear(field, nx, iy, fy, ix, fx) {
  const a = iy * nx + ix, b = a + nx;
  return (field[a] * (1 - fx) + field[a + 1] * fx) * (1 - fy) + (field[b] * (1 - fx) + field[b + 1] * fx) * fy;
}

/** Longitude of each grid column and latitude of each grid row (Web Mercator pixel centres). */
export function gridAxes(grid) {
  const lon = new Float64Array(grid.nx), lat = new Float64Array(grid.ny);
  for (let c = 0; c < grid.nx; c++) lon[c] = (grid.x0 + (c + 0.5) * grid.res) / R_EARTH * 180 / Math.PI;
  for (let r = 0; r < grid.ny; r++) {
    const y = grid.y1 - (r + 0.5) * grid.res;
    lat[r] = (2 * Math.atan(Math.exp(y / R_EARTH)) - Math.PI / 2) * 180 / Math.PI;
  }
  return { lon, lat };
}

export function pixelOf(grid, lat, lon) {
  const x = R_EARTH * lon * Math.PI / 180;
  const y = R_EARTH * Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360));
  const c = Math.floor((x - grid.x0) / grid.res), r = Math.floor((grid.y1 - y) / grid.res);
  return r >= 0 && r < grid.ny && c >= 0 && c < grid.nx ? [r, c] : null;
}

/** Decision value at a pixel from the coarse fields (exactly what the map shows). */
export function pixelLogit(sp, fields, iy, fy, ix, fx, elev) {
  let logit = bilinear(fields.base, fields.nx, iy, fy, ix, fx);
  for (const f in fields.temps) {
    const t = bilinear(fields.temps[f], fields.nx, iy, fy, ix, fx) + LAPSE_RATE * elev;
    logit += tableInterp(sp.modele.tables[f], t);
  }
  return logit;
}

export function pixelHabitat(sp, layers, p) {
  const group = layers.host[p];
  const elev = layers.elev[p] === 65535 ? NaN : layers.elev[p];
  const ph = layers.ph10[p] === 0 ? NaN : layers.ph10[p] / 10;
  const out = { group, host: hostFactor(sp, group), elev, elevF: elevationFactor(sp, elev), ph, phF: phFactor(sp, ph) };
  out.H = out.host * out.elevF * out.phF;
  return out;
}

/** Full breakdown at one pixel (details panel and tests). Effects are in log-odds. */
export function explain(sp, layers, fields, wts, r, c) {
  const p = r * layers.grid.nx + c;
  const habitat = pixelHabitat(sp, layers, p);
  const z = Number.isFinite(habitat.elev) ? habitat.elev : 0;
  const iy = wts.lat.idx[r], fy = wts.lat.w[r], ix = wts.lon.idx[c], fx = wts.lon.w[c];
  const m = sp.modele, nx = fields.nx;
  const terms = [{ name: "doy", value: fields.doy, effect: tableInterp(m.tables.doy, fields.doy) }];
  for (const f of m.features) {
    if (f === "doy") continue;
    if (f in fields.temps) {
      const value = bilinear(fields.temps[f], nx, iy, fy, ix, fx) + LAPSE_RATE * z;
      terms.push({ name: f, value, effect: tableInterp(m.tables[f], value) });
    } else {
      terms.push({ name: f, value: bilinear(fields.values[f], nx, iy, fy, ix, fx),
                   effect: bilinear(fields.contrib[f], nx, iy, fy, ix, fx) });
    }
  }
  const logit = pixelLogit(sp, fields, iy, fy, ix, fx, z);
  const q = percentile(m.quantiles, logit);
  return { habitat, terms, logit, q, index: habitat.H * q };
}

/** Lookup tables of the habitat factors (elevation by 10 m steps, pH by tenths). */
export function habitatLUTs(sp) {
  const host = Float32Array.from(sp.hotes);
  const elev = new Float32Array(6554);
  for (let k = 0; k < 6553; k++) elev[k] = elevationFactor(sp, k * 10);
  const ph = new Float32Array(256);
  ph[0] = 1;                                   // unknown soil: no penalty
  for (let k = 1; k < 256; k++) ph[k] = phFactor(sp, k / 10);
  return { host, elev, ph };
}

/** Value of every pixel for a layer: "habitat" (H), "meteo" (conditions percentile where H >= minH) or
 *  "indice" (H × conditions). Pixels without forest formation get NaN. */
export function computeGrid(sp, layers, fields, wts, mode, minH = 0.15, step = 1) {
  const { nx, ny } = layers.grid;
  const lut = habitatLUTs(sp);
  const quant = sp.modele.quantiles;
  const tNames = fields ? Object.keys(fields.temps) : [];
  const tFields = tNames.map((f) => fields.temps[f]);
  const tTables = tNames.map((f) => sp.modele.tables[f]);
  const cnx = fields ? fields.nx : 0;
  const out = new Float32Array(Math.ceil(ny / step) * Math.ceil(nx / step)).fill(NaN);
  let k = 0;
  for (let r = 0; r < ny; r += step) {
    const iy = wts.lat.idx[r], fy = wts.lat.w[r];
    for (let c = 0; c < nx; c += step, k++) {
      const p = r * nx + c, g = layers.host[p];
      if (!g) continue;
      const e = layers.elev[p];
      const H = lut.host[g] * lut.elev[e === 65535 ? 6553 : (e / 10) | 0] * lut.ph[layers.ph10[p]];
      if (mode === "habitat") { out[k] = H; continue; }
      const ix = wts.lon.idx[c], fx = wts.lon.w[c];
      const a = iy * cnx + ix, b = a + cnx, w00 = (1 - fx) * (1 - fy), w01 = fx * (1 - fy), w10 = (1 - fx) * fy, w11 = fx * fy;
      const base = fields.base;
      let logit = base[a] * w00 + base[a + 1] * w01 + base[b] * w10 + base[b + 1] * w11;
      const z = e === 65535 ? 0 : e;
      for (let t = 0; t < tFields.length; t++) {
        const T = tFields[t];
        logit += tableInterp(tTables[t], T[a] * w00 + T[a + 1] * w01 + T[b] * w10 + T[b + 1] * w11 + LAPSE_RATE * z);
      }
      const q = percentile(quant, logit);
      out[k] = mode === "meteo" ? (H >= minH ? q : NaN) : H * q;
    }
  }
  return out;
}

/** Mean conditions percentile over favourable habitat (H >= 0.5) for each day, on a subsampled grid. */
export function dailySummary(sp, layers, weather, wts, step = 8) {
  const out = [];
  for (let d = 0; d < weather.dates.length; d++) {
    const fields = coarseFields(sp, weather, d);
    const H = computeGrid(sp, layers, fields, wts, "habitat", 0, step);
    const Q = computeGrid(sp, layers, fields, wts, "meteo", 0.5, step);
    let sum = 0, n = 0;
    for (let k = 0; k < Q.length; k++) if (H[k] >= 0.5 && Q[k] === Q[k]) { sum += Q[k]; n++; }
    out.push(n ? sum / n : NaN);
  }
  return out;
}
