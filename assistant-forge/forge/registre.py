"""Registre de TOUTES les passes vues (une ligne JSON par rune), conservé d'une session à l'autre.

Pourquoi : le journal de session garde l'état de l'objet, pas la liste des runes. Ici chaque rune lue dans l'historique
du jeu est notée avec ce qu'on sait d'elle et le degré de certitude :
  lue        : un gain est visible (« 3 Agilité »), la rune est connue exactement ;
  conseillee : échec sans gain, la rune est celle que le programme venait de conseiller (estimation) ;
  inconnue   : échec sans gain et aucun conseil disponible ;
  illisible  : une rangée de l'entrée n'a pas pu être lue (rune comptée mais issue incertaine) ;
  perdue     : des runes ont changé l'objet mais l'historique n'a pas pu être aligné : nombre inconnu.
Le champ `exo` vaut vrai quand la rune est une des exos visées (PA, PM, % Dommages...).
(v110) Champs ajoutés (sans rien retirer) : session, passe, source, lot, q_etat (observe / inconnu), q_issue, suivi,
etat_avant / max_avant / reliquat_avant (v109) et etat_apres / reliquat_apres (passe isolée seulement).
"""

from __future__ import annotations

from contextlib import nullcontext
import json
import os
import threading
import time
from typing import Optional

from forge.journal import ajouter_ligne

from forge.chemins import dossier_journaux

FICHIER_REGISTRE = os.path.join(dossier_journaux(), "registre_runes.jsonl")
SESSION = time.strftime("%Y%m%d_%H%M%S")   # (v110) identifiant de la session : heure de lancement de l'assistant


class Registre:
    def __init__(self, chemin: Optional[str] = FICHIER_REGISTRE):
        self.chemin = chemin
        self.ecrits = 0
        self.non_enregistrees = []
        self.erreur_ecriture = ""
        self._tentatives = 0
        self._ecriture_suspendue = False
        self._sans_secours = 0
        self._verrou = threading.RLock()

    def noter(self, **champs) -> None:
        if not self.chemin:
            return
        with getattr(self, "_verrou", None) or nullcontext():
            self._noter_interne(**champs)

    def _noter_interne(self, **champs) -> None:
        champs.setdefault("heure", time.time())
        # (v110) identifiants : session (lancement de l'assistant) et numéro de passe dans la session, source
        champs.setdefault("session", SESSION)
        self._tentatives += 1
        champs.setdefault("passe", self._tentatives)
        champs.setdefault("source", "jeu")
        try:
            if self._ecriture_suspendue:
                raise OSError("Écriture principale suspendue après une erreur ; passes suivantes mises à l'abri séparément")
            # Ne jamais coller une nouvelle passe à un fragment laissé par un arrêt précédent.
            try:
                with open(self.chemin, "rb") as f:
                    if f.seek(0, os.SEEK_END):
                        f.seek(-1, os.SEEK_END)
                        if f.read(1) != b"\n":
                            raise OSError("Fin de registre incomplète : original conservé sans modification")
            except FileNotFoundError:
                pass
            ajouter_ligne(self.chemin, json.dumps(champs, ensure_ascii=False) + "\n")
            self.ecrits += 1
        except OSError as exc:
            self._ecriture_suspendue = True
            # Pas de réessai automatique : une écriture partielle pourrait créer un doublon.
            self.non_enregistrees.append(champs)
            from forge.erreurs import noter
            noter("registre.noter")
            import tempfile
            import uuid
            secours = os.path.join(tempfile.gettempdir(), "AssistantForge_secours")
            try:
                os.makedirs(secours, exist_ok=True)
                copie = os.path.join(secours, uuid.uuid4().hex + ".jsonl")
                with open(copie, "x", encoding="utf-8") as f:
                    f.write(json.dumps(champs, ensure_ascii=False) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                detail = f"Copie de secours : {copie}."
            except OSError:
                self._sans_secours += 1
                detail = "Copie de secours impossible."
            if self._sans_secours:
                detail += (f" {self._sans_secours} passe(s) gardée(s) uniquement en mémoire : "
                           "ne ferme pas cette session avant récupération.")
            self.erreur_ecriture = f"Registre non enregistré ({exc}). {detail} Le suivi continue."


    def lire(self) -> list:
        """Toutes les lignes valides (les lignes abîmées sont ignorées).

        (v112, R1) Le fichier ne fait que grandir : on garde les lignes déjà lues en mémoire et on ne lit que la fin
        ajoutée depuis la dernière fois (avant : tout le fichier relu après chaque rune). Fichier raccourci ou remplacé :
        on relit tout. Renvoie une copie de la liste (l'appelant peut la modifier)."""
        if not self.chemin:
            return []
        with getattr(self, "_verrou", None) or nullcontext():
            if not hasattr(self, "_lignes"):
                self._lignes, self._pos = [], 0
            try:
                taille = os.path.getsize(self.chemin)
                if taille < self._pos:
                    self._lignes, self._pos = [], 0
                if taille > self._pos:
                    with open(self.chemin, "rb") as f:
                        f.seek(self._pos)
                        bloc = f.read(taille - self._pos)
                    fin = bloc.rfind(b"\n")
                    if fin >= 0:                       # une ligne pas encore finie reste pour la prochaine lecture
                        for l in bloc[:fin + 1].split(b"\n"):
                            if not l.strip():
                                continue
                            try:
                                self._lignes.append(json.loads(l.decode("utf-8")))
                            except (ValueError, UnicodeDecodeError):
                                continue
                        self._pos += fin + 1
            except OSError:
                pass
            return list(self._lignes)
