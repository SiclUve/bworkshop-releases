"""(v117) Objets reconnus : catalogue appris EN JEU, à partir de la fiche de l'objet (souris sur l'objet).

La fiche affiche le nom, « Niveau 183 • Ceinture », la panoplie et chaque effet avec ses bornes « [251 à 300] ». On en tire
une signature (lignes + Min/Max) qu'on retrouve ensuite dans le tableau de forgemagie : l'objet est reconnu sans
nouvelle fiche, et la session de coûts porte son nom. Observation seule : lecture de l'écran, rien n'est fait dans le jeu.
(v118) Complété par les objets DofusDB téléchargés une fois à la main (forge/objets_dofusdb.py).
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from forge.erreurs import noter as _noter_erreur

TYPES = ("Ceinture", "Bottes", "Anneau", "Amulette", "Cape", "Chapeau", "Bouclier", "Dofus", "Trophée",
         # (v169d) armes : fiches d'armes lues aussi (onglet Simuler, objets appris)
         "Arc", "Baguette", "Bâton", "Dague", "Épée", "Marteau", "Pelle", "Hache", "Pioche", "Faux", "Lance")
_TYPES_NORM = {t.lower(): t for t in TYPES}
_TYPES_NORM.update({"".join(c for c in __import__("unicodedata").normalize("NFD", t)
                            if __import__("unicodedata").category(c) != "Mn").lower(): t for t in TYPES})
_NIVEAU = re.compile(r"niveau\s*(\d{1,3})\s*[^A-Za-zÀ-ÿ]{0,6}\s*([A-Za-zÀ-ÿ]+)", re.I)
# « ?38Sagesse[31a40] », « e12DommagesNeutre[9a12] », « @6% Resistance Eau [5a7] », « ★1 PA [1] », « -10 Dommages Poussée [-10a-7] »
_EFFET = re.compile(r"(?<![\d\]])(-?\d{1,4})\s*(%?)\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' .]{1,40}?)\s*\[\s*(-?\d{1,4})\s*"
                    r"(?:(?:[aàαd]\s*|\s+)(-?\d{1,4})\s*)?\]")   # « à » lu a, α, d, ou perdu (« [11  15] »)
_BRUIT_NOM = re.compile(r"\b(forge)?[mn]ager\b|\binventaire\b|\bniveau.*$|\bfusionner.*$|\breliquat.*$", re.I)
SCORE_MINI = 0.8   # part des lignes de l'objet retrouvées avec les mêmes Min/Max dans le tableau
LIGNES_MINI = 3
PART_PARTIELLE = 0.6   # (v123) reconnaissance avec des Min/Max non lus : bornes lues sur 60 % des lignes au moins
PART_MAX_SEUL = 0.6    # (v127) idem en comptant aussi les lignes dont seul le MAX est lu (le Min à un chiffre saute souvent)
ECART_AMBIGU = 0.05    # (v127) un 2e objet de nom différent couvert à 5 % près du meilleur : on ne choisit pas


def _sans_accents(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def _separer(chiffres: str, valeur: int) -> Optional[Tuple[int, int]]:
    """« [1625] » : le « à » perdu par l'OCR. Une seule borne de 3 chiffres ou plus, très loin de la valeur, est coupée
    en deux nombres de longueurs voisines (16 et 25) ; une seule borne courte (« [1] », « [2] ») reste Min = Max."""
    n = int(chiffres)
    neg = chiffres.startswith("-")
    d = chiffres.lstrip("-")
    if neg or len(d) < 2 or n <= max(2 * abs(valeur), 9):
        return n, n
    for i in sorted(range(1, len(d)), key=lambda i: abs(len(d) - 2 * i)):
        a, b = int(d[:i]), int(d[i:])
        if abs(len(d[:i]) - len(d[i:])) <= 1 and d[i] != "0" and a < b:
            return a, b
    return None


def lire_fiche_objet(texte: str) -> Optional[dict]:
    """Fiche d'un équipement lue par l'OCR -> {nom, niveau, type, panoplie, lignes: {id: [min, max]}} ; None si ce n'est
    pas une fiche d'objet (une fiche de rune, par exemple) ou si moins de 3 effets à bornes sont lisibles."""
    from forge.cout import _ligne_id
    if not texte:
        return None
    lignes_txt = texte.splitlines()
    niveau = type_ = None
    i_niv = None
    for i, l in enumerate(lignes_txt):
        for m in _NIVEAU.finditer(l):
            t = _TYPES_NORM.get(_sans_accents(m.group(2)).lower().replace("trophee", "trophée"))
            if t:
                niveau, type_, i_niv = int(m.group(1)), t, i
                break
        if type_:
            break
    if not type_:
        return None
    lignes: Dict[str, List[int]] = {}
    for l in lignes_txt:
        for m in _EFFET.finditer(l):
            lib = m.group(3).strip(" .")
            if lib.lower().startswith(("poids", "prix", "quantit", "densit")):
                continue
            r = _ligne_id(lib, bool(m.group(2)))
            if r is None:
                continue
            mini = int(m.group(4))
            maxi = int(m.group(5)) if m.group(5) is not None else mini
            if m.group(5) is None:
                bornes = _separer(m.group(4), int(m.group(1)))
                if bornes is None:
                    continue
                mini, maxi = bornes
            if mini > maxi and not (mini < 0 and maxi < 0):
                continue
            lignes.setdefault(r[0], [mini, maxi])
    if len(lignes) < LIGNES_MINI:
        return None
    nom = None
    if i_niv:
        brut = lignes_txt[i_niv - 1]
        if not re.search(r"\d|min\s*max|reliquat|effets", brut, re.I):
            n = re.sub(r"\s+", " ", _BRUIT_NOM.sub(" ", brut)).strip(" -:·+")
            if 4 <= len(n) <= 40 and re.search(r"[A-Za-zÀ-ÿ]{3}", n):
                nom = n
    panoplie = None
    m = re.search(r"panoplie\s*(?:de|des|du|d')?\s*([A-Za-zÀ-ÿ' ]{3,40})", texte, re.I)
    if m:
        panoplie = re.sub(r"\s+", " ", m.group(0)).strip()
        panoplie = re.split(r"\s{2,}|\bQ\b|Recherche|mage\]", panoplie)[0].strip()
    return {"nom": nom, "niveau": niveau, "type": type_, "panoplie": panoplie, "lignes": lignes}


def signature(lignes: Dict[str, List[int]]) -> str:
    return "|".join(f"{k}:{v[0]}:{v[1]}" for k, v in sorted(lignes.items()))


def lignes_tableau(panneau) -> Dict[str, List[int]]:
    """Lignes d'origine du tableau (Min ET Max lus, hors exo et malus)."""
    out = {}
    for l in getattr(panneau, "lignes", []) or []:
        if l.mini is not None and l.maxi is not None and not getattr(l, "exo_lue", False):
            out[l.id] = [int(l.mini), int(l.maxi)]
    return out


def ressemblance(a: Dict[str, List[int]], b: Dict[str, List[int]]) -> float:
    """Part des lignes de a et de b qui ont les mêmes bornes (0 à 1) : min des deux taux de couverture."""
    if not a or not b:
        return 0.0
    communes = sum(1 for k, v in a.items() if b.get(k) == v)
    return min(communes / len(a), communes / len(b))


def compatibles(a: Dict[str, List[int]], b: Dict[str, List[int]]) -> bool:
    """Deux lectures du même objet : leurs lignes communes couvrent 80 % de la plus petite et ont les mêmes bornes
    à 90 % (une ligne cachée ou mal lue n'en fait pas un autre objet)."""
    communes = set(a) & set(b)
    if not communes or len(communes) < 0.8 * min(len(a), len(b)):
        return False
    return sum(a[k] == b[k] for k in communes) >= 0.9 * len(communes)


def nom_affiche(fiche: Optional[dict], defaut: str = "Objet") -> str:
    if not fiche:
        return defaut
    base = fiche.get("nom") or f"{fiche.get('type') or 'Objet'}"
    niv = f" (niv. {fiche['niveau']})" if fiche.get("niveau") else ""
    pano = "" if fiche.get("nom") or not fiche.get("panoplie") else f", {fiche['panoplie']}"
    return base + niv + pano


class Catalogue:
    """{signature: {nom, noms_lus {nom: n}, niveau, type, panoplie, lignes, vu}} sauvé dans journaux/objets_connus.json."""

    def __init__(self, fichier: Optional[str] = None):
        self.fichier = fichier
        self.objets: Dict[str, dict] = {}
        if fichier and os.path.exists(fichier):
            try:
                with open(fichier, encoding="utf-8") as f:
                    self.objets = json.load(f)
            except Exception:
                _noter_erreur("objets.Catalogue")
                self.objets = {}
        # (v118) objets téléchargés depuis DofusDB (Telecharger_objets.bat) : reconnus dès la première passe, sans fiche.
        # Gardés à part : un objet appris en jeu passe toujours avant.
        self.reference: Dict[str, dict] = {}
        try:
            from forge.objets_dofusdb import charger
            self.reference = charger() if fichier else {}
        except Exception:
            _noter_erreur("objets.Catalogue.reference")

    def enregistrer(self):
        if not self.fichier:
            return
        try:
            from forge.erreurs import ecrire_json
            ecrire_json(self.fichier, self.objets, ensure_ascii=False, indent=1)
        except Exception:
            _noter_erreur("objets.Catalogue.enregistrer")

    def apprendre(self, fiche: Optional[dict]) -> Optional[str]:
        """Ajoute ou complète un objet ; renvoie sa signature. Le nom retenu est le plus souvent lu (l'OCR en abîme
        parfois un : « oottesaeFrigostine »)."""
        if not fiche or not fiche.get("lignes"):
            return None
        cle = signature(fiche["lignes"])
        # même objet déjà connu, avec une ligne mal lue ou cachée : on rattache à la fiche compatible et on complète
        for k, o in self.objets.items():
            if k != cle and o.get("type") == fiche.get("type") and o.get("niveau") == fiche.get("niveau") \
                    and compatibles(o["lignes"], fiche["lignes"]):
                cle = k
                for lid, b in fiche["lignes"].items():
                    o["lignes"].setdefault(lid, b)
                break
        o = self.objets.setdefault(cle, {"noms_lus": {}, "lignes": dict(fiche["lignes"])})
        for k in ("niveau", "type", "panoplie"):
            if fiche.get(k):
                o[k] = fiche[k]
        if fiche.get("nom"):
            o["noms_lus"][fiche["nom"]] = o["noms_lus"].get(fiche["nom"], 0) + 1
        if o["noms_lus"] and not o.get("nom_choisi"):
            o["nom"] = max(o["noms_lus"].items(), key=lambda t: (t[1], -len(t[0])))[0]
            # (v123) même objet dans DofusDB (mêmes lignes, mêmes bornes) : son nom est bien écrit (« Anneaude Brouce »
            # lu par l'OCR -> « Anneau de Brouce »)
            for ref in list(self.reference.values()):
                if ref.get("nom") and ressemblance(ref.get("lignes") or {}, o["lignes"]) == 1.0:
                    o["nom"] = ref["nom"]
                    break
        o["vu"] = time.strftime("%Y-%m-%d %H:%M")
        self.enregistrer()
        return cle

    def renommer(self, cle: str, nom: str):
        if cle not in self.objets and cle in self.reference and nom.strip():
            o = self.reference[cle]
            self.objets[cle] = {"noms_lus": {}, "lignes": dict(o["lignes"]), "niveau": o.get("niveau"),
                                "type": o.get("type")}
        if cle in self.objets and nom.strip():
            self.objets[cle]["nom"] = nom.strip()
            self.objets[cle]["nom_choisi"] = True
            self.enregistrer()

    def reconnaitre(self, panneau) -> Optional[Tuple[str, dict, float]]:
        """(signature, objet, ressemblance) de l'objet du tableau, ou None si aucun objet connu ne colle assez.
        Objets appris en jeu d'abord, puis (v118) objets DofusDB."""
        tab = lignes_tableau(panneau)
        if len(tab) < LIGNES_MINI:
            return None
        for source in (self.objets, self.reference):
            r = self._meilleur(source, tab)
            if r is not None:
                return r
        # (v123) Min/Max à un chiffre souvent non lus (« 4 5 » Fuite) : 6 lignes complètes sur 9 = 67 %, l'Anneau de
        # Brouce n'était jamais reconnu (30/10). Deuxième essai : toutes les lignes du tableau existent dans l'objet,
        # aucune borne lue ne le contredit, et les bornes lues couvrent au moins 60 % de ses lignes.
        # lignes lues en bleu (exo) mises à part ; une ligne sans Min/Max ni couleur compte (elle doit exister dans l'objet)
        ids = {l.id for l in getattr(panneau, "lignes", []) or [] if getattr(l, "couleur", None) != "bleue"}
        for source in (self.objets, self.reference):
            r = self._partiel(source, tab, ids)
            if r is not None:
                return r
        # (v127) Anneau Crustique : 3 lignes sur 9 seulement avec Min ET Max lus (le Min à un chiffre, le Critique « 2 2 »
        # et la Résistance Eau ne sortent pas), jamais reconnu sur 61 lectures vidéo. Troisième essai : on compte aussi les
        # lignes dont seul le Max est lu. Rejouée sur les 38 117 lectures vidéo (401 séquences d'objet) : un nom unique et
        # stable dans chaque séquence (le seul cas de deux noms est un vrai changement d'objet, bornes différentes).
        for source in (self.objets, self.reference):
            r = self._par_max(source, panneau)
            if r is not None:
                return r
        return None

    @staticmethod
    def _par_max(source: Dict[str, dict], panneau) -> Optional[Tuple[str, dict, float]]:
        """Toutes les lignes du tableau (hors exo bleues) existent dans l'objet, aucune borne lue ne le contredit (Max ET
        Min quand ils sont lus), et les lignes à Max lu couvrent 60 % de ses lignes au moins."""
        lignes = [l for l in getattr(panneau, "lignes", []) or [] if getattr(l, "couleur", None) != "bleue"]
        ids = {l.id for l in lignes}
        lus = [l for l in lignes if l.maxi is not None]
        ok = []
        for k, o in list(source.items()):
            lo = o.get("lignes") or {}
            if not lo or not ids <= set(lo):
                continue
            if any(lo[l.id][1] != l.maxi or (l.mini is not None and lo[l.id][0] != l.mini) for l in lus):
                continue
            if any(l.maxi is None and l.mini is not None and lo[l.id][0] != l.mini for l in lignes):
                continue
            if len(lus) >= max(LIGNES_MINI, PART_MAX_SEUL * len(lo)) and len(ids) >= SCORE_MINI * len(lo):
                ok.append((len(lus) / len(lo), k))
        if not ok:
            return None
        ok.sort(reverse=True)
        noms = {source[k].get("nom") for s, k in ok if s == ok[0][0]}
        if len(noms) > 1:
            return None   # deux objets différents collent autant : on ne choisit pas
        if len(ok) > 1 and source[ok[1][1]].get("nom") != source[ok[0][1]].get("nom") and ok[1][0] >= ok[0][0] - ECART_AMBIGU:
            return None   # un autre objet colle presque autant
        s, k = ok[0]
        return k, source[k], s

    @staticmethod
    def _partiel(source: Dict[str, dict], tab, ids) -> Optional[Tuple[str, dict, float]]:
        ok = []
        for k, o in list(source.items()):
            lo = o.get("lignes") or {}
            if not lo or not ids <= set(lo):
                continue
            if any(lo.get(i) != v for i, v in tab.items()):
                continue
            communes = len(tab)
            if communes >= max(LIGNES_MINI, PART_PARTIELLE * len(lo)) and len(ids) >= SCORE_MINI * len(lo):
                ok.append((communes / len(lo), k))
        if not ok:
            return None
        ok.sort(reverse=True)
        noms = {source[k].get("nom") for s, k in ok if s == ok[0][0]}
        if len(noms) > 1:
            return None   # deux objets différents collent autant : on ne choisit pas
        s, k = ok[0]
        return k, source[k], s

    @staticmethod
    def _meilleur(source: Dict[str, dict], tab) -> Optional[Tuple[str, dict, float]]:
        meilleurs = sorted(((ressemblance(o["lignes"], tab), k) for k, o in source.items()), reverse=True)
        if not meilleurs or meilleurs[0][0] < SCORE_MINI:
            return None
        if len(meilleurs) > 1 and meilleurs[1][0] == meilleurs[0][0] and \
                source[meilleurs[1][1]].get("nom") != source[meilleurs[0][1]].get("nom"):
            return None   # deux objets différents collent autant : on ne choisit pas
        s, k = meilleurs[0]
        return k, source[k], s


def completer_bornes(panneau, objet: Optional[dict]) -> List[str]:
    """(v123) Objet reconnu : les Min/Max NON LUS du tableau sont repris de l'objet (jamais un Min/Max lu n'est changé).
    Renvoie les libellés complétés."""
    faits = []
    lo = (objet or {}).get("lignes") or {}
    for l in getattr(panneau, "lignes", []) or []:
        b = lo.get(l.id)
        if not b or getattr(l, "couleur", None) == "bleue" or getattr(l, "bornes_supposees", False):
            continue
        if l.mini is None or l.maxi is None:
            if l.mini is None:
                l.mini = int(b[0])
            if l.maxi is None:
                l.maxi = int(b[1])
            l.bornes_catalogue = True
            faits.append(l.libelle)
    return faits
