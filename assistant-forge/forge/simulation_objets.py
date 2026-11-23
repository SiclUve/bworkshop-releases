"""(v167) Onglet Simuler : objets reconnus à l'écran (HDV, inventaire...) et objet NEUF tiré au hasard.

Observation seule : la fiche de l'objet est lue sur une capture (comme le reste de l'assistant), rien n'est fait dans le
jeu. Les bornes [min à max] sont reprises de DofusDB quand l'objet y est (nom bien écrit, pas d'erreur de lecture),
sinon de la fiche lue. Un objet neuf = chaque ligne tirée au hasard entre son min et son max (jet de craft supposé
uniforme : NON VÉRIFIÉ), reliquat 0. Les lignes négatives (malus) et les exos déjà posées sont ignorées.
"""

from __future__ import annotations

import os
import random
from fractions import Fraction
from typing import Dict, List, Optional

from forge.erreurs import noter as _noter_erreur

MAX_OBJETS = 30   # objets gardés dans la liste de l'onglet


def jets_lus(texte: str) -> Dict[str, int]:
    """(v168) Jets réels de l'objet affiché (« 289 Vitalité [251 à 300] » -> {"vitalite": 289}). Première valeur lue
    par ligne ; les valeurs négatives (malus) sont ignorées."""
    from forge.cout import _ligne_id
    from forge.objets import _EFFET
    out: Dict[str, int] = {}
    for l in (texte or "").splitlines():
        for m in _EFFET.finditer(l):
            lib = m.group(3).strip(" .")
            if lib.lower().startswith(("poids", "prix", "quantit", "densit")):
                continue
            r = _ligne_id(lib, bool(m.group(2)))
            v = int(m.group(1))
            if r is not None and v > 0:
                out.setdefault(r[0], v)
    return out


def _avec_jets(objet: dict, texte: str) -> dict:
    """Garde les jets lus qui tombent dans les bornes [min à max] de l'objet (un jet hors bornes = lecture douteuse)."""
    jets = {k: v for k, v in jets_lus(texte).items()
            if k in objet["lignes"] and objet["lignes"][k][0] <= v <= objet["lignes"][k][1]}
    if jets:
        objet["jets"] = jets
    return objet


def reconnaitre(texte: str, reference: Optional[Dict[str, dict]] = None) -> Optional[dict]:
    """Texte lu à l'écran -> {nom, niveau, type, lignes {id: [min, max]}, jets {id: valeur}, source} ou None si aucune
    fiche d'objet. (v168) « jets » = jets réels de l'objet vu (HDV) : ils deviennent les cibles par défaut."""
    from forge.objets import lire_fiche_objet, ressemblance
    fiche = lire_fiche_objet(texte)
    if not fiche:
        return None
    lues = {k: list(v) for k, v in fiche["lignes"].items() if v[1] > 0}
    meilleurs = []
    for ref in (reference or {}).values():
        if ref.get("niveau") != fiche.get("niveau") or ref.get("type") != fiche.get("type"):
            continue
        s = ressemblance(ref.get("lignes") or {}, lues)
        if s >= 0.8:
            meilleurs.append((s, ref))
    meilleurs.sort(key=lambda t: -t[0])
    if meilleurs and not (len(meilleurs) > 1 and meilleurs[1][0] == meilleurs[0][0]
                          and meilleurs[1][1].get("nom") != meilleurs[0][1].get("nom")):
        ref = meilleurs[0][1]
        return _avec_jets({"nom": ref["nom"], "niveau": ref.get("niveau"), "type": ref.get("type"),
                           "lignes": {k: list(v) for k, v in ref["lignes"].items() if v[1] > 0}, "source": "DofusDB"},
                          texte)
    if len(lues) < 3:
        return None
    nom = fiche.get("nom") or f"{fiche.get('type') or 'Objet'} niv. {fiche.get('niveau')}"
    return _avec_jets({"nom": nom, "niveau": fiche.get("niveau"), "type": fiche.get("type"), "lignes": lues,
                       "source": "lecture"}, texte)


def marges_des_jets(objet: dict, marge_defaut: int = 1) -> Dict[str, int]:
    """(v168) Marge par ligne = max - jet lu (la cible devient le jet de l'objet vu) ; sans jet lu : marge_defaut."""
    jets = objet.get("jets") or {}
    out = {}
    for k, (mn, mx) in objet["lignes"].items():
        ecart = max(0, mx - mn)
        out[k] = min(ecart, max(0, mx - jets[k])) if k in jets else min(marge_defaut, ecart)
    return out


def _libelles_par_id() -> Dict[str, tuple]:
    from forge.lecture import charger_libelles
    out = {}
    for lib, v in charger_libelles().items():
        out.setdefault(v["id"], (v["poids"], lib[:1].upper() + lib[1:] if not lib.startswith("%")
                                  else "% " + lib[1:2].upper() + lib[2:], lib.startswith("%")))
    return out


def lignes_connues(objet: dict, poids) -> List[str]:
    """Lignes simulables (poids connu), dans l'ordre de la fiche."""
    libs = _libelles_par_id()
    return [k for k in objet["lignes"] if k in libs and libs[k][0] in poids]


_ACCENTS = {"vitalite": "vitalité", "agilite": "agilité", "portee": "portée", "resistance": "résistance",
            "pieges": "pièges", "degats": "dégâts", "elementaires": "élémentaires", "pousse": "poussée",
            "poussee": "poussée", "melee": "mêlée", "soins": "soins"}


def libelle(ligne_id: str) -> str:
    """Nom de la ligne pour l'affichage, avec ses accents (« % Résistance feu »)."""
    brut = _libelles_par_id().get(ligne_id, (None, ligne_id))[1]
    mots = [(_ACCENTS.get(m.lower(), m) if m.lower() in _ACCENTS else m) for m in brut.split(" ")]
    t = " ".join(mots)
    i = 2 if t.startswith("% ") else 0
    return t[:i] + t[i:i + 1].upper() + t[i + 1:]


def fabrique_neuf(objet: dict, poids):
    """Fonction rng -> panneau d'un objet NEUF (chaque ligne tirée entre son min et son max, reliquat 0)."""
    from forge.lecture import Ligne, Panneau
    libs = _libelles_par_id()
    ids = lignes_connues(objet, poids)

    def neuf(rng: random.Random):
        lignes = []
        for k in ids:
            mn, mx = objet["lignes"][k]
            cle, lib, pct = libs[k]
            lignes.append(Ligne(k, cle, lib, rng.randint(min(mn, mx), mx), mn, mx, pct))
        return Panneau(lignes=lignes, reliquat=Fraction(0))
    return neuf


def objectif_simulation(base, objet: dict, marges: Dict[str, int], ignorees: List[str], exo: Optional[str]):
    """Objectif de simulation : TES réglages de stratégie et de chance d'exo, mais les marges/lignes de l'onglet Simuler.
    Lignes ignorées = sacrifiables (elles peuvent servir de puits). Aucune autre ligne n'est sacrifiée."""
    from forge.objectif import Objectif
    return Objectif(marge=0, marges={k: int(v) for k, v in marges.items() if k in objet["lignes"]},
                    sacrifiables=[k for k in ignorees if k in objet["lignes"]], ignorees=[],
                    exo=[exo] if exo else [], chance_exo=getattr(base, "chance_exo", 0.01),
                    chances_exo=dict(getattr(base, "chances_exo", {}) or {}),
                    strategie=getattr(base, "strategie", "conseil"), un_seul_exo=True)


class ListeSimulee:
    """Objets ajoutés à l'onglet Simuler, gardés dans journaux/objets_simules.json (avec leurs marges)."""

    def __init__(self, fichier: Optional[str] = None):
        self.fichier = fichier
        self.objets: List[dict] = []
        if fichier and os.path.exists(fichier):
            try:
                import json
                with open(fichier, encoding="utf-8") as f:
                    self.objets = list(json.load(f).get("objets", []))
            except Exception:
                from forge.erreurs import fichier_abime
                fichier_abime(fichier, "simulation_objets.ListeSimulee")
                self.objets = []

    def enregistrer(self):
        if not self.fichier:
            return
        try:
            from forge.erreurs import ecrire_json
            os.makedirs(os.path.dirname(self.fichier), exist_ok=True)
            ecrire_json(self.fichier, {"objets": self.objets[:MAX_OBJETS]}, ensure_ascii=False, indent=1)
        except OSError:
            _noter_erreur("simulation_objets.ListeSimulee.enregistrer")

    def ajouter(self, objet: dict, marge_defaut: int = 1) -> tuple:
        """Ajoute l'objet en tête (ou le remonte s'il y est déjà, réglages gardés). Renvoie (index, nouveau ?).
        (v168) Cibles par défaut = jets lus sur l'objet vu. Même objet revu avec d'AUTRES jets (autre offre de l'HDV) :
        les cibles prennent ces nouveaux jets et l'objet compte comme nouveau (le coût est recalculé)."""
        for i, o in enumerate(self.objets):
            if o.get("nom") == objet.get("nom") and o.get("lignes") == objet.get("lignes"):
                self.objets.insert(0, self.objets.pop(i))
                if objet.get("jets") and objet["jets"] != o.get("jets"):
                    o["jets"] = dict(objet["jets"])
                    o["marges"] = marges_des_jets(o, marge_defaut)
                    o["ignorees"] = []
                    o.pop("resultat", None)
                    self.enregistrer()
                    return 0, True
                return 0, False
        o = dict(objet)
        o.setdefault("marges", marges_des_jets(objet, marge_defaut))
        o.setdefault("ignorees", [])
        o.setdefault("exo", "pa")
        self.objets.insert(0, o)
        del self.objets[MAX_OBJETS:]
        self.enregistrer()
        return 0, True
