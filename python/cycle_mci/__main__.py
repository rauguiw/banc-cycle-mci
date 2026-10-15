"""Interface en ligne de commande.

Exemples
--------
    python -m cycle_mci --liste
    python -m cycle_mci audi-40tfsi
    python -m cycle_mci audi-40tfsi --cycle otto --lambda 0.9
    python -m cycle_mci --cycle diesel --epsilon 18 --carburant diesel --lambda 1.5
"""

from __future__ import annotations

import argparse
import sys

from .catalogue import charger, consignes_calees, trouver
from .thermo import Consignes, Resultat, calculer_cycle


def _tableau(res: Resultat) -> str:
    lignes = ["  État                              P [bar]     T [K]    V [cm³]   s [J/kg·K]"]
    for e in res.etats:
        lignes.append(f"  {e.id} {e.libelle:<31} {e.P / 1e5:8.2f} {e.T:9.1f} {e.V * 1e6:10.1f} {e.s:12.1f}")
    lignes.append("")
    lignes.append("  Transformation              Q [J]       W [J]      ΔU [J]")
    for t in res.transformations:
        lignes.append(f"  {t.id} {t.nom:<12} {t.nature:<12} {t.Q:9.1f} {t.W:11.1f} {t.dU:11.1f}")
    return "\n".join(lignes)


def _synthese(titre: str, c: Consignes, res: Resultat) -> str:
    sortie = [
        titre,
        f"  Cycle {c.cycle}, ε = {c.epsilon:g}, P1 = {c.p1_bar:g} bar, T1 = {c.t1_c:g} °C, "
        f"N = {c.regime_tr_min:g} tr/min, λ = {c.lambda_:g}",
        f"  γ = {res.gamma:.4f} ({res.iterations_gamma} itérations), cv = {res.cv:.1f}, cp = {res.cp:.1f} J/kg·K",
        "",
        _tableau(res),
        "",
        f"  Rendement thermique      {res.eta_th * 100:7.2f} %   (Otto équivalent {res.eta_otto * 100:.2f} %)",
        f"  PMI                      {res.pmi_bar:7.2f} bar",
        f"  Puissance indiquée       {res.puissance_kW:7.1f} kW  ({res.puissance_ch:.0f} ch)",
        f"  Couple indiqué           {res.couple_Nm:7.1f} N·m",
        f"  Conso. spécifique ind.   {res.csi_g_kWh:7.1f} g/kWh",
        f"  Pmax / Tmax              {res.p_max_bar:7.1f} bar / {res.t_max_K:.0f} K",
    ]
    for a in res.avertissements:
        sortie.append(f"  [{a.niveau}] {a.texte}")
    return "\n".join(sortie)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m cycle_mci", description="Calcul de cycle théorique d'un moteur 4 temps.")
    p.add_argument("moteur", nargs="?", help="identifiant d'un moteur du catalogue (voir --liste)")
    p.add_argument("--liste", action="store_true", help="liste les moteurs du catalogue")
    p.add_argument("--cycle", choices=["otto", "diesel", "sabathe"])
    p.add_argument("--carburant", choices=["essence", "diesel"])
    p.add_argument("--epsilon", type=float)
    p.add_argument("--p1", type=float, help="pression fin d'admission (bar abs)")
    p.add_argument("--t1", type=float, help="température fin d'admission (°C)")
    p.add_argument("--regime", type=float, help="tr/min")
    p.add_argument("--lambda", dest="lambda_", type=float)
    p.add_argument("--x", type=float, help="part isochore du cycle de Sabathé (%%)")
    p.add_argument("--gamma", type=float, help="impose γ (mode manuel)")
    a = p.parse_args(argv)

    if a.liste:
        for m in charger():
            print(f"{m.id:<22} {m.libelle:<40} {m.puissance_ch:>5.0f} ch  ε {m.epsilon:>4}  {m.carburant}")
        return 0

    if a.moteur:
        m = trouver(a.moteur)
        c = consignes_calees(m)
        titre = f"{m.libelle} ({m.code}) — point de calage, constructeur {m.puissance_ch:.0f} ch eff."
    else:
        c = Consignes()
        titre = "Configuration personnalisée"
    modifs = {k: v for k, v in {
        "cycle": a.cycle, "carburant": a.carburant, "epsilon": a.epsilon, "p1_bar": a.p1, "t1_c": a.t1,
        "regime_tr_min": a.regime, "lambda_": a.lambda_, "part_isochore_pct": a.x,
    }.items() if v is not None}
    if a.gamma is not None:
        modifs.update(mode_gamma="manuel", gamma=a.gamma)
    if modifs:
        c = c.avec(**modifs)
        if a.moteur:
            titre += " — consignes modifiées"
    print(_synthese(titre, c, calculer_cycle(c)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
