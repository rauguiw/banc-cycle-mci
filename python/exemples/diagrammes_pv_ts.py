"""Diagrammes P-V et T-s des trois cycles, à taux de compression et chaleur apportée égaux.

    python exemples/diagrammes_pv_ts.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _style import COULEUR_CYCLE, ENCRE_2, NOM_CYCLE, enregistrer, plt  # noqa: E402

from cycle_mci import Consignes, calculer_cycle  # noqa: E402

BASE = Consignes(epsilon=16.0, lambda_=1.5, p1_bar=1.0, t1_c=35.0, part_isochore_pct=50.0)


def main() -> None:
    fig, (ax_pv, ax_ts) = plt.subplots(1, 2, figsize=(11, 4.8))
    for cycle in ("otto", "sabathe", "diesel"):
        r = calculer_cycle(BASE.avec(cycle=cycle))
        couleur = COULEUR_CYCLE[cycle]
        etiquette = f"{NOM_CYCLE[cycle]} · η = {100 * r.eta_th:.1f} %".replace(".", ",")
        ax_pv.plot([p.V_cm3 for p in r.trajet], [p.P_bar for p in r.trajet], color=couleur, label=etiquette)
        ax_ts.plot([p.s for p in r.trajet], [p.T for p in r.trajet], color=couleur, label=etiquette)
        for e in r.etats:
            ax_ts.plot(e.s, e.T, "o", ms=5, color=couleur, mec="#fcfcfb", mew=1.5, zorder=4)

    ax_pv.set_xscale("log")
    ax_pv.set_yscale("log")
    ax_pv.set_xticks([30, 50, 100, 200, 400], ["30", "50", "100", "200", "400"])
    ax_pv.set_xticks([], minor=True)
    ax_pv.set_yticks([1, 2, 5, 10, 20, 50, 100], ["1", "2", "5", "10", "20", "50", "100"])
    ax_pv.set_yticks([], minor=True)
    ax_pv.set_title("Diagramme P-V (log-log)")
    ax_pv.set_xlabel("Volume du cylindre (cm³)")
    ax_pv.set_ylabel("Pression (bar)")
    ax_ts.set_title("Diagramme T-s")
    ax_ts.set_xlabel("Entropie massique s (J/kg·K, réf. 25 °C, 1 atm)")
    ax_ts.set_ylabel("Température (K)")
    ax_ts.legend(loc="upper left", fontsize=9)
    fig.suptitle("ε = 16, même chaleur apportée (essence, λ = 1,5, P₁ = 1 bar, T₁ = 35 °C), γ itéré sur cp(T)",
                 x=0.01, ha="left", y=1.0, fontsize=9, color=ENCRE_2)
    fig.tight_layout()
    print(enregistrer(fig, "python-diagrammes-pv-ts.png"))


if __name__ == "__main__":
    main()
