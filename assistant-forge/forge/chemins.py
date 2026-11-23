"""Où écrire les journaux : toujours le même dossier « journaux », à côté du logiciel (exe ou fenetre_forge.py).

Avant, ils s'écrivaient dans le dossier d'où le logiciel était lancé, donc ailleurs selon le raccourci."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def dossier_data() -> Path:
    """Dossier « data » des ressources embarquées (supporte PyInstaller _MEIPASS et mode développement)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidat = Path(meipass) / "data"
        if candidat.is_dir():
            return candidat
    if getattr(sys, "frozen", False):
        candidat = Path(sys.executable).resolve().parent / "data"
        if candidat.is_dir():
            return candidat
    return Path(__file__).resolve().parent.parent / "data"


def chemin_data(*parties: str) -> Path:
    """Chemin complet vers une ressource dans data/."""
    return dossier_data().joinpath(*parties)


def dossier_logiciel() -> str:
    from forge.edition import dossier_donnees_publique, publique
    if publique():   # (v169) version partagée : données de l'utilisateur dans %LOCALAPPDATA%\AssistantForge
        d = dossier_donnees_publique()
        os.makedirs(d, exist_ok=True)
        return d
    if getattr(sys, "frozen", False):
        return racine_si_exe_du_projet(os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def racine_si_exe_du_projet(dossier_exe: str) -> str:
    """(v164) MÉMOIRE UNIQUE : l'exe construit dans <projet>\\dist\\AssistantForge utilise les journaux et réglages du
    projet, comme Lancer_assistant.bat. Avant, chacun avait les siens (5 268 passes d'un côté, 1 269 de l'autre ; prix
    et stock différents). Un exe copié ailleurs (hors d'un projet) garde son propre dossier, comme avant."""
    p = os.path.abspath(dossier_exe)
    parent = os.path.dirname(p)
    racine = os.path.dirname(parent)
    if (os.path.basename(p).lower() == "assistantforge" and os.path.basename(parent).lower() == "dist"
            and os.path.isfile(os.path.join(racine, "Lancer_assistant.bat"))
            and os.path.isfile(os.path.join(racine, "forge", "chemins.py"))):
        return racine
    return p


def dossier_journaux() -> str:
    """Le dossier « journaux » (créé à l'écriture, pas à l'import).

    (v128) FORGE_JOURNAUX, s'il est défini, le remplace : les tests l'utilisent pour ne jamais écrire dans les vrais
    journaux (developpement/tests/isolement.py). Le logiciel ne le définit jamais."""
    force = os.environ.get("FORGE_JOURNAUX")
    if force:
        return force
    return os.path.join(dossier_logiciel(), "journaux")


def preparer_reglages():
    """Chemins stables ; migration par copie uniquement si la destination manque.

    Une ancienne configuration valide est sauvegardée et vérifiée avant sa copie.
    Aucune valeur déjà présente à côté du logiciel n'est remplacée.
    """
    import hashlib
    import json
    from pathlib import Path
    import uuid
    racine = Path(dossier_logiciel()).resolve()
    ancien = Path.cwd().resolve()
    noms = ("objectif.json", "prix_runes.json", "stock_runes.json", "compteur_session.json",
            "observation.json", "observation_video.json")
    resultat = {n: str(racine / n) for n in noms}
    from forge.edition import publique
    if publique():   # (v169) version partagée : jamais de reprise de réglages trouvés dans le dossier courant
        return resultat
    for nom in noms:
        cible, source = racine / nom, ancien / nom
        if cible.exists() or ancien == racine or not source.is_file():
            continue
        contenu = source.read_bytes()
        if not isinstance(json.loads(contenu.decode("utf-8-sig")), dict):
            raise ValueError(f"Réglages {source} invalides : migration annulée, original conservé.")
        if os.name != "nt":
            raise OSError("Migration automatique réservée à Windows (remplacement interdit).")
        sauvegarde = racine / "sauvegardes" / ("reglages_" + uuid.uuid4().hex)
        sauvegarde.mkdir(parents=True)
        copie = sauvegarde / nom
        with copie.open("xb") as f:
            f.write(contenu)
            f.flush()
            os.fsync(f.fileno())
        if copie.stat().st_size != len(contenu) or hashlib.sha256(copie.read_bytes()).digest() != hashlib.sha256(contenu).digest():
            raise OSError("Sauvegarde des réglages non vérifiée : migration annulée.")
        temporaire = racine / (nom + ".migration_" + uuid.uuid4().hex)
        with temporaire.open("xb") as f:
            f.write(contenu)
            f.flush()
            os.fsync(f.fileno())
        try:
            # Sous Windows rename refuse une destination apparue entre-temps.
            os.rename(temporaire, cible)
        except FileExistsError:
            pass  # conserver aussi la copie temporaire ; priorité au réglage déjà présent
    return resultat
