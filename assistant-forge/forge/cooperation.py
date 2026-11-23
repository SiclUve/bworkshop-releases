"""(v143) Forgemagie en COOPÉRATION (vu en vidéo) : ce qui change par rapport au mode solo, et seulement ça.

Constats sur journal_video.jsonl (31/10, 980 lectures coop contre 12 161 solo) :
  1. Sous l'historique, la fenêtre coop affiche « VIDER L'HISTORIQUE », le « Sac d'ingrédients » (icônes de runes du
     client et leurs quantités, qui changent à chaque passe) et « Paiement ». La zone de l'historique les contient.
     Ces lignes sont EN BAS, là où arrivent les passes nouvelles : l'alignement de deux lectures échouait (texte aligné
     33 % des lectures coop contre 96 % en solo), et les icônes du sac faussaient le repérage des icônes de passes.
     -> on coupe la zone au-dessus du pied (texte ET image) ; rien n'est deviné.
  2. Image coop plus petite : « -1 » lu « -i » / « -l », « reliquat » lu « relquat ». Avant, ces rangées étaient
     ignorées : une perte disparaissait sans bruit (la passe semblait propre), une ligne reliquat aussi (la passe
     devenait un « succès critique »). -> en coop, une perte sans chiffre rend la passe INCOMPLÈTE (jamais un chiffre
     inventé) et les variantes de « reliquat » sont reconnues.
  3. Le chiffre du reliquat manque dans 11,6 % des lectures coop (0,5 % en solo) : « reliquat : CLIENT », il est collé
     aux cases de runes. -> une relecture de la petite zone à droite de « reliquat : », acceptée seulement si deux
     lectures (deux agrandissements) donnent exactement le même nombre bien formé ; sinon le reliquat reste inconnu.
Le mode solo ne passe par aucune de ces règles (rien ne change pour lui).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, Optional, Tuple


def _cle(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z]", "", t)


_PIED = ("viderlhistorique", "sacdingredient", "paiement")


def ligne_de_pied(texte: str) -> bool:
    """Texte du bas de la fenêtre coop (« VIDER L'HISTORIQUE », « Sac d'ingrédients », « Paiement : »)."""
    k = _cle(texte)
    return any(m in k for m in _PIED)


def haut_du_pied(infos: Iterable[Dict]) -> Optional[float]:
    """Hauteur (y, pixels de la zone) où commence le pied de la fenêtre coop, ou None s'il n'y en a pas (mode solo)."""
    ys = [i.get("y0", i.get("cy")) for i in infos if ligne_de_pied(i.get("t", ""))]
    ys = [y for y in ys if y is not None]
    return min(ys) if ys else None


def table_coop(texte: str) -> bool:
    """Le tableau lu est celui de la fenêtre coop (le jeu y écrit « CLIENT » à côté du nom du client)."""
    return bool(re.search(r"\bCLIENT\b", texte or ""))


# reliquat : variantes vues en coop (« relquat », « relqugt », « rellguat », « reliquq1 »)
RELIQUAT_COOP = re.compile(r"([+\-−–])?\s*r[eé]l{1,2}[il1]{0,2}[qg][a-z1]{1,4}\b", re.I)
# perte dont le chiffre est perdu : « -i Dommage Neutre », « * -l Dommoge Terre », « w-i Tacle », « -1 » devenu lettre
_SANS_CHIFFRE = re.compile(r"^[^\d]{0,3}?[+\-−–]\s*[ilI|!]?\s*(%)?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' ]{2,})$")


def effet_sans_chiffre(texte: str) -> bool:
    """Rangée d'historique qui est un effet (signe + caractéristique connue) dont le nombre n'a pas été lu."""
    t = (texte or "").strip()
    if re.search(r"\d", t):
        return False
    m = _SANS_CHIFFRE.match(t)
    if not m:
        return False
    from forge.historique import libelle_reconnu
    lib = re.sub(r"\s+", " ", m.group(2)).strip(" '")
    return len(re.sub(r"[^A-Za-zÀ-ÿ]", "", lib)) >= 3 and libelle_reconnu(lib)


# --- reliquat ----------------------------------------------------------------------------------------------------------

_NOMBRE_RELIQUAT = re.compile(r"^(0|[1-9]\d{0,3})(?:[.,](\d{1,2}))?$")


def nombre_reliquat(textes) -> Optional[str]:
    """Le nombre lu, s'il est SEUL et bien formé (« 0,6 », « 12 », « 9,1 ») ; sinon None (on ne devine pas)."""
    # « :5 », « t:2 » (fin de « reliquat ») : le deux-points et la lettre qui le précède sont retirés
    morceaux = [re.sub(r"^[A-Za-z]{0,2}\s*[:;]\s*", "", t.strip()) for t in textes if t and t.strip()]
    morceaux = [t for t in morceaux if t]
    if len(morceaux) != 1 or re.search(r"\s", morceaux[0]):
        return None   # « 0, 1 », « 1 012 », deux nombres : ambigu (même règle que la lecture du tableau, v116)
    m = _NOMBRE_RELIQUAT.match(morceaux[0])
    if not m:
        return None
    if not m.group(2) and len(m.group(1)) > 1:
        return None   # « 35 » : peut-être « 3,5 » dont la virgule est perdue (vu le 31/10) ; seul un chiffre seul est sûr
    return m.group(1) + ("." + m.group(2) if m.group(2) else "")


def relire_reliquat(image, case: Tuple[float, float, float], lire=None) -> Optional[str]:
    """Relit le chiffre du reliquat juste à droite de « reliquat : » (case = (x de fin du mot, y du centre, hauteur)).
    Trois lectures à trois agrandissements : le nombre n'est gardé que si au moins deux donnent EXACTEMENT le même et
    qu'aucune ne dit autre chose. Le « : » est gardé dans la zone (un chiffre seul, collé à l'icône, n'est pas vu sans)."""
    import cv2
    import numpy as np
    if lire is None:
        from forge.ocr import lire_elements as lire
    x1, cy, h = case
    H, W = image.shape[:2]
    x0, xb = max(0, int(x1 - 0.6 * h)), min(W, int(x1 + 3.4 * h))
    y0, yb = max(0, int(cy - 0.8 * h)), min(H, int(cy + 0.8 * h))
    crop = image[y0:yb, x0:xb]
    if crop.size == 0 or xb - x0 < 4 or yb - y0 < 4:
        return None
    # la case de rune (icône colorée) suit le chiffre, gris clair : on coupe avant la première colonne colorée
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    couleur = ((hsv[..., 1] > 110) & (hsv[..., 2] > 90)).sum(axis=0) >= max(2, int(0.25 * crop.shape[0]))
    if couleur.any():
        crop = crop[:, :int(np.argmax(couleur))]
    if crop.shape[1] < max(4, int(0.4 * h)):
        return None
    crop = cv2.copyMakeBorder(crop, 24, 24, 24, 24, cv2.BORDER_REPLICATE)
    lus = []
    for f in (3, 4, 6):
        grand = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        try:
            elements, _ = lire(grand, agrandir=1)
        except Exception:
            return None
        textes = [t for _, t in elements if t and t.strip()]
        if not textes:
            continue                       # rien vu à cette taille : ni pour ni contre
        lus.append(nombre_reliquat(textes))   # None = lu mais pas un nombre net : compte CONTRE
    if len(lus) >= 2 and None not in lus and len(set(lus)) == 1:
        return lus[0]
    return None
