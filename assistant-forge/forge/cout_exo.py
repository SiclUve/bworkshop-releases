"""(v167) Coût estimé en kamas JUSQU'À L'EXO (onglet Objectif « Coût estimé » et onglet Simuler).

Méthode (simulation, même moteur que forge/estimation.py : le conseil réel choisit chaque rune) :
  1. « premier essai » : on passe les runes conseillées jusqu'à ce que le conseil dise « tente l'exo » ;
  2. « cycle après un échec » : l'exo rate (son poids est payé par le reliquat puis par des lignes tirées au hasard,
     comme un échec ordinaire), puis on remonte jusqu'au prochain essai ; plusieurs cycles sont simulés à la suite ;
  3. le nombre d'essais suit TA chance d'exo (onglet Objectif, 1 % par défaut : environ 100 essais en moyenne) ;
     total = premier essai + chaque échec (rune exo + remontée) + la rune exo qui passe, tiré 4 000 fois.
Hypothèses (non vérifiées en jeu) : une exo ratée se comporte comme un échec ordinaire (perte du poids de la rune) ; une
exo réussie ne fait rien perdre. C'est une ESTIMATION avec une fourchette, pas une promesse.
"""

from __future__ import annotations

import dataclasses
import random
import time
from fractions import Fraction
from typing import Callable, Optional, Union

from forge.conseil import chances_passe, chances_rune_ligne, conseiller
from forge.estimation import _milliers, _perdre, environ
from forge.objectif import Objectif

TIRAGES = 4000   # nombre de totaux tirés pour la fourchette


def _nom(r) -> str:
    from forge.runes_jeu import nom_rune
    return nom_rune(r.ligne_id, r.taille) or f"{r.stat} {r.taille}"


def _monter(panneau, lignes, rel, objectif, poids, infos, rng, cap, prix, compte):
    """Passe les runes conseillées jusqu'à « exo » ou « atteint ». Renvoie (rel, conseil final ou None, statut)."""
    n0 = compte["n"]
    while compte["n"] - n0 < cap:
        p = dataclasses.replace(panneau, lignes=list(lignes.values()), reliquat=Fraction(str(round(rel, 3))))
        c = conseiller(p, objectif, poids, infos)
        if c.statut == "exo" and c.rune_exo is not None:
            return rel, c, "exo"
        if c.rune is None or c.statut in ("exo", "atteint"):
            return rel, c, c.statut or "fini"
        r = c.rune
        nom = _nom(r)
        if prix.get(nom):
            compte["kamas"] += prix[nom]
        else:
            compte["sans_prix"].add(nom)
        l = lignes.get(r.ligne_id)
        ch = chances_passe(p, poids)
        if l is None or ch is None:
            return rel, None, "inconnu"
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
            if besoin > 1e-9:
                rel += _perdre(lignes, poids, besoin, rng, l.id if gagne else None)
        compte["n"] += 1
    return rel, None, "cap"


def _rater_exo(lignes, rel, rune_exo, poids, rng) -> float:
    """Exo ratée : son poids est payé par le reliquat, puis par des lignes tirées au hasard."""
    w = float(rune_exo.poids)
    pay = min(rel, w)
    rel -= pay
    if w - pay > 1e-9:
        rel += _perdre(lignes, poids, w - pay, rng, None)
    return rel


def estimer_cout_exo(depart: Union[object, Callable], objectif: Objectif, poids, infos, prix: dict,
                     premiers: int = 12, cycles: int = 40, cap: int = 400, graine: int = 1,
                     limite_s: float = 25.0) -> Optional[dict]:
    """`depart` : le panneau actuel, ou une fonction rng -> panneau (objet neuf tiré au hasard, onglet Simuler).
    None si le panneau n'est pas exploitable ; {"sans_exo": True, ...} si le conseil ne demande jamais d'exo."""
    rng = random.Random(graine)
    t0 = time.perf_counter()
    prix = prix or {}

    def nouveau():
        return depart(rng) if callable(depart) else depart

    p0 = nouveau()
    if not p0.lignes or p0.reliquat is None or chances_passe(p0, poids) is None:
        return None
    A, etats, sans_prix, exo = [], [], set(), None
    for i in range(premiers):
        if i >= 3 and time.perf_counter() - t0 > limite_s / 2:
            break
        p = p0 if i == 0 else nouveau()
        lignes = {l.id: l for l in p.lignes}
        compte = {"n": 0, "kamas": 0, "sans_prix": set()}
        rel, c, statut = _monter(p, lignes, float(p.reliquat or 0), objectif, poids, infos, rng, cap, prix, compte)
        sans_prix |= compte["sans_prix"]
        if statut != "exo":
            A.append((compte["n"], compte["kamas"], statut))
            continue
        exo = c.rune_exo
        A.append((compte["n"], compte["kamas"], "exo"))
        etats.append((p, lignes, rel, c.rune_exo))
    if not etats:
        finis = [a for a in A if a[2] in ("atteint", "fini")]
        return {"sans_exo": True, "parties": len(A), "finies": len(finis), "cap": cap,
                "statuts": sorted({a[2] for a in A}), "sans_prix": sorted(sans_prix)}
    # cycles : exo ratée puis remontée, enchaînés à partir des états atteints
    B, bloques = [], 0
    k = 0
    while len(B) < cycles and (len(B) < 5 or time.perf_counter() - t0 < limite_s) and bloques < 3 * cycles:
        p, lignes, rel, r_exo = etats[k % len(etats)]
        lignes = dict(lignes)
        rel = _rater_exo(lignes, rel, r_exo, poids, rng)
        compte = {"n": 0, "kamas": 0, "sans_prix": set()}
        rel, c, statut = _monter(p, lignes, rel, objectif, poids, infos, rng, cap, prix, compte)
        sans_prix |= compte["sans_prix"]
        if statut == "exo":
            B.append((compte["n"], compte["kamas"]))
            etats[k % len(etats)] = (p, lignes, rel, c.rune_exo)
        else:
            bloques += 1
        k += 1
    if not B:
        return {"sans_exo": False, "bloque": True, "parties": len(A), "cap": cap, "sans_prix": sorted(sans_prix)}
    chance = objectif.chances_exo.get(exo.ligne_id, objectif.chance_exo)
    nom_exo = _nom(exo)
    px_exo = prix.get(nom_exo) or 0
    if not px_exo:
        sans_prix.add(nom_exo)
    A_ok = [a for a in A if a[2] == "exo"]
    totaux, runes, essais = [], [], []
    for _ in range(TIRAGES):
        a = rng.choice(A_ok)
        n_essais = 1
        while rng.random() >= chance and n_essais < 100000:
            n_essais += 1
        k_tot, n_tot = a[1] + px_exo * n_essais, a[0] + n_essais
        for _ in range(n_essais - 1):
            b = rng.choice(B)
            k_tot += b[1]
            n_tot += b[0]
        totaux.append(k_tot)
        runes.append(n_tot)
        essais.append(n_essais)
    totaux.sort()
    runes.sort()

    def q(v, f):
        return v[min(len(v) - 1, int(f * len(v)))]
    moy = lambda v: sum(v) / len(v)
    return {"sans_exo": False, "bloque": False, "exo": nom_exo, "chance": chance, "prix_exo": px_exo,
            "k_median": q(totaux, .5), "k_p10": q(totaux, .1), "k_p90": q(totaux, .9), "k_moyen": moy(totaux),
            "n_median": q(runes, .5), "essais_moyen": moy(essais),
            "premier_kamas": moy([a[1] for a in A_ok]), "premier_runes": moy([a[0] for a in A_ok]),
            "cycle_kamas": moy([b[1] for b in B]), "cycle_runes": moy([b[0] for b in B]),
            "premiers": len(A_ok), "cycles": len(B), "bloques": bloques, "sans_prix": sorted(sans_prix)}


def texte_cout_exo(e: Optional[dict]) -> str:
    if e is None:
        return "Coût impossible à estimer : l'objet n'est pas lu en entier ou le reliquat est inconnu."
    if e.get("sans_exo"):
        return ("Le conseil ne propose jamais de tenter l'exo sur cet objet (exo non cochée, déjà posée, ou objectif "
                f"non atteint en {e['cap']} runes). Coche l'exo voulue dans l'onglet Objectif.")
    if e.get("bloque"):
        return (f"Coût impossible à estimer : après une exo ratée, l'objet ne revient jamais à l'essai suivant en "
                f"{e['cap']} runes. L'objectif est peut-être trop haut.")
    t = (f"Coût estimé jusqu'à l'exo ({e['exo']}, {e['chance'] * 100:g} % de chance par essai, environ "
         f"{e['essais_moyen']:.0f} essais en moyenne) : environ {environ(e['k_median'])} kamas "
         f"(entre {environ(e['k_p10'])} et {environ(e['k_p90'])} dans 8 cas sur 10), environ {environ(e['n_median'])} runes.\n"
         f"Détail : environ {environ(e['premier_kamas'])} kamas pour arriver au premier essai ; puis chaque essai raté "
         f"coûte environ {environ(e['prix_exo'] + e['cycle_kamas'])} kamas ({_milliers(e['prix_exo'])} la rune d'exo + "
         f"environ {environ(e['cycle_kamas'])} pour remonter, ~{environ(e['cycle_runes'])} runes).")
    if e["sans_prix"]:
        noms = ", ".join(e["sans_prix"][:6]) + (" ..." if len(e["sans_prix"]) > 6 else "")
        t += f"\nRunes sans prix, comptées à 0 (coût sous-estimé) : {noms}."
    return t + (f"\nEstimation ({e['premiers']} montées, {e['cycles']} remontées simulées), pas une promesse ; "
                "hypothèse : une exo ratée fait perdre son poids comme un échec ordinaire.")
