"""Noyau thermodynamique : cycle théorique à air d'un moteur 4 temps.

Portage Python fidèle du noyau de calcul de l'application web (index.html,
fonctions ``cpAir``, ``solveAtGamma`` et ``computeEngine``).

Hypothèses
----------
- Gaz parfait (air, R = 287,05 J/kg·K) en système fermé, sans gaz résiduels
  ni échanges aux parois.
- 1→2 compression isentropique, 2→3 apport isochore, 3→4 apport isobare,
  4→5 détente isentropique, 5→1 rejet isochore.
- Combustion instantanée : une fraction ``x`` de Q_in à volume constant, le
  reste à pression constante (x = 1 : Otto, x = 0 : Diesel, sinon Sabathé).
- γ unique sur le cycle ; en mode « auto », γ est itéré à la température
  moyenne des cinq états avec cp(T) de l'air (polynôme de Çengel).
- Grandeurs *indiquées* : avant frottements et travail de pompage.

Unités : SI dans les calculs (Pa, K, m³, J, kg) ; les entrées et certaines
sorties sont exprimées en unités d'usage (bar, °C, mm, tr/min), indiquées
dans le nom du champ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import List

R_AIR = 287.05  # J/(kg·K) — constante massique de l'air
T_REF = 298.15  # K — état de référence de l'entropie
P_REF = 101325.0  # Pa
CH_W = 735.49875  # 1 ch (cheval-vapeur métrique) en W

CYCLES = ("otto", "diesel", "sabathe")
CARBURANTS = ("essence", "diesel")


# ---------------------------------------------------------------------------
# Propriétés du gaz
# ---------------------------------------------------------------------------

def cp_air(T: float) -> float:
    """cp de l'air (J/kg·K), polynôme de Çengel valide de 273 à 1 800 K.

    La température est bornée à [250 ; 1 800] K, comme dans l'application.
    """
    t = min(max(T, 250.0), 1800.0)
    return (28.11 + 0.1967e-2 * t + 0.4802e-5 * t * t - 1.966e-9 * t * t * t) / 28.97 * 1000.0


def gamma_air(T: float) -> float:
    """Rapport γ = cp/cv de l'air à la température T (K)."""
    cp = cp_air(T)
    return cp / (cp - R_AIR)


def entropie(T: float, P: float, cp: float) -> float:
    """Entropie massique (J/kg·K) relative à 25 °C et 1 atm."""
    return cp * math.log(T / T_REF) - R_AIR * math.log(P / P_REF)


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Consignes:
    """Paramètres d'entrée d'un calcul de cycle (par défaut : 1.4 TSI à λ = 1)."""

    carburant: str = "essence"        # "essence" ou "diesel"
    cycle: str = "sabathe"            # "otto", "diesel" ou "sabathe"
    mode_gamma: str = "auto"          # "auto" (γ itéré sur cp(T)) ou "manuel"
    alesage_mm: float = 74.5
    course_mm: float = 80.0
    bielle_mm: float = 140.0
    n_cyl: int = 4
    epsilon: float = 10.0             # taux de compression volumétrique
    p1_bar: float = 1.0               # pression au PMB, fin d'admission (bar abs)
    t1_c: float = 35.0                # température au PMB, fin d'admission (°C)
    regime_tr_min: float = 6000.0
    lambda_: float = 1.0              # coefficient d'excès d'air λ = 1/φ
    pci_mj_kg: float = 42.7           # pouvoir calorifique inférieur
    afr_st: float = 14.7              # rapport air/carburant stœchiométrique
    eta_comb_pct: float = 97.0        # rendement de combustion
    part_isochore_pct: float = 80.0   # x, utilisé pour le cycle de Sabathé
    gamma: float = 1.33               # utilisé en mode manuel

    def avec(self, **modifs) -> "Consignes":
        """Copie modifiée (les consignes sont immuables)."""
        return replace(self, **modifs)


@dataclass(frozen=True)
class Etat:
    """Point d'état du cycle, par cylindre."""

    id: str
    libelle: str
    P: float   # Pa
    T: float   # K
    V: float   # m³
    v: float   # m³/kg
    u: float   # J/kg (origine 0 K)
    h: float   # J/kg (origine 0 K)
    s: float   # J/(kg·K)
    m: float   # kg
    U: float   # J
    H: float   # J
    S: float   # J/K


@dataclass(frozen=True)
class Transformation:
    """Bilan d'une transformation (convention : Q reçu, W fourni par le gaz)."""

    id: str
    nom: str
    nature: str
    Q: float   # J
    W: float   # J
    dU: float  # J


@dataclass(frozen=True)
class PointTrajet:
    """Point du cycle discrétisé, pour les diagrammes."""

    V_cm3: float
    P_bar: float
    T: float
    s: float
    segment: int  # 0 : 1→2, 1 : 2→3, 2 : 3→4, 3 : 4→5, 4 : 5→1


@dataclass(frozen=True)
class Avertissement:
    code: str
    niveau: str  # "warn" ou "info"
    texte: str


@dataclass
class Resultat:
    """Résultat complet d'un calcul de cycle (grandeurs par cylindre et par cycle)."""

    gamma: float
    cv: float
    cp: float
    iterations_gamma: int
    Vd: float
    Vc: float
    V_tot: float
    m_air: float
    m_carb: float
    m_carb_brule: float
    Q_carb: float
    Q_in: float
    Q_out: float
    Q_pertes: float
    W_net: float
    eta_th: float
    eta_carb: float
    eta_otto: float
    pmi_bar: float
    puissance_W: float
    couple_Nm: float
    csi_g_kWh: float
    debit_air_kg_h: float
    debit_carb_kg_h: float
    rho: float      # rapport de détente préalable V4/V3
    alpha: float    # rapport de pression P3/P2
    x_v: float      # part isochore effective
    p_max_bar: float
    t_max_K: float
    tronque: bool   # phase isobare limitée par le PMB
    etats: List[Etat] = field(default_factory=list)
    transformations: List[Transformation] = field(default_factory=list)
    trajet: List[PointTrajet] = field(default_factory=list)
    avertissements: List[Avertissement] = field(default_factory=list)

    @property
    def puissance_kW(self) -> float:
        return self.puissance_W / 1000.0

    @property
    def puissance_ch(self) -> float:
        return self.puissance_W / CH_W

    def est_fini(self) -> bool:
        """Vrai si toutes les grandeurs principales sont finies."""
        valeurs = [self.W_net, self.pmi_bar, self.puissance_W, self.eta_th, self.gamma]
        for e in self.etats:
            valeurs += [e.P, e.T, e.V, e.s]
        return all(math.isfinite(v) for v in valeurs)


# ---------------------------------------------------------------------------
# Résolution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Cycle:
    Vd: float; Vc: float
    V1: float; V2: float; V3: float; V4: float; V5: float
    P1: float; P2: float; P3: float; P4: float; P5: float
    T1: float; T2: float; T3: float; T4: float; T5: float
    m: float; cv: float; cp: float; g: float
    m_carb: float; m_brule: float; Q_carb: float; Q_lib: float
    Qv: float; Qp: float; xv: float; tronque: bool


def _resoudre(c: Consignes, g: float) -> _Cycle:
    """Résout les cinq états pour un γ donné."""
    B, S = c.alesage_mm / 1000.0, c.course_mm / 1000.0
    Vd = math.pi / 4.0 * B * B * S                  # cylindrée unitaire
    Vc = Vd / (c.epsilon - 1.0)                     # volume mort
    V1, V2 = Vd + Vc, Vc
    P1, T1 = c.p1_bar * 1e5, c.t1_c + 273.15
    m = P1 * V1 / (R_AIR * T1)                      # masse enfermée (gaz parfait)
    cv = R_AIR / (g - 1.0)
    cp = g * cv
    m_carb = m / (c.lambda_ * c.afr_st)             # carburant introduit
    m_brule = m_carb * min(1.0, c.lambda_)          # plafonné par l'oxygène disponible
    Q_carb = m_carb * c.pci_mj_kg * 1e6
    Q_lib = m_brule * c.pci_mj_kg * 1e6 * c.eta_comb_pct / 100.0
    xv = 1.0 if c.cycle == "otto" else 0.0 if c.cycle == "diesel" else c.part_isochore_pct / 100.0

    T2 = T1 * c.epsilon ** (g - 1.0)
    P2 = P1 * c.epsilon ** g
    Qv = xv * Q_lib
    V3, T3 = V2, T2 + Qv / (m * cv)
    P3 = P2 * T3 / T2
    Qp = (1.0 - xv) * Q_lib
    T4 = T3 + Qp / (m * cp)
    V4 = V3 * T4 / T3
    P4 = P3
    tronque = False
    if V4 > V1:  # l'apport isobare ne peut pas dépasser le PMB
        tronque = True
        V4 = V1
        T4 = T3 * V4 / V3
        Qp = m * cp * (T4 - T3)
    V5 = V1
    T5 = T4 * (V4 / V5) ** (g - 1.0)
    P5 = P4 * (V4 / V5) ** g
    return _Cycle(Vd, Vc, V1, V2, V3, V4, V5, P1, P2, P3, P4, P5, T1, T2, T3, T4, T5,
                  m, cv, cp, g, m_carb, m_brule, Q_carb, Q_lib, Qv, Qp, xv, tronque)


def _fr(x: float, decimales: int = 2) -> str:
    """Formatage à la française (espace pour les milliers, virgule décimale)."""
    texte = f"{x:,.{decimales}f}".replace(",", " ").replace(".", ",")
    if "," in texte:
        texte = texte.rstrip("0").rstrip(",")
    return texte


def _avertissements(c: Consignes, r: _Cycle, p_max_bar: float, t_max_K: float) -> List[Avertissement]:
    a: List[Avertissement] = []
    if r.tronque:
        a.append(Avertissement("isobare_tronquee", "warn",
                               "L'apport isobare atteint le PMB : la chaleur restante n'est pas convertie. "
                               "Augmentez la part isochore ou réduisez la charge."))
    if c.lambda_ < 1:
        a.append(Avertissement("melange_riche", "warn",
                               f"Mélange riche (λ = {_fr(c.lambda_, 3)}) : {_fr((1 - c.lambda_) * 100, 1)} % du carburant "
                               "ne trouve pas d'oxygène. L'énergie libérée est plafonnée à λ = 1."))
    if c.carburant == "diesel" and c.lambda_ < 1.2:
        a.append(Avertissement("fumee_diesel", "warn",
                               "Diesel sous λ ≈ 1,2 : limite de fumée dépassée, émissions de suies probables."))
    if c.carburant == "essence" and c.lambda_ > 1.5:
        a.append(Avertissement("pauvre_essence", "info",
                               "Mélange homogène très pauvre : au-delà de λ ≈ 1,5 l'allumage commandé devient instable (ratés)."))
    if c.carburant == "essence" and c.epsilon > 12 and c.p1_bar > 1.5:
        a.append(Avertissement("cliquetis", "info",
                               "Taux de compression élevé avec suralimentation : risque de cliquetis non modélisé ici."))
    if c.carburant == "diesel" and c.epsilon < 13:
        a.append(Avertissement("auto_inflammation", "info",
                               "Taux inférieur à 13 : l'auto-inflammation à froid du gazole devient difficile."))
    if t_max_K > 2800:
        a.append(Avertissement("dissociation", "info",
                               f"Tmax ≈ {_fr(round(t_max_K), 0)} K : au-delà de 2 500 K la dissociation de CO₂ et H₂O "
                               "limite la température réelle. Le cycle à air la surestime."))
    if p_max_bar > 220:
        a.append(Avertissement("pression_pointe", "warn",
                               f"Pmax théorique ≈ {round(p_max_bar)} bar : la combustion instantanée du cycle idéal "
                               "surestime la pression de pointe. Les moteurs de série plafonnent vers 120 à 200 bar."))
    return a


def calculer_cycle(c: Consignes, n_points: int = 64) -> Resultat:
    """Calcule le cycle, les bilans, les performances indiquées et les contrôles de validité.

    Paramètres
    ----------
    c : Consignes
        Paramètres du moteur et du point de fonctionnement.
    n_points : int
        Nombre de pas de discrétisation par transformation pour ``trajet``.
    """
    if c.cycle not in CYCLES:
        raise ValueError(f"cycle inconnu : {c.cycle!r} (attendu : {', '.join(CYCLES)})")
    if c.carburant not in CARBURANTS:
        raise ValueError(f"carburant inconnu : {c.carburant!r} (attendu : {', '.join(CARBURANTS)})")

    # --- γ : valeur imposée ou point fixe γ = γ(T_moy) avec relaxation 1/2 ---
    g = c.gamma if c.mode_gamma == "manuel" else 1.35
    r = _resoudre(c, g)
    iterations = 0
    if c.mode_gamma == "auto":
        for i in range(60):
            T_moy = (r.T1 + r.T2 + r.T3 + r.T4 + r.T5) / 5.0
            g_nouveau = gamma_air(T_moy)
            iterations = i + 1
            if abs(g_nouveau - g) < 1e-7:
                g = g_nouveau
                r = _resoudre(c, g)
                break
            g = 0.5 * g + 0.5 * g_nouveau
            r = _resoudre(c, g)

    m, cv, cp = r.m, r.cv, r.cp

    # --- points d'état ---
    base = [
        ("1", "PMB · fin d'admission", r.P1, r.T1, r.V1),
        ("2", "PMH · fin de compression", r.P2, r.T2, r.V2),
        ("3", "Fin de combustion isochore", r.P3, r.T3, r.V3),
        ("4", "Fin de combustion isobare", r.P4, r.T4, r.V4),
        ("5", "PMB · fin de détente", r.P5, r.T5, r.V5),
    ]
    etats = []
    for id_, libelle, P, T, V in base:
        s = entropie(T, P, cp)
        etats.append(Etat(id_, libelle, P, T, V, V / m, cv * T, cp * T, s, m, m * cv * T, m * cp * T, m * s))

    # --- bilans des transformations (dU = Q − W) ---
    brut = [
        ("1→2", "Compression", "isentropique", 0.0, -m * cv * (r.T2 - r.T1)),
        ("2→3", "Combustion", "isochore", r.Qv, 0.0),
        ("3→4", "Combustion", "isobare", r.Qp, r.P3 * (r.V4 - r.V3)),
        ("4→5", "Détente", "isentropique", 0.0, m * cv * (r.T4 - r.T5)),
        ("5→1", "Échappement", "isochore", -m * cv * (r.T5 - r.T1), 0.0),
    ]
    transformations = [Transformation(i, n, nat, Q, W, Q - W) for i, n, nat, Q, W in brut]

    # --- discrétisation pour les diagrammes ---
    trajet: List[PointTrajet] = []

    def ajouter(V: float, P: float, T: float, seg: int) -> None:
        trajet.append(PointTrajet(V * 1e6, P / 1e5, T, entropie(T, P, cp), seg))

    N = n_points
    for i in range(N + 1):  # 1→2, P·V^γ = cte, espacement géométrique
        V = r.V1 * (r.V2 / r.V1) ** (i / N)
        ajouter(V, r.P1 * (r.V1 / V) ** g, r.T1 * (r.V1 / V) ** (g - 1), 0)
    for i in range(N + 1):
        T = r.T2 + (r.T3 - r.T2) * i / N
        ajouter(r.V2, r.P2 * T / r.T2, T, 1)
    for i in range(N + 1):
        V = r.V3 + (r.V4 - r.V3) * i / N
        ajouter(V, r.P3, r.T3 * V / r.V3, 2)
    for i in range(N + 1):
        V = r.V4 * (r.V5 / r.V4) ** (i / N)
        ajouter(V, r.P4 * (r.V4 / V) ** g, r.T4 * (r.V4 / V) ** (g - 1), 3)
    for i in range(N + 1):
        T = r.T5 + (r.T1 - r.T5) * i / N
        ajouter(r.V1, r.P5 * T / r.T5, T, 4)

    # --- performances indiquées ---
    W_net = sum(t.W for t in transformations)
    Q_in = r.Qv + r.Qp
    Q_out = m * cv * (r.T5 - r.T1)
    cycles_par_s = c.n_cyl * c.regime_tr_min / 120.0  # 4 temps : 1 cycle pour 2 tours
    puissance_W = W_net * cycles_par_s
    omega = 2.0 * math.pi * c.regime_tr_min / 60.0
    p_max_bar = max(r.P3, r.P4) / 1e5
    t_max_K = max(r.T3, r.T4)

    return Resultat(
        gamma=g, cv=cv, cp=cp, iterations_gamma=iterations,
        Vd=r.Vd, Vc=r.Vc, V_tot=r.Vd * c.n_cyl,
        m_air=m, m_carb=r.m_carb, m_carb_brule=r.m_brule,
        Q_carb=r.Q_carb, Q_in=Q_in, Q_out=Q_out, Q_pertes=r.Q_carb - Q_in,
        W_net=W_net,
        eta_th=W_net / Q_in if Q_in > 0 else 0.0,
        eta_carb=W_net / r.Q_carb if r.Q_carb > 0 else 0.0,
        eta_otto=1.0 - c.epsilon ** (1.0 - g),
        pmi_bar=W_net / r.Vd / 1e5,
        puissance_W=puissance_W,
        couple_Nm=puissance_W / omega,
        csi_g_kWh=r.m_carb / W_net * 3.6e9 if W_net > 0 else math.nan,
        debit_air_kg_h=m * cycles_par_s * 3600.0,
        debit_carb_kg_h=r.m_carb * cycles_par_s * 3600.0,
        rho=r.V4 / r.V3, alpha=r.P3 / r.P2, x_v=r.xv,
        p_max_bar=p_max_bar, t_max_K=t_max_K, tronque=r.tronque,
        etats=etats, transformations=transformations, trajet=trajet,
        avertissements=_avertissements(c, r, p_max_bar, t_max_K),
    )
