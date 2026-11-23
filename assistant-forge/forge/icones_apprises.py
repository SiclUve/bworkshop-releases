"""(v117) Icônes de runes APPRISES sur ton écran, pour reconnaître la rune d'un échec dans l'historique.

Les 105 icônes de data/icones (128 px) ne ressemblent pas toujours aux petites icônes du jeu : reconnaissance de 3 % à
80 % selon la rune (audit du 29/10). Ici, chaque passe dont la rune est SÛRE (un seul gain, d'une taille de rune qui
existe : « +15 Vitalité » = Pa Vi) fournit l'icône telle que le jeu l'affiche chez toi. Un échec (pas de gain) est ensuite
comparé à ces icônes.

Prudence : la reconnaissance apprise ne remplace l'ancienne que si elle fait MIEUX sur tes propres passes sûres
(au moins 30 comparaisons, +5 points de bonnes réponses). Les comptes sont dans journaux/icones_stats.json.
Observation seule : lecture de l'écran.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from forge.erreurs import noter as _noter_erreur

TAILLE = 24            # icône ramenée à 24 x 24 pour la comparaison
MAX_PAR_RUNE = 12
DOUBLON = 0.985        # icône presque identique à une déjà gardée : inutile
SEUIL = 0.80           # ressemblance minimale
ECART = 0.04           # avance minimale sur la deuxième rune
N_MINI = 30            # comparaisons avant de faire confiance aux icônes apprises
GAIN_MINI = 0.05       # bonnes réponses en plus exigées face à l'ancienne méthode

_ETAT: Dict[str, object] = {}


def _dossier() -> str:
    from forge.chemins import dossier_journaux
    return os.path.join(dossier_journaux(), "icones_apprises")


def _vecteur(crop):
    import cv2
    import numpy as np
    v = cv2.resize(crop[..., :3], (TAILLE, TAILLE), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1)
    c = crop[..., :3].reshape(-1, 3).mean(axis=0).astype(np.float32)
    v = v - v.mean()
    n = float(np.linalg.norm(v)) or 1.0
    return v / n, c


def _charger():
    if "modeles" in _ETAT:
        return
    import cv2
    modeles: Dict[str, List[Tuple[object, object]]] = {}
    d = _dossier()
    if os.path.isdir(d):
        for nom_dossier in sorted(os.listdir(d)):
            sous = os.path.join(d, nom_dossier)
            if not os.path.isdir(sous):
                continue
            nom = nom_dossier.replace("_", " ")
            for f in sorted(os.listdir(sous)):
                img = cv2.imread(os.path.join(sous, f), cv2.IMREAD_COLOR)
                if img is not None and img.size:
                    modeles.setdefault(nom, []).append(_vecteur(img))
    _ETAT["modeles"] = modeles
    try:
        with open(os.path.join(os.path.dirname(d), "icones_stats.json"), encoding="utf-8") as f:
            _ETAT["stats"] = json.load(f)
    except Exception:
        _ETAT["stats"] = {"ancienne": [0, 0], "apprise": [0, 0]}


def oublier():
    """Pour les tests : relire le dossier au prochain appel."""
    _ETAT.clear()


def classer(crop, n: int = 2) -> List[Tuple[str, float]]:
    import numpy as np
    _charger()
    if crop is None or crop.size == 0:
        return []
    v, c = _vecteur(crop)
    res = []
    for nom, liste in _ETAT["modeles"].items():
        best = -1.0
        for vm, cm in liste:
            s = float(np.dot(v, vm)) - 0.6 * float(np.linalg.norm(c - cm)) / 441.7
            best = max(best, s)
        res.append((nom, best))
    res.sort(key=lambda t: -t[1])
    return res[:n]


def identifier(crop) -> Optional[Tuple[str, float]]:
    c = classer(crop, 2)
    if not c or c[0][1] < SEUIL or (len(c) > 1 and c[0][1] - c[1][1] < ECART):
        return None
    return c[0]


def apprendre(nom: str, crop) -> bool:
    """Garde l'icône d'une rune SÛRE (au plus 12 par rune, sans doublon). Renvoie True si gardée."""
    try:
        import cv2
        import numpy as np
        _charger()
        if crop is None or crop.size == 0 or min(crop.shape[:2]) < 8:
            return False
        liste = _ETAT["modeles"].setdefault(nom, [])
        v, c = _vecteur(crop)
        if any(float(np.dot(v, vm)) >= DOUBLON for vm, _ in liste) or len(liste) >= MAX_PAR_RUNE:
            return False
        sous = os.path.join(_dossier(), nom.replace(" ", "_"))
        os.makedirs(sous, exist_ok=True)
        cv2.imwrite(os.path.join(sous, f"{len(liste):02d}.png"), crop[..., :3])
        liste.append((v, c))
        return True
    except Exception:
        _noter_erreur("icones_apprises.apprendre")
        return False


def noter_comparaison(vrai: str, ancienne: Optional[str], apprise: Optional[str]):
    """Passe à rune sûre : chaque méthode a-t-elle trouvé la bonne rune ? (une absence de réponse compte comme fausse)"""
    _charger()
    st = _ETAT["stats"]
    st["ancienne"][1] += 1
    st["ancienne"][0] += ancienne == vrai
    if _ETAT["modeles"]:
        st["apprise"][1] += 1
        st["apprise"][0] += apprise == vrai
    try:
        d = os.path.dirname(_dossier())
        os.makedirs(d, exist_ok=True)
        from forge.erreurs import ecrire_json   # (v165) écriture sûre : copie puis remplacement
        ecrire_json(os.path.join(d, "icones_stats.json"), st)
    except Exception:
        _noter_erreur("icones_apprises.noter_comparaison")


def faire_confiance() -> bool:
    _charger()
    a, n = _ETAT["stats"]["apprise"]
    b, m = _ETAT["stats"]["ancienne"]
    return n >= N_MINI and m >= N_MINI and a / n >= b / m + GAIN_MINI


def choisir(ancienne: Optional[Tuple[str, float]], apprise: Optional[Tuple[str, float]]):
    """Réponse retenue pour l'icône d'une passe : l'apprise seulement si elle a fait ses preuves sur tes passes."""
    if apprise is not None and faire_confiance():
        return apprise
    return ancienne
