"""(v97) Fichier d'ANALYSE : tout ce qu'il faut pour étudier la forgemagie, une ligne par lecture d'historique.

Pour chaque lot de runes lues : l'objet AVANT (chaque ligne : valeur, min, max) et son reliquat, l'objet APRÈS, et chaque
rune lue (nom reconnu par l'icône ou le gain, issue, effets, ligne « reliquat »). C'est exactement ce qui manquait pour les
analyses (état avant chaque passe, maximums, reliquat). Observation seule ; aucune donnée personnelle.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional
from forge.erreurs import noter as _noter_erreur


def _etat(p) -> Optional[dict]:
    if p is None:
        return None
    return {"lignes": {l.id: [l.valeur, l.mini, l.maxi] + ([l.couleur] if getattr(l, "couleur", None) else []) for l in p.lignes},
            "reliquat": float(p.reliquat) if getattr(p, "reliquat", None) is not None else None}


def enregistrer(chemin, ev, objet: str = "", source: str = "jeu") -> bool:
    """Ajoute une ligne au fichier d'analyse pour un événement « historique ». Renvoie True si écrit."""
    try:
        d = getattr(ev, "difference", None)
        entrees = [] if d is None else (d.entrees or [])
        rec = {"heure": getattr(ev, "heure", None) or time.time(), "source": source, "objet": objet,
               "avant": _etat(getattr(ev, "avant", None)), "apres": _etat(getattr(ev, "panneau", None)),
               "historique_aligne": d is not None and d.entrees is not None,
               "runes": [{"rune": getattr(e, "rune", None), "issue": e.issue,
                          "effets": [[x.libelle, x.valeur, bool(getattr(x, "pct", False))] for x in e.effets],
                          "reliquat": e.reliquat, "par_texte": bool(getattr(e, "par_texte", False)), "incomplete": bool(getattr(e, "incomplete", False))} for e in entrees],
               "changements": [] if d is None else [list(c) for c in (d.changements or [])]}
        Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:
        _noter_erreur("analyse.enregistrer")
        return False
