"""Mise en forme des résultats pour l'affichage (console et fenêtre). Aucune dépendance graphique."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from forge.conseil import Conseil, g
from forge.runes_jeu import chemin_icone, nom_rune


def _carte_rune(r, **plus) -> Dict:
    nom = nom_rune(r.ligne_id, r.taille, r.nom_special)
    return {"nom": nom, "montant": r.montant, "stat": r.stat, "poids": g(r.poids),
            "icone": str(chemin_icone(nom) or ""), **plus}


def vue_carte(c: Conseil, plan=None) -> Dict:
    """Ce que le joueur regarde pendant la forge : la rune à passer (icône, nom, poids) et la suite du plan."""
    if c.statut == "exo" and c.rune_exo is not None:
        etat = "Tente l'exo"
        sures = (c.exo_plan or {}).get("sures", 0)
        rune = _carte_rune(c.rune_exo, essais=sures)
    elif c.rune is not None:
        if c.phase == "remise":
            etat = "Remets la ligne"
        elif c.phase == "tampon":
            etat = "Monte la ligne tampon"
        elif c.rune.sure:
            etat = "Prochaine rune"
        elif c.rune.perte_faible:
            etat = "Prochaine rune · léger risque"
        else:
            etat = "Pas de rune sûre · la moins risquée"
        rune = _carte_rune(c.rune, essais=None)
    else:
        etat = "Objectif atteint" if c.statut == "atteint" else "Pas de conseil"
        rune = None
    suite = []
    besoin = None
    if plan:
        for r in (plan["runes"][1:] if c.rune is not None and c.statut != "exo" and plan["runes"] else plan["runes"]):
            nom = nom_rune(r.ligne_id, r.taille, r.nom_special)
            if suite and suite[-1]["nom"] == nom:
                suite[-1]["fois"] += 1
            else:
                suite.append({"nom": nom, "montant": r.montant, "poids": g(r.poids),
                              "icone": str(chemin_icone(nom) or ""), "fois": 1, "exo": False})
        if plan.get("exo") is not None and c.statut != "exo":
            e = plan["exo"]
            nom = nom_rune(e.ligne_id, e.taille, e.nom_special)
            suite.append({"nom": nom, "montant": e.montant, "poids": g(e.poids),
                          "icone": str(chemin_icone(nom) or ""), "fois": 1, "exo": True})
        if plan.get("besoin") is not None and plan["besoin"] > 0:
            besoin = g(plan["besoin"])
    return {"etat": etat, "rune": rune, "suite": suite, "besoin": besoin}


def _exo_court(c: Conseil) -> List[str]:
    """Une ligne par exo : pas de probabilités dans l'onglet Suivi (le détail reste dans c.exo)."""
    court = [t for t in c.exo if "obtenue" in t]
    if c.exo_plan is not None:
        p = c.exo_plan
        court.append(f"Exo {p['nom']} : {p['sures']} tentative(s) sûre(s) avec le reliquat actuel.")
    return court


def vue_conseil(c: Conseil, plan=None) -> Dict:
    """Textes et couleur à afficher : titre, détail, tableau des lignes."""
    if c.statut == "exo":
        titre, couleur = "Presque parfait atteint : tu peux tenter l'exo", "bleu"
        if c.rune_exo is not None:
            exo_plan = c.exo_plan or {}
            titre = f"Tente l'exo : {c.rune_exo.nom}"
            if exo_plan.get("sures"):
                titre += f" ({exo_plan['sures']} tentative(s) sûre(s))"
    elif c.statut == "atteint":
        titre, couleur = "Objectif atteint (presque parfait)", "bleu"
    elif c.rune is not None and c.rune.sure:
        titre, couleur = f"Prochaine rune : {c.rune.nom}", "vert"
    elif c.rune is not None and c.rune.perte_faible:
        titre, couleur = f"Prochaine rune : {c.rune.nom} (reliquat juste : perte possible tolérable)", "vert"
    elif c.rune is not None:
        titre, couleur = f"Pas de rune sûre (la moins risquée : {c.rune.nom})", "orange"
    else:
        titre, couleur = "Pas de conseil", "gris"
    if getattr(c, "strategie", "conseil") == "optimisee":
        titre += " — conseil optimisé"
    elif getattr(c, "strategie", "conseil") == "repli_optimise":
        titre += " — conseil habituel (cas particulier)"
    lignes: List[Tuple[str, str, str, str]] = []
    for lo in c.lignes:
        if lo.role == "source":
            etat = "source de puits"
        elif lo.role == "ignoree":
            etat = "ignorée"
        elif lo.role == "sans_cible" and lo.mini is None and lo.maxi is None:
            etat = "sans cible"  # ni Min ni Max lus : on ne sait rien de plus (ce n'est PAS une exo : seules celles cochées à l'Objectif le sont)
        elif lo.role == "sans_cible":
            etat = "cible ?"
        elif lo.role == "exo":
            etat = "exo visée"
        else:
            etat = ("OK" if not (lo.cible and lo.valeur < lo.cible) else f"OK (−{lo.cible - lo.valeur})") if lo.ok else f"manque {lo.manque}"
        if lo.hors_vue:
            etat += " (hors vue)"
        lignes.append((lo.libelle, str(lo.valeur),
                       "-" if lo.cible is None or lo.role not in ("obligatoire",) else str(lo.cible), etat))
    details = [{"id": lo.id, "mini": lo.mini, "maxi": lo.maxi, "hors_vue": lo.hors_vue, "role": lo.role}
               for lo in c.lignes]
    return {"titre": titre, "couleur": couleur, "detail": c.raison, "lignes": lignes, "details": details,
            "rune_courte": (c.rune.court if c.rune is not None else
                            (c.rune_exo.court if c.statut == "exo" and c.rune_exo is not None else "")),
            "avertissements": list(c.avertissements), "exo": list(c.exo), "exo_court": _exo_court(c), "carte": vue_carte(c, plan),
            "prochain": ({"id": c.rune.ligne_id, "montant": c.rune.montant}
                         if c.rune is not None and c.statut != "exo" else None)}


def texte_bilan(b: dict) -> str:
    e = b["ecart"]
    if b.get("ecrase"):
        return (f"poids objet {g(b['delta_poids'])}, reliquat {g(b['delta_reliquat'])} -> objet écrasé "
                "(rune trop lourde pour le puits : toutes les lignes sont tombées à 0), bilan non calculable")
    if e == 0:
        verdict = "cohérent : toutes les runes ont donné quelque chose"
    elif e < 0:
        verdict = f"runes sans effet, poids {g(-e)} au total"
    else:
        verdict = (f"succès critique probable : une rune de poids {g(e)} a donné son gain sans toucher au reliquat "
                   "(c'est la définition du succès critique dans les guides tofus.fr et jeuxonline : "
                   "« la ligne gagne le bonus, le reliquat ne change pas »)")
    if b["plancher"]:
        verdict += " (reliquat à 0 : peut être faussé)"
    if b.get("hors_vue") and e != 0:
        verdict += (f" ATTENTION : {b['hors_vue']} ligne(s) hors vue : une rune a pu tomber sur l'une d'elles, "
                    "bilan peu fiable")
    return (f"poids objet {g(b['delta_poids'])}, reliquat {g(b['delta_reliquat'])} -> {verdict}")


def lignes_runes(entrees) -> List[str]:
    """Une ligne par rune lue dans l'historique du jeu (la plus ancienne d'abord)."""
    return [f"Rune : {e.resume()}" for e in entrees or []]


def ligne_journal(ev) -> str:
    """Une ligne lisible pour l'historique de la fenêtre."""
    h = datetime.fromtimestamp(ev.heure).strftime("%H:%M:%S")
    d = ev.difference
    if d is None:
        return f"{h}  {ev.message}"
    morceaux = [f"{nom} {a}->{b}" for nom, a, b in d.changements]
    if d.reliquat is not None:
        morceaux.append(f"reliquat {g(d.reliquat[0])}->{g(d.reliquat[1])}")
    txt = f"{h}  " + (", ".join(morceaux) if morceaux else "changement")
    if d.bilan is not None:
        txt += "\n          " + texte_bilan(d.bilan)
    return txt
