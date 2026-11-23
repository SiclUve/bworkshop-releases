"""Chance de réussite d'une rune selon le REMPLISSAGE de la ligne (observation seule).

D'où vient cette courbe : environ 4 900 runes passées par script dans le bac à sable de
succescritique.com, sur la Ceste de Guerre (voir MESURES.md). En rangeant toutes les runes
mesurées par « valeur de la ligne / maximum de la ligne », le résultat est net : c'est le
remplissage de la ligne qui commande, pas la taille de la rune en elle-même.

    ligne à 71 % de son max (Ré Per Terre 5/7)      -> 91 % de réussite
    ligne à 75 % (Critique 3/4)                     -> 88 %
    ligne à 80 % (Dommages Feu 8/10)                -> 84 %
    ligne à 87 % (Dommages Critiques 13/15)         -> 83 %
    ligne à 89 % (Vitalité 310/350, Pa Vi)          -> 43 %
    ligne à 92 % (Vitalité 320/350, Pa Vi)          -> 33 %
    ligne à 95 % (Vitalité 332/350, Pa Vi)          -> 25 %
    ligne à 97 % (Vitalité 340/350, Vi)             -> 11 %
    ligne à 97 % (Intelligence 58/60, Ine)          ->  3 %

ATTENTION : ces chiffres viennent d'un simulateur, pas du jeu. Tes propres passes donnent 39 %
pour la Rune Vi sur une Vitalité à 333-348, là où ce simulateur donne 11 %. Les deux disent que
c'est le plus mauvais coup de l'objet, pas de combien. Cette courbe ne sert donc que de valeur de
DÉPART : dès que tu as 15 passes d'une rune, forge/apprentissage.py prend le relais avec tes
chiffres à toi.
"""

from __future__ import annotations

from typing import Optional

# (remplissage de la ligne, chance de réussite observée)
COURBE = [
    (0.00, 0.95),
    (0.70, 0.91),
    (0.80, 0.85),
    (0.87, 0.80),
    (0.90, 0.50),
    (0.92, 0.35),
    (0.95, 0.25),
    (0.97, 0.13),
    (1.00, 0.10),
]


def chance_remplissage(remplissage: float) -> float:
    """Chance de réussite lue sur la courbe (interpolation entre deux points mesurés)."""
    r = max(0.0, min(1.0, remplissage))
    for i in range(1, len(COURBE)):
        x0, y0 = COURBE[i - 1]
        x1, y1 = COURBE[i]
        if r <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (r - x0) / (x1 - x0)
    return COURBE[-1][1]


def chance_ligne(valeur: int, maxi: Optional[int]) -> Optional[float]:
    """Chance de réussite d'une rune sur cette ligne, d'après son remplissage. None si le max est inconnu."""
    if not maxi or maxi <= 0:
        return None
    return chance_remplissage(valeur / maxi)
