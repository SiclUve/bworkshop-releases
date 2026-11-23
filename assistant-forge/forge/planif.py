"""Plan de runes d'UNE ligne, plusieurs coups à l'avance (observation seule : ce module calcule un conseil, il n'agit jamais).

Pour une ligne qui doit passer de `valeur` à au moins `cible - marge` sans dépasser `cible`, on cherche la suite de runes
la moins chère en espérance. Le coût d'une rune posée sur une ligne à v est (1 + MU x poids perdu en cas de non-critique)
divisé par sa chance de réussite (modèle valeur / bonus, forge/modele_rune.py), plus le coût de la suite depuis v + bonus.

Conséquences, toutes retrouvées par le calcul :
  - Vitalité 296 : Ra +50 (91 %, 1 critique sur 2) -> 346, une seule rune ;
  - Vitalité 260 : Pa +15, Pa +15, puis Ra +50 -> 340 (trois runes sans malus), au lieu de Ra +50 -> 310 qui bloque la ligne ;
  - Vitalité 318 : toutes les runes sont en malus (Ra dépasse), le coût est élevé : la ligne est « bloquée » et on travaille
    les autres lignes en attendant qu'un échec la fasse redescendre sous 300.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from forge.modele_rune import chances

MU = 0.5            # poids donné à la perte de poids d'une passe non critique (en « passes équivalentes par point de poids »)
INFINI = 1e9
_CACHE: Dict[tuple, Tuple[List[float], List[int]]] = {}


def table(cible_min: int, cap: int, tailles: Tuple[int, ...], pp: float, ligne=None, maxi=None) -> Tuple[List[float], List[int]]:
    """cout[v] et rune[v] (bonus à passer) pour toute valeur v de 0 à cap. Avec `ligne` et `maxi` : chances apprises sur
    cette ligne (forge/chances_lignes.py, v95)."""
    cle = (cible_min, cap, tailles, round(pp, 4), MU, ligne, maxi)
    t = _CACHE.get(cle)
    if t is not None:
        return t
    cout = [INFINI] * (cap + 1)
    rune = [0] * (cap + 1)
    for v in range(cap, -1, -1):
        if v >= cible_min:
            cout[v] = 0.0
            continue
        meilleur, choix = INFINI, 0
        for s in tailles:
            if v + s > cap:
                continue
            if ligne and maxi:
                from forge.chances_lignes import chances as ch_ligne
                ch = ch_ligne(ligne, s, v, maxi)
            else:
                ch = chances(v, s)
            p = ch["critique"] + ch["succes"]
            if p <= 0:
                continue
            suite = cout[v + s]
            if suite >= INFINI:
                continue
            c = (1 + MU * s * pp * (1 - ch["critique"])) / p + suite
            if c < meilleur:
                meilleur, choix = c, s
        cout[v], rune[v] = meilleur, choix
    if len(_CACHE) > 2000:
        _CACHE.clear()
    _CACHE[cle] = (cout, rune)
    return cout, rune


def prochaine(valeur: int, cible_min: int, cap: int, tailles, pp: float, ligne=None, maxi=None) -> Optional[Tuple[int, float]]:
    """(bonus de la prochaine rune, coût attendu pour finir la ligne) ; None si aucune suite n'existe sans dépasser `cap`."""
    tailles = tuple(sorted(tailles))
    if valeur < 0 or valeur > cap:
        return None
    cout, rune = table(cible_min, cap, tailles, float(pp), ligne, maxi)
    if cout[valeur] >= INFINI:
        return None
    return rune[valeur], cout[valeur]
