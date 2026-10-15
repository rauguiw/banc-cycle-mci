"""Style commun des figures (matplotlib)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DOSSIER_FIGURES = Path(__file__).resolve().parents[2] / "docs" / "img"

# Ordre catégoriel fixe, une teinte par série (jamais recyclée)
BLEU, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
ENCRE, ENCRE_2, GRILLE, FOND = "#1f2328", "#5b6470", "#e3e6ea", "#fcfcfb"
COULEUR_CYCLE = {"otto": BLEU, "sabathe": ORANGE, "diesel": AQUA}
NOM_CYCLE = {"otto": "Otto", "sabathe": "Sabathé (x = 50 %)", "diesel": "Diesel"}

plt.rcParams.update({
    "figure.facecolor": FOND, "axes.facecolor": FOND, "savefig.facecolor": FOND,
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": ENCRE_2, "axes.labelcolor": ENCRE, "axes.titlecolor": ENCRE,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 24,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRILLE, "grid.linewidth": 0.8,
    "xtick.color": ENCRE_2, "ytick.color": ENCRE_2,
    "lines.linewidth": 2, "legend.frameon": False,
})


def enregistrer(fig, nom: str) -> Path:
    DOSSIER_FIGURES.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_FIGURES / nom
    fig.savefig(chemin, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return chemin
