"""Cinématique bielle-manivelle et état du gaz en fonction de l'angle de vilebrequin.

Convention : θ = 0 au PMH de début d'admission, 720° par cycle 4 temps.
Portage des fonctions ``makeKin``, ``pinHeight``, ``volumeAt``,
``pistonVelocity``, ``liftFrac`` et ``cycleAt`` de l'application web.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .thermo import Consignes, Resultat

TEMPS = ("Admission", "Compression", "Combustion – détente", "Échappement")

# Calage de distribution indicatif (°V) : AOA 10°, RFA 40°, AOE 40°, RFE 10°
CALAGE = {"ouverture_adm": 710.0, "duree_adm": 230.0, "ouverture_ech": 500.0, "duree_ech": 230.0}


@dataclass(frozen=True)
class Cinematique:
    r: float   # rayon de manivelle (m) = S/2
    L: float   # longueur de bielle entre axes (m)
    A: float   # section du piston (m²)
    Vc: float  # volume mort (m³)


@dataclass(frozen=True)
class EtatAngle:
    theta: float
    V: float      # m³
    P: float      # Pa
    T: float      # K (NaN pendant l'échappement : gaz expulsés)
    temps: int    # 0 admission, 1 compression, 2 combustion-détente, 3 échappement
    gaz: str      # "frais", "comprime", "brule", "echappement"


def cinematique(c: Consignes, res: Resultat) -> Cinematique:
    B = c.alesage_mm / 1000.0
    return Cinematique(r=c.course_mm / 2000.0, L=c.bielle_mm / 1000.0, A=math.pi / 4.0 * B * B, Vc=res.Vc)


def hauteur_axe(k: Cinematique, theta_deg: float) -> float:
    """Distance axe du vilebrequin → axe du piston (m)."""
    t = math.radians(theta_deg)
    s = math.sin(t)
    return k.r * math.cos(t) + math.sqrt(k.L * k.L - k.r * k.r * s * s)


def volume(k: Cinematique, theta_deg: float) -> float:
    """Volume instantané du cylindre (m³)."""
    return k.Vc + k.A * (k.L + k.r - hauteur_axe(k, theta_deg))


def vitesse_piston(k: Cinematique, theta_deg: float, regime_tr_min: float) -> float:
    """Vitesse du piston (m/s), positive vers le PMH."""
    t = math.radians(theta_deg)
    w = 2.0 * math.pi * regime_tr_min / 60.0
    s, co = math.sin(t), math.cos(t)
    return -k.r * w * s - k.r * k.r * w * s * co / math.sqrt(k.L * k.L - k.r * k.r * s * s)


def levee_relative(theta_deg: float, ouverture: float, duree: float) -> float:
    """Levée de soupape relative (0 à 1), profil en sin²."""
    rel = ((theta_deg - ouverture) % 720.0 + 720.0) % 720.0
    return 0.0 if rel >= duree else math.sin(math.pi * rel / duree) ** 2


def etat_a_angle(res: Resultat, k: Cinematique, theta_deg: float) -> EtatAngle:
    """État du gaz dans le cylindre à l'angle θ, suivant le cycle théorique calculé."""
    th = (theta_deg % 720.0 + 720.0) % 720.0
    V, g = volume(k, th), res.gamma
    s1, s3, s4 = res.etats[0], res.etats[2], res.etats[3]
    temps = min(3, int(th // 180))
    if temps == 0:
        return EtatAngle(th, V, s1.P, s1.T, temps, "frais")
    if temps == 1:
        return EtatAngle(th, V, s1.P * (s1.V / V) ** g, s1.T * (s1.V / V) ** (g - 1), temps, "comprime")
    if temps == 2:
        if V <= s4.V:
            return EtatAngle(th, V, s3.P, s3.T * V / s3.V, temps, "brule")
        return EtatAngle(th, V, s4.P * (s4.V / V) ** g, s4.T * (s4.V / V) ** (g - 1), temps, "brule")
    return EtatAngle(th, V, s1.P, math.nan, temps, "echappement")
