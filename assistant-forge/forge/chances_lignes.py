"""Chances d'une passe (critique / neutre / échec) sur une ligne à maximum connu. Observation seule.

(v109) Refonte mesurée (developpement/VALIDATION_ETAPE_B.md, developpement/diagnostic/valider_chances.py), sur 7 092 passes
de 23 sessions, chaque passe notée par un modèle qui ne l'avait pas vue :

  1. Base = modèle général par case de remplissage (forge/modele_rune.py, réappris sur toutes les passes).
  2. Tables (ligne, rune, tranche de 5 %) apprises EN DIRECT sur l'OBJET EN COURS seulement, mélangées à la base
     (PRIOR passes de la base).
  3. Correction de niveau de l'objet (critiques / échecs), apprise en direct passe après passe.
  Les échecs à rune non reconnue ne sont plus jetés : ils sont répartis entre les runes possibles (rune conseillée, rune de
  la passe d'avant, rune de la passe d'après), au prorata de leur chance d'échec.

Log-loss hors échantillon (plus bas = mieux) : v108 0,993 (1,025 avec sa correction d'objet) -> v109 0,911.
Pourquoi le changement :
  * les tables par ligne de la v95 venaient de TA Ceste et étaient appliquées à tous les objets (ex. Pa Vi à 80-95 % du
    max : critiques prévus < 10 %, observés 54 % sur d'autres objets) ;
  * elles ne gardaient que les passes à rune reconnue : 10 % d'échecs vus contre 15 à 35 % en vrai (un échec est rarement
    reconnu). Le facteur x1,4 (CORR_ECHEC) ne corrigeait pas ce biais : supprimé (1,0) ;
  * (bug B1) les passes des autres objets étaient rangées avec le maximum de l'objet actuel.
Les tables de data/chances_lignes.json restent dans le fichier (compatibilité) mais ne servent plus (TABLES_BASE = False).
"""

from __future__ import annotations

from forge.fiabilite import passe_exploitable

import json
import math
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional
from forge.chemins import chemin_data
from forge.erreurs import noter as _noter_erreur

PRIOR = 8.0
CORR_ECHEC = 1.0      # (v109) était 1,4 : sans effet démontré, et ne corrigeait pas le vrai biais (voir en-tête)
CALAGE_ECHEC = 1.0
POIDS_VIDEO = 0.5
TABLES_BASE = False   # (v109) tables apprises sur d'autres objets : moins bonnes hors échantillon que le modèle général
FICHIER = chemin_data("chances_lignes.json")
_BASE: Optional[Dict[tuple, Dict[str, float]]] = None
_FIN = 0.0
# comptes (ligne, rune, tranche) de l'OBJET EN COURS, appris en direct (fractionnaires : échecs à rune inconnue répartis)
EN_DIRECT: Dict[tuple, Dict[str, float]] = defaultdict(lambda: {"SC": 0.0, "SN": 0.0, "EC": 0.0})
# marge minimale affichée : écart de calibration mesuré entre chances prédites et observées (5 points environ)
MARGE_MODELE = 0.05
_VERROU = threading.RLock()


def tranche(valeur: int, maxi: int) -> float:
    return min(int(max(0, valeur) / maxi * 20), 20) / 20


def _base():
    global _BASE, _FIN
    if _BASE is None:
        _BASE = {}
        try:
            d = json.loads(FICHIER.read_text(encoding="utf-8"))
            _FIN = float(d.get("fin_heure", 0))
            for source, poids in (("cases", 1.0), ("cases_video", POIDS_VIDEO)):
                for k, v in d.get(source, {}).items():
                    ligne, m, b = k.split("|")
                    cle = (ligne, int(m), float(b))
                    old = _BASE.get(cle, {"SC": 0.0, "SN": 0.0, "EC": 0.0})
                    _BASE[cle] = {o: old[o] + poids * float(v.get(o, 0)) for o in ("SC", "SN", "EC")}
        except Exception:
            _noter_erreur("chances_lignes._base")
            _BASE = {}
    return _BASE


def comptes(ligne: str, montant: int, valeur: int, maxi: int) -> Dict[str, float]:
    k = (ligne, int(montant), tranche(valeur, maxi))
    a = _base().get(k, {"SC": 0, "SN": 0, "EC": 0}) if TABLES_BASE else {"SC": 0, "SN": 0, "EC": 0}
    with _VERROU:
        b = EN_DIRECT.get(k, {"SC": 0, "SN": 0, "EC": 0})
        return {o: a[o] + b[o] for o in ("SC", "SN", "EC")}


# Correction PAR OBJET (v106), apprise en direct : deux décalages (critique et échec, en log-cotes face au succès neutre).
# (v109) apprise sur TOUTES les passes de l'objet (avant : seulement celles à rune reconnue, donc trop optimiste).
APPRENTISSAGE_OBJET = 0.04
OBJET_DECALAGE = {"critique": 0.0, "echec": 0.0, "n": 0}


def _decaler(ch: dict) -> dict:
    a, b = OBJET_DECALAGE["critique"], OBJET_DECALAGE["echec"]
    if a == 0.0 and b == 0.0:
        return ch
    z = {"critique": math.log(max(1e-4, ch["critique"])) + a, "succes": math.log(max(1e-4, ch["succes"])),
         "echec": math.log(max(1e-4, ch["echec"])) + b}
    m = max(z.values())
    e = {k: math.exp(v - m) for k, v in z.items()}
    t = sum(e.values())
    return {k: v / t for k, v in e.items()}


def noter_passe_objet(ch: dict, issue: str, poids: float = 1.0) -> None:
    """Met à jour les décalages de l'objet avec une passe (ch = chances prévues SANS décalage ; poids = part de la passe
    attribuée à cette rune quand la rune n'est pas sûre)."""
    with _VERROU:
        q = _decaler(ch)
        y = {"critique": issue == "SC", "echec": issue == "EC"}
        for k in ("critique", "echec"):
            OBJET_DECALAGE[k] += APPRENTISSAGE_OBJET * poids * (float(y[k]) - q[k])
        OBJET_DECALAGE["n"] += poids


def facteur_critique_objet() -> float:
    """Pour l'affichage : critiques prévus avec / sans la correction de l'objet, à remplissage moyen."""
    base = {"critique": 0.35, "succes": 0.58, "echec": 0.07}
    with _VERROU:
        return _decaler(base)["critique"] / base["critique"]


def chances(ligne: Optional[str], montant: int, valeur: int, maxi, G=None) -> dict:
    """{critique, succes, echec} : modèle général, corrigé par les passes de l'objet en cours, puis par son niveau."""
    with _VERROU:
        return _decaler(_caler(_chances_brutes(ligne, montant, valeur, maxi, G)))


def _caler(ch: dict) -> dict:
    if CALAGE_ECHEC == 1.0:
        return ch
    ec = min(0.9, ch["echec"] * CALAGE_ECHEC)
    r = (1 - ec) / max(1e-9, ch["critique"] + ch["succes"])
    return {"critique": ch["critique"] * r, "succes": ch["succes"] * r, "echec": ec}


def _chances_brutes(ligne: Optional[str], montant: int, valeur: int, maxi, G=None) -> dict:
    from forge.modele_rune import chances as general
    base = general(valeur, montant, None, maxi, G)
    if not ligne or not maxi or maxi <= 0 or montant <= 0:
        return base
    c = comptes(ligne, montant, valeur, maxi)
    sc, sn, ec = c["SC"], c["SN"], c["EC"] * CORR_ECHEC
    n = sc + sn + ec
    if n <= 0:
        return base
    tot = n + PRIOR
    return {"critique": (sc + PRIOR * base["critique"]) / tot, "succes": (sn + PRIOR * base["succes"]) / tot,
            "echec": (ec + PRIOR * base["echec"]) / tot}


def _issue(r) -> Optional[str]:
    iss = r.get("issue") or ""
    return "SC" if iss == "succès critique" else ("SN" if iss.startswith("succès") else ("EC" if iss.startswith("échec") else None))


def candidats_registre(rows, i, info_rune, etat):
    """Runes possibles de la passe rows[i] : [(ligne, montant, valeur, part)]. Rune lue -> une seule. Échec à rune non
    reconnue -> rune conseillée, rune lue juste avant, rune lue juste après (même objet), à parts égales."""
    r = rows[i]
    if not passe_exploitable(r):
        return []
    if r.get("certitude") == "lue":
        info = info_rune(r.get("rune"))
        if not info:
            return []
        v = r.get("valeur_avant")
        if v is None:
            v = etat.get(info[0])
        return [] if v is None else [(info[0], info[2], v, 1.0)]
    if r.get("certitude") != "conseillee" or _issue(r) != "EC":
        return []
    noms = [r.get("conseillee") or r.get("rune")]
    obj = r.get("objet")
    for sens in (-1, 1):
        j = i + sens
        while 0 <= j < len(rows) and abs(j - i) <= 3:
            x = rows[j]
            if passe_exploitable(x) and x.get("objet") == obj and x.get("certitude") == "lue" and not x.get("exo"):
                noms.append(x.get("rune"))
                break
            j += sens
    vus = []
    for n in noms:
        info = info_rune(n)
        if info and info[0] in etat and (info[0], info[2]) not in [(a, b) for a, b, _ in vus]:
            vus.append((info[0], info[2], etat[info[0]]))
    return [(a, b, v, 1.0 / len(vus)) for a, b, v in vus]


def charger_rows(rows, panneau) -> None:
    """(v109) Réapprend tables et niveau de l'OBJET EN COURS à partir de ses passes du registre, dans l'ordre.
    Seules les passes de cet objet comptent (bug B1 corrigé) ; échecs à rune inconnue répartis (bug B2 corrigé)."""
    from forge.optimisation import info_rune
    with _VERROU:
        EN_DIRECT.clear()
        OBJET_DECALAGE.update(critique=0.0, echec=0.0, n=0)
        try:
            from forge import planif
            planif._CACHE.clear()
        except Exception:
            _noter_erreur("chances_lignes.charger_rows")
        maxis = {l.id: l.maxi for l in getattr(panneau, "lignes", []) if getattr(l, "maxi", None)}
        rows = list(rows or [])
        objet = next((r.get("objet") for r in reversed(rows) if r.get("objet")), None)
        if objet is None:
            return
        etat: Dict[str, int] = {l.id: l.valeur for l in getattr(panneau, "lignes", [])}
        a_jour = False
        for i, r in enumerate(rows):
            if r.get("objet") != objet or r.get("exo"):
                continue
            if not passe_exploitable(r):
                a_jour = False
                continue
            if r.get("etat_avant") and r.get("q_etat") != "incoherent":   # (v112, C1)
                etat = dict(r["etat_avant"])
                a_jour = True
            if not a_jour:
                continue
            o = _issue(r)
            if o is None:
                continue
            cs = [(l, m, v, maxis[l], w) for (l, m, v, w) in candidats_registre(rows, i, info_rune, etat) if l in maxis]
            apprendre_passe(cs, o)


def apprendre_passe(cs, o: str) -> None:
    """Apprend une passe de l'objet en cours. cs = [(ligne, montant, valeur, maxi, part)] runes possibles (une seule si la
    rune est reconnue) ; o = "SC" | "SN" | "EC". Chaque rune reçoit sa part de la passe, au prorata de la chance qu'elle
    avait de donner cette issue (une rune qui rate souvent « prend » davantage l'échec)."""
    if not cs:
        return
    with _VERROU:
        cle = {"SC": "critique", "SN": "succes", "EC": "echec"}[o]
        brutes = [_chances_brutes(l, m, v, mx) for (l, m, v, mx, w) in cs]
        qs = [_decaler(b) for b in brutes]
        py = sum(c[4] * q[cle] for c, q in zip(cs, qs)) or 1e-9
        for (l, m, v, mx, w), b, q in zip(cs, brutes, qs):
            part = w * q[cle] / py
            noter_passe_objet(b, o, part)
            EN_DIRECT[(l, m, tranche(v, mx))][o] += part


def avec_incertitude(ligne: Optional[str], montant: int, valeur: int, maxi, G=None) -> dict:
    """Chances + incertitude : {critique, succes, echec, n (passes vues ici sur cet objet), marge_echec, marge_critique}.
    Marge = un écart-type (passes de l'objet + PRIOR passes du modèle général), jamais moins que l'écart de calibration
    mesuré (MARGE_MODELE) : une chance affichée n'est pas un pourcentage exact."""
    with _VERROU:
        ch = dict(chances(ligne, montant, valeur, maxi, G))
        n = 0.0
        if ligne and maxi and maxi > 0 and montant > 0:
            c = comptes(ligne, montant, valeur, maxi)
            n = c["SC"] + c["SN"] + c["EC"]
    tot = n + PRIOR
    for k in ("echec", "critique"):
        p = ch[k]
        ch["marge_" + k] = max(MARGE_MODELE, (p * (1 - p) / (tot + 1)) ** 0.5)
    ch["n"] = int(round(n))
    return ch
