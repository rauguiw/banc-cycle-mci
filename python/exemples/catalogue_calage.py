"""Calage des 124 moteurs du catalogue : pression d'admission équivalente P₁.

Pour chaque moteur, P₁ est calée de sorte que P_i(cycle théorique) × 0,62
(essence) ou 0,66 (diesel) retrouve la puissance constructeur. Aucune
information sur la suralimentation n'entre dans ce calage : la séparation
nette entre moteurs atmosphériques et suralimentés est un contrôle de
vraisemblance du modèle.

    python exemples/catalogue_calage.py
"""

import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _style import BLEU, ENCRE, ENCRE_2, ORANGE, enregistrer, plt  # noqa: E402

from cycle_mci import caler_p1, charger  # noqa: E402


def main() -> None:
    moteurs = charger()
    groupes = {
        "Atmosphériques": [caler_p1(m) for m in moteurs if not m.suralimente],
        "Suralimentés": [caler_p1(m) for m in moteurs if m.suralimente],
    }
    couleurs = {"Atmosphériques": BLEU, "Suralimentés": ORANGE}
    rng = np.random.default_rng(7)

    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    for i, (nom, valeurs) in enumerate(groupes.items()):
        y = i + rng.uniform(-0.18, 0.18, len(valeurs))
        ax.scatter(valeurs, y, s=34, color=couleurs[nom], edgecolors="#fcfcfb", linewidths=1.2, zorder=3)
        med = statistics.median(valeurs)
        ax.plot([med, med], [i - 0.3, i + 0.3], color=ENCRE, lw=2, zorder=4)
        ax.annotate(f"médiane {med:.2f} bar · {len(valeurs)} moteurs".replace(".", ","), (med, i + 0.3),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=ENCRE)

    ax.set_yticks([0, 1], list(groupes))
    ax.set_ylim(-0.6, 1.75)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Pression d'admission équivalente P₁ calée (bar abs)")
    ax.set_title("Calage des 124 moteurs sur la puissance constructeur")
    ax.text(0, 1.015, "Le calage ignore le type d'admission : la séparation des deux groupes ressort du modèle seul",
            transform=ax.transAxes, fontsize=9, color=ENCRE_2, va="bottom")
    print(enregistrer(fig, "python-calage-catalogue.png"))


if __name__ == "__main__":
    main()
