"""Catalogue de 124 moteurs réels et calage sur la puissance constructeur.

Les fiches (alésage, course, taux de compression, puissance, couple…) sont
celles de l'application web, exportées dans ``donnees/catalogue.json`` par
``outils/generer_reference.mjs``.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from .thermo import CH_W, Consignes, Resultat, calculer_cycle

# Rapport P_effective / P_indiquée(cycle théorique) supposé pour le calage de P1
QUALITE = {"essence": 0.62, "diesel": 0.66}

_FICHIER = Path(__file__).with_name("donnees") / "catalogue.json"


@dataclass(frozen=True)
class Moteur:
    id: str
    marque: str
    code: str
    nom: str
    vehicules: str
    annees: str
    carburant: str
    architecture: str        # I, V, VR, W, B (boxer)
    angle: float
    n_cyl: int
    alesage_mm: float
    course_mm: float
    bielle_mm: Optional[float]
    epsilon: float
    induction: str
    puissance_ch: float
    regime_tr_min: float
    couple_Nm: float
    cylindree_cm3: float

    @property
    def suralimente(self) -> bool:
        return not re.search("atmosph", self.induction, re.IGNORECASE)

    @property
    def libelle(self) -> str:
        return f"{self.marque} {self.nom}"


@lru_cache(maxsize=1)
def charger() -> List[Moteur]:
    """Charge les 124 moteurs du catalogue."""
    with open(_FICHIER, encoding="utf-8") as f:
        brut = json.load(f)
    return [
        Moteur(id=d["id"], marque=d["brand"], code=d["code"], nom=d["name"], vehicules=d["apps"], annees=d["years"],
               carburant=d["fuel"], architecture=d["layout"], angle=d["angle"], n_cyl=d["n"],
               alesage_mm=d["bore"], course_mm=d["stroke"], bielle_mm=d["rod"], epsilon=d["eps"],
               induction=d["ind"], puissance_ch=d["ps"], regime_tr_min=d["rpm"], couple_Nm=d["nm"], cylindree_cm3=d["cc"])
        for d in brut
    ]


def trouver(id_moteur: str) -> Moteur:
    """Retourne le moteur d'identifiant donné (ex. ``"audi-40tfsi"``)."""
    for m in charger():
        if m.id == id_moteur:
            return m
    raise KeyError(f"moteur inconnu : {id_moteur!r}")


def _arrondi_js(x: float, decimales: int = 2) -> float:
    """Arrondi « au plus proche, demi vers +∞ », comme Math.round en JavaScript."""
    f = 10 ** decimales
    return math.floor(x * f + 0.5) / f


def consignes_de_base(m: Moteur) -> Consignes:
    """Consignes pleine charge au régime nominal, avec P1 = 1 bar (avant calage)."""
    diesel = m.carburant == "diesel"
    return Consignes(
        carburant=m.carburant, cycle="sabathe", mode_gamma="auto",
        alesage_mm=m.alesage_mm, course_mm=m.course_mm,
        bielle_mm=m.bielle_mm if m.bielle_mm is not None else round(m.course_mm * 1.62, 1),
        n_cyl=m.n_cyl, epsilon=m.epsilon,
        p1_bar=1.0, t1_c=45.0 if m.suralimente else 35.0, regime_tr_min=m.regime_tr_min,
        lambda_=1.4 if diesel else 1.0,
        pci_mj_kg=42.6 if diesel else 42.7, afr_st=14.5 if diesel else 14.7,
        eta_comb_pct=98.0 if diesel else 97.0,
        part_isochore_pct=35.0 if diesel else 80.0, gamma=1.33,
    )


def caler_p1(m: Moteur) -> float:
    """Pression d'admission équivalente (bar) qui retrouve la puissance annoncée.

    La puissance indiquée étant proportionnelle à P1 (à T1 fixée), le calage est
    direct : P1 = P_cible / P_i(P1 = 1 bar), avec P_cible = P_constructeur / QUALITE.
    Le résultat est arrondi au centième et borné à [0,6 ; 4,5] bar.
    """
    r = calculer_cycle(consignes_de_base(m))
    cible = m.puissance_ch * CH_W / QUALITE[m.carburant]
    p1 = cible / r.puissance_W if r.puissance_W > 0 else 1.0
    return min(4.5, max(0.6, _arrondi_js(p1, 2)))


def consignes_calees(m: Moteur) -> Consignes:
    """Consignes de base avec P1 calée sur la puissance constructeur."""
    return consignes_de_base(m).avec(p1_bar=caler_p1(m))


def calculer_moteur(id_moteur: str) -> Resultat:
    """Raccourci : calcul du cycle d'un moteur du catalogue à son point de calage."""
    return calculer_cycle(consignes_calees(trouver(id_moteur)))
