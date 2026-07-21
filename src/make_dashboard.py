import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import gridspec

from config import DATA_DIR, INDICATOR_COLS, OUTPUTS_DIR

plt.rcParams["font.family"] = "DejaVu Sans"

# Palette
BG = "#0f1419"
PANEL = "#1a222c"
ACCENT = ["#4fd1c5", "#68a0ff", "#f6ad55", "#f56565", "#9f7aea", "#48bb78"]
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"

SEGMENT_LABELS = {
    "coeur_actif_0": "Assidus intensifs",
    "coeur_actif_1": "Réguliers modérés",
    "usage_regulier_0": "Sporadiques",
    "usage_regulier_1": "Sporadiques (bis)",
    "inactif_recent_0": "Décrocheurs",
    "inactif_recent_1": "Décrocheurs (bis)",
}

# Les 4 segments de la "story" présentée dans le panneau "Lecture rapide" :
# fixes, plutôt que sélectionnés par taille, pour que radars et texte
# restent toujours cohérents entre eux.
CANONICAL_SEGMENTS = ["coeur_actif_0", "coeur_actif_1", "usage_regulier_0", "inactif_recent_0"]

# Une couleur fixe par segment canonique, partagée entre le graphique de
# tailles et les radars, pour qu'un même segment se reconnaisse d'un panneau
# à l'autre.
CANONICAL_COLORS = {
    "Assidus intensifs": ACCENT[0],
    "Réguliers modérés": ACCENT[1],
    "Sporadiques": ACCENT[2],
    "Décrocheurs": ACCENT[3],
}

RADAR_LABELS = [
    "Volume\nséances", "Durée\nmoyenne", "Récence\n(inversée)",
    "Régularité\n(inversée)", "% semaines\nactives", "Diversité\nactivités",
    "Intensité\nressentie", "Tendance\nrécente",
]


def prep_radar_data(df):
    grouped = df.groupby("segment_final")[INDICATOR_COLS].mean()
    norm = (grouped - grouped.min()) / (grouped.max() - grouped.min() + 1e-9)
    # inverser récence et écart-type (plus petit = meilleur engagement)
    norm["jours_depuis_derniere_session"] = 1 - norm["jours_depuis_derniere_session"]
    norm["ecart_type_intervalle"] = 1 - norm["ecart_type_intervalle"]
    return norm


def main():
    df = pd.read_csv(DATA_DIR / "utilisateurs_segmentes.csv")
    radar = prep_radar_data(df)
    sizes = df["segment_final"].value_counts()

    fig = plt.figure(figsize=(14, 9), facecolor=BG)
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[1.1, 1], hspace=0.45, wspace=0.35,
                           top=0.82, bottom=0.06)

    fig.suptitle("FitTrack — Segmentation comportementale des utilisateurs",
                 fontsize=20, color=TEXT, fontweight="bold", x=0.05, ha="left", y=0.985)
    fig.text(0.05, 0.92,
             "Illustration d'une démarche qui combine des règles simples et un algorithme de "
             "regroupement — le raisonnement détaillé est dans le README / notebook",
             fontsize=11, color=SUBTEXT, ha="left")

    # --- Bar chart : taille des segments ---
    # Les sous-segments "(bis)" n'ont pas de nom distinct pour le lecteur
    # métier (cf. SEGMENT_LABELS) : on les fusionne avec leur parent pour ce
    # graphique, plutôt que d'afficher une catégorie que rien n'explique.
    display_sizes = sizes.rename(index=lambda s: SEGMENT_LABELS.get(s, s))
    display_sizes = display_sizes.groupby(
        lambda name: name.replace(" (bis)", "")
    ).sum()

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_bar.set_facecolor(PANEL)
    segs_sorted = display_sizes.sort_values(ascending=True)
    labels_disp = list(segs_sorted.index)
    bar_colors = [CANONICAL_COLORS[label] for label in labels_disp]
    bars = ax_bar.barh(labels_disp, segs_sorted.values, color=bar_colors)
    ax_bar.set_title("Taille des segments", color=TEXT, fontsize=13, loc="left", pad=10)
    ax_bar.tick_params(colors=TEXT, labelsize=9.5)
    for spine in ax_bar.spines.values():
        spine.set_visible(False)
    ax_bar.grid(axis="x", color="#2d3748", linewidth=0.6)
    for bar, val in zip(bars, segs_sorted.values):
        ax_bar.text(val + 5, bar.get_y() + bar.get_height() / 2, str(val),
                    va="center", color=TEXT, fontsize=9.5)

    # --- Radar charts (petits multiples) ---
    # Segments canoniques fixes (et non les 4 plus gros par taille), pour que
    # ce qui est tracé corresponde toujours au panneau "Lecture rapide".
    top_segments = [s for s in CANONICAL_SEGMENTS if s in sizes.index]
    missing = [s for s in CANONICAL_SEGMENTS if s not in sizes.index]
    if missing:
        print(f"Attention : segments canoniques absents des données : {missing}")
    angles = np.linspace(0, 2 * np.pi, len(RADAR_LABELS), endpoint=False).tolist()
    angles += angles[:1]

    positions = [gs[0, 1], gs[0, 2], gs[1, 0], gs[1, 1]]
    for i, seg in enumerate(top_segments):
        ax = fig.add_subplot(positions[i], polar=True)
        ax.set_facecolor(PANEL)
        values = radar.loc[seg].tolist()
        values += values[:1]
        color = CANONICAL_COLORS[SEGMENT_LABELS.get(seg, seg)]
        ax.plot(angles, values, color=color, linewidth=2)
        ax.fill(angles, values, color=color, alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(RADAR_LABELS, color=SUBTEXT, fontsize=7.5)
        ax.set_yticklabels([])
        ax.set_ylim(0, 1)
        ax.spines["polar"].set_color("#2d3748")
        ax.grid(color="#2d3748", linewidth=0.5)
        ax.set_title(SEGMENT_LABELS.get(seg, seg), color=TEXT, fontsize=12, pad=14, fontweight="bold")

    # --- Panneau texte : lecture des profils ---
    ax_text = fig.add_subplot(gs[1, 2])
    ax_text.set_facecolor(PANEL)
    ax_text.axis("off")
    ax_text.set_title("Repères de lecture", color=TEXT, fontsize=13, loc="left", pad=10)
    lines = [
        ("Assidus intensifs", "Volume élevé, intensité forte, très réguliers",
         "→ contenu avancé, programme de fidélité"),
        ("Réguliers modérés", "Cadence stable, effort modéré, cœur de l'usage",
         "→ défis progressifs pour engager davantage"),
        ("Sporadiques", "Usage irrégulier, activités variées",
         "→ contenu de découverte pour créer l'habitude"),
        ("Décrocheurs", "Aucune séance depuis 45+ jours",
         "→ notification de relance ciblée"),
    ]
    y = 0.92
    for name, desc, action in lines:
        ax_text.text(0.03, y, name, color=TEXT, fontsize=10.5, fontweight="bold", transform=ax_text.transAxes)
        ax_text.text(0.03, y - 0.075, desc, color=SUBTEXT, fontsize=8.5, transform=ax_text.transAxes)
        ax_text.text(0.03, y - 0.14, action, color=ACCENT[0], fontsize=8.5, style="italic", transform=ax_text.transAxes)
        y -= 0.24

    fig.text(0.05, 0.01, "Données 100% synthétiques — projet de démonstration méthodologique",
              fontsize=8.5, color="#5a6472", ha="left")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUTS_DIR / "dashboard_segmentation.png",
                dpi=180, facecolor=BG, bbox_inches="tight")
    print("Dashboard sauvegardé.")


if __name__ == "__main__":
    main()
