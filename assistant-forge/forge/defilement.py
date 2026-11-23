"""Barre de défilement du tableau d'effets.

Un objet avec beaucoup de lignes ne tient pas dans le tableau : le jeu affiche alors une barre de défilement à droite
(absente quand tout tient). On ne défile JAMAIS à ta place : on repère seulement la position de la poignée, pour
savoir si le tableau a défilé (les lignes qui sortent de la vue ne sont alors pas « perdues ») et combien de lignes
restent hors vue. Calibré sur une vidéo 1080p : poignée claire (~150 de luminosité) sur un fond ~35, 280 à 540 px.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SEUIL_CLAIR = 110        # luminosité minimale de la poignée
LONGUEUR_MIN = 0.15      # la poignée mesure au moins 15 % de la hauteur de la zone (le bruit fait ~5 %)
DEBUT_CORPS = 0.17       # on ignore le haut de la zone (reliquat, boutons, en-tête)
PISTE = 0.775            # longueur approximative de la piste, en part de la hauteur de la zone


@dataclass(frozen=True)
class Defilement:
    haut: int       # position du haut de la poignée (pixels dans la zone)
    long: int       # longueur de la poignée
    piste: int      # longueur estimée de la piste complète

    def a_bouge(self, autre: "Defilement", tolerance: int = 4) -> bool:
        return abs(self.haut - autre.haut) > tolerance

    def longueur_a_change(self, autre: "Defilement", tolerance: int = 4) -> bool:
        return abs(self.long - autre.long) > tolerance

    def lignes_cachees(self, lignes_vues: int) -> float:
        """Estimation du nombre de lignes hors vue : si la poignée fait 87 % de la piste, on voit 87 % des lignes."""
        if self.long <= 0:
            return 0.0
        return max(0.0, lignes_vues * (self.piste / self.long - 1))


def lire_defilement(zone) -> Optional[Defilement]:
    """Repère la poignée de la barre de défilement dans l'image de la zone. None = pas de barre (tout tient)."""
    import cv2
    import numpy as np

    if zone is None or zone.size == 0:
        return None
    g = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY) if zone.ndim == 3 else zone
    H, W = g.shape
    y0 = int(DEBUT_CORPS * H)
    bande = g[y0:, int(W * 0.9):W - 2] > SEUIL_CLAIR
    if bande.size == 0:
        return None
    meilleur = (0, 0)
    for x in range(bande.shape[1]):
        col = bande[:, x].astype(np.int8)
        # plus longue suite de pixels clairs de la colonne
        d = np.diff(np.concatenate(([0], col, [0])))
        debuts, fins = np.where(d == 1)[0], np.where(d == -1)[0]
        if len(debuts):
            longueurs = fins - debuts
            k = int(np.argmax(longueurs))
            if longueurs[k] > meilleur[0]:
                meilleur = (int(longueurs[k]), int(debuts[k]) + y0)
    long_, haut = meilleur
    if long_ < LONGUEUR_MIN * H:
        return None
    return Defilement(haut=haut, long=long_, piste=int(PISTE * H))
