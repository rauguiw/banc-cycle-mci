"""Contrôles de cohérence physique, indépendants du code JavaScript."""

import math
import unittest

from cycle_mci import Consignes, calculer_cycle, calculer_moteur, charger, consignes_calees, cp_air, gamma_air
from cycle_mci.cinematique import cinematique, volume

BASE = Consignes(mode_gamma="manuel", gamma=1.4, epsilon=10.0, lambda_=1.0)


class Thermodynamique(unittest.TestCase):

    def test_premier_principe_sur_le_cycle(self):
        """Sur un cycle fermé : ΣΔU = 0 et W_net = Q_in − Q_out."""
        for cycle in ("otto", "diesel", "sabathe"):
            for mode in ("auto", "manuel"):
                with self.subTest(cycle=cycle, mode=mode):
                    r = calculer_cycle(BASE.avec(cycle=cycle, mode_gamma=mode))
                    self.assertAlmostEqual(sum(t.dU for t in r.transformations), 0.0, delta=1e-9 * r.Q_in)
                    self.assertAlmostEqual(r.W_net, r.Q_in - r.Q_out, delta=1e-9 * r.Q_in)

    def test_rendement_otto_analytique(self):
        """Cycle d'Otto à γ constant : η = 1 − ε^(1−γ), indépendant de la charge."""
        for eps in (6, 8, 10, 12, 14):
            for lam in (1.0, 1.3):
                r = calculer_cycle(BASE.avec(cycle="otto", epsilon=eps, lambda_=lam))
                self.assertAlmostEqual(r.eta_th, 1 - eps ** (1 - 1.4), places=12)

    def test_rendement_diesel_analytique(self):
        """Cycle Diesel à γ constant : η = 1 − (ρ^γ − 1) / (γ ε^(γ−1) (ρ − 1))."""
        g = 1.4
        for eps in (14, 18, 22):
            r = calculer_cycle(BASE.avec(cycle="diesel", carburant="diesel", epsilon=eps, lambda_=1.6, afr_st=14.5))
            rho = r.rho
            attendu = 1 - (rho ** g - 1) / (g * eps ** (g - 1) * (rho - 1))
            self.assertAlmostEqual(r.eta_th, attendu, places=12)

    def test_classement_des_cycles(self):
        """À ε et chaleur apportée égaux : η_Otto > η_Sabathé > η_Diesel."""
        eta = {c: calculer_cycle(BASE.avec(cycle=c, epsilon=12, lambda_=1.6)).eta_th for c in ("otto", "sabathe", "diesel")}
        self.assertGreater(eta["otto"], eta["sabathe"])
        self.assertGreater(eta["sabathe"], eta["diesel"])

    def test_isentropiques(self):
        """s1 = s2 et s4 = s5 ; l'entropie croît pendant l'apport de chaleur."""
        r = calculer_cycle(BASE.avec(mode_gamma="auto"))
        s = [e.s for e in r.etats]
        self.assertAlmostEqual(s[0], s[1], places=9)
        self.assertAlmostEqual(s[3], s[4], places=9)
        self.assertLess(s[1], s[2])
        self.assertLessEqual(s[2], s[3])

    def test_puissance_proportionnelle_a_p1(self):
        """À T1 fixée, la masse enfermée et donc W_net sont proportionnelles à P1."""
        r1 = calculer_cycle(BASE.avec(p1_bar=1.0))
        r2 = calculer_cycle(BASE.avec(p1_bar=2.0))
        self.assertAlmostEqual(r2.puissance_W / r1.puissance_W, 2.0, places=12)

    def test_melange_riche_plafonne(self):
        """En dessous de λ = 1, l'énergie libérée n'augmente plus."""
        r1 = calculer_cycle(BASE.avec(lambda_=1.0))
        r2 = calculer_cycle(BASE.avec(lambda_=0.8))
        self.assertAlmostEqual(r2.Q_in, r1.Q_in, places=9)
        self.assertGreater(r2.Q_carb, r1.Q_carb)
        self.assertIn("melange_riche", [a.code for a in r2.avertissements])

    def test_troncature_au_pmb(self):
        r = calculer_cycle(BASE.avec(cycle="diesel", carburant="diesel", epsilon=4, afr_st=14.5, pci_mj_kg=42.6))
        self.assertTrue(r.tronque)
        self.assertAlmostEqual(r.etats[3].V, r.etats[0].V, places=15)
        self.assertIn("isobare_tronquee", [a.code for a in r.avertissements])


class ProprietesDuGaz(unittest.TestCase):

    def test_cp_air_valeurs_tabulees(self):
        """cp de l'air à ±1,5 % des valeurs tabulées (Çengel, table A-2b)."""
        for T, cp_table in ((300, 1005), (500, 1029), (1000, 1142)):
            self.assertAlmostEqual(cp_air(T) / cp_table, 1.0, delta=0.015)

    def test_gamma_decroit_avec_la_temperature(self):
        valeurs = [gamma_air(T) for T in (300, 600, 900, 1200, 1500, 1800)]
        self.assertEqual(valeurs, sorted(valeurs, reverse=True))
        self.assertAlmostEqual(gamma_air(300), 1.40, delta=0.005)

    def test_convergence_de_gamma(self):
        r = calculer_cycle(BASE.avec(mode_gamma="auto"))
        T_moy = sum(e.T for e in r.etats) / 5
        self.assertLess(abs(r.gamma - gamma_air(T_moy)), 1e-6)
        self.assertLess(r.iterations_gamma, 60)


class Cinematique(unittest.TestCase):

    def test_volumes_aux_points_morts(self):
        c = BASE
        r = calculer_cycle(c)
        k = cinematique(c, r)
        self.assertAlmostEqual(volume(k, 0), r.Vc, places=15)
        self.assertAlmostEqual(volume(k, 180), r.Vc + r.Vd, places=15)
        self.assertAlmostEqual(volume(k, 360), r.Vc, places=15)


class Catalogue(unittest.TestCase):

    def test_tous_les_moteurs_calculables(self):
        moteurs = charger()
        self.assertEqual(len(moteurs), 124)
        for m in moteurs:
            with self.subTest(moteur=m.id):
                r = calculer_cycle(consignes_calees(m))
                self.assertTrue(r.est_fini())
                self.assertGreater(r.eta_th, 0.3)
                self.assertLess(r.eta_th, r.eta_otto + 1e-12)

    def test_calage_retrouve_la_puissance_constructeur(self):
        """Après calage, P_i × 0,62 (essence) ou 0,66 (diesel) ≈ puissance annoncée, à l'arrondi de P1 près."""
        for m in charger():
            with self.subTest(moteur=m.id):
                r = calculer_cycle(consignes_calees(m))
                q = 0.66 if m.carburant == "diesel" else 0.62
                p1 = consignes_calees(m).p1_bar
                if 0.6 < p1 < 4.5:  # hors butée de calage
                    self.assertAlmostEqual(r.puissance_ch * q / m.puissance_ch, 1.0, delta=0.005 / p1 + 1e-9)

    def test_cylindree_coherente_avec_la_fiche(self):
        """Cylindrée calculée (alésage, course) à ±1 % de la cylindrée publiée."""
        for m in charger():
            with self.subTest(moteur=m.id):
                V = math.pi / 4 * m.alesage_mm ** 2 * m.course_mm * m.n_cyl / 1000
                self.assertAlmostEqual(V / m.cylindree_cm3, 1.0, delta=0.01)

    def test_exemple_audi(self):
        r = calculer_moteur("audi-40tfsi")
        self.assertAlmostEqual(r.puissance_kW, 711.73, places=2)
        self.assertEqual(r.iterations_gamma, 20)


if __name__ == "__main__":
    unittest.main()
