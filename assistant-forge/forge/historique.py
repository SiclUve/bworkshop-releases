"""Historique des runes affiché à gauche du tableau : lecture et détection des lignes nouvelles.

Constat sur les vraies données : la liste est chronologique, la ligne la plus récente est EN BAS ;
quand elle est pleine, les plus anciennes disparaissent par le haut. Entre deux lectures, les lignes
nouvelles sont donc celles ajoutées en bas. Comparer deux lectures permet de savoir ce qui s'est passé
même si plusieurs runes ont été passées entre-temps.

Principe de fiabilité : si les deux listes ne peuvent pas être alignées avec certitude, on renvoie None
(« inconnu ») au lieu de deviner.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


def lignes_historique(texte: str) -> List[str]:
    return [l.strip(" :|") for l in (texte or "").splitlines() if l.strip(" :|")]


def _cle(ligne: str) -> str:
    t = unicodedata.normalize("NFD", ligne)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9%+\-]", "", t)


def _egal(a: str, b: str) -> bool:
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


_VIDE = re.compile(r"pas\s*d.?\s*historique", re.I)
# (v138) « ^[+-] reli » : ligne « + reliquat » coupée (zone trop étroite, 31/10 : « - reliq », « + relic ») ; elle était
# comptée comme texte d'une autre fenêtre et déclenchait à tort « Une autre fenêtre recouvre l'historique »
_LIGNE_FORGE = re.compile(r"(?i)succ[eè]s|[eé]chec|reliquat|pas\s*d.?\s*historique|^\s*\S?\s*[+-]?\d+\s*%?\s*[a-zé]"
                          r"|^\W{0,2}[+-]\s*reli", re.M)


def texte_etranger(texte: str) -> bool:
    """(v124, C5) Historique lu qui ne ressemble pas à l'historique de forge : une autre fenêtre est par-dessus (chat,
    autre programme : « Mode test (sans clic) » le 30/10, 38 lectures sur 140). Même règle que la routine (audit_donnees)."""
    lignes = [l for l in (texte or "").splitlines() if re.search(r"[a-zA-Z]{3}", l)]
    if len(lignes) < 3:
        return False
    return sum(1 for l in lignes if _LIGNE_FORGE.search(l)) < 0.3 * len(lignes)


def historique_vide(texte: str) -> bool:
    """(v109) « Il n'y a pas d'historique actuellement. » : aucune rune passée sur cet objet."""
    return bool(_VIDE.search(texte or ""))


def nouvelles_entrees(avant: str, apres: str) -> Optional[List[str]]:
    """Lignes ajoutées en bas de l'historique entre deux lectures, ou None si on ne peut pas aligner."""
    p, c = lignes_historique(avant), lignes_historique(apres)
    if historique_vide(avant) and c and not historique_vide(apres):
        # (v109, bug B7) l'historique était vide : TOUT est nouveau, sauf le nom de l'objet écrit en tête (pas d'effet chiffré)
        i = 0
        while i < len(c) and not re.search(r"\d", c[i]) and "reliquat" not in c[i].lower():
            i += 1
        return c[i:]
    return _ajoutees(p, c, [_cle(l) for l in p], [_cle(l) for l in c])


def _ajoutees(p, c, kp, kc):
    """Éléments de `c` ajoutés en bas par rapport à `p` (kp/kc : clés de comparaison), ou None."""
    if not p or not c:
        return None
    for i in range(len(kp) + 1):  # i = nombre de lignes anciennes sorties par le haut
        reste = kp[i:]
        k = len(reste)
        if k == 0:
            break
        if k > len(kc):
            continue
        ok = sum(_egal(a, b) for a, b in zip(reste, kc[:k]))
        if ok == k or (k >= 4 and ok >= 0.85 * k):
            return c[k:]
    return None


# --- lecture structurée : une entrée par rune passée ---------------------------------------------
#
# Vu sur la vidéo : chaque rune passée commence par SON ICÔNE à gauche, suivie de ses lignes :
#   « 3 Agilité » (gain), « -1 Sagesse » (perte), « + reliquat » (le reliquat a monté), « - reliquat » (il a baissé).
# Une entrée sans ligne « reliquat » avec un gain = succès critique (le reliquat n'a pas bougé), ce qui confirme
# la définition des guides. Les couleurs (vert/rouge) ne sont pas utilisées : le signe suffit.

@dataclass
class Effet:
    libelle: str
    valeur: int      # > 0 gain, < 0 perte
    pct: bool = False


@dataclass
class EntreeRune:
    effets: List[Effet] = field(default_factory=list)
    reliquat: Optional[str] = None   # "+" (monté), "-" (baissé) ou None (pas de ligne reliquat)
    brut: str = ""
    rune: Optional[str] = None       # rune reconnue d'après son icône (même sur un échec), None si doute
    incomplete: bool = False         # une rangée de cette entrée n'a pas pu être lue : l'issue est incertaine
    # (v133) bande (y_haut, y_bas) de l'icône de CETTE entrée : l'icône est identifiée à sa position, même quand une
    # autre icône de la lecture n'a donné aucune entrée (avant : tout était abandonné si les nombres différaient)
    bande: Optional[Tuple[int, int]] = field(default=None, compare=False, repr=False)

    @property
    def gains(self) -> List[Effet]:
        return [e for e in self.effets if e.valeur > 0]

    @property
    def pertes(self) -> List[Effet]:
        return [e for e in self.effets if e.valeur < 0]

    @property
    def issue(self) -> str:
        if self.incomplete:
            return "lecture incomplète"
        if self.gains:
            if self.reliquat is None and not self.pertes:
                return "succès critique"
            return "succès avec pertes" if self.pertes else "succès"
        if self.pertes:
            return "échec avec pertes"
        if self.reliquat is None:
            return "illisible"
        return "échec sans perte"

    def signature(self) -> str:
        return "|".join(f"{_cle(e.libelle)}{e.valeur:+d}" for e in self.effets) + f"|{self.reliquat or ''}"

    def resume(self) -> str:
        morceaux = [f"{e.valeur:+d}{'%' if e.pct else ''} {e.libelle}" for e in self.effets]
        if self.reliquat:
            morceaux.append(f"{self.reliquat} reliquat")
        tete = f"{self.rune} : " if self.rune else ""
        return tete + ", ".join(morceaux or [self.brut]) + f" → {self.issue}"


_RELIQUAT = re.compile(r"([+\-−–])?\s*r[eé]l[il1]q[a-z]{1,3}t?\b", re.I)  # « reliquqt », « reliquct » vus en vidéo
_EFFET = re.compile(r"([+\-−–]?\d+)\s*(%)?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' ]+)")


def _libelle_propre(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip(" '")


_LIBELLES: Optional[List[str]] = None


def _libelles_connus() -> List[str]:
    global _LIBELLES
    if _LIBELLES is None:
        from forge.lecture import charger_libelles
        _LIBELLES = sorted({k.lstrip("%") for k in charger_libelles()})
    return _LIBELLES


def libelle_reconnu(libelle: str) -> bool:
    """Le libellé lu est-il une vraie caractéristique ? L'historique écrit au singulier (« Dommage Air »)."""
    from forge.lecture import _normaliser
    cle = _normaliser(libelle)
    candidats = {cle, cle.replace("dommage ", "dommages ", 1), cle.replace("resistance ", "resistances ", 1),
                 cle.replace("dommage", "dommages", 1)}
    connus = _libelles_connus()
    if candidats & set(connus):
        return True
    return any(difflib.get_close_matches(c, connus, n=1, cutoff=0.85) for c in candidats)


def analyser_rangee(texte: str, coop: bool = False) -> Optional[Tuple[str, object]]:
    """Une rangée de l'historique -> ("reliquat", "+"/"-"/None) ou ("effet", Effet) ou None (bruit).
    (v143) `coop` : fenêtre de coopération (forge/cooperation.py) ; « relquat » est une ligne reliquat, et une perte dont
    le chiffre est perdu (« -i Dommage Neutre ») rend l'entrée incomplète au lieu d'être ignorée. Solo : inchangé."""
    m = _RELIQUAT.search(texte)
    if m is None and coop:
        from forge.cooperation import RELIQUAT_COOP
        m = RELIQUAT_COOP.search(texte)
    if m:
        signe = m.group(1)
        return "reliquat", ({"+": "+"}.get(signe, "-") if signe else None)
    trouves = list(_EFFET.finditer(texte))
    if not trouves:
        if coop:
            from forge.cooperation import effet_sans_chiffre
            if effet_sans_chiffre(texte):
                return "inconnu", texte   # une perte a eu lieu, sa valeur n'est pas lue : on ne l'invente pas
        return None
    e = trouves[-1]  # le dernier nombre suivi d'un libellé : un parasite d'icône placé avant est ignoré
    valeur = int(e.group(1).replace("−", "-").replace("–", "-"))
    libelle = _libelle_propre(e.group(3))
    if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", libelle)) < 2:
        return None
    if not libelle_reconnu(libelle):
        return "inconnu", texte  # des chiffres suivis de texte illisible : on ne l'invente pas
    return "effet", Effet(libelle, valeur, bool(e.group(2)))


def detecter_icones(image) -> List[Tuple[int, int]]:
    """Bandes verticales (y_haut, y_bas) occupées par une icône de rune dans la colonne de gauche de l'historique."""
    import numpy as np
    if image is None or image.size == 0:
        return []
    H, W = image.shape[:2]
    x0, x1 = int(0.04 * W), int(0.18 * W)
    bande = image[:, x0:x1].astype(int)
    if bande.size == 0:
        return []
    fond = np.median(bande.reshape(-1, bande.shape[-1]), axis=0)
    ecart = np.abs(bande - fond).max(axis=2)
    lignes = (ecart > 55).sum(axis=1) >= 3
    bandes, debut, dernier, trou = [], None, 0, 0
    for y, v in enumerate(lignes):
        if v:
            if debut is None:
                debut = y
            dernier, trou = y, 0
        elif debut is not None:
            trou += 1
            if trou > 3:
                bandes.append((debut, dernier))
                debut = None
    if debut is not None:
        bandes.append((debut, dernier))
    return [b for b in bandes if b[1] - b[0] >= 9]


def entrees_depuis_rangees(rangees_: Sequence[Tuple[float, str]], icones: Sequence[Tuple[int, int]],
                           coop: bool = False) -> List[EntreeRune]:
    """Regroupe les rangées de texte (y_centre, texte) par icône : une icône = une rune.

    Les rangées au-dessus de la première icône appartiennent à une rune dont l'icône est sortie de la vue : elles
    sont ignorées (on ne devine pas). Sans aucune icône, on ne devine pas non plus : liste vide.
    """
    if not icones:
        return []
    entrees: List[EntreeRune] = [EntreeRune(bande=tuple(b)) for b in icones]
    for y, texte in sorted(rangees_):
        k = -1
        for i, (h, b) in enumerate(icones):
            if y >= h - 8:
                k = i
        if k < 0:
            continue
        r = analyser_rangee(texte, coop)
        if r is None:
            continue
        entrees[k].brut += (" ; " if entrees[k].brut else "") + texte.strip()
        if r[0] == "inconnu":
            entrees[k].incomplete = True
        elif r[0] == "reliquat":
            entrees[k].reliquat = r[1] if r[1] else entrees[k].reliquat or "-"
        else:
            entrees[k].effets.append(r[1])
    return [e for e in entrees if e.effets or e.reliquat or e.incomplete]


def nouvelles_entrees_structurees(avant: Sequence[EntreeRune], apres: Sequence[EntreeRune]) -> Optional[List[EntreeRune]]:
    """Entrées ajoutées en bas entre deux lectures (même principe que `nouvelles_entrees`), ou None si inalignable.

    Limite : des entrées identiques qui se répètent (« - reliquat » × 3) peuvent faire sous-compter les nouvelles.
    """
    p, c = list(avant), list(apres)
    return _ajoutees(p, c, [e.signature() for e in p], [e.signature() for e in c])



def _cle_libelle(t: str) -> str:
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return "".join(re.sub(r"s$", "", w) for w in re.findall(r"[a-z%]+", t))


def runes_par_position(texte: Sequence[EntreeRune], icones: Sequence[EntreeRune]) -> int:
    """(v133) Entrées découpées par le TEXTE (vidéo, icônes non alignables entre deux lectures) : on reprend la rune
    identifiée par l'icône dans la lecture en cours, en partant du BAS de l'historique (les entrées nouvelles y sont),
    seulement tant que les effets et le reliquat sont exactement les mêmes. Renvoie le nombre de runes reprises."""
    n = 0
    for t, e in zip(reversed(list(texte)), reversed(list(icones))):
        if t.signature() != e.signature():
            break
        if t.rune is None and e.rune is not None:
            t.rune = e.rune
            n += 1
    return n


def entrees_depuis_texte(lignes: Sequence[str], ordre: Sequence[str] = (), coop: bool = False) -> List[EntreeRune]:
    """(v99c, vidéo) Découpe des lignes NOUVELLES de l'historique en runes, sans les icônes (souvent ratées sur un
    stream réduit). Vu sur les journaux : la ligne « reliquat » termine une rune ; les pertes peuvent être avant ou
    après le gain, dans n'importe quel ordre ; un succès critique = un gain seul (pas de perte, pas de reliquat).
    Donc, dans un bloc terminé par « reliquat » : chaque gain sauf le dernier est un critique seul, et toutes les
    pertes vont avec le dernier gain. Une même caractéristique perdue deux fois = deux runes. Moins sûr que les
    icônes : chaque rune est marquée « par_texte ». `ordre` est gardé pour compatibilité (non utilisé)."""
    blocs: List[Tuple[List[Effet], Optional[str], List[str], bool]] = []
    effets: List[Effet] = []
    bruts: List[str] = []
    incomplet = False

    def fermer(rel):
        nonlocal effets, bruts, incomplet
        if effets or rel or incomplet:
            blocs.append((effets, rel, bruts, incomplet))
        effets, bruts, incomplet = [], [], False

    for t in lignes:
        r = analyser_rangee(t, coop)
        if r is None:
            continue
        if r[0] == "reliquat":
            bruts.append(t.strip())
            fermer(r[1] or "-")
            continue
        if r[0] == "inconnu":
            incomplet = True
            bruts.append(t.strip())
            continue
        e = r[1]
        if e.valeur < 0 and any(x.valeur < 0 and _cle_libelle(x.libelle) == _cle_libelle(e.libelle) for x in effets):
            fermer(None)
        effets.append(e)
        bruts.append(t.strip())
    fermer(None)

    entrees: List[EntreeRune] = []
    for effets, rel, bruts, incomplet in blocs:
        gains = [i for i, x in enumerate(effets) if x.valeur > 0]
        for i in gains[:-1]:
            entrees.append(EntreeRune([effets[i]], None, effets[i].libelle))
        reste = [x for i, x in enumerate(effets) if i not in gains[:-1]]
        if reste or rel or incomplet:
            entrees.append(EntreeRune(reste, rel, " ; ".join(bruts), incomplete=incomplet))
    for e in entrees:
        e.par_texte = True
    return entrees
