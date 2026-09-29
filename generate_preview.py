"""
generate_preview.py - Génère l'image haute résolution jobs_france.png pour le README
------------------------------------------------------------------------------------
Crée une capture visuelle fidèle à la version originale d'Andrej Karpathy (jobs.png)
avec la barre latérale analytique à gauche et le treemap squarifié à droite.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

# Palette de couleurs Karpathy (Vert -> Ambre -> Rouge)
COLORS = [
    (0.0, "#22c55e"),   # 0: Vert résilient
    (0.3, "#84cc16"),   # 3: Vert clair
    (0.5, "#eab308"),   # 5: Jaune / ambré
    (0.7, "#f97316"),   # 7: Orange soutenu
    (1.0, "#ef4444"),   # 10: Rouge très exposé
]
CMAP = LinearSegmentedColormap.from_list("karpathy_exposure", [c[1] for c in COLORS])


def squarify(items, x, y, w, h):
    if not items or len(items) == 0:
        return []
    if len(items) == 1:
        return [{**items[0], "rx": x, "ry": y, "rw": w, "rh": h}]

    total = sum(d["value"] for d in items)
    if total <= 0:
        return []

    results = []
    remaining = list(items)
    cx, cy, cw, ch = x, y, w, h

    while remaining:
        rem_total = sum(d["value"] for d in remaining)
        vertical = cw >= ch
        side = ch if vertical else cw

        row = [remaining[0]]
        row_sum = remaining[0]["value"]

        for i in range(1, len(remaining)):
            candidate = row + [remaining[i]]
            cand_sum = row_sum + remaining[i]["value"]
            if worst_aspect(candidate, cand_sum, side, rem_total, cw if vertical else ch) < \
               worst_aspect(row, row_sum, side, rem_total, cw if vertical else ch):
                row = candidate
                row_sum = cand_sum
            else:
                break

        row_fraction = row_sum / rem_total if rem_total > 0 else 0
        row_thick = cw * row_fraction if vertical else ch * row_fraction

        offset = 0
        for it in row:
            it_fraction = it["value"] / row_sum if row_sum > 0 else 0
            it_len = side * it_fraction
            if vertical:
                results.append({**it, "rx": cx, "ry": cy + offset, "rw": row_thick, "rh": it_len})
            else:
                results.append({**it, "rx": cx + offset, "ry": cy, "rw": it_len, "rh": row_thick})
            offset += it_len

        if vertical:
            cx += row_thick
            cw -= row_thick
        else:
            cy += row_thick
            ch -= row_thick

        remaining = remaining[len(row):]

    return results


def worst_aspect(row, row_sum, side, total_area, available_extent):
    row_extent = available_extent * (row_sum / total_area) if total_area > 0 else 0
    if row_extent == 0:
        return float("inf")
    worst = 0
    for it in row:
        it_len = side * (it["value"] / row_sum) if row_sum > 0 else 0
        if it_len == 0:
            continue
        aspect = max(row_extent / it_len, it_len / row_extent)
        if aspect > worst:
            worst = aspect
    return worst


def main():
    print("Génération de l'aperçu `jobs_france.png`...")
    with open("site/data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Dimensions globales (2048 x 1065 comme Karpathy)
    fig = plt.figure(figsize=(20.48, 10.65), dpi=100, facecolor="#090a0f")

    # Découpage : 22% sidebar, 78% treemap
    ax_sidebar = fig.add_axes([0.01, 0.02, 0.20, 0.96], facecolor="#12131c")
    ax_treemap = fig.add_axes([0.22, 0.02, 0.77, 0.96], facecolor="#090a0f")

    for ax in [ax_sidebar, ax_treemap]:
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#2a2d3d")
            spine.set_linewidth(1.0)

    # ── Sidebar ──────────────────────────────────────────────────────────
    total_jobs = sum(d["jobs"] for d in data)
    weighted_score = sum(d["exposure"] * d["jobs"] for d in data) / total_jobs
    wages_exposed = sum(d["jobs"] * d["pay"] for d in data if d["exposure"] >= 7)

    y_pos = 0.95
    ax_sidebar.text(0.06, y_pos, "Exposition à l'IA\nMarché Français", fontsize=16, fontweight="bold", color="#ffffff", va="top")
    y_pos -= 0.08
    ax_sidebar.text(0.06, y_pos, "1 124 métiers · France Travail (ROME 4.0)\nRéplique de l'étude d'Andrej Karpathy", fontsize=9.5, color="#94a3b8", va="top")

    y_pos -= 0.08
    # Stat 1: Total Jobs
    ax_sidebar.text(0.06, y_pos, "TOTAL ACTIFS REPRÉSENTÉS", fontsize=8.5, fontweight="bold", color="#64748b", va="top")
    y_pos -= 0.03
    ax_sidebar.text(0.06, y_pos, f"{total_jobs / 1e6:.1f} M".replace(".", ","), fontsize=24, fontweight="heavy", color="#38bdf8", va="top")

    y_pos -= 0.07
    # Stat 2: Weighted Score
    ax_sidebar.text(0.06, y_pos, "EXPOSITION MOYENNE PONDÉRÉE", fontsize=8.5, fontweight="bold", color="#64748b", va="top")
    y_pos -= 0.03
    ax_sidebar.text(0.06, y_pos, f"{weighted_score:.1f} / 10".replace(".", ","), fontsize=24, fontweight="heavy", color="#f59e0b", va="top")

    y_pos -= 0.07
    # Stat 3: Wages Exposed
    ax_sidebar.text(0.06, y_pos, "MASSE SALARIALE EXPOSÉE (≥ 7)", fontsize=8.5, fontweight="bold", color="#64748b", va="top")
    y_pos -= 0.03
    ax_sidebar.text(0.06, y_pos, f"{wages_exposed / 1e9:.1f} Mds € / an".replace(".", ","), fontsize=20, fontweight="heavy", color="#ef4444", va="top")

    y_pos -= 0.08
    # Histogramme 0 à 10
    ax_sidebar.text(0.06, y_pos, "DISTRIBUTION DES EMPLOIS (0 À 10)", fontsize=8.5, fontweight="bold", color="#64748b", va="top")
    y_pos -= 0.03

    hist_data = [0] * 11
    for d in data:
        hist_data[d["exposure"]] += d["jobs"]
    max_h = max(hist_data)

    bar_w = 0.07
    for i in range(11):
        bx = 0.06 + i * bar_w
        bh = (hist_data[i] / max_h) * 0.08
        col = CMAP(i / 10.0)
        rect = patches.Rectangle((bx, y_pos - 0.08), bar_w * 0.8, bh, facecolor=col, edgecolor="none", zorder=3)
        ax_sidebar.add_patch(rect)

    y_pos -= 0.11
    ax_sidebar.text(0.06, y_pos, "0 (Résilient)", fontsize=7.5, color="#64748b")
    ax_sidebar.text(0.80, y_pos, "10 (Exposé)", fontsize=7.5, color="#64748b")

    y_pos -= 0.05
    # Paliers de risque
    tiers = [
        ("Minimale (0–1)", [0, 1], "#22c55e"),
        ("Faible (2–3)", [2, 3], "#84cc16"),
        ("Modérée (4–5)", [4, 5], "#eab308"),
        ("Élevée (6–7)", [6, 7], "#f97316"),
        ("Très élevée (8–10)", [8, 10], "#ef4444"),
    ]
    ax_sidebar.text(0.06, y_pos, "RÉPARTITION PAR PALIER DE RISQUE", fontsize=8.5, fontweight="bold", color="#64748b", va="top")
    y_pos -= 0.03

    for name, rng, col in tiers:
        t_jobs = sum(d["jobs"] for d in data if rng[0] <= d["exposure"] <= rng[1])
        pct = (t_jobs / total_jobs) * 100
        # Color dot
        ax_sidebar.add_patch(patches.Rectangle((0.06, y_pos - 0.015), 0.025, 0.015, facecolor=col, edgecolor="none"))
        ax_sidebar.text(0.11, y_pos - 0.005, f"{name}", fontsize=8.5, color="#cbd5e1", va="center")
        ax_sidebar.text(0.92, y_pos - 0.005, f"{pct:.0f}%", fontsize=8.5, fontweight="bold", color="#ffffff", va="center", ha="right")
        y_pos -= 0.035

    y_pos -= 0.03
    # Légende graduée
    ax_sidebar.text(0.06, y_pos, "LÉGENDE D'EXPOSITION", fontsize=8.5, fontweight="bold", color="#64748b", va="top")
    y_pos -= 0.03
    # Gradient bar
    grad = np.linspace(0, 1, 256).reshape(1, -1)
    ax_sidebar.imshow(grad, extent=[0.06, 0.92, y_pos - 0.015, y_pos], cmap=CMAP, aspect="auto", zorder=3)
    y_pos -= 0.025
    ax_sidebar.text(0.06, y_pos, "Manuel / Présentiel", fontsize=7.5, color="#64748b")
    ax_sidebar.text(0.92, y_pos, "100% Numérique / LLM", fontsize=7.5, color="#64748b", ha="right")

    ax_sidebar.set_xlim(0, 1)
    ax_sidebar.set_ylim(0, 1)

    # ── Treemap Layout ───────────────────────────────────────────────────
    by_category = {}
    for d in data:
        cat = d["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(d)

    categories = []
    for cat, items in by_category.items():
        categories.append({
            "cat": cat,
            "name": items[0].get("category_name", cat),
            "items": sorted(items, key=lambda x: x["jobs"], reverse=True),
            "value": sum(it["jobs"] for it in items),
        })
    categories.sort(key=lambda x: x["value"], reverse=True)

    cat_rects = squarify(categories, 0.0, 0.0, 1000.0, 1000.0)

    rects = []
    gap = 2.0
    for cr in cat_rects:
        inner_items = [{"value": it["jobs"], **it} for it in cr["items"]]
        inner_rects = squarify(
            inner_items,
            cr["rx"] + gap,
            cr["ry"] + gap,
            max(1.0, cr["rw"] - gap * 2),
            max(1.0, cr["rh"] - gap * 2)
        )
        rects.extend(inner_rects)

    # Draw rectangles on ax_treemap
    for r in rects:
        rx, ry, rw, rh = r["rx"], r["ry"], r["rw"], r["rh"]
        score = r["exposure"]
        col = CMAP(score / 10.0)

        # Draw box
        rect_patch = patches.Rectangle(
            (rx + 0.5, ry + 0.5),
            max(0.1, rw - 1.0),
            max(0.1, rh - 1.0),
            facecolor=col,
            alpha=0.68,
            edgecolor=(0, 0, 0, 0.6),
            linewidth=0.5
        )
        ax_treemap.add_patch(rect_patch)

        # Draw label if box is large enough
        if rw > 45 and rh > 22:
            title_text = r["title"]
            if len(title_text) > int(rw / 4.8):
                title_text = title_text[:max(4, int(rw / 4.8) - 2)] + "..."
            
            font_size = min(9.5, max(6.5, min(rw / 10.0, rh / 3.2)))
            ax_treemap.text(
                rx + 3.0,
                ry + rh - 3.0,
                title_text,
                fontsize=font_size,
                fontweight="bold",
                color="#ffffff",
                va="top",
                ha="left",
                clip_on=True
            )

            if rh > 38 and rw > 60:
                jobs_k = f"{r['jobs'] // 1000}k" if r['jobs'] >= 1000 else str(r['jobs'])
                info_text = f"{r['exposure']}/10 · {jobs_k}"
                ax_treemap.text(
                    rx + 3.0,
                    ry + rh - font_size - 6.0,
                    info_text,
                    fontsize=max(5.5, font_size - 2.0),
                    color="#cbd5e1",
                    va="top",
                    ha="left",
                    clip_on=True
                )

    ax_treemap.set_xlim(0, 1000)
    ax_treemap.set_ylim(0, 1000)

    save_path = "jobs_france.png"
    plt.savefig(save_path, dpi=100, facecolor="#090a0f", bbox_inches="tight")
    plt.close()
    print(f"✓ Image haute résolution sauvegardée : {save_path}")


if __name__ == "__main__":
    main()
