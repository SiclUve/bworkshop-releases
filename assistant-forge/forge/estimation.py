"""Estimation de la suite par simulation (Monte-Carlo) : combien de runes, combien d'échecs, quelle chance de finir.

Le programme rejoue le conseil sur une copie de l'objet : à chaque passe il tire succès critique / succès / échec avec
les chances de `chances_ligne`, applique la loi du puits vérifiée (reliquat = max(0, reliquat − poids + poids perdu)),
et fait perdre le poids manquant à des lignes tirées au hasard, avec les chances relatives mesurées (v109 : ligne au-dessus
de son max touchée bien plus souvent, PA/PM/PO de base rarement, ligne lourde un peu moins). C'est une ESTIMATION, pas une promesse.
"""

from __future__ import annotations

import dataclasses
import math
import random
from fractions import Fraction
from typing import Dict, Optional

from forge.conseil import chances_passe, chances_rune_ligne, conseiller
from forge.objectif import Objectif

# Chances RELATIVES d'être touchée par une perte (1 = ligne ordinaire). (v109) mesurées sur 1 928 pertes à manque connu
# (tes sessions + vidéos, developpement/diagnostic/valider_pertes.py) :
POIDS_LIGNE_LOURDE = 0.75  # un point pèse plus que le manque : x0,70 (tes passes) / x0,81 (vidéos) ; était 0,45 (v102)
POIDS_LIGNE_OVER = 4.5     # ligne AU-DESSUS de son maximum : x5,2 (n = 37) / x4,4 (n = 297) ; ignoré avant la v109
POIDS_LIGNE_BASE = 0.15    # PA / PM / PO de base (maximum 1) : x0,13 (n = 545) ; ignoré avant la v109
PART_PERTE_COMPLETE = 0.1  # part des tirages où une seule ligne absorbe tout le manque (mesure sur les pertes réelles)


def _poids_tirage(k, l, poids, manque) -> float:
    mx = getattr(l, "maxi", None)
    if mx is not None and mx > 0 and l.valeur > mx:
        return POIDS_LIGNE_OVER
    if mx == 1 and k in ("pa", "pm", "po"):
        return POIDS_LIGNE_BASE
    return 1.0 if float(poids[l.cle_poids]) <= manque + 1e-9 else POIDS_LIGNE_LOURDE


def _perdre(lignes: dict, poids: Dict[str, Fraction], manque: float, rng, exclu: Optional[str]):
    """Retire `manque` de poids à des lignes tirées au hasard ; renvoie le surplus rendu en reliquat."""
    g = 0
    while manque > 1e-9 and g < 30:
        g += 1
        cand = [k for k, l in lignes.items() if l.valeur > 0 and k != exclu and l.cle_poids in poids] or \
               [k for k, l in lignes.items() if l.valeur > 0 and l.cle_poids in poids]
        if not cand:
            break
        # (v102) vu sur ~700 pertes (vidéo) : une ligne dont UN point pèse plus que ce qu'il reste à payer est touchée
        # environ 2 fois moins souvent (Critique 10 % contre 30 % pour les autres lignes)
        pds = [_poids_tirage(x, lignes[x], poids, manque) for x in cand]
        k = rng.choices(cand, weights=pds)[0]
        pp = float(poids[lignes[k].cle_poids])
        pts = math.ceil(manque / pp - 1e-9) if rng.random() < PART_PERTE_COMPLETE else max(1, math.ceil(rng.random() * manque / pp))
        pts = min(pts, lignes[k].valeur)
        lignes[k] = dataclasses.replace(lignes[k], valeur=lignes[k].valeur - pts)
        manque -= pts * pp
    return -manque if manque < 0 else 0.0


def _une_partie(panneau, objectif: Objectif, poids, infos, rng, cap: int, prix: Optional[dict] = None):
    lignes = {l.id: l for l in panneau.lignes}
    rel = float(panneau.reliquat or 0)
    n = fails = 0
    kamas, sans_prix = 0, set()   # (v166) coût en kamas des runes passées (prix de l'onglet Coûts)
    while n < cap:
        p = dataclasses.replace(panneau, lignes=list(lignes.values()), reliquat=Fraction(str(round(rel, 3))))
        c = conseiller(p, objectif, poids, infos)
        if c.rune is None or c.statut in ("exo", "atteint"):
            return {"fini": True, "n": n, "echecs": fails, "statut": c.statut, "kamas": kamas, "sans_prix": sans_prix}
        r = c.rune
        if prix is not None:
            from forge.runes_jeu import nom_rune
            nom = nom_rune(r.ligne_id, r.taille)
            if prix.get(nom):
                kamas += prix[nom]
            else:
                sans_prix.add(nom or f"{r.stat} {r.taille}")
        l = lignes.get(r.ligne_id)
        ch = chances_passe(p, poids)
        if l is None or ch is None:
            return {"fini": False, "n": n, "echecs": fails, "statut": "inconnu"}
        ch = chances_rune_ligne(p, poids, l, r.montant, ch)
        x = rng.random()
        w = float(r.poids)
        if x < ch["critique"]:
            lignes[l.id] = dataclasses.replace(l, valeur=l.valeur + r.montant)
        else:
            pay = min(rel, w)
            rel -= pay
            besoin = w - pay
            gagne = x < ch["critique"] + ch["succes"]
            if gagne:
                lignes[l.id] = dataclasses.replace(l, valeur=l.valeur + r.montant)
            else:
                fails += 1
            if besoin > 1e-9:
                rel += _perdre(lignes, poids, besoin, rng, l.id if gagne else None)
        n += 1
    return {"fini": False, "n": n, "echecs": fails, "statut": "cap", "kamas": kamas, "sans_prix": sans_prix}


def estimer(panneau, objectif: Objectif, poids, infos, parties: int = 40, cap: int = 150, graine: int = 1) -> Optional[dict]:
    """Résumé de `parties` parties simulées à partir de l'état actuel (None si le panneau n'est pas exploitable)."""
    if not panneau.lignes or panneau.reliquat is None or chances_passe(panneau, poids) is None:
        return None
    rng = random.Random(graine)
    res = [_une_partie(panneau, objectif, poids, infos, rng, cap) for _ in range(parties)]
    ns = sorted(r["n"] for r in res)
    fin = [r for r in res if r["fini"]]

    def q(f):
        return ns[min(len(ns) - 1, int(f * len(ns)))]

    return {"parties": parties, "finies": len(fin), "median": q(0.5), "p10": q(0.1), "p90": q(0.9), "echecs_moy": sum(r["echecs"] for r in res) / parties,
            "dans_20": sum(1 for r in fin if r["n"] <= 20) / parties, "dans_50": sum(1 for r in fin if r["n"] <= 50) / parties,
            "dans_100": sum(1 for r in fin if r["n"] <= 100) / parties, "cap": cap}


def texte_estimation(e: Optional[dict]) -> str:
    if e is None:
        return "Estimation impossible : l'objet n'est pas lu en entier ou le reliquat est inconnu."
    t = (f"Estimation sur {e['parties']} parties simulées : il reste en général {e['median']} runes "
         f"(1 fois sur 10 moins de {e['p10']}, 1 fois sur 10 plus de {e['p90']}), avec environ {e['echecs_moy']:.0f} échecs. "
         f"Chance de finir en 20 runes : {e['dans_20'] * 100:.0f} %, en 50 : {e['dans_50'] * 100:.0f} %, en 100 : {e['dans_100'] * 100:.0f} %.")
    if e["finies"] < e["parties"]:
        t += f" {e['parties'] - e['finies']} parties n'ont pas fini en {e['cap']} runes."
    return t + " C'est une estimation : les chances de chaque passe sont mesurées sur tes captures, pas fournies par le jeu."


def _milliers(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", " ")


def environ(x: float) -> str:
    """(v168c) Nombre ESTIMÉ affiché arrondi, pour ne pas faire croire à un chiffre exact (règle 5) :
    5 169 239 -> « 5,2 M » ; 123 400 000 -> « 123 M » ; 92 383 -> « 92 000 » ; 1 612 -> « 1 600 » ; 22 -> « 22 »."""
    x = float(x or 0)
    if abs(x) >= 1e6:
        m = x / 1e6
        return (f"{m:.0f}" if abs(m) >= 100 else f"{m:.1f}".replace(".", ",").replace(",0", "")) + " M"
    if abs(x) < 100:
        return str(int(round(x)))
    from math import floor, log10
    pas = 10 ** (floor(log10(abs(x))) - 1)   # 2 chiffres significatifs
    return _milliers(round(x / pas) * pas)


def estimer_cout(panneau, objectif: Objectif, poids, infos, prix: dict, parties: int = 30, cap: int = 400,
                 graine: int = 1, limite_s: float = 25.0) -> Optional[dict]:
    """(v166) Coût en kamas pour finir l'objectif, par simulation de parties (même moteur que `estimer`).
    S'arrête après `limite_s` secondes avec les parties déjà jouées (au moins 5)."""
    import time
    if not panneau.lignes or panneau.reliquat is None or chances_passe(panneau, poids) is None:
        return None
    rng = random.Random(graine)
    t0, res = time.perf_counter(), []
    while len(res) < parties and (len(res) < 5 or time.perf_counter() - t0 < limite_s):
        res.append(_une_partie(panneau, objectif, poids, infos, rng, cap, prix=prix))
    fin = [r for r in res if r["fini"]]
    ks = sorted(r["kamas"] for r in fin) or [0]
    ns = sorted(r["n"] for r in fin) or [0]

    def q(v, f):
        return v[min(len(v) - 1, int(f * len(v)))]
    sans = set().union(*(r["sans_prix"] for r in res)) if res else set()
    passes = sum(r["n"] for r in fin)
    return {"parties": len(res), "finies": len(fin), "cap": cap, "k_median": q(ks, .5), "k_p10": q(ks, .1),
            "k_p90": q(ks, .9), "n_median": q(ns, .5), "par_passe": (sum(ks) / passes) if passes else 0,
            "sans_prix": sorted(sans)}


def texte_cout(panneau, objectif: Objectif, poids, infos, prix: dict) -> str:
    e = estimer_cout(panneau, objectif, poids, infos, prix)
    if e is None:
        return "Coût impossible à estimer : l'objet n'est pas lu en entier ou le reliquat est inconnu."
    if not e["finies"]:
        return (f"Coût impossible à estimer : aucune des {e['parties']} parties simulées n'a atteint ton objectif en "
                f"{e['cap']} runes. L'objectif est peut-être trop haut.")
    t = (f"Coût estimé pour finir : environ {environ(e['k_median'])} kamas "
         f"(entre {environ(e['k_p10'])} et {environ(e['k_p90'])} dans 8 cas sur 10), "
         f"environ {environ(e['n_median'])} runes, environ {environ(e['par_passe'])} kamas par rune en moyenne.")
    if e["finies"] < e["parties"]:
        t += f" Attention : {e['parties'] - e['finies']} parties sur {e['parties']} n'ont pas fini en {e['cap']} runes."
    if e["sans_prix"]:
        noms = ", ".join(e["sans_prix"][:6]) + (" ..." if len(e["sans_prix"]) > 6 else "")
        t += f" Runes sans prix, comptées à 0 (coût sous-estimé) : {noms}."
    return t + f" Estimation sur {e['parties']} parties simulées, pas une promesse."


def texte_comparaison(panneau, objectif: Objectif, poids, infos, parties: int = 40) -> str:
    """Estimation pour l'objectif actuel, puis pour le même objectif avec 1 point de marge de plus sur chaque ligne."""
    e1 = estimer(panneau, objectif, poids, infos, parties=parties)
    if e1 is None:
        return texte_estimation(None)
    souple = dataclasses.replace(objectif, marge=objectif.marge + 1)
    e2 = estimer(panneau, souple, poids, infos, parties=parties, graine=2)
    t = texte_estimation(e1)
    if e2 is not None:
        t += (f"\n\nSi tu acceptes 1 point de moins sur chaque ligne (marge {souple.marge} au lieu de {objectif.marge}) : "
              f"{e2['median']} runes au milieu (1 fois sur 10 plus de {e2['p90']}), chance de finir en 50 runes "
              f"{e2['dans_50'] * 100:.0f} % au lieu de {e1['dans_50'] * 100:.0f} %.")
    return t
