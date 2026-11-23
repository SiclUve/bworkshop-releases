"""STRATÉGIE OPTIMISÉE (MODE PAR DÉFAUT). Observation seule : rien n'est fait dans le jeu.

Ne change que le CHOIX de la ligne et de la taille de rune ; la rune est construite avec les règles de sécurité du
conseil (_rune : poids, rune sûre, perte tolérable, alternative plus sûre).

Choix : parmi les lignes qui manquent, la rune qui donne le plus de poids utile par kamas selon le modèle de chances :
    score = (SC + SN) × poids utile / prix − 0,5 × EC × poids de la rune / prix
Pourquoi : sur les vraies passes, ce modèle prévoit mieux les issues que les chances affichées du conseil habituel.

Jamais au-dessus du max du jeu (ni de ton maximum réglé) ; ta cible peut être dépassée sous le max. Niveau de l'objet
inconnu ici -> pas de malus « bas niveau ». Rune sans prix connu (onglet Coûts) : ignorée.
Règles dures : jamais de rune sur une ligne négative, une ligne exo (bleue), une source de puits, une exo visée ou une
ligne ignorée ; PA / PM / PO jamais choisies ici. Exo, remise, reliquat, presque parfait : conseil habituel.
Repli sur le conseil habituel (et c'est dit) si le tableau est douteux ou si un maximum n'est pas lu.
"""

from __future__ import annotations

import math
import time
from fractions import Fraction
from typing import Optional, Tuple

PLAFOND = 101
EPS = 1e-9
EXO_QUALITE = ("pa", "pm")
EXO = ("pa", "pm", "po")
LIGNES_MINI = 3


class RuneInterdite(ValueError):
    pass


def _pp(l, poids) -> float:
    try:
        return float(poids.get(l.cle_poids) or 0)
    except Exception:
        return 0.0


def _exo(l) -> bool:
    return bool(getattr(l, "exo_lue", False))


def _charge(lignes, poids, valeurs, sauf=None) -> float:
    """Poids « over + exo » de l'objet."""
    t = 0.
    for l in lignes:
        v, w = valeurs[l.id], _pp(l, poids)
        if l.id == sauf or w <= 0 or v <= 0:
            continue
        if _exo(l):
            t += v * w
        elif l.maxi is not None:
            t += max(0, v - l.maxi) * w
    return t


def _qualite(lignes, poids, valeurs, sauf) -> float:
    num = den = 0.
    for l in lignes:
        w = _pp(l, poids)
        if l.id == sauf or _exo(l) or w <= 0 or l.maxi is None or l.maxi < 0:
            continue
        num += w * min(max(0, valeurs[l.id]), l.maxi)
        den += w * l.maxi
    return num / den if den > 0 else 0.


def _repartition(S, over):
    sc = max(2, (100 - S) / 2)
    if over:
        sn = max(5, 40 - .375 * (S - 100))
    else:
        sn = min(50, 100 - sc) if S <= 100 else 50 - .375 * (S - 100)
    sn = min(max(sn, 0), 100 - sc)
    return sc, sn, 100 - sc - sn


def chances(panneau, poids, ligne, bonus, niveau: int = 200) -> Tuple[float, float, float]:
    """(SC, SN, EC) en fraction pour une rune de `bonus` points sur une ligne de base. Lève RuneInterdite."""
    lignes = [l for l in panneau.lignes if l.cle_poids in poids]
    valeurs = {l.id: (l.valeur or 0) for l in lignes}
    o, d, wpp = valeurs[ligne.id], bonus, _pp(ligne, poids)
    mn, mx = ligne.mini, ligne.maxi
    if mx is None or wpp <= 0:
        raise RuneInterdite("maximum ou poids inconnu")
    if mn is None:
        mn = mx
    cap = max(mx, math.floor(PLAFOND / wpp + EPS))
    if o + d > cap:
        raise RuneInterdite("ligne")
    apres = dict(valeurs); apres[ligne.id] = o + d
    if _charge(lignes, poids, apres) > PLAFOND + EPS:
        raise RuneInterdite("objet")
    f = _qualite(lignes, poids, valeurs, ligne.id)
    over = o + d > mx
    if over and (o + d) * wpp + _charge(lignes, poids, valeurs, sauf=ligne.id) > PLAFOND + EPS:
        raise RuneInterdite("objet")
    fixe = mx == mn
    position = 1 if fixe else (o + d - mn) / (mx - mn)
    exo_pa = any(_exo(l) and l.id in EXO_QUALITE and valeurs[l.id] > 0 for l in lignes)
    qual = 1. if exo_pa else f
    S = 5 + 4 * wpp * d * max(0, o / d - 14) + 60 * qual ** 12
    if over:
        S += 65 + 4 * max(0, (o + d - mx) * wpp)
    elif not fixe and position >= .8 - EPS:
        S += 45
    if niveau < 170:
        S -= 20 * max(0, 1.1 - qual)
    if niveau < 100:
        S -= 15
    sc, sn, ec = _repartition(S, over)
    return sc / 100, sn / 100, ec / 100


def _plafond(l, objectif, cible) -> int:
    """Valeur à ne pas dépasser : le max du jeu (ou ta cible si elle est au-dessus : over voulu), et ton maximum
    s'il est réglé. Dépasser un peu ta cible sous le max ne coûte rien."""
    plaf = max(l.maxi, cible)
    mx = (getattr(objectif, "maximums", None) or {}).get(l.id)
    return min(plaf, mx) if mx is not None else plaf


def _rune(l, montant, panneau, poids, infos):
    """Rune construite avec les règles du conseil (poids, rune sûre, perte tolérable, alternative plus sûre)."""
    from forge import conseil as C
    info = infos[l.cle_poids]
    pp = poids[l.cle_poids]
    taille = next(t for t, m in info["runes"].items() if m == montant)
    puits = panneau.reliquat if panneau.reliquat is not None else Fraction(0)
    total = sum((Fraction(max(0, x.valeur or 0)) * poids[x.cle_poids] for x in panneau.lignes if x.cle_poids in poids),
                Fraction(0)) or Fraction(10 ** 6)
    w = montant * pp
    sure = w <= puits
    r = C.Rune(l.id, info["nom"], taille, montant, w, sure, False,
               perte_faible=(not sure and (w <= puits or C._perte_tolerable(w, puits, total))),
               malus=(l.valeur or 0) >= C.SEUIL_MALUS * montant)
    plus_legeres = sorted((t, m) for t, m in info["runes"].items() if m < montant and m * pp <= puits)
    if not sure and plus_legeres:
        t, m = max(plus_legeres, key=lambda x: x[1])
        r.plus_sure = C.Rune(l.id, info["nom"], t, m, m * pp, True, False, malus=(l.valeur or 0) >= C.SEUIL_MALUS * m)
    return r


def choisir(panneau, objectif, poids, infos, prix) -> Tuple[Optional[tuple], str]:
    """((ligne, montant, taille, (SC, SN, EC)), « ») ou (None, raison du repli)."""
    from forge.conseil import marge_ligne
    from forge.runes_jeu import nom_rune
    lignes = list(getattr(panneau, "lignes", []) or [])
    if getattr(panneau, "avertissements", None):
        return None, "tableau douteux (lecture à vérifier)"
    if len(lignes) < LIGNES_MINI:
        return None, "objet inconnu ou trop peu de lignes lues"
    ignorees = set(objectif.ignorees or [])
    for l in lignes:
        if l.id not in EXO and l.id not in ignorees and not _exo(l) and l.maxi is None:
            return None, f"maximum non lu ({l.libelle})"
    interdites = set(objectif.sacrifiables or []) | set(objectif.exo or []) | ignorees
    exo_posee = any(_exo(x) and (x.valeur or 0) > 0 for x in lignes)
    maximums = getattr(objectif, "maximums", None) or {}
    meilleur, sans_prix, manque_lignes, bloquees = None, 0, 0, []
    for l in lignes:
        if l.id in EXO or l.id in interdites or _exo(l) or not l.maxi or l.maxi <= 0 or (l.valeur or 0) < 0:
            continue
        info = (infos or {}).get(l.cle_poids)
        if not info or l.cle_poids not in poids:
            continue
        cible = (objectif.cibles or {}).get(l.id, l.maxi)
        lim = _plafond(l, objectif, cible)
        v = l.valeur or 0
        if v >= cible - marge_ligne(objectif, l.id, cible):
            continue
        manque_lignes += 1
        w = _pp(l, poids)
        if all(v + m > lim for m in info["runes"].values()):
            bloquees.append((l, v, cible, w, info))
        # Limites gardées : ton maximum s'il est réglé, la règle de surcharge « over + exo ≤ 101 » (RuneInterdite),
        # et pas d'over si une exo est déjà posée.
        lim_over = lim if (exo_posee or l.id in maximums) else float("inf")
        for taille, m in info["runes"].items():
            if v + m > lim_over:
                continue
            px = (prix or {}).get(nom_rune(l.id, taille))
            if not px:
                sans_prix += 1
                continue
            try:
                sc, sn, ec = chances(panneau, poids, l, m)
            except RuneInterdite:
                continue
            s = (sc + sn) * min(m, max(0, cible - v)) * w / px - .5 * ec * m * w / px
            if meilleur is None or s > meilleur[0]:
                meilleur = (s, (l, m, taille, (sc, sn, ec), max(0, v + m - l.maxi)))
    if meilleur:
        return meilleur[1], (f"{sans_prix} rune(s) sans prix ignorée(s) : remplis l'onglet Coûts" if sans_prix else "")
    # OVER DE DERNIER RECOURS : si une ligne manque encore mais même sa plus petite rune dépasse le max du jeu.
    if not exo_posee:
        for l, v, cible, w, info in bloquees:
            if l.id in maximums or cible > l.maxi:
                continue
            taille, m = min(info["runes"].items(), key=lambda x: x[1])
            px = (prix or {}).get(nom_rune(l.id, taille))
            if not px:
                sans_prix += 1
                continue
            try:
                sc, sn, ec = chances(panneau, poids, l, m)
            except RuneInterdite:
                continue
            s = (sc + sn) * min(m, max(0, cible - v)) * w / px - .5 * ec * m * w / px
            if meilleur is None or s > meilleur[0]:
                meilleur = (s, (l, m, taille, (sc, sn, ec), v + m - l.maxi))
        if meilleur:
            return meilleur[1], (f"{sans_prix} rune(s) sans prix ignorée(s) : remplis l'onglet Coûts" if sans_prix else "")
    if sans_prix:
        return None, "prix des runes inconnus (remplis l'onglet Coûts)"
    if not manque_lignes:
        return None, "ta cible est atteinte"
    return None, "aucune rune ne rentre sous le maximum"


def appliquer(c, panneau, objectif, poids, infos, prix):
    """Remplace la rune affichée par la rune choisie selon le modèle optimisé."""
    t0 = time.perf_counter()
    if getattr(c, "rune_conseil", None) is None:
        c.rune_conseil = c.rune
    base = c.rune_conseil
    fini_par_le_conseil = c.statut == "atteint" or (c.statut == "en_cours" and base is None)
    if c.phase or not (c.statut == "en_cours" or fini_par_le_conseil):
        choix, raison = None, "exo, reliquat ou remise : géré par le conseil habituel"
    else:
        choix, raison = choisir(panneau, objectif, poids, infos, prix)
    if choix is None:
        c.rune = base
        c.strategie = "repli_optimise"
        c.note_strategie = f"Conseil optimisé : {raison} -> conseil habituel affiché."
        c.avertissements.append(c.note_strategie)
    else:
        l, m, _taille, (sc, sn, ec) = choix[:4]
        over = choix[4] if len(choix) > 4 else 0
        meme = base is not None and (base.ligne_id, base.montant) == (l.id, m)
        r = base if meme else _rune(l, m, panneau, poids, infos)
        c.rune_optimisee = c.rune = r
        c.strategie = "optimisee"
        if fini_par_le_conseil:
            c.statut = "en_cours"
        c.note_strategie = ("Conseil optimisé : meilleure chance par kamas selon le modèle de réussite "
                            f"(SC {sc:.0%}, SN {sn:.0%}, EC {ec:.0%} ; estimation, pas une valeur exacte). "
                            + ("Même rune que le conseil habituel." if meme else
                               f"Conseil habituel : {base.nom}." if base is not None else
                               f"Le conseil habituel s'arrêtait ici ; {l.libelle} est encore sous ta cible."))
        if raison:
            c.note_strategie += f" Attention : {raison}."
        if over:
            c.note_strategie += (f" OVER : {l.libelle} passera {over} au-dessus du max du jeu si la rune réussit "
                                 "(un over se perd en premier lors d'un échec).")
        c.raison = c.note_strategie
    c.temps_strategie = time.perf_counter() - t0
    return c
