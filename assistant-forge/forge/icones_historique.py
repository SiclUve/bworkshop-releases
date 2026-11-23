"""Identifie la rune passée grâce à son ICÔNE dans l'historique (colonne de gauche du tableau de forgemagie).

On compare l'icône vue à l'écran aux 105 icônes de runes (data/icones/, 128 px) : la plus ressemblante donne le nom
de la rune, même quand l'essai a échoué et que l'historique ne montre que des pertes. Observation seule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

SEUIL_SCORE = 0.55   # ressemblance minimale (corrélation normalisée, 1 = identique)
ECART_MINI = 0.04    # avance minimale sur la deuxième icône la plus ressemblante

_MODELES: Optional[Dict[str, object]] = None
_NOMS: Optional[Dict[str, str]] = None


def _noms_runes() -> Dict[str, str]:
    """{nom de fichier d'icône (sans .png): nom de la rune dans le jeu} pour toutes les runes de forgemagie connues."""
    global _NOMS
    if _NOMS is None:
        from forge import runes_jeu as R
        noms = {}
        for ligne_id in list(R.CODES) + list(R.SPECIALES):
            for taille in R.PREFIXES:
                n = R.nom_rune(ligne_id, taille)
                noms[R._slug(n)] = n
        _NOMS = noms
    return _NOMS


def _modeles() -> Dict[str, object]:
    """{slug: icône BGRA rognée sur sa partie visible}."""
    global _MODELES
    if _MODELES is None:
        import cv2
        from forge.chemins import chemin_data
        _MODELES = {}
        dossier = chemin_data("icones")
        for slug in _noms_runes():
            f = dossier / f"{slug}.png"
            if not f.exists():
                continue
            img = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
            if img is None or img.ndim != 3 or img.shape[2] != 4:
                continue
            ys, xs = (img[..., 3] > 40).nonzero()
            if len(xs) == 0:
                continue
            _MODELES[slug] = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return _MODELES


def recadrer_icone(zone, bande: Tuple[int, int]):
    """Rogne l'icône d'une bande (y_haut, y_bas) de la colonne de gauche ; None si rien de net."""
    import numpy as np
    H, W = zone.shape[:2]
    y0, y1 = max(0, bande[0] - 3), min(H, bande[1] + 4)
    x0, x1 = int(0.05 * W), int(0.19 * W)
    bloc = zone[y0:y1, x0:x1]
    if bloc.size == 0:
        return None
    fond = np.median(bloc.reshape(-1, 3), axis=0)
    ecart = np.abs(bloc.astype(int) - fond).max(axis=2) > 40
    ys, xs = ecart.nonzero()
    if len(xs) < 20:
        return None
    return bloc[ys.min():ys.max() + 1, xs.min():xs.max() + 1], fond


def classer(zone, bande: Tuple[int, int], n: int = 3) -> List[Tuple[str, float]]:
    """Les n icônes de runes les plus ressemblantes : [(nom de la rune, score)] du plus au moins ressemblant."""
    import cv2
    import numpy as np
    r = recadrer_icone(zone, bande)
    if r is None:
        return []
    crop, fond = r
    h, w = crop.shape[:2]
    if h < 8 or w < 8:
        return []
    resultats = []
    # couleur moyenne de l'icône vue (pixels qui se détachent du fond) : la corrélation seule ne distingue pas
    # les runes de même forme et de couleurs différentes (Do Air / Do Terre / Do Feu)
    masque = np.abs(crop.astype(int) - fond).max(axis=2) > 40
    couleur_vue = crop[masque].mean(axis=0) if masque.any() else fond
    bord = 3
    large = cv2.copyMakeBorder(crop, bord, bord, bord, bord, cv2.BORDER_REPLICATE).astype(np.float32)
    for slug, modele in _modeles().items():
        meilleur = -1.0
        for echelle in (0.9, 1.0, 1.1):
            tw, th = max(6, round(w * echelle)), max(6, round(h * echelle))
            if tw > large.shape[1] or th > large.shape[0]:
                continue
            petit = cv2.resize(modele, (tw, th), interpolation=cv2.INTER_AREA)
            alpha = petit[..., 3:].astype(np.float32) / 255.0
            sur_fond = (petit[..., :3] * alpha + fond * (1 - alpha)).astype(np.float32)
            score = float(cv2.matchTemplate(large, sur_fond, cv2.TM_CCOEFF_NORMED).max())
            meilleur = max(meilleur, score)
        m = modele[..., 3] > 40
        couleur_modele = modele[..., :3][m].mean(axis=0) if m.any() else couleur_vue
        ecart_couleur = float(np.linalg.norm(couleur_vue - couleur_modele)) / 441.7
        resultats.append((slug, meilleur - 1.2 * ecart_couleur))
    resultats.sort(key=lambda t: -t[1])
    noms = _noms_runes()
    return [(noms[s], sc) for s, sc in resultats[:n]]


def identifier(zone, bande: Tuple[int, int]) -> Optional[Tuple[str, float]]:
    """(nom de la rune, score) si l'icône est reconnue sans ambiguïté, sinon None."""
    c = classer(zone, bande, 2)
    if not c or c[0][1] < SEUIL_SCORE:
        return None
    if len(c) > 1 and c[0][1] - c[1][1] < ECART_MINI:
        return None
    return c[0]


_CACHE_ICONES: Dict[bytes, Optional[Tuple[str, float]]] = {}


def identifier_en_cache(zone, bande: Tuple[int, int]) -> Optional[Tuple[str, float]]:
    """Comme identifier, mais une icône déjà vue n'est pas recalculée (la comparaison coûte ~0,1 s)."""
    r = recadrer_icone(zone, bande)
    if r is None:
        return None
    cle = r[0].tobytes() + bytes(r[0].shape)
    if cle not in _CACHE_ICONES:
        if len(_CACHE_ICONES) > 300:
            _CACHE_ICONES.clear()
        _CACHE_ICONES[cle] = identifier(zone, bande)
    return _CACHE_ICONES[cle]
