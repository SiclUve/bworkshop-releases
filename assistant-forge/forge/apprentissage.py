"""Apprentissage des chances de réussite, à partir de TES passes (observation seule, aucune action dans le jeu).

Le registre (journaux/registre_runes.jsonl) garde chaque rune lue avec son résultat et la valeur de la ligne avant la
passe. Ici on en tire, par rune et selon que la ligne est « en malus » (valeur >= 20 fois le bonus) ou non, le taux de
réussite observé. Prudence : avec peu de passes, on mélange avec une valeur de départ ; en dessous de MIN_PASSES on
n'utilise pas du tout l'estimation apprise. Seules les passes dont la rune est lue exactement (« lue ») comptent.
Le résultat est écrit dans journaux/chances_apprises.json (lisible) et utilisé par le conseiller.
"""

from __future__ import annotations

from forge.fiabilite import passe_exploitable

import json  # noqa: F401  (v165) gardé pour compatibilité ; l'écriture passe par erreurs.ecrire_json
import os
import threading
from typing import Dict, List, Optional

MIN_PASSES = 15     # en dessous : estimation de départ seulement
POIDS_DEPART = 10   # la valeur de départ compte comme 10 passes
MALUS_FOIS = 20

# {rune: {"malus": [passes, réussites, critiques], "normal": [passes, réussites, critiques]}}
APPRIS: Dict[str, Dict[str, List[int]]] = {}
_VERROU = threading.RLock()


def _classe(r: dict) -> Optional[str]:
    from forge.optimisation import info_rune
    info = info_rune(r.get("rune"))
    if info is None or r.get("valeur_avant") is None:
        return None
    return "malus" if info[2] and r["valeur_avant"] >= MALUS_FOIS * info[2] else "normal"


def apprendre(rows: List[dict]) -> Dict[str, Dict[str, List[int]]]:
    out: Dict[str, Dict[str, List[int]]] = {}
    for r in rows:
        if not passe_exploitable(r):
            continue
        if r.get("certitude") != "lue" or r.get("exo") or not r.get("rune"):
            continue
        issue = r.get("issue") or ""
        if not (issue.startswith("succès") or issue.startswith("échec")):
            continue
        cl = _classe(r)
        if cl is None:
            continue
        s = out.setdefault(r["rune"], {}).setdefault(cl, [0, 0, 0])
        s[0] += 1
        s[1] += issue.startswith("succès")
        s[2] += issue == "succès critique"
    return out


def charger_rows(rows: List[dict]) -> None:
    nouveau = apprendre(rows)
    with _VERROU:
        APPRIS.clear()
        APPRIS.update(nouveau)


def chance(rune: Optional[str], malus: bool, defaut: float) -> float:
    """Chance de réussite de la rune : apprise si assez de passes, sinon `defaut`. Mélangée à `defaut` (prudence)."""
    with _VERROU:
        s = (APPRIS.get(rune or "") or {}).get("malus" if malus else "normal")
        if not s or s[0] < MIN_PASSES:
            return defaut
        p = (s[1] + POIDS_DEPART * defaut) / (s[0] + POIDS_DEPART)
    return min(0.98, max(0.05, p))


def ecrire(chemin: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    with _VERROU:
        copie = sorted((nom, {cl: list(vals) for cl, vals in d.items()}) for nom, d in APPRIS.items())
    txt = {}
    for nom, d in copie:
        for cl, (n, ok, cr) in d.items():
            txt[f"{nom} ({'ligne haute, malus' if cl == 'malus' else 'ligne normale'})"] = {
                "passes": n, "reussite": round(ok / n, 2), "critiques": round(cr / n, 2),
                "utilise": n >= MIN_PASSES}
    from forge.erreurs import ecrire_json   # (v165) écriture sûre : copie puis remplacement
    ecrire_json(chemin, txt, ensure_ascii=False, indent=1)
