"""(v117) Une session de coûts PAR OBJET forgé : runes passées, kamas, critiques, du début à la fin de l'objet.

Une nouvelle session commence quand l'objet change (autre objet reconnu, ou lignes et bornes d'un autre objet), ou à la
demande (bouton « Nouvel exemplaire » : même objet, nouvel exemplaire). Sauvé dans journaux/sessions_objets.json.
"""

from __future__ import annotations

import json
import hashlib
import uuid
from pathlib import Path
import os
import time
from typing import Dict, List, Optional, Tuple

from forge.erreurs import noter as _noter_erreur
from forge.objets import compatibles

MAX_SESSIONS = 300
CONFIRMATIONS = 2   # un autre objet doit être lu 2 fois de suite (bornes mal lues une fois : pas de nouvelle session)


class Sessions:
    def __init__(self, fichier: Optional[str] = None):
        self.fichier = fichier
        self.liste: List[dict] = []
        self._candidat: Optional[Tuple[str, int]] = None
        if fichier and os.path.exists(fichier):
            try:
                with open(fichier, encoding="utf-8") as f:
                    self.liste = json.load(f)
            except Exception:
                _noter_erreur("sessions.Sessions")
                self.liste = []

    # --- état -------------------------------------------------------------------------------------------------------
    @property
    def courante(self) -> Optional[dict]:
        return self.liste[-1] if self.liste and not self.liste[-1].get("fin") else None

    def enregistrer(self):
        if not self.fichier:
            return
        try:
            if len(self.liste) > MAX_SESSIONS:
                # Une archive immuable précède la réduction du fichier actif ; format liste JSON conservé.
                contenu = json.dumps(self.liste[:-MAX_SESSIONS], ensure_ascii=False, indent=1).encode("utf-8")
                dossier = Path(str(self.fichier) + ".archives")
                dossier.mkdir(parents=True, exist_ok=True)
                attente = getattr(self, "_archive_en_attente", None)
                if attente is None or attente[0] != contenu:
                    # Deux sessions distinctes peuvent avoir exactement les mêmes valeurs (heure à la minute).
                    archive = dossier / (hashlib.sha256(contenu).hexdigest() + "_" + uuid.uuid4().hex + ".json")
                    self._archive_en_attente = (contenu, archive)
                else:
                    archive = attente[1]  # réessai de la même sauvegarde, pas un nouvel événement
                if archive.exists():
                    if archive.read_bytes() != contenu:
                        raise OSError("Archive existante différente : historique actif conservé.")
                else:
                    with archive.open("xb") as f:
                        f.write(contenu)
                        f.flush()
                        os.fsync(f.fileno())
            from forge.erreurs import ecrire_json
            ecrire_json(self.fichier, self.liste[-MAX_SESSIONS:], ensure_ascii=False, indent=1)
            self.liste = self.liste[-MAX_SESSIONS:]
            self._archive_en_attente = None
        except Exception:
            _noter_erreur("sessions.enregistrer")

    def _ouvrir(self, lignes: Dict[str, list], nom: str, cle_objet: Optional[str], raison: str):
        c = self.courante
        if c is not None:
            c["fin"] = time.strftime("%Y-%m-%d %H:%M")
        self.liste.append({"debut": time.strftime("%Y-%m-%d %H:%M"), "fin": None, "nom": nom, "cle_objet": cle_objet,
                           "lignes": lignes, "runes": {}, "estimees": {}, "critiques": 0, "raison": raison})
        self._candidat = None
        self.enregistrer()

    # --- objet vu ---------------------------------------------------------------------------------------------------
    def objet_vu(self, lignes: Dict[str, list], nom: str, cle_objet: Optional[str] = None, force: bool = False) -> bool:
        """Tableau stable lu (lignes d'origine avec Min/Max). Renvoie True si une NOUVELLE session vient de commencer.
        force : le suivi a vu le tableau changer de structure (« nouvel objet ») : pas besoin de deuxième lecture."""
        if len(lignes) < 3:
            return False
        c = self.courante
        if c is None:
            self._ouvrir(lignes, nom, cle_objet, "premier objet")
            return True
        meme = (cle_objet is not None and cle_objet == c.get("cle_objet")) or compatibles(c["lignes"], lignes)
        if meme:
            self._candidat = None
            change = False
            if cle_objet and not c.get("cle_objet"):
                c["cle_objet"] = cle_objet
                change = True
            if nom and nom != c.get("nom") and (cle_objet or not c.get("cle_objet")):
                c["nom"] = nom          # objet reconnu en cours de route (fiche vue après le début)
                change = True
            if change:
                self.enregistrer()
            return False
        sig = json.dumps(lignes, sort_keys=True)
        n = self._candidat[1] + 1 if self._candidat and self._candidat[0] == sig else 1
        self._candidat = (sig, n)
        if n >= CONFIRMATIONS or force:
            self._ouvrir(lignes, nom, cle_objet, "autre objet")
            return True
        return False

    def nouvel_exemplaire(self):
        """Même objet, nouvel exemplaire : on ferme la session et on en rouvre une au même nom."""
        c = self.courante
        if c is None:
            return
        self._ouvrir(dict(c["lignes"]), c["nom"], c.get("cle_objet"), "nouvel exemplaire")

    def renommer(self, nom: str):
        c = self.courante
        if c is not None and nom.strip():
            c["nom"] = nom.strip()
            self.enregistrer()

    # --- runes ------------------------------------------------------------------------------------------------------
    def ajouter(self, exactes: Dict[str, int], estimees: Dict[str, int], critiques: int = 0):
        c = self.courante
        if c is None or not (exactes or estimees or critiques):
            return
        for nom, n in exactes.items():
            c["runes"][nom] = c["runes"].get(nom, 0) + n
        for nom, n in estimees.items():
            c["estimees"][nom] = c["estimees"].get(nom, 0) + n
        c["critiques"] = c.get("critiques", 0) + critiques
        self.enregistrer()

    @staticmethod
    def bilan(s: dict, prix: Dict[str, int]) -> dict:
        """{runes, estimees, kamas, sans_prix, critiques} d'une session, avec les prix actuels."""
        n = sum(s["runes"].values()) + sum(s["estimees"].values())
        kamas, sans = 0, 0
        for d in (s["runes"], s["estimees"]):
            for nom, q in d.items():
                p = prix.get(nom)
                if p:
                    kamas += p * q
                else:
                    sans += q
        return {"runes": n, "estimees": sum(s["estimees"].values()), "kamas": kamas, "sans_prix": sans,
                "critiques": s.get("critiques", 0)}

    def precedentes(self, n: int = 5) -> List[dict]:
        fermees = [s for s in self.liste if s.get("fin")]
        return list(reversed(fermees[-n:]))
