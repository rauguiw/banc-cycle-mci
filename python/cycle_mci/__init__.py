"""cycle_mci — modèle thermodynamique 0D d'un moteur à combustion interne 4 temps.

Portage Python du noyau de calcul du Banc Cycle MCI
(https://rauguiw.github.io/banc-cycle-mci/).

Exemple
-------
>>> from cycle_mci import Consignes, calculer_cycle
>>> res = calculer_cycle(Consignes(cycle="otto", epsilon=10.5, p1_bar=1.0))
>>> round(res.eta_th, 4)
0.5098
"""

from .thermo import (Avertissement, Consignes, Etat, PointTrajet, Resultat, Transformation,
                     calculer_cycle, cp_air, entropie, gamma_air)
from .catalogue import Moteur, calculer_moteur, caler_p1, charger, consignes_calees, consignes_de_base, trouver
from .cinematique import cinematique, etat_a_angle, levee_relative, vitesse_piston, volume

__version__ = "1.0.0"

__all__ = [
    "Avertissement", "Consignes", "Etat", "PointTrajet", "Resultat", "Transformation",
    "calculer_cycle", "cp_air", "entropie", "gamma_air",
    "Moteur", "calculer_moteur", "caler_p1", "charger", "consignes_calees", "consignes_de_base", "trouver",
    "cinematique", "etat_a_angle", "levee_relative", "vitesse_piston", "volume",
]
