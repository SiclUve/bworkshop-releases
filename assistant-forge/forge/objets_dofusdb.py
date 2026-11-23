"""(v118) Catalogue d'objets téléchargé depuis DofusDB (api.dofusdb.fr), pour reconnaître un objet DÈS LA PREMIÈRE PASSE.

Lancé à la main, une fois (Telecharger_objets.bat) : bottes, ceintures, anneaux et amulettes de niveau 180 à 200.
Pour chaque objet : nom, niveau, type et bornes de chaque ligne ([251 à 300] Vitalité...). L'assistant reconnaît ensuite
l'objet du tableau de forgemagie à ses lignes et à leurs Min/Max, comme pour les objets appris en jeu (forge/objets.py).
Pas d'image : la reconnaissance par les lignes est plus sûre qu'une petite icône. Le libellé de chaque effet est lu dans
la description française de DofusDB et rattaché aux lignes du logiciel par la même fonction que l'historique
(cout._ligne_id) ; un libellé non reconnu est compté et affiché, jamais deviné.

Observation seule : rien n'est fait dans le jeu. Le seul accès réseau est ce téléchargement, lancé par toi.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple

API = "https://api.dofusdb.fr"
# (v169d) TOUS les objets forgemageables de DOFUS 3, niveaux 1 à 200 (ids de types lus sur DofusDB /item-types le
# 07/11/2026). Pas de familiers, Dofus, trophées, prysmaradites ni montures (non forgemageables).
TYPES = {1: "Amulette", 9: "Anneau", 10: "Ceinture", 11: "Bottes", 16: "Chapeau", 17: "Cape", 82: "Bouclier",
         2: "Arc", 3: "Baguette", 4: "Bâton", 5: "Dague", 6: "Épée", 7: "Marteau", 8: "Pelle", 19: "Hache",
         21: "Pioche", 22: "Faux", 271: "Lance", 114: "Arme magique", 20: "Outil"}
NIVEAU_MIN, NIVEAU_MAX = 1, 200
FICHIER = "objets_dofusdb.json"
PAGE = 50


def _get_json(url: str, params: List[Tuple[str, object]], timeout: float = 20.0):
    q = urllib.parse.urlencode(params, safe="[]$")
    req = urllib.request.Request(f"{url}?{q}" if q else url,
                                 headers={"User-Agent": "AssistantForge (observation seule)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def libelle_effet(description: str) -> Tuple[Optional[str], bool, bool]:
    """« #1{{~1~2 à }}#2% Résistance Terre » -> (« Résistance Terre », pourcentage, malus).
    « -#1{{~1~2 à -}}#2 Chance » -> (« Chance », False, True). (None, False, False) si rien d'exploitable."""
    if not description:
        return None, False, False
    d = description.strip()
    malus = d.startswith("-")
    if "#2" in d:
        reste = d.rsplit("#2", 1)[1]
    else:
        reste = re.sub(r"#\d|\{\{.*?\}\}", " ", d)
    reste = re.sub(r"\{\{.*?\}\}|#\d|~\d", " ", reste).strip()
    pct = reste.startswith("%")
    reste = reste.lstrip("%").strip(" :-")
    if not re.search(r"[A-Za-zÀ-ÿ]{2}", reste) or re.search(r"#|\{", reste):
        return None, False, malus
    avant = d.split("#1", 1)[0].strip(" -") if "#1" in d else ""
    if re.search(r"[A-Za-zÀ-ÿ]{2}", avant):   # « Renvoie #1...#2 dommages » : le texte d'avant fait partie du libellé
        reste = f"{avant} {reste}"
    return re.sub(r"\s+", " ", reste), pct, malus


def construire(items: List[dict], descriptions: Dict[int, str]) -> Tuple[Dict[str, dict], Counter]:
    """Objets DofusDB -> {signature: {nom, niveau, type, lignes, dofusdb_id, source}} ; + libellés non reconnus."""
    from forge.cout import _ligne_id
    from forge.objets import LIGNES_MINI, signature
    objets: Dict[str, dict] = {}
    inconnus: Counter = Counter()
    for it in items:
        lignes: Dict[str, List[int]] = {}
        for e in it.get("effects") or []:
            lib, pct, malus = libelle_effet(descriptions.get(e.get("effectId"), ""))
            if lib is None or malus:
                continue
            r = _ligne_id(lib, pct) or (_ligne_id(lib + "s", pct) if not lib.endswith("s") else None)  # « 1 Pod »
            if r is None:
                inconnus[("% " if pct else "") + lib] += 1
                continue
            a, b = int(e.get("from") or 0), int(e.get("to") or 0)
            mini, maxi = (a, b) if b >= a else (a, a)   # « to » vaut 0 pour une ligne fixe (PM 1)
            lignes.setdefault(r[0], [mini, maxi])
        if len(lignes) < LIGNES_MINI:
            continue
        nom = (it.get("name") or {}).get("fr") if isinstance(it.get("name"), dict) else it.get("name")
        objets[signature(lignes)] = {"nom": nom, "niveau": it.get("level"), "type": TYPES.get(it.get("typeId")),
                                     "lignes": lignes, "dofusdb_id": it.get("id"), "source": "dofusdb"}
    return objets, inconnus


def telecharger(get: Callable = _get_json, attente: float = 0.3, dire=print) -> dict:
    """Télécharge les objets et les descriptions de leurs effets ; renvoie le contenu du fichier à écrire."""
    items = []
    for type_id, type_nom in TYPES.items():   # un type à la fois : le filtre « $in » n'est pas sûr côté DofusDB
        params = [("typeId", type_id), ("level[$gte]", NIVEAU_MIN), ("level[$lte]", NIVEAU_MAX), ("$limit", PAGE),
                  ("lang", "fr")]
        skip, total, n0 = 0, None, len(items)
        while total is None or skip < total:
            page = get(f"{API}/items", params + [("$skip", skip)])
            total = int(page.get("total") or 0)
            donnees = [d for d in (page.get("data") or []) if d.get("typeId") in (None, type_id)]
            items += donnees
            if not page.get("data"):
                break
            skip += PAGE
            time.sleep(attente)
        dire(f"  {type_nom} : {len(items) - n0} objets")
    ids = sorted({e.get("effectId") for it in items for e in (it.get("effects") or []) if e.get("effectId") is not None})
    descriptions = {}
    for i, eid in enumerate(ids, 1):
        try:
            d = get(f"{API}/effects/{eid}", [("lang", "fr")])
            descriptions[eid] = ((d.get("description") or {}).get("fr")) or ""
        except Exception as exc:  # un effet illisible ne bloque pas les autres
            dire(f"  effet {eid} non lu : {exc}")
        if i % 10 == 0:
            dire(f"  effets : {i} / {len(ids)}")
        time.sleep(attente)
    objets, inconnus = construire(items, descriptions)
    return {"source": API, "date": time.strftime("%Y-%m-%d %H:%M"), "niveaux": [NIVEAU_MIN, NIVEAU_MAX],
            "types": list(TYPES.values()), "objets_telecharges": len(items), "objets": objets,
            "libelles_non_reconnus": dict(inconnus)}


def chemins_fichier() -> List[str]:
    """Où le chercher : le dossier journaux du logiciel (à jour sans reconstruire l'exe), puis data/."""
    from forge.chemins import chemin_data, dossier_journaux
    return [os.path.join(dossier_journaux(), FICHIER), str(chemin_data(FICHIER))]


def charger() -> Dict[str, dict]:
    for c in chemins_fichier():
        if os.path.exists(c):
            try:
                with open(c, encoding="utf-8") as f:
                    return (json.load(f) or {}).get("objets") or {}
            except Exception:
                from forge.erreurs import noter
                noter("objets_dofusdb.charger")
    return {}


def main():
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Téléchargement des objets DofusDB (tous les objets forgemageables, niveau {NIVEAU_MIN} à {NIVEAU_MAX})...")
    try:
        contenu = telecharger()
    except Exception as exc:
        print(f"\nÉchec du téléchargement : {exc}\nVérifie ta connexion internet et relance.")
        return 1
    cibles = [os.path.join(racine, "data", FICHIER)]
    exe = os.path.join(racine, "dist", "AssistantForge", "journaux")
    if os.path.isdir(os.path.dirname(exe)):
        cibles.append(os.path.join(exe, FICHIER))
    for c in cibles:
        os.makedirs(os.path.dirname(c), exist_ok=True)
        from forge.erreurs import ecrire_json   # (v165) écriture sûre : copie puis remplacement
        ecrire_json(c, contenu, ensure_ascii=False, indent=1)
    n = len(contenu["objets"])
    print(f"\n{contenu['objets_telecharges']} objets téléchargés, {n} gardés (au moins 3 lignes reconnues).")
    if contenu["libelles_non_reconnus"]:
        print("Libellés non reconnus (lignes ignorées) :")
        for lib, k in sorted(contenu["libelles_non_reconnus"].items(), key=lambda t: -t[1]):
            print(f"  {lib} : {k}")
    print("Écrit dans : " + " et ".join(cibles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
