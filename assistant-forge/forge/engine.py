"""Moteur de calcul du puits (reliquat) de forgemagie.

Règle de base, confirmée par plusieurs guides communautaires :
    puits_après = puits_avant - poids_de_la_rune + poids_perdu
(valable pour un succès neutre ou un échec critique ; un succès critique
ne change pas le puits ; le puits ne descend jamais sous 0).

Ce module ne devine rien : quand une situation est ambiguë ou incohérente,
il renvoie des avertissements au lieu d'inventer une valeur.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional

SUCCES_CRITIQUE = "succes_critique"
SUCCES_NEUTRE = "succes_neutre"
ECHEC_CRITIQUE = "echec_critique"
INCONNU = "inconnu"

from forge.chemins import chemin_data

DATA_FILE = chemin_data("stats.json")


def charger_poids(chemin: Path = DATA_FILE) -> Dict[str, Fraction]:
    """Lit data/stats.json et renvoie {nom_stat: poids_par_point}."""
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    return {cle: Fraction(info["poids_par_point"]) for cle, info in donnees["stats"].items()}


def poids_de_changements(changements: Dict[str, int], poids: Dict[str, Fraction]) -> Fraction:
    """Poids total d'un ensemble de points (ex: {'force': 3, 'initiative': 2})."""
    total = Fraction(0)
    for stat, points in changements.items():
        if stat not in poids:
            raise KeyError(f"Caractéristique inconnue : {stat!r} (à ajouter dans data/stats.json)")
        total += poids[stat] * abs(points)
    return total


def poids_de_rune(stat: str, montant: int, poids: Dict[str, Fraction]) -> Fraction:
    """Poids d'une rune = montant du bonus x poids par point."""
    return poids_de_changements({stat: montant}, poids)


@dataclass
class Tentative:
    """Résultat de l'analyse d'une rune passée."""

    issue: str
    gains: Dict[str, int]
    pertes: Dict[str, int]
    poids_perdu: Fraction
    puits_avant: Optional[Fraction]
    puits_apres: Optional[Fraction]  # None = inconnu
    puits_apres_min: Optional[Fraction] = None  # fourchette si ambigu
    puits_apres_max: Optional[Fraction] = None
    avertissements: List[str] = field(default_factory=list)
    fiable: bool = True


def comparer_etats(avant: Dict[str, int], apres: Dict[str, int]):
    """Renvoie (gains, pertes) entre deux états de l'objet."""
    gains, pertes = {}, {}
    for stat in set(avant) | set(apres):
        delta = apres.get(stat, 0) - avant.get(stat, 0)
        if delta > 0:
            gains[stat] = delta
        elif delta < 0:
            pertes[stat] = -delta
    return gains, pertes


def analyser_tentative(
    avant: Dict[str, int],
    apres: Dict[str, int],
    poids_rune: Fraction,
    poids: Dict[str, Fraction],
    puits_avant: Optional[Fraction],
    issue_lue: str = INCONNU,
    puits_affiche: Optional[Fraction] = None,
) -> Tentative:
    """Analyse une rune passée et met à jour le puits.

    avant / apres : valeurs des caractéristiques avant et après la rune.
    poids_rune    : poids de la rune utilisée.
    puits_avant   : puits connu avant la rune (None si inconnu).
    issue_lue     : issue affichée par le jeu si elle a pu être lue.
    puits_affiche : puits lu à l'écran après la rune (prioritaire si fourni).
    """
    gains, pertes = comparer_etats(avant, apres)
    perdu = poids_de_changements(pertes, poids)
    avert: List[str] = []
    t = Tentative(
        issue=issue_lue,
        gains=gains,
        pertes=pertes,
        poids_perdu=perdu,
        puits_avant=puits_avant,
        puits_apres=None,
        avertissements=avert,
    )

    # 1) Issue : celle lue à l'écran, sinon déduite quand c'est sans ambiguïté.
    if issue_lue == INCONNU:
        if pertes and gains:
            t.issue = SUCCES_NEUTRE
        elif pertes and not gains:
            t.issue = ECHEC_CRITIQUE
        elif gains and not pertes:
            if puits_avant is not None and puits_avant < poids_rune:
                # Un succès neutre aurait forcément coûté des caractéristiques.
                t.issue = SUCCES_CRITIQUE
            else:
                avert.append(
                    "Gain sans perte : succès critique, ou succès neutre entièrement "
                    "absorbé par le puits. Impossible de trancher sans lire l'issue "
                    "ou le puits affiché."
                )
        else:
            avert.append("Aucun changement détecté : rune non passée, ou lecture ratée.")

    if t.issue == ECHEC_CRITIQUE and gains:
        avert.append("Échec critique avec un gain : lecture incohérente, à revérifier.")

    # 2) Puits après.
    if puits_affiche is not None:
        t.puits_apres = puits_affiche
        if puits_avant is not None:
            attendu = _puits_attendu(t.issue, puits_avant, poids_rune, perdu)
            if attendu is not None and attendu != puits_affiche:
                avert.append(
                    f"Le puits affiché ({float(puits_affiche):g}) diffère du calcul "
                    f"({float(attendu):g}) : vérifie les poids de data/stats.json."
                )
        return _finaliser(t)

    if puits_avant is None:
        avert.append("Puits de départ inconnu : saisis-le pour un calcul fiable.")
        return _finaliser(t)

    if t.issue == INCONNU:
        # Fourchette honnête : SC (inchangé) ou SN absorbé (puits - poids).
        bas = max(Fraction(0), puits_avant - poids_rune)
        t.puits_apres_min, t.puits_apres_max = bas, puits_avant
        return _finaliser(t)

    t.puits_apres = _puits_attendu(t.issue, puits_avant, poids_rune, perdu)

    # 3) Contrôle de cohérence : la perte doit couvrir ce que le puits n'a pas absorbé.
    if t.issue in (SUCCES_NEUTRE, ECHEC_CRITIQUE):
        minimum = max(Fraction(0), poids_rune - puits_avant)
        if perdu < minimum:
            avert.append(
                f"Perte observée ({float(perdu):g}) inférieure au minimum attendu "
                f"({float(minimum):g}) : lecture incomplète ou poids de rune faux."
            )
    return _finaliser(t)


def _puits_attendu(issue, puits_avant, poids_rune, perdu) -> Optional[Fraction]:
    if issue == SUCCES_CRITIQUE:
        return puits_avant
    if issue in (SUCCES_NEUTRE, ECHEC_CRITIQUE):
        return max(Fraction(0), puits_avant - poids_rune + perdu)
    return None


def _finaliser(t: Tentative) -> Tentative:
    t.fiable = not t.avertissements and (
        t.puits_apres is not None or t.puits_apres_min is not None
    ) and t.puits_apres_min is None
    return t
