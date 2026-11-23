"""(v100) Journal des erreurs : avant, ~40 « except Exception: pass » avalaient les erreurs sans rien dire (un bug dans
le calcul d'un conseil changeait le conseil en silence). Chaque erreur rattrapée est maintenant écrite dans
journaux/erreurs.log, avec l'endroit et la trace. Limites : une même erreur au même endroit n'est écrite qu'une fois
par minute ; au-delà de 1 Mo, l'ancien fichier est gardé sous erreurs.log.1 (v120, C8 : avant, il était effacé).
Cette fonction ne lève jamais d'erreur elle-même.

(v120, C7) Fichiers de réglages : `ecrire_json` écrit d'abord un fichier temporaire puis le met en place (un arrêt
brutal ne laisse plus un fichier à moitié écrit) ; `fichier_abime` garde une copie « .abime » d'un fichier illisible
avant qu'il soit remplacé par les valeurs par défaut, note l'erreur, et retient un message pour la fenêtre.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import traceback
import uuid

_DERNIERES = {}
TAILLE_MAX = 1_000_000
CHEMIN = None  # forcé par les tests ; sinon journaux/erreurs.log
COMPTE = 0
ABIMES = []   # (v120, C7) messages « fichier illisible » à montrer dans la fenêtre


def noter(endroit: str) -> None:
    """À appeler dans un bloc « except » : écrit l'erreur en cours dans journaux/erreurs.log."""
    global COMPTE
    try:
        typ, val, tb = sys.exc_info()
        if typ is None:
            return
        COMPTE += 1
        cle = (endroit, typ.__name__, str(val)[:120])
        t = time.time()
        if t - _DERNIERES.get(cle, 0) < 60:
            return
        _DERNIERES[cle] = t
        if CHEMIN is not None:
            chemin = CHEMIN
        else:
            from forge.chemins import dossier_journaux
            chemin = os.path.join(dossier_journaux(), "erreurs.log")
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        if os.path.exists(chemin) and os.path.getsize(chemin) > TAILLE_MAX:
            os.rename(chemin, chemin + ".1" if not os.path.exists(chemin + ".1")
                      else chemin + ".1." + uuid.uuid4().hex)   # (v120, C8) l'ancien journal est gardé, pas effacé
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} {endroit} : {typ.__name__}: {val}\n")
            f.write("".join(traceback.format_tb(tb)[-4:]))
    except Exception:
        pass


def ecrire_json(chemin, donnees, **options) -> None:
    """(v120) Écriture sûre : fichier temporaire puis remplacement. Lève OSError comme open() en cas d'échec."""
    chemin = str(chemin)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, **options)
    os.replace(tmp, chemin)


def fichier_abime(chemin, endroit: str) -> None:
    """(v120, C7) À appeler dans le « except » d'une lecture de fichier : copie le fichier illisible en « .abime »,
    note l'erreur et retient un message pour la fenêtre. Ne lève jamais d'erreur."""
    try:
        noter(endroit)
        chemin = str(chemin)
        copie = chemin + ".abime"
        if os.path.exists(copie):
            copie += "." + uuid.uuid4().hex
        if os.path.exists(chemin):
            with open(chemin, "rb") as source, open(copie, "xb") as destination:
                shutil.copyfileobj(source, destination)
        msg = (f"Fichier illisible : {os.path.basename(chemin)}. Valeurs par défaut utilisées ; "
               f"l'ancien fichier est gardé sous {os.path.basename(copie)}.")
        if msg not in ABIMES:
            ABIMES.append(msg)
    except Exception:
        pass
