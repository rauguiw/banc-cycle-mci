"""Étude paramétrique : rendement thermique en fonction du taux de compression.

Compare les cycles d'Otto, de Sabathé et Diesel à chaleur apportée identique,
avec γ itéré sur cp(T), et la formule de manuel 1 − ε^(1−γ) à γ = 1,4 constant.

    python exemples/etude_parametrique.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _style import BLEU, COULEUR_CYCLE, ENCRE_2, NOM_CYCLE, enregistrer, plt  # noqa: E402

from cycle_mci import Consignes, calculer_cycle  # noqa: E402

BASE = Consignes(lambda_=1.5, p1_bar=1.0, t1_c=35.0, part_isochore_pct=50.0)
EPSILONS = np.linspace(6, 24, 73)


def main() -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.0))

    ax.plot(EPSILONS, 100 * (1 - EPSILONS ** (1 - 1.4)), color=ENCRE_2, lw=1.2, ls=(0, (4, 3)))
    ax.annotate("Otto, γ = 1,4 constant (formule de manuel)", (15, 100 * (1 - 15 ** -0.4)),
                xytext=(0, -8), textcoords="offset points", ha="left", va="top", color=ENCRE_2, fontsize=9)

    for cycle in ("otto", "sabathe", "diesel"):
        res = [calculer_cycle(BASE.avec(cycle=cycle, epsilon=float(e))) for e in EPSILONS]
        eta = [100 * r.eta_th for r in res]
        ax.plot(EPSILONS, eta, color=COULEUR_CYCLE[cycle], label=NOM_CYCLE[cycle])
        decalage = {"otto": 7, "sabathe": -7, "diesel": 0}[cycle]
        ax.annotate(NOM_CYCLE[cycle], (EPSILONS[-1], eta[-1]), xytext=(6, decalage), textcoords="offset points",
                    va="center", color="#1f2328", fontsize=9.5)

    r10 = calculer_cycle(BASE.avec(cycle="otto", epsilon=10.0))
    ax.plot([10], [100 * r10.eta_th], "o", ms=8, color=BLEU, mec="#fcfcfb", mew=2, zorder=5)
    ax.annotate(f"ε = 10 : η = {100 * r10.eta_th:.1f} % (γ itéré = {r10.gamma:.3f})".replace(".", ","),
                (10, 100 * r10.eta_th), xytext=(10, -26), textcoords="offset points", fontsize=9, color="#1f2328")

    ax.set_title("Rendement thermique selon le taux de compression")
    ax.text(0, 1.015, "Même chaleur apportée (essence, λ = 1,5, P₁ = 1 bar, T₁ = 35 °C), γ itéré sur cp(T)",
            transform=ax.transAxes, fontsize=9, color=ENCRE_2, va="bottom")
    ax.set_xlabel("Taux de compression ε")
    ax.set_ylabel("Rendement thermique η (%)")
    ax.set_xlim(6, 24)
    ax.legend(loc="lower right", fontsize=9)
    fig.subplots_adjust(right=0.82)
    print(enregistrer(fig, "python-etude-parametrique.png"))


if __name__ == "__main__":
    main()
