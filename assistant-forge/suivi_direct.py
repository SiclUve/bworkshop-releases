"""Étape 3 : suit la forgemagie en continu en regardant l'écran.

OBSERVATION SEULE : ce programme ne clique pas, n'envoie aucune touche et n'agit jamais
dans DOFUS. Tu passes les runes toi-même ; il détecte ce qui change et l'affiche.

Utilisations :
    python suivi_direct.py --lister-fenetres          (trouver le titre de la fenêtre DOFUS)
    python suivi_direct.py --fenetre dofus            (suivre la fenêtre dont le titre contient « dofus »)
    python suivi_direct.py --region 0 0 1920 1080     (suivre un rectangle fixe de l'écran)
    python suivi_direct.py --dossier captures         (rejouer des images : test sans le jeu)
Arrêt : touche Ctrl+C dans la fenêtre noire.
"""

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime

from forge.capture import FinDuFlux, SourceFenetre, SourceFichiers, SourceRegion, lister_fenetres
from forge.engine import charger_poids
from forge.lecture import poids_objet
from forge.conseil import conseiller
from forge.envoi import archiver_journaux
from forge.journal import ajouter_ligne
from forge.objectif import FICHIER as FICHIER_OBJECTIF, charger_objectif, sauver_objectif
from forge.vue import lignes_runes, texte_bilan, vue_conseil
from forge.suivi import Suivi

from forge.chemins import dossier_journaux

JOURNAL = os.path.join(dossier_journaux(), "journal_session.jsonl")
JOURNAL_DOUTES = os.path.join(dossier_journaux(), "journal_douteux.txt")
JOURNAL_INFOBULLES = os.path.join(dossier_journaux(), "journal_infobulles.txt")
DOSSIER_DOUTES = os.path.join(dossier_journaux(), "images_douteuses")


def g(x):
    return f"{float(x):g}"


def _instantane(panneau):
    return {l.id: {"libelle": l.libelle, "valeur": l.valeur, "min": l.mini, "max": l.maxi, "modif": l.modif}
            for l in panneau.lignes}


def afficher(ev, poids, objectif=None):
    h = datetime.fromtimestamp(ev.heure).strftime("%H:%M:%S")
    print(f"[{h}] {ev.message}")
    if ev.type in ("premiere_lecture", "nouvel_objet"):
        for l in ev.panneau.lignes:
            print(f"      {l.libelle:<22}{l.valeur}{'%' if l.pct else ''}")
    if ev.difference is not None:
        for nom, a, b in ev.difference.changements:
            print(f"      {nom:<22}{a} -> {b}  ({b - a:+d})")
        for nom in ev.difference.apparues:
            print(f"      {nom:<22}ligne apparue")
        for nom in ev.difference.disparues:
            print(f"      {nom:<22}ligne DISPARUE")
        if ev.difference.reliquat is not None:
            a, b = ev.difference.reliquat
            print(f"      {'Reliquat (puits)':<22}{g(a)} -> {g(b)}  ({g(b - a)})")
    b = ev.difference.bilan if ev.difference is not None else None
    if b is not None:
        print("      Bilan du puits : " + texte_bilan(b))
    if ev.difference is not None and ev.difference.entrees:
        for ligne in lignes_runes(ev.difference.entrees):
            print("      " + ligne)
    elif ev.difference is not None and ev.difference.historique:
        print("      Nouvelles lignes de l'historique (la plus récente en bas) :")
        for ligne in ev.difference.historique:
            print(f"        {ligne}")
    elif ev.difference is not None:
        print("      Historique : nouvelles lignes non déterminées (voir journal)")
    if ev.panneau is not None and ev.type in ("premiere_lecture", "nouvel_objet", "changement", "stabilise"):
        actuel, maxi = poids_objet(ev.panneau, poids)
        print(f"      Poids de l'objet : {g(actuel)}" + (f" sur {g(maxi)}" if maxi is not None else ""))
        if ev.panneau.reliquat is not None:
            print(f"      Reliquat (puits) : {g(ev.panneau.reliquat)}")
        else:
            print("      Reliquat (puits) : non lu")
        if objectif is not None and ev.type == "stabilise":
            v = vue_conseil(conseiller(ev.panneau, objectif, poids))
            print(f"      >>> {v['titre']}")
            if v["detail"]:
                print(f"          {v['detail']}")
            for t in v["exo"]:
                print(f"          {t}")
            for a in v["avertissements"]:
                print(f"          (!) {a}")


def _sauver_image(ev, prefixe):
    """Garde une image de la zone lue : permet de voir pourquoi une lecture a échoué."""
    if getattr(ev, "zone", None) is None:
        return
    import cv2
    os.makedirs(DOSSIER_DOUTES, exist_ok=True)
    cv2.imwrite(os.path.join(DOSSIER_DOUTES, f"{prefixe}_{datetime.fromtimestamp(ev.heure):%H%M%S}.png"),
                ev.zone)


_ajouter_ligne = ajouter_ligne  # nom conservé (tests)


def journaliser(ev):
    os.makedirs(dossier_journaux(), exist_ok=True)
    if ev.type == "infobulle":
        with open(JOURNAL_INFOBULLES, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.fromtimestamp(ev.heure):%H:%M:%S}\n{ev.texte}\n\n")
        _sauver_image(ev, "infobulle")
        return
    if ev.type == "reliquat_instable":
        with open(JOURNAL_DOUTES, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.fromtimestamp(ev.heure):%H:%M:%S} {ev.message}\n\n")
        return
    if ev.type == "forgemagie_impossible":
        _sauver_image(ev, "impossible")
        with open(JOURNAL_DOUTES, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.fromtimestamp(ev.heure):%H:%M:%S} {ev.message}\n{ev.texte}\n\n")
        return
    if ev.type == "lecture_douteuse":
        _sauver_image(ev, "douteux")
        with open(JOURNAL_DOUTES, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.fromtimestamp(ev.heure):%H:%M:%S} {ev.message}\n{ev.texte}\n\n")
        return
    if ev.type not in ("premiere_lecture", "nouvel_objet", "changement", "stabilise", "historique"):
        return
    ligne = {"heure": ev.heure, "type": ev.type, "lignes": _instantane(ev.panneau),
             "reliquat": float(ev.panneau.reliquat) if ev.panneau.reliquat is not None else None,
             "historique": ev.panneau.historique, "texte_brut": ev.texte, "chrono": ev.chrono}
    if ev.difference is not None:
        ligne["changements"] = [{"ligne": n, "avant": a, "apres": b} for n, a, b in ev.difference.changements]
        ligne["apparues"], ligne["disparues"] = ev.difference.apparues, ev.difference.disparues
        ligne["historique_nouveau"] = ev.difference.historique
        if ev.difference.entrees is not None:
            # (v133) la rune identifiée par l'icône et la façon dont la passe a été découpée sont gardées ici aussi
            ligne["runes_historique"] = [{"effets": [[e.libelle, e.valeur] for e in r.effets], "reliquat": r.reliquat,
                                          "issue": r.issue, "brut": r.brut, "rune": getattr(r, "rune", None),
                                          "par_texte": bool(getattr(r, "par_texte", False))} for r in ev.difference.entrees]
        if ev.difference.bilan is not None:
            ligne["bilan_puits"] = {k: (float(v) if not isinstance(v, bool) else v)
                                    for k, v in ev.difference.bilan.items()}
        if ev.difference.reliquat is not None:
            ligne["reliquat_avant_apres"] = [float(x) for x in ev.difference.reliquat]
    _ajouter_ligne(JOURNAL, json.dumps(ligne, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Suivi de la forgemagie par lecture d'écran (aucune action en jeu).")
    ap.add_argument("--lister-fenetres", action="store_true")
    ap.add_argument("--fenetre", metavar="TITRE", nargs="?", const="auto")
    ap.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "LARGEUR", "HAUTEUR"))
    ap.add_argument("--dossier", metavar="CHEMIN")
    ap.add_argument("--intervalle", type=float, default=0.15, help="secondes entre deux images (défaut 0.15)")
    ap.add_argument("--attente-rapide", type=float, default=0.12,
                    help="secondes sans changement quand le reliquat a déjà changé")
    ap.add_argument("--attente", type=float, default=0.5,
                    help="secondes sans changement avant de calculer le bilan et le conseil (défaut 0.5)")
    a = ap.parse_args()
    global FICHIER_OBJECTIF
    try:
        from forge.securite_construction import proteger_session
        from forge.chemins import preparer_reglages
        proteger_session()
        FICHIER_OBJECTIF = preparer_reglages()["objectif.json"]
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Démarrage suspendu : {exc}")
        return 1

    if a.lister_fenetres:
        for _h, titre in lister_fenetres():
            print(titre)
        return 0
    if a.dossier:
        chemins = sorted(glob.glob(os.path.join(a.dossier, "*.png")))
        if not chemins:
            print(f"Aucune image .png dans {a.dossier}")
            return 1
        source = SourceFichiers(chemins)
    elif a.region:
        source = SourceRegion(*a.region)
    elif a.fenetre is not None:
        source = SourceFenetre(a.fenetre)
        print(f"Fenêtre suivie : {source.titre_trouve}")
    else:
        ap.print_help()
        return 2

    rangement = archiver_journaux(dossier_journaux())
    if rangement:
        print(f"Journaux de la session précédente rangés dans : {rangement}")
    poids = charger_poids()
    objectif = charger_objectif(FICHIER_OBJECTIF)
    if not os.path.exists(FICHIER_OBJECTIF):
        sauver_objectif(objectif, FICHIER_OBJECTIF)  # crée le fichier avec les valeurs par défaut
    print(f"Objectif : marge {objectif.marge}, sources de puits {', '.join(objectif.sacrifiables) or 'aucune'} "
          f"({FICHIER_OBJECTIF})")
    suivi = Suivi(poids=poids, attente=a.attente, attente_rapide=a.attente_rapide)
    print("Suivi en cours (Ctrl+C pour arrêter). Aucune action n'est faite dans le jeu.")
    try:
        while True:
            try:
                image = source.lire()
            except FinDuFlux:
                break
            if image is not None:
                for ev in suivi.traiter(image):
                    afficher(ev, poids, objectif)
                    journaliser(ev)
            time.sleep(a.intervalle if not a.dossier else 0)
    except KeyboardInterrupt:
        print("\nArrêté.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
