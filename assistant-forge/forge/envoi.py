"""Gestion des journaux de session : rangement automatique et préparation d'un seul fichier à envoyer.

Aucun contenu n'est envoyé nulle part : `preparer_envoi` crée un zip local que tu transmets toi-même.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from datetime import datetime
from typing import List, Optional, Tuple

JOURNAUX = ("journal_session.jsonl", "journal_douteux.txt", "journal_infobulles.txt")
DOSSIER_IMAGES = "images_douteuses"
DOSSIER_ARCHIVES = "archives"
FICHIER_ENVOI = "a_envoyer.zip"


def archiver_journaux(dossier: str = ".") -> Optional[str]:
    """Range les journaux d'une session précédente dans archives/<date_heure>/ pour repartir à zéro.

    Renvoie le dossier d'archive, ou None s'il n'y avait rien à ranger. Rien n'est supprimé.
    """
    a_ranger = [n for n in JOURNAUX if os.path.isfile(os.path.join(dossier, n))]
    images = os.path.isdir(os.path.join(dossier, DOSSIER_IMAGES))
    if not a_ranger and not images:
        return None
    cible = os.path.join(dossier, DOSSIER_ARCHIVES, datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(cible, exist_ok=True)
    for n in a_ranger:
        shutil.move(os.path.join(dossier, n), os.path.join(cible, n))
    if images:
        shutil.move(os.path.join(dossier, DOSSIER_IMAGES), os.path.join(cible, DOSSIER_IMAGES))
    return cible


def preparer_envoi(dossier: str = ".", max_images: int = 30, racine: Optional[str] = None) -> Tuple[str, List[str]]:
    """Crée a_envoyer.zip : journaux de la session, objectif.json et les images douteuses les plus récentes.

    Renvoie (chemin du zip, liste des fichiers inclus). Lève FileNotFoundError s'il n'y a rien à envoyer.
    """
    racine = racine or dossier  # objectif.json et observation*.json restent là où tu lances le logiciel
    fichiers = [n for n in JOURNAUX + ("registre_runes.jsonl", "diag_stock.txt", "erreurs.log") if os.path.isfile(os.path.join(dossier, n))]
    fichiers_racine = [n for n in ("objectif.json", "observation.json", "observation_video.json") if os.path.isfile(os.path.join(racine, n))]
    images: List[str] = []
    dossier_img = os.path.join(dossier, DOSSIER_IMAGES)
    if os.path.isdir(dossier_img):
        noms = [n for n in os.listdir(dossier_img) if n.lower().endswith(".png")]
        noms.sort(key=lambda n: os.path.getmtime(os.path.join(dossier_img, n)), reverse=True)
        images = [os.path.join(DOSSIER_IMAGES, n) for n in noms[:max_images]]
    if not any(n in JOURNAUX for n in fichiers) and not images:
        raise FileNotFoundError("Aucun journal à envoyer : lance d'abord une session.")
    chemin = os.path.join(dossier, FICHIER_ENVOI)
    inclus = fichiers + fichiers_racine + images
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        for n in fichiers + images:
            z.write(os.path.join(dossier, n), n)
        for n in fichiers_racine:
            z.write(os.path.join(racine, n), n)
    return chemin, inclus
