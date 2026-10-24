"""Figures for the feasibility study (light and dark variants).

Usage: python feasibility_figures.py EOBS_NPZ RESULTS_DIR FIG_DIR
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from feasibility import Weather, features, model

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  axis="#c3c2b7", s1="#2a78d6", s2="#eb6834", s3="#1baf7a"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 axis="#383835", s1="#3987e5", s2="#d95926", s3="#199e70"),
}
NAMES = {"Boletus_edulis": "Cèpe de Bordeaux", "Macrolepiota_procera": "Coulemelle",
         "Craterellus_cornucopioides": "Trompette de la mort", "Morchella": "Morilles",
         "Cantharellus_cibarius": "Girolle", "Hydnum_repandum": "Pied de mouton",
         "Fagus_sylvatica": "Témoin : hêtre (effort)"}


def style(ax, th, xgrid=False, ygrid=True):
    ax.set_facecolor(th["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(th["axis"])
    ax.spines["bottom"].set_linewidth(1)
    ax.tick_params(colors=th["muted"], labelcolor=th["ink2"], length=0, labelsize=9)
    ax.grid(False)
    if ygrid:
        ax.yaxis.grid(True, color=th["grid"], linewidth=0.8)
    if xgrid:
        ax.xaxis.grid(True, color=th["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def titles(fig, th, title, subtitle):
    fig.text(0.02, 0.97, title, ha="left", va="top", fontsize=12.5, fontweight="semibold", color=th["ink"])
    fig.text(0.02, 0.915, subtitle, ha="left", va="top", fontsize=9, color=th["ink2"])


def fig_auc(summary, th, path):
    d = summary[summary.design == "matched"].copy()
    d["nom"] = d.species.map(NAMES)
    ctrl = d[d.species == "Fagus_sylvatica"]
    sp = d[d.species != "Fagus_sylvatica"].sort_values("auc_year_saison+meteo", ascending=False)
    d = pd.concat([sp, ctrl]).reset_index(drop=True)    # best at the top, control at the bottom
    fig, ax = plt.subplots(figsize=(8.2, 4.6), dpi=150, facecolor=th["surface"])
    fig.subplots_adjust(left=0.27, right=0.93, top=0.74, bottom=0.14)
    style(ax, th, xgrid=True, ygrid=False)
    ys = np.arange(len(d))[::-1].astype(float)
    series = [("auc_year_saison", "Saisonnalité seule", th["s1"]),
              ("auc_year_meteo", "Météo seule", th["s2"]),
              ("auc_year_saison+meteo", "Saisonnalité + météo", th["s3"])]
    for y, (_, r) in zip(ys, d.iterrows()):
        vals = [r[c] for c, _, _ in series]
        ax.plot([min(vals), max(vals)], [y, y], color=th["axis"], linewidth=1.2, zorder=1)
    for c, label, col in series:
        ax.scatter(d[c], ys, s=64, color=col, edgecolors=th["surface"], linewidths=2, zorder=3, label=label)
    for y, (_, r) in zip(ys, d.iterrows()):
        top = max(r[c] for c, _, _ in series)
        ax.text(top + 0.008, y, f"{r['auc_year_saison+meteo']:.2f}".replace(".", ","), va="center",
                ha="left", fontsize=9, color=th["ink2"])
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n}  (n={p})" for n, p in zip(d.nom, d.n_pos)], fontsize=9.5, color=th["ink"])
    ax.set_xlim(0.5, 0.9)
    ax.set_xticks(np.arange(0.5, 0.91, 0.1))
    ax.set_xticklabels([f"{v:.1f}".replace(".", ",") for v in np.arange(0.5, 0.91, 0.1)])
    ax.set_xlabel("AUC en validation « une année exclue » (0,5 = hasard, 1 = parfait)", color=th["ink2"], fontsize=9)
    ax.axhline(ys[-1] + 0.5, color=th["grid"], linewidth=0.8)
    leg = ax.legend(loc="lower left", bbox_to_anchor=(-0.36, 1.0), ncol=3, frameon=False, fontsize=9,
                    handletextpad=0.3, columnspacing=1.4)
    for t in leg.get_texts():
        t.set_color(th["ink2"])
    titles(fig, th, "Prédire la date d'observation à partir de la météo passée",
           "France, observations GBIF 2011-2024 · météo E-OBS 0,1° · 10 dates témoins par observation (même lieu)")
    fig.savefig(path, facecolor=th["surface"])
    plt.close(fig)


def ratio_curve(X, y, col, edges, min_pos=12, min_bg=60):
    pos, bg = X.loc[y == 1, col], X.loc[y == 0, col]
    cp, _ = np.histogram(pos, edges)
    cb, _ = np.histogram(bg, edges)
    ratio = (cp / cp.sum()) / np.where(cb > 0, cb / cb.sum(), np.nan)
    ok = (cp >= min_pos) & (cb >= min_bg)
    mids = 0.5 * (edges[1:] + edges[:-1])
    return mids[ok], ratio[ok]


def fig_curves(results, th, path):
    sp = [("Boletus_edulis", th["s1"]), ("Macrolepiota_procera", th["s2"]), ("Morchella", th["s3"])]
    panels = [("P30", "Pluie cumulée sur 30 jours (mm)", np.array([0, 20, 40, 60, 80, 100, 125, 150, 200, 300])),
              ("T14", "Température moyenne sur 14 jours (°C)", np.arange(0, 27, 2.0))]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.2), dpi=150, facecolor=th["surface"], sharey=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.72, bottom=0.15, wspace=0.08)
    for ax, (col, label, edges) in zip(axes, panels):
        style(ax, th)
        ax.axhline(1.0, color=th["axis"], linewidth=1.2, zorder=1)
        for s, c in sp:
            df = pd.read_csv(Path(results) / f"{s}_matched_dataset.csv.gz")
            x, r = ratio_curve(df, df.y.to_numpy(), col, edges)
            ax.plot(x, r, color=c, linewidth=2, solid_capstyle="round", zorder=2, label=NAMES[s])
            ax.scatter(x, r, s=36, color=c, edgecolors=th["surface"], linewidths=2, zorder=3)
        ax.set_xlabel(label, color=th["ink2"], fontsize=9)
        ax.set_ylim(0, 3.2)
    axes[0].set_ylabel("Observé / disponible", color=th["ink2"], fontsize=9)
    axes[0].text(axes[0].get_xlim()[1] * 0.98, 0.95, "neutre = 1", ha="right", va="top", fontsize=8,
                 color=th["muted"])
    leg = axes[0].legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=3, frameon=False, fontsize=9,
                         handletextpad=0.4, columnspacing=1.4)
    for t in leg.get_texts():
        t.set_color(th["ink2"])
    titles(fig, th, "Dans quelles conditions les observations se concentrent",
           "Rapport entre la fréquence d'une condition les jours d'observation et sa fréquence les jours témoins")
    fig.savefig(path, facecolor=th["surface"])
    plt.close(fig)


def season_example(w, results):
    """Daily index for the cèpe cell-year with the most observation days, model trained on other years."""
    df = pd.read_csv(Path(results) / "Boletus_edulis_matched_dataset.csv.gz")
    pos = df[df.y == 1]
    best = pos.groupby(["i", "j", "year"]).size().sort_values(ascending=False)
    i, j, year = best.index[0]
    cols = [c for c in df.columns if c not in ("y", "year", "i", "j", "t")]
    train = df[df.year != year]
    m = model().fit(train[cols].to_numpy(), train.y.to_numpy())
    # Reference: out-of-sample scores of the held-out year's control dates (all observation cells).
    bg_scores = m.predict_proba(df[(df.year == year) & (df.y == 0)][cols].to_numpy())[:, 1]
    days = pd.date_range(f"{year}-07-15", f"{year}-11-30", freq="D")
    t = w.day_index(days.to_numpy())
    cells = np.array([[i, j]])
    X = features(w, np.zeros(len(t), dtype=int), cells, t)
    d = days.day_of_year.to_numpy()
    X["doy_sin"], X["doy_cos"] = np.sin(2 * np.pi * d / 365.25), np.cos(2 * np.pi * d / 365.25)
    X["lat"], X["lon"] = w.lat[i], w.lon[j]
    p = m.predict_proba(X[cols].to_numpy())[:, 1]
    pct = np.searchsorted(np.sort(bg_scores), p) / len(bg_scores) * 100
    obs_t = pos[(pos.i == i) & (pos.j == j) & (pos.year == year)].t.to_numpy()
    obs_days = pd.to_datetime(w.time[obs_t])
    rain = np.nan_to_num(w.rr[t, i, j])
    return dict(days=days, pct=pct, obs=obs_days, rain=rain, lat=float(w.lat[i]), lon=float(w.lon[j]),
                year=int(year), n=len(obs_t))


def fig_season(ex, th, path):
    fig, (ax, axr) = plt.subplots(2, 1, figsize=(8.6, 5.0), dpi=150, facecolor=th["surface"], sharex=True,
                                  gridspec_kw=dict(height_ratios=[2.2, 1]))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.80, bottom=0.08, hspace=0.12)
    style(ax, th)
    style(axr, th)
    ax.fill_between(ex["days"], ex["pct"], color=th["s1"], alpha=0.10, linewidth=0)
    ax.plot(ex["days"], ex["pct"], color=th["s1"], linewidth=2, solid_capstyle="round", label="Indice modélisé")
    idx = np.searchsorted(ex["days"].values, ex["obs"].values)
    ax.scatter(ex["obs"], ex["pct"][np.clip(idx, 0, len(ex["pct"]) - 1)], s=64, color=th["s2"],
               edgecolors=th["surface"], linewidths=2, zorder=3, label="Jours avec observation GBIF")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Indice (percentile)", color=th["ink2"], fontsize=9)
    leg = ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, frameon=False, fontsize=9)
    for tx in leg.get_texts():
        tx.set_color(th["ink2"])
    axr.bar(ex["days"], ex["rain"], width=0.8, color=th["muted"], linewidth=0)
    axr.set_ylabel("Pluie (mm/j)", color=th["ink2"], fontsize=9)
    axr.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m"))
    lat, lon = ex["lat"], ex["lon"]
    titles(fig, th, f"Cèpe de Bordeaux, saison {ex['year']} : indice journalier et observations",
           f"Maille E-OBS {lat:.2f}°N {lon:.2f}°E · modèle saisonnalité + météo entraîné sans l'année {ex['year']}"
           .replace(".", ","))
    fig.savefig(path, facecolor=th["surface"])
    plt.close(fig)


def main(eobs, results, figdir):
    out = Path(figdir)
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(Path(results) / "summary.csv")
    w = Weather(eobs)
    ex = season_example(w, results)
    print("example:", ex["year"], ex["lat"], ex["lon"], ex["n"], "obs days")
    for mode, th in THEMES.items():
        fig_auc(summary, th, out / f"auc_{mode}.png")
        fig_curves(results, th, out / f"conditions_{mode}.png")
        fig_season(ex, th, out / f"saison_cepe_{mode}.png")


if __name__ == "__main__":
    main(*sys.argv[1:4])
