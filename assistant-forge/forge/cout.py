"""Comptage des runes passées pendant la session et estimation de leur prix (observation seule).

- Une rune qui a donné un gain est connue exactement (on lit « 3 Agilité » dans l'historique du jeu).
- Une rune qui n'a rien donné (échec) ne dit pas laquelle c'était : on la compte comme la rune que l'assistant
  venait de conseiller (estimation, signalée comme telle).
- Les prix sont en kamas, modifiables dans l'onglet Coûts ; une rune sans prix connu est comptée mais pas chiffrée.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import difflib
from typing import Dict, Iterable, List, Optional, Tuple

from forge.historique import _cle  # noqa: F401  (même normalisation que l'historique)
from forge.lecture import _normaliser, charger_libelles, libelles_lecture_seule  # noqa: F401
from forge.runes_jeu import nom_rune
from forge.erreurs import noter as _noter_erreur

# Prix relevés par l'utilisateur (hôtel de vente) ou lus sur les infobulles de ses journaux. À ajuster dans l'onglet.
PRIX_DEFAUT: Dict[str, int] = {
    "Rune Ga Pa": 22730, "Rune Ga Pme": 18887, "Rune Po": 7399, "Rune Invo": 5140, "Rune Do Per So": 42988,
    "Rune Prospe": 463, "Rune Ré Cri": 358, "Rune Vi": 151,
}
INCONNUE = "Rune inconnue (échec)"

_TAILLES = None


def _tailles() -> dict:
    global _TAILLES
    if _TAILLES is None:
        from forge.engine import DATA_FILE
        with open(DATA_FILE, encoding="utf-8") as f:
            _TAILLES = json.load(f)["stats"]
    return _TAILLES


def _ligne_id(libelle: str, pct: bool = False) -> Optional[Tuple[str, str]]:
    """Libellé lu dans l'historique -> (id de ligne, clé de poids), ou None."""
    libs = libelles_lecture_seule()   # (v162) même contenu que charger_libelles(), sans relire le fichier à chaque appel
    cle = _normaliser(libelle)
    essais = [cle, cle.replace("dommage ", "dommages ", 1), cle.replace("resistance ", "resistances ", 1),
              cle.replace("dommage", "dommages", 1), cle.replace("resistances", "resistance", 1)]
    for e in essais:
        for k in ((("%" + e),) if pct else ()) + (e,):
            if k in libs:
                return libs[k]["id"], libs[k]["poids"]
    # OCR : espace perdu (« ResistanceAir », « DommagesCritiques »), lettre abîmée (« Critigue »), singulier
    sans = lambda t: t.replace(" ", "")
    index = {sans(k): k for k in libs if k.startswith("%") == bool(pct)}
    visee = ("%" if pct else "") + sans(cle)
    candidats = [visee, visee.replace("dommage", "dommages", 1), visee.replace("resistance", "resistances", 1),
                 visee.replace("critique", "critiques")]
    for c in candidats:
        if c in index:
            k = index[c]
            return libs[k]["id"], libs[k]["poids"]
    for c in (candidats[0], candidats[1], candidats[3], candidats[1].replace("critique", "critiques")):
        proches = difflib.get_close_matches(c, list(index), n=2, cutoff=0.88)
        if proches and (len(proches) == 1 or libs[index[proches[0]]]["id"] == libs[index[proches[1]]]["id"]):
            k = index[proches[0]]
            return libs[k]["id"], libs[k]["poids"]
    return None


def runes_de_l_objet(panneau, infos=None) -> List[str]:
    """(v164) Noms de toutes les runes utilisables sur les lignes de l'objet en cours (toutes tailles), avec le même
    filtre que le conseil optimisé (pas les exos PA/PM/PO, ni une ligne exo, ni une ligne sans max ou négative).
    Sert à lister les runes SANS PRIX : le conseil optimisé les ignore."""
    if infos is None:
        from forge.conseil import charger_infos
        infos = charger_infos()
    out: List[str] = []
    for l in getattr(panneau, "lignes", None) or []:
        if (l.id in ("pa", "pm", "po") or getattr(l, "exo_lue", False) or not l.maxi or l.maxi <= 0
                or (l.valeur or 0) < 0):
            continue
        for taille in ((infos or {}).get(l.cle_poids) or {}).get("runes") or {}:
            n = nom_rune(l.id, taille)
            if n and n not in out:
                out.append(n)
    return out


def nom_de_gain(libelle: str, valeur: int, pct: bool = False) -> Optional[str]:
    """Nom de la rune qui donne `valeur` points de `libelle` (ex. 3 Agilité -> « Rune Pa Age »)."""
    r = _ligne_id(libelle, pct)
    if r is None:
        return None
    ligne_id, cle_poids = r
    if ligne_id in ("pa", "pm"):
        return nom_rune(ligne_id, "simple") if valeur == 1 else None
    tailles = (_tailles().get(cle_poids) or {}).get("runes") or {"simple": 1}
    for taille, montant in tailles.items():
        if montant == valeur:
            return nom_rune(ligne_id, taille)
    return None  # un gain hors des tailles connues ne prouve aucune rune


def etat_coherent(avant, apres, entree) -> bool:
    """(v112, C1) Vrai si le tableau avant -> après est exactement l'effet de cette passe (ligne par ligne).
    Un effet dont la ligne est ambiguë (fixe ou %) est accepté s'il colle à l'une des lignes possibles."""
    a = {l.id: l.valeur for l in avant.lignes}
    b = {l.id: l.valeur for l in apres.lignes}
    delta = {k: (b.get(k) or 0) - (a.get(k) or 0) for k in set(a) | set(b) if k != "initiative"}
    delta = {k: v for k, v in delta.items() if v}
    vu = {}
    for x in getattr(entree, "effets", []):
        ids = []
        for pct in ((x.pct,) if getattr(x, "pct", False) else (False, True)):
            r = _ligne_id(x.libelle, pct)
            if r and r[0] not in ids:
                ids.append(r[0])
        ids = [i for i in ids if i in delta or i in a or i in b] or ids
        if not ids:
            return False
        k = next((i for i in ids if delta.get(i, 0) - vu.get(i, 0) == x.valeur), ids[0])
        vu[k] = vu.get(k, 0) + x.valeur
    return {k: v for k, v in vu.items() if v and k != "initiative"} == delta


def poids_objet(panneau, poids) -> Optional[float]:
    """Poids total de l'objet, reliquat compris (None si inconnu)."""
    if panneau is None:
        return None
    tot = 0.0
    for l in panneau.lignes:
        pp = poids.get(l.cle_poids)
        if pp is not None:
            tot += max(0, l.valeur) * float(pp)
    return tot + float(panneau.reliquat or 0)


def _version_algo() -> str:
    try:
        from forge.optimisation import VERSION_ALGO
        return VERSION_ALGO
    except Exception:
        _noter_erreur("cout._version_algo")
        return ""


class Compteur:
    def __init__(self, fichier: Optional[Path] = None, fichier_comptes: Optional[Path] = None):
        self.fichier = Path(fichier) if fichier else None
        self.fichier_comptes = Path(fichier_comptes) if fichier_comptes else None
        self.exo: Counter = Counter()        # tentatives d'exo (rune exo posée ou conseillée), par nom de rune
        self.illisibles = 0                  # runes dont l'entrée de l'historique n'a pas pu être lue en entier
        self.non_alignees = 0                # lectures où des runes sont passées mais l'historique n'a pas pu être aligné
        self.prix: Dict[str, int] = dict(PRIX_DEFAUT)
        self.exact: Counter = Counter()      # runes dont le nom est lu avec certitude (gain vu)
        self.estime: Counter = Counter()     # échecs attribués à la rune conseillée
        self.critiques = 0
        self._retard_en_attente = False      # (v87) l'historique du jeu n'avait pas encore affiché la dernière rune
        self.charger()
        self.charger_comptes()

    # --- comptes de la session (conservés si le programme est fermé) ---
    def charger_comptes(self):
        if self.fichier_comptes and self.fichier_comptes.exists():
            try:
                d = json.loads(self.fichier_comptes.read_text(encoding="utf-8"))
                self.exact.update({str(k): int(v) for k, v in d.get("exact", {}).items()})
                self.estime.update({str(k): int(v) for k, v in d.get("estime", {}).items()})
                self.exo.update({str(k): int(v) for k, v in d.get("exo", {}).items()})
                self.critiques = int(d.get("critiques", 0))
                self.illisibles = int(d.get("illisibles", 0))
                self.non_alignees = int(d.get("non_alignees", 0))
            except (OSError, ValueError, TypeError, AttributeError):
                from forge.erreurs import fichier_abime
                fichier_abime(self.fichier_comptes, "cout.charger_comptes")

    def sauver_comptes(self):
        if self.fichier_comptes:
            try:
                from forge.erreurs import ecrire_json
                ecrire_json(self.fichier_comptes, {
                    "exact": dict(self.exact), "estime": dict(self.estime), "exo": dict(self.exo),
                    "critiques": self.critiques, "illisibles": self.illisibles, "non_alignees": self.non_alignees,
                }, ensure_ascii=False, indent=1)
            except OSError:
                _noter_erreur("cout.sauver_comptes")

    # --- prix ---
    def charger(self):
        if self.fichier and self.fichier.exists():
            try:
                with open(self.fichier, encoding="utf-8") as f:
                    for k, v in json.load(f).items():
                        self.prix[k] = max(0, int(v))
            except (OSError, ValueError, TypeError, AttributeError):
                from forge.erreurs import fichier_abime
                fichier_abime(self.fichier, "cout.charger")

    def enregistrer_prix(self):
        if self.fichier:
            try:
                from forge.erreurs import ecrire_json
                ecrire_json(self.fichier, self.prix, ensure_ascii=False, indent=1)
            except OSError:
                _noter_erreur("cout.enregistrer_prix")

    def fixer_prix(self, nom: str, kamas: int):
        self.prix[nom] = max(0, int(kamas))

    # --- comptage ---
    def ajouter(self, entrees: Iterable, conseillee: Optional[str] = None, exo_noms: Iterable[str] = (),
                registre=None, objet: str = "", avant=None, ignorees: Iterable[str] = (), reglages: Optional[dict] = None,
                apres=None) -> List[str]:
        """Compte les runes passées (liste d'EntreeRune). Renvoie les noms comptés.

        exo_noms : noms des runes d'exo visées (« Rune Ga Pa »...) : une rune de cette liste, lue ou conseillée, compte
        comme une tentative d'exo. Chaque rune est aussi notée dans le registre (si fourni)."""
        exo_noms = set(exo_noms)
        noms = []
        entrees = list(entrees or [])
        lot = len(entrees)
        if len(entrees) != 1:
            avant = None  # plusieurs runes depuis la dernière lecture : l'état « avant » de chacune est inconnu
            apres = None  # ... et l'état « après » de chacune aussi
        for e in entrees:
            if getattr(e, "incomplete", False):
                self.illisibles += 1
                if registre is not None:
                    registre.noter(objet=objet, certitude="illisible", rune=None, exo=False, issue=e.issue, brut=e.brut)
                continue
            gains = [g for g in e.gains]
            if gains:
                g = max(gains, key=lambda x: x.valeur)
                nom = nom_de_gain(g.libelle, g.valeur, g.pct) if len(gains) == 1 else None
                if getattr(e, "rune", None) and e.rune != nom:
                    nom = None
                if nom is None:
                    self.illisibles += 1
                    if registre is not None:
                        registre.noter(objet=objet, certitude="illisible", rune=None, exo=False, issue=e.issue, brut=e.brut,
                                       effets=[[x.libelle, x.valeur] for x in e.effets],
                                       effets_pct=[bool(getattr(x, "pct", False)) for x in e.effets])
                    continue
                self.exact[nom] += 1
                certitude = "lue"
                if e.issue == "succès critique":
                    self.critiques += 1
            elif getattr(e, "rune", None):
                nom = e.rune          # reconnue d'après l'icône de l'historique : compte comme exacte
                self.exact[nom] += 1
                certitude = "lue"
            else:
                nom = conseillee or INCONNUE
                self.estime[nom] += 1
                certitude = "conseillee" if conseillee else "inconnue"
            est_exo = nom in exo_noms
            if est_exo:
                self.exo[nom] += 1
            if registre is not None:
                try:
                    from forge.optimisation import analyser_passe
                    extra = analyser_passe(avant, nom if certitude == "lue" else None, conseillee, ignorees)
                except Exception:  # le journal d'optimisation est un plus : jamais d'erreur
                    _noter_erreur("cout.ajouter")
                    extra = {}
                if est_exo and avant is not None:
                    extra["puits_avant"] = puits_disponible(avant)  # (v103) pour mesurer la chance de l'exo selon le puits
                # (v110) passe rejouable : état APRÈS, certitudes, suivi du conseil
                extra["lot"] = lot                                   # nombre de runes lues ensemble (1 = passe isolée)
                extra["q_etat"] = "observe" if lot == 1 and avant is not None else "inconnu"
                if lot == 1 and avant is not None and apres is not None and not etat_coherent(avant, apres, e):
                    # (v112, C1) le tableau avant -> après ne raconte pas CETTE passe : état gardé pour l'audit, jamais
                    # utilisé comme sûr (apprentissage, analyses)
                    extra["q_etat"] = "incoherent"
                extra["q_issue"] = "historique"                      # issue lue dans l'historique du jeu
                if conseillee and certitude == "lue":
                    extra["suivi"] = (nom == conseillee)
                if apres is not None:
                    extra["etat_apres"] = {x.id: x.valeur for x in apres.lignes}
                    extra["reliquat_apres"] = float(apres.reliquat) if getattr(apres, "reliquat", None) is not None else None
                registre.noter(objet=objet, certitude=certitude, rune=nom, exo=est_exo, issue=e.issue,
                               effets=[[x.libelle, x.valeur] for x in e.effets],
                               # (audit 29/10) le « % » de chaque effet : sans lui, « -2 % Résistance Air » (poids 12) et
                               # « -2 Résistance Air » (poids 4) se confondent dans le registre
                               effets_pct=[bool(getattr(x, "pct", False)) for x in e.effets],
                               reliquat=e.reliquat, brut=e.brut,
                               **(reglages or {}), **extra)
            noms.append(nom)
            if apres is not None and nom != INCONNUE and (avant is None or etat_coherent(avant, apres, e)):
                try:
                    from forge.conseil import noter_issue
                    from forge.optimisation import info_rune
                    info = info_rune(nom)
                    if info:
                        lp = next((x for x in apres.lignes if x.id == info[0]), None)
                        noter_issue(info[0], e.issue, lp.valeur if lp else None)
                except Exception:
                    _noter_erreur("cout.ajouter")
                    pass
        self.sauver_comptes()
        return noms

    def exo_deduite(self, nom: str, registre=None, objet: str = "", chute: float = 0.0):
        """(v94) Tentative d'exo reconnue à la chute de poids de l'objet (l'historique ne l'a pas lue) : le 23/10, 24 chutes
        de ~90 de poids contre 12 Ga Pme notées. On la compte, notée « deduite » dans le registre."""
        self.exo[nom] += 1
        self.estime[nom] += 1
        if registre is not None:
            registre.noter(objet=objet, certitude="deduite", rune=nom, exo=True, issue="échec avec pertes",
                           brut=f"chute de poids de l'objet : {chute:.0f}", version=_version_algo())
        self.sauver_comptes()

    def lecture_sans_entree(self, retard_possible: bool, registre=None, objet: str = "", resume: str = "") -> str:
        """L'objet a changé mais aucune entrée n'a pu être lue dans l'historique. Renvoie « retard » ou « perdue ».

        Si l'historique est bien aligné mais sans ligne nouvelle (`retard_possible`), le jeu ne l'a simplement pas encore
        mis à jour : la lecture suivante compare avec cette lecture périmée et rattrape la rune. On ne note « perdue »
        que si ça se produit deux fois de suite, ou si l'historique est inalignable."""
        if retard_possible and not self._retard_en_attente:
            self._retard_en_attente = True
            return "retard"
        self._retard_en_attente = False
        self.non_alignee(registre, objet, resume)
        return "perdue"

    def entrees_recues(self):
        self._retard_en_attente = False

    def non_alignee(self, registre=None, objet: str = "", resume: str = ""):
        """Des runes sont passées mais l'historique n'a pas pu être aligné : on le note (nombre inconnu)."""
        self.non_alignees += 1
        if registre is not None:
            registre.noter(objet=objet, certitude="perdue", rune=None, exo=False, brut=resume, version=_version_algo())
        self.sauver_comptes()

    def reinitialiser(self):
        self.exact.clear()
        self.estime.clear()
        self.exo.clear()
        self.illisibles = 0
        self.non_alignees = 0
        self.critiques = 0
        self.sauver_comptes()

    # --- bilan ---
    def lignes(self) -> List[dict]:
        noms = sorted(set(self.exact) | set(self.estime), key=lambda n: -(self.exact[n] + self.estime[n]))
        out = []
        for n in noms:
            q = self.exact[n] + self.estime[n]
            p = self.prix.get(n)
            out.append({"nom": n, "quantite": q, "estimees": self.estime[n], "prix": p,
                        "total": (p * q) if p else None})
        return out

    def total(self) -> Tuple[int, int]:
        """(sous-total chiffrable, nombre de runes sans coût connu, y compris illisibles)."""
        kamas, sans = 0, self.illisibles
        for l in self.lignes():
            if l["total"] is None:
                sans += l["quantite"]
            else:
                kamas += l["total"]
        return kamas, sans

    def nombre(self) -> int:
        return sum(self.exact.values()) + sum(self.estime.values())


def kamas(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " kamas"


def puits_disponible(panneau) -> Optional[float]:
    """(v103) Puits avant une passe : reliquat + poids des points AU-DESSUS du maximum (une ligne en over paie en premier).
    Sert à mesurer si une exo passe plus souvent quand ce puits couvre le poids de la rune (guide : « avec puits, tenter
    des Ga Pme jusqu'au passage du PM »)."""
    try:
        from forge.engine import charger_poids
        poids = charger_poids()
        total = float(panneau.reliquat or 0)
        for l in panneau.lignes:
            pp = poids.get(l.cle_poids)
            if pp is not None and l.maxi and l.maxi > 0 and l.valeur > l.maxi:
                total += (l.valeur - l.maxi) * float(pp)
        return round(total, 1)
    except Exception:
        _noter_erreur("cout.puits_disponible")
        return None
