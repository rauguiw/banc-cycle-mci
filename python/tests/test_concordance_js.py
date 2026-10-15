"""Concordance du portage Python avec le code JavaScript de l'application.

Les valeurs de référence (tests/donnees/reference_js.json) sont produites en
exécutant le code d'origine extrait de index.html (outils/generer_reference.mjs) :
124 moteurs du catalogue à leur point de calage et 20 cas particuliers
(Otto / Diesel / Sabathé, γ auto ou imposé, mélanges riche et pauvre,
phase isobare tronquée au PMB).
"""

import json
import math
import unittest
from pathlib import Path

from cycle_mci import Consignes, calculer_cycle, caler_p1, cinematique, consignes_de_base, etat_a_angle, trouver
from cycle_mci.cinematique import vitesse_piston, volume

REFERENCE = json.loads((Path(__file__).parent / "donnees" / "reference_js.json").read_text(encoding="utf-8"))
TOL = 1e-9  # tolérance relative : écarts d'arrondi machine uniquement

# Correspondance noms JavaScript → champs Python
SORTIES = {
    "gamma": "gamma", "cv": "cv", "cp": "cp", "Vd": "Vd", "Vc": "Vc", "Vtot": "V_tot",
    "mAir": "m_air", "mFuel": "m_carb", "mFuelBurnt": "m_carb_brule", "Qfuel": "Q_carb", "Qadd": "Q_in",
    "Qout": "Q_out", "Qloss": "Q_pertes", "Wnet": "W_net", "etaTh": "eta_th", "etaFuel": "eta_carb",
    "etaOttoRef": "eta_otto", "pmiBar": "pmi_bar", "powerW": "puissance_W", "torqueNm": "couple_Nm",
    "isfc": "csi_g_kWh", "airKgH": "debit_air_kg_h", "fuelKgH": "debit_carb_kg_h", "rc": "rho",
    "alphaP": "alpha", "xv": "x_v", "pmaxBar": "p_max_bar", "tmaxK": "t_max_K",
}

# Identification des avertissements JavaScript par un fragment de leur texte
CODES_AVERTISSEMENT = {
    "apport isobare atteint": "isobare_tronquee", "Mélange riche": "melange_riche",
    "limite de fumée": "fumee_diesel", "très pauvre": "pauvre_essence", "cliquetis": "cliquetis",
    "Taux inférieur à 13": "auto_inflammation", "dissociation": "dissociation", "Pmax théorique": "pression_pointe",
}


def consignes_depuis_js(e: dict) -> Consignes:
    return Consignes(
        carburant=e["fuel"], cycle=e["cycle"], mode_gamma=e["gammaMode"],
        alesage_mm=e["boreMm"], course_mm=e["strokeMm"], bielle_mm=e["rodMm"], n_cyl=e["nCyl"],
        epsilon=e["eps"], p1_bar=e["p1Bar"], t1_c=e["t1C"], regime_tr_min=e["rpm"], lambda_=e["lambda"],
        pci_mj_kg=e["pciMJ"], afr_st=e["afrSt"], eta_comb_pct=e["etaCombPct"],
        part_isochore_pct=e["xvPct"], gamma=e["gamma"],
    )


def code_js(texte: str) -> str:
    for fragment, code in CODES_AVERTISSEMENT.items():
        if fragment in texte:
            return code
    raise AssertionError(f"avertissement JavaScript non reconnu : {texte}")


class ConcordanceJS(unittest.TestCase):

    def proche(self, attendu, obtenu, contexte):
        if attendu is None:  # NaN sérialisé en null par JSON
            self.assertTrue(math.isnan(obtenu), contexte)
            return
        self.assertTrue(math.isclose(obtenu, attendu, rel_tol=TOL, abs_tol=1e-12),
                        f"{contexte} : Python {obtenu!r} ≠ JavaScript {attendu!r}")

    def verifier_cas(self, cas):
        c = consignes_depuis_js(cas["entrees"])
        res = calculer_cycle(c)
        nom = cas["nom"]
        for cle_js, cle_py in SORTIES.items():
            self.proche(cas["sorties"][cle_js], getattr(res, cle_py), f"{nom} · {cle_py}")
        self.assertEqual(res.iterations_gamma, cas["sorties"]["gammaIterations"], f"{nom} · itérations")
        self.assertEqual(res.tronque, cas["sorties"]["capped"], f"{nom} · troncature")
        for e_js, e_py in zip(cas["etats"], res.etats):
            for cle in ("P", "T", "V", "s", "u", "h"):
                self.proche(e_js[cle], getattr(e_py, cle), f"{nom} · état {e_py.id} · {cle}")
        for t_js, t_py in zip(cas["transformations"], res.transformations):
            for cle in ("Q", "W", "dU"):
                self.proche(t_js[cle], getattr(t_py, cle), f"{nom} · {t_py.id} · {cle}")
        self.assertEqual([code_js(t) for t in cas["avertissements"]], [a.code for a in res.avertissements], nom)
        k = cinematique(c, res)
        for pt in cas["cinematique"]:
            th = pt["theta"]
            self.proche(pt["V"], volume(k, th), f"{nom} · V({th}°)")
            self.proche(pt["vitesse"], vitesse_piston(k, th, c.regime_tr_min), f"{nom} · vitesse({th}°)")
            ea = etat_a_angle(res, k, th)
            self.proche(pt["P"], ea.P, f"{nom} · P({th}°)")
            self.proche(pt["T"], ea.T, f"{nom} · T({th}°)")

    def test_catalogue_124_moteurs(self):
        self.assertEqual(len(REFERENCE["catalogue"]), 124)
        for cas in REFERENCE["catalogue"]:
            with self.subTest(moteur=cas["nom"]):
                self.verifier_cas(cas)

    def test_cas_particuliers(self):
        self.assertTrue(any(c["sorties"]["capped"] for c in REFERENCE["cas_particuliers"]))
        for cas in REFERENCE["cas_particuliers"]:
            with self.subTest(cas=cas["nom"]):
                self.verifier_cas(cas)

    def test_calage_p1_et_consignes(self):
        """Le calage de P1 et les consignes par défaut reproduisent ceux de l'application."""
        for cas in REFERENCE["catalogue"]:
            with self.subTest(moteur=cas["nom"]):
                m = trouver(cas["nom"])
                self.assertEqual(caler_p1(m), cas["entrees"]["p1Bar"])
                base = consignes_de_base(m)
                for cle_js, cle_py in (("t1C", "t1_c"), ("lambda", "lambda_"), ("xvPct", "part_isochore_pct"),
                                       ("pciMJ", "pci_mj_kg"), ("afrSt", "afr_st"), ("etaCombPct", "eta_comb_pct")):
                    self.assertEqual(getattr(base, cle_py), cas["entrees"][cle_js], f"{m.id} · {cle_py}")
                self.assertAlmostEqual(base.bielle_mm, cas["entrees"]["rodMm"], places=9)


if __name__ == "__main__":
    unittest.main()
