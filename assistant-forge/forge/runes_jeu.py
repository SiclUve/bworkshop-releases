"""Noms de runes tels qu'ils s'affichent dans le jeu, et leurs icônes (data/icones/, prises du jeu).

« Rune Fo », « Rune Pa Fo », « Rune Ra Fo » : le code de la caractéristique + la taille (Ba = sans préfixe).
Les runes spéciales (Ga Pa, Ga Pme...) n'ont pas de taille.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Optional

from forge.chemins import chemin_data

DOSSIER_ICONES = chemin_data("icones")

CODES = {
    "vitalite": "Vi", "force": "Fo", "intelligence": "Ine", "chance": "Cha", "agilite": "Age", "sagesse": "Sa",
    "puissance": "Pui", "prospection": "Prospe", "pods": "Pod", "initiative": "Ini", "coup_critique": "Cri",
    "invocation": "Invo", "po": "Po", "dommages": "Do", "soins": "So", "tacle": "Tac", "fuite": "Fui",
    "do_neutre": "Do Neutre", "do_terre": "Do Terre", "do_feu": "Do Feu", "do_eau": "Do Eau", "do_air": "Do Air",
    "do_critique": "Do Cri", "do_poussee": "Do Pou", "do_pieges": "Do Pi", "renvoi": "Do Ren",
    "pct_do_sorts": "Do Per So", "pct_do_armes": "Do Per Ar", "pct_do_distance": "Do Per Di",
    "pct_do_melee": "Do Per Mé",
    "pct_res_neutre": "Ré Per Neutre", "pct_res_terre": "Ré Per Terre", "pct_res_feu": "Ré Per Feu",
    "pct_res_eau": "Ré Per Eau", "pct_res_air": "Ré Per Air", "pct_res_distance": "Ré Per Di",
    "pct_res_melee": "Ré Per Mé",
    "res_neutre": "Ré Neutre", "res_terre": "Ré Terre", "res_feu": "Ré Feu", "res_eau": "Ré Eau", "res_air": "Ré Air",
    "res_critique": "Ré Cri", "res_poussee": "Ré Pou",
    "retrait_pa": "Ret Pa", "retrait_pm": "Ret Pme", "esquive_pa": "Ré Pa", "esquive_pm": "Ré Pme",
}
SPECIALES = {"pa": "Ga Pa", "pm": "Ga Pme"}
PREFIXES = {"simple": "", "pa": "Pa ", "ra": "Ra "}


def nom_rune(ligne_id: str, taille: str, special: str = "") -> str:
    """Nom de la rune dans le jeu (sans le « +1 »). Repli lisible si la caractéristique est inconnue."""
    if special:
        return special if special.startswith("Rune") else f"Rune {special}"
    if ligne_id in SPECIALES:
        return f"Rune {SPECIALES[ligne_id]}"
    code = CODES.get(ligne_id)
    if code is None:
        return f"Rune {PREFIXES.get(taille, '')}{ligne_id}".strip()
    return f"Rune {PREFIXES.get(taille, '')}{code}"


def _slug(nom: str) -> str:
    n = unicodedata.normalize("NFD", nom)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return n.lower().strip().replace(" ", "_")


def chemin_icone(nom: str) -> Optional[Path]:
    """Fichier d'icône de la rune, ou None s'il n'existe pas."""
    p = DOSSIER_ICONES / f"{_slug(nom)}.png"
    return p if p.exists() else None


GROUPES = ("Exo", "Caractéristiques", "Vitalité, pods, initiative", "Dommages", "Résistances", "Autres")
_GROUPE_PAR_CODE = {}
for _code in ("Ga Pa", "Ga Pme", "Po", "Invo"):
    _GROUPE_PAR_CODE[_code] = 0
for _code in ("Fo", "Ine", "Cha", "Age", "Sa", "Pui"):
    _GROUPE_PAR_CODE[_code] = 1
for _code in ("Vi", "Pod", "Ini"):
    _GROUPE_PAR_CODE[_code] = 2
for _id, _code in CODES.items():
    if _code not in _GROUPE_PAR_CODE:
        _GROUPE_PAR_CODE[_code] = (3 if _code.startswith("Do") else 4 if _code.startswith("Ré") else 5)


def groupe_rune(nom: str) -> tuple:
    """(rang du groupe, nom du groupe, rang du code, rang de la taille) d'une rune, pour trier la liste de courses :
    par type (Exo, Caractéristiques, Vitalité…, Dommages, Résistances, Autres), puis par stat, puis Ba < Pa < Ra."""
    n = nom[5:] if nom.startswith("Rune ") else nom
    taille = 0
    for rang, pre in ((2, "Ra "), (1, "Pa ")):
        if n.startswith(pre) and n[len(pre):] in _GROUPE_PAR_CODE:
            taille, n = rang, n[len(pre):]
            break
    g = _GROUPE_PAR_CODE.get(n, 5)
    codes = list(_GROUPE_PAR_CODE)
    return (g, GROUPES[g], codes.index(n) if n in codes else len(codes), taille)
