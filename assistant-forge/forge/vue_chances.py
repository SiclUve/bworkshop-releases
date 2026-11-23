"""Chances SC / SN / EC de chaque rune de l'objet, mises en forme pour le tableau de l'onglet Suivi.

SC = succès critique, SN = succès neutre, EC = échec critique.
Seule source des chiffres : forge.conseil.chances_rune_ligne (clés « critique », « succes », « echec »).
Ce module ne calcule AUCUNE chance : il reprend les valeurs du moteur telles quelles, et écrit « inconnu » quand le
moteur ne sait pas (None, clé absente, valeur illisible). Ce sont des estimations mesurées, pas la formule du jeu.
Le conseil n'est pas touché : ces fonctions ne font que lire.
Aucune dépendance graphique (testable sans écran).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from forge.erreurs import noter as _noter_erreur

INCONNU = "inconnu"
# (sigle affiché, clé renvoyée par chances_rune_ligne)
CLES = (("SC", "critique"), ("SN", "succes"), ("EC", "echec"))
ORDRE_TAILLES = ("simple", "pa", "ra")
LEGENDE = ("≈ chances estimées de chaque rune (mesures, pas la formule du jeu) · SC succès critique · "
           "SN succès neutre · EC échec critique")


def valeur_sure(ch, cle: str) -> Optional[float]:
    """Probabilité du moteur pour `cle`, ou None si elle manque ou n'est pas un nombre entre 0 et 1.
    Aucune correction : une valeur hors de [0, 1] n'est pas « réparée », elle devient inconnue."""
    if not isinstance(ch, dict):
        return None
    v = ch.get(cle)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = float(v)
    if math.isnan(v) or v < 0 or v > 1:
        return None
    return v


def texte_pourcent(v: Optional[float]) -> str:
    """« 22 % » ; sous 1 % une décimale (« 0,4 % ») pour ne pas afficher 0 % à tort ; None -> « inconnu »."""
    if v is None:
        return INCONNU
    p = v * 100
    if p == 0:
        return "0 %"
    if p < 1:
        return f"{p:.1f} %".replace(".", ",")
    return f"{p:.0f} %"


def _nom_court(ligne_id: str, taille: str) -> str:
    """« Ba », « Pa », « Ra » ; nom propre pour les runes spéciales (« Ga Pa »)."""
    from forge.conseil import NOMS_TAILLES
    from forge.runes_jeu import SPECIALES
    if ligne_id in SPECIALES:
        return SPECIALES[ligne_id]
    return NOMS_TAILLES.get(taille, taille)


def chances_ligne_runes(panneau, poids, ligne) -> List[Dict]:
    """Une entrée par rune de la ligne (Ba, Pa, Ra), dans cet ordre. Chaque entrée :
    {"runes": "Pa", "nom": "Rune Pa Vi", "montant": 15, "icone": chemin ou "", "SC": float|None, "SN": ..., "EC": ...}.
    Liste vide si la ligne n'a pas de rune connue."""
    from forge.conseil import chances_rune_ligne, infos_taille
    from forge.runes_jeu import chemin_icone, nom_rune
    try:
        tailles = infos_taille(ligne) or {}
    except Exception:
        _noter_erreur("vue_chances.infos_taille")
        tailles = {}
    runes: List[Dict] = []
    for taille in sorted(tailles, key=lambda t: ORDRE_TAILLES.index(t) if t in ORDRE_TAILLES else 99):
        montant = tailles[taille]
        try:
            ch = chances_rune_ligne(panneau, poids, ligne, montant)
        except Exception:
            _noter_erreur("vue_chances.chances_rune_ligne")
            ch = None
        nom = nom_rune(ligne.id, taille)
        try:
            icone = str(chemin_icone(nom) or "")
        except Exception:
            _noter_erreur("vue_chances.chemin_icone")
            icone = ""
        runes.append({"runes": _nom_court(ligne.id, taille), "nom": nom, "montant": montant, "icone": icone,
                      **{sigle: valeur_sure(ch, cle) for sigle, cle in CLES}})
    return runes


def chances_objet(panneau, poids) -> Dict[str, List[Dict]]:
    """id de ligne -> runes de chances_ligne_runes, pour toutes les lignes lues de l'objet."""
    if panneau is None:
        return {}
    out = {}
    for l in getattr(panneau, "lignes", None) or []:
        groupes = chances_ligne_runes(panneau, poids, l)
        if groupes:
            out[l.id] = groupes
    return out


def textes_groupe(groupe: Dict) -> List[tuple]:
    """[(sigle, texte)] à écrire : [("SC", "SC 22 %"), ("SN", "SN 55 %"), ("EC", "EC inconnu")]."""
    return [(s, f"{s} {texte_pourcent(groupe.get(s))}") for s, _ in CLES]


def phrase_groupe(groupe: Dict) -> str:
    """Phrase complète, lisible telle quelle : « Ba · Pa · Ra : ≈ SC 22 %, SN 55 %, EC 22 % »."""
    return f"{groupe['runes']} : ≈ " + ", ".join(t for _, t in textes_groupe(groupe))


def nombre_sous_rangees(details, chances: Optional[Dict[str, List[Dict]]]) -> int:
    """Nombre de sous-lignes de chances que le tableau va dessiner (une par ligne qui a des runes ; sert à sa hauteur)."""
    if not chances:
        return 0
    return sum(1 for d in details or () if chances.get(d.get("id")))
