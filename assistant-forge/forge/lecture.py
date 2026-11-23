"""Transforme le texte lu à l'écran (panneau de forgemagie) en lignes structurées.

Principe de fiabilité : une ligne ambiguë ou inconnue n'est JAMAIS devinée.
Elle est rejetée et signalée dans `Panneau.avertissements`.
"""

from __future__ import annotations

import difflib
import json
import re
import statistics
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from forge.chemins import chemin_data
from forge.ocr import normaliser_elements, rangees

LIBELLES_FILE = chemin_data("libelles.json")

SOUS_MIN, DANS_JET, AU_MAX, OVER = "sous_min", "dans_jet", "au_max", "over"
SEUIL_FLOU = 0.88   # similarité minimale pour accepter un libellé mal lu
SEUIL_SUR = 0.90    # au-dessus : faute de lecture bénigne, signalée par une simple note


@dataclass
class Ligne:
    id: str
    cle_poids: str
    libelle: str
    valeur: int
    mini: Optional[int]
    maxi: Optional[int]
    pct: bool
    flou: bool = False       # libellé accepté malgré une petite erreur de lecture
    non_confirme: bool = False  # libellé jamais vu sur une capture réelle
    brut: str = ""
    lu_comme: str = ""  # libellé tel que lu par le moteur, quand il diffère légèrement du libellé reconnu
    hors_vue: bool = False  # ligne mémorisée : le tableau a défilé, sa valeur est celle de la dernière lecture
    modif: str = ""  # texte brut de la colonne « Modif. » (format encore inconnu : on le garde tel quel)
    cy: float = 0.0  # hauteur de la rangée à l'écran (pour lire les cases de runes)
    zero_incertain: bool = False  # « o » lu comme 0 sans Min/Max : refusé si la ligne valait plus à la lecture d'avant
    couleur: Optional[str] = None  # (v103) couleur du texte : « verte » ligne de base, « bleue » exo, « rouge » malus, « blanche » plus de stat (0)
    x_effet: Optional[tuple] = None  # (v103) début et fin du texte de la colonne Effets, pour lire sa couleur
    bornes_supposees: bool = False  # (v113, N3) Min/Max non lus, supposés égaux à la valeur (ligne de base PA/PM/PO verte)

    @property
    def exo_lue(self) -> bool:
        """(v103) Ligne exo : texte BLEU, ou (couleur inconnue) ni Min ni Max lus. Une ligne VERTE est une ligne de base,
        même si son Min/Max (souvent « 1 1 » pour PA/PM/PO) n'a pas été lu."""
        if self.couleur == "bleue":
            return True
        if self.couleur in ("verte", "rouge", "blanche"):
            return False
        return self.mini is None and self.maxi is None

    @property
    def malus(self) -> bool:
        """Ligne négative (ex. -5% Critique). On ignore comment le jeu pèse ces lignes."""
        return self.valeur < 0 or (self.maxi is not None and self.maxi < 0)

    @property
    def statut(self) -> Optional[str]:
        if self.mini is None or self.maxi is None:
            return None
        if self.valeur > self.maxi:
            return OVER
        if self.valeur == self.maxi:
            return AU_MAX
        if self.valeur < self.mini:
            return SOUS_MIN
        return DANS_JET


@dataclass
class Panneau:
    lignes: List[Ligne] = field(default_factory=list)
    avertissements: List[str] = field(default_factory=list)
    ignorees: List[str] = field(default_factory=list)
    texte_brut: str = ""
    notes: List[str] = field(default_factory=list)  # informations, n'enlèvent pas la fiabilité
    manquants: List[str] = field(default_factory=list)  # lignes dont Min et/ou Max n'ont pas été lus
    historique: str = ""  # texte brut du panneau d'historique des runes (format encore à découvrir)
    entrees: list = field(default_factory=list)  # historique structuré : une EntreeRune par rune passée
    defilement: object = None  # position de la barre de défilement du tableau (None = pas de barre)
    non_lues: float = 0.0  # estimation du nombre de lignes jamais lues (hors vue depuis le début)
    entete: object = None  # colonnes repérées (dictionnaire de trouver_entete), None si lecture par texte seul
    reliquat: Optional[Fraction] = None  # puits affiché par le jeu (« reliquat : 12 »), None si non lu
    # (v143) « reliquat : » lu sans son chiffre : (x de fin du mot, y du centre, hauteur), pour une relecture ciblée (coop)
    reliquat_case: Optional[tuple] = None
    coop: bool = False  # (v143) historique lu dans une fenêtre de coopération (pied « VIDER L'HISTORIQUE » repéré)

    @property
    def complet(self) -> bool:
        """Vrai si le Min et le Max de toutes les lignes sont connus."""
        return not self.manquants

    @property
    def fiable(self) -> bool:
        return bool(self.lignes) and not self.avertissements

    def par_id(self) -> Dict[str, Ligne]:
        return {l.id: l for l in self.lignes}


RELIQUAT_ILLISIBLE = "Reliquat affiché mais illisible : le puits n'est pas connu."


def _normaliser(texte: str) -> str:
    t = unicodedata.normalize("NFD", texte)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower().replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


_INTERFACE = re.compile(r"votre\s*m[eé]tier|annuler|types?\s*d.?\s*objets?|autoris[eé]s|fusionner|recettes?\b", re.I)


def texte_d_interface(brut: str) -> bool:
    """(v111) Texte de la fenêtre d'artisanat / de l'atelier (montée de métier) lu avec le tableau : à ignorer
    sans le compter comme une lecture douteuse (vu le 25/10 : 166 lignes « Votre métier Cordomage »)."""
    return bool(_INTERFACE.search(brut or ""))


def charger_libelles(chemin: Path = LIBELLES_FILE) -> Dict[str, dict]:
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)["libelles"]


_LIBELLES_LECTURE_SEULE: dict = {}


def libelles_lecture_seule(chemin: Path = LIBELLES_FILE) -> Dict[str, dict]:
    """(v162, vitesse) Même contenu que charger_libelles, gardé en mémoire et relu seulement si le fichier change
    (date ou taille). Objet PARTAGÉ : à lire seulement, jamais à modifier. Avant, cout._ligne_id relisait le fichier à
    chaque passe du registre (3 248 fois, 0,6 s à chaque rune posée sur 5 268 passes)."""
    import os
    import time
    m = _LIBELLES_LECTURE_SEULE
    maintenant = time.monotonic()
    if m.get("chemin") == str(chemin) and maintenant - m.get("verifie", -9.0) < 1.0:
        return m["libelles"]   # vérifié il y a moins d'une seconde (os.stat coûte cher ici : ~50 µs)
    st = os.stat(chemin)
    cle = (str(chemin), st.st_mtime_ns, st.st_size)
    if m.get("cle") != cle:
        m.update(cle=cle, libelles=charger_libelles(chemin))
    m.update(chemin=str(chemin), verifie=maintenant)
    return m["libelles"]


_NOMBRE = re.compile(r"(?<![\w])(-?\d+)(\s?%)?")


def analyser_ligne(brut: str, libelles: Dict[str, dict]) -> Tuple[Optional[Ligne], Optional[str]]:
    """Analyse une ligne de texte. Renvoie (ligne, None) ou (None, raison du rejet)."""
    # (v99) icône de la ligne lue comme une lettre collée au nombre (« 11 15 e9DommagesNeutre ») : on l'enlève
    brut = re.sub(r"(?:(?<=\s)|^)[a-zA-Z@*?!](?=\d)", " ", brut)
    nombres = list(_NOMBRE.finditer(brut))
    if len(nombres) == 2 and not nombres[1].group(2):
        # (v99) « 6%Critique 138 » : valeur + libellé, puis le stock de la case Pa (ligne sans Min/Max)
        lib = brut[nombres[0].end():nombres[1].start()]
        if re.search(r"[A-Za-zÀ-ÿ]{3,}", lib) and not re.search(r"[A-Za-zÀ-ÿ]{3,}", brut[nombres[1].end():]):
            ligne, raison = _construire_ligne(None, None, int(nombres[0].group(1)), bool(nombres[0].group(2)),
                                              _nettoyer_libelle(lib), libelles, brut)
            if ligne is not None:
                return ligne, None
    if not nombres and re.search(r"\d", brut):
        vl = _valeur_et_libelle(brut)
        if vl is None:
            return None, "chiffres collés à du texte : valeur ou libellé non lu"
        valeur, pct, libelle, _zero = vl
        return _construire_ligne(None, None, valeur, pct, libelle, libelles, brut)
    if len(nombres) <= 1:
        avant = brut[:nombres[0].start()] if nombres else brut
        z = _zero_o_libelle_connu(avant, libelles)
        if z is not None:  # « @oEsquivePA 18 » : valeur 0, le 18 est le stock de runes
            ligne, raison = _construire_ligne(None, None, 0, z[1], z[2], libelles, brut)
            if ligne is not None:
                ligne.zero_incertain = True
            return ligne, raison
    if not nombres:
        return None, "sans chiffre"
    if len(nombres) == 2:  # « 16 20 o Vitalité » : le 0 en gras est lu comme la lettre « o »
        z = _zero_lu_comme_o(brut[nombres[1].end():]) or _zero_o_libelle_connu(brut[nombres[1].end():], libelles)
        if z is not None and not (nombres[0].group(2) or nombres[1].group(2)):
            mini, maxi = int(nombres[0].group(1)), int(nombres[1].group(1))
            if mini <= maxi:
                return _construire_ligne(mini, maxi, 0, z[1], z[2], libelles, brut)
    if len(nombres) == 2 and re.search(r"[A-Za-zÀ-ÿ]{3,}", brut[:nombres[0].start()]) and not nombres[0].group(2):
        # (v97) « eliquat 350 335Vital » : du texte de l'historique (à gauche) collé à la ligne, et le Min coupé : on lit
        # (max, valeur) ; le Min est repris de la lecture précédente
        maxi, valeur = int(nombres[0].group(1)), int(nombres[1].group(1))
        if 0 <= valeur <= maxi:
            ligne, raison = _construire_ligne(None, maxi, valeur, bool(nombres[1].group(2)),
                                              _nettoyer_libelle(brut[nombres[1].end():]), libelles, brut)
            if ligne is not None:
                return ligne, None
    if len(nombres) > 3 and not any(m.group(2) for m in nombres[:2]):
        # (v98) « 61 80 76Force 7316 484 161 » : les nombres après le libellé sont le stock des cases Pa / Ra
        texte_lib = brut[nombres[2].end():nombres[3].start()]
        if re.search(r"[A-Za-zÀ-ÿ]{3,}", texte_lib):
            mini, maxi, valeur = (int(nombres[i].group(1)) for i in range(3))
            if mini <= maxi or (maxi < 0 and valeur < 0):
                ligne, raison = _construire_ligne(mini, maxi, valeur, bool(nombres[2].group(2)),
                                                  _nettoyer_libelle(texte_lib), libelles, brut)
                if ligne is not None:
                    return ligne, None
    if len(nombres) not in (1, 3):
        return None, (f"{len(nombres)} nombres lus ({[m.group(1) for m in nombres]}) : "
                      "attendu 3 (min, max, valeur) ou 1")
    dernier = nombres[-1]
    valeur = int(dernier.group(1))
    pct = bool(dernier.group(2))
    if len(nombres) == 3:
        mini, maxi = int(nombres[0].group(1)), int(nombres[1].group(1))
        if mini > maxi and not (maxi < 0 and valeur < 0):
            # (v99) une ligne malus s'affiche « -401 -500 -465 Initiative » (Min > Max en négatif) : acceptée
            return None, f"min ({mini}) supérieur au max ({maxi}) : lecture douteuse"
        if nombres[0].group(2) or nombres[1].group(2):
            return None, "signe % inattendu dans les colonnes Min/Max"
    else:
        mini = maxi = None

    reste = brut[dernier.end():]
    return _construire_ligne(mini, maxi, valeur, pct, _nettoyer_libelle(reste), libelles, brut)


_MOTS = {"vitalite": "Vitalité", "agilite": "Agilité", "portee": "Portée", "resistance": "Résistance",
         "resistances": "Résistances", "poussee": "Poussée", "melee": "mêlée", "pieges": "Pièges",
         "pa": "PA", "pm": "PM", "po": "PO", "a": "à", "de": "de", "aux": "aux", "en": "en",
         "sorts": "sorts", "distance": "distance", "d'armes": "d'armes"}


def _joli(cle: str) -> str:
    mots = cle.lstrip("%").split()
    out = [_MOTS.get(m, m.capitalize()) for m in mots]
    if out:
        out[0] = out[0][:1].upper() + out[0][1:]
    texte = " ".join(out)
    if cle.startswith("%resistance"):
        return "% " + texte  # résistance en pourcentage (poids 6), à ne pas confondre avec la résistance fixe (poids 2)
    if cle in ("resistance neutre", "resistance terre", "resistance feu", "resistance eau", "resistance air"):
        return texte + " (fixe)"
    return texte


def _nettoyer_libelle(reste: str) -> str:
    reste = re.sub(r"(?<=[A-Za-z])5(?=[A-Za-z])", "s", reste)  # « Sages5e » : le « s » lu comme un 5
    libelle = re.sub(r"[^A-Za-zÀ-ÿ' ]", " ", reste)
    libelle = re.sub(r"(?<=[a-zà-ÿ])(?=[A-Z])", " ", libelle)  # « DommagesAir » -> « Dommages Air »
    return re.sub(r"\s+", " ", libelle).strip()


def _construire_ligne(mini, maxi, valeur, pct, libelle, libelles, brut) -> Tuple[Optional[Ligne], Optional[str]]:
    if not libelle:
        return None, "aucun libellé après la valeur"
    cle = ("%" if pct else "") + _normaliser(libelle)
    flou = False
    par_prefixe = False
    une_lettre = False
    if cle not in libelles:
        memes = [k for k in libelles if k.startswith("%") == pct]
        proches = difflib.get_close_matches(cle, memes, n=2, cutoff=SEUIL_FLOU)
        if not proches:
            # vidéo compressée : le « a » est souvent lu « o » (Sogesse, Tocle, Resistonce Eou)
            alt = {}
            for k in memes:
                if len(k) >= 5:
                    alt.setdefault(k.replace("o", "a"), []).append(k)
            candidats = alt.get(cle.replace("o", "a"), [])
            if len(candidats) != 1 and len(cle.lstrip("%")) >= 6:
                # (v168d) UNE seule lettre fausse, même longueur (« Vifalité » : 87,5 % de ressemblance, sous le seuil de
                # 88 %) : acceptée si elle ne mène qu'à UNE ligne connue.
                sub = [k for k in memes if len(k) == len(cle) and sum(a != b for a, b in zip(k, cle)) == 1]
                if len({libelles[k].get("id") for k in sub}) == 1:
                    candidats, une_lettre = [sub[0]], True
            if len(candidats) != 1:
                # (v97) libellé COUPÉ au bord de l'image (vidéo plus petite, fenêtre étroite) : « Vital », « Sages »,
                # « Critig » ; accepté s'il commence UN SEUL libellé connu (5 lettres au moins), marqué approximatif
                base = cle.lstrip("%")
                if len(base) >= 4:
                    debut = [k for k in memes if k.lstrip("%").startswith(base)
                             or (len(base) >= 6 and k.lstrip("%").startswith(base[:-1]))]
                    ids = {libelles[k].get("id") for k in debut}
                    if len(ids) == 1:
                        candidats = [min(debut, key=len)]
                        par_prefixe = True
            if len(candidats) != 1:
                return None, f"libellé inconnu : {libelle!r}{' (avec %)' if pct else ''}"
            proches = candidats
        if len(proches) == 2:
            r1 = difflib.SequenceMatcher(None, cle, proches[0]).ratio()
            r2 = difflib.SequenceMatcher(None, cle, proches[1]).ratio()
            meme_ligne = libelles[proches[0]].get("id") == libelles[proches[1]].get("id")
            if r1 - r2 < 0.05 and not meme_ligne:
                return None, f"libellé ambigu : {libelle!r} ressemble à {proches}"
        ratio = difflib.SequenceMatcher(None, cle, proches[0]).ratio()
        cle, flou = proches[0], (ratio < SEUIL_SUR and not par_prefixe and not une_lettre)
        lu_comme = libelle
    else:
        lu_comme = ""
    info = libelles[cle]
    return Ligne(
        id=info["id"], cle_poids=info["poids"], libelle=_joli(cle), valeur=valeur,
        mini=mini, maxi=maxi, pct=pct, flou=flou, lu_comme=lu_comme,
        non_confirme=not info.get("vu_en_jeu", True), brut=brut,
    ), None


_ARME = re.compile(r"\d[aàαád]\d+(?:dom|vol)|vol(?:air|terre|feu|eau|neutre)")


def ligne_de_lecteur_video(brut: str) -> bool:
    """Menu du lecteur vidéo (« 1.0 1.25 1.5 2.0 », « 0.25x », « Playback speed ») : jamais une ligne d'objet."""
    t = brut.strip()
    return bool(re.match(r"\d\.\d+x?(\s+\d\.\d+x?)*", t)) or "playback" in t.lower()


def ligne_d_arme(brut: str) -> bool:
    """Ligne d'effet d'ARME (« 9 à 14 Dommages Neutre », « 5 à 8 Vol Air ») : une fourchette, pas un jet d'objet.
    Elle ne change jamais en forgemagie et ressemble aux lignes de dommages de l'objet : on l'ignore."""
    return bool(_ARME.search(re.sub(r"\s+", "", brut).lower().replace("é", "e")))


def analyser_texte(texte: str, libelles: Optional[Dict[str, dict]] = None) -> Panneau:
    """Analyse le texte d'un panneau complet (une ligne d'objet par ligne de texte)."""
    libelles = libelles or charger_libelles()
    p = Panneau(texte_brut=texte)
    vus = set()
    for brut in texte.splitlines():
        if not brut.strip():
            continue
        if ligne_d_arme(brut) or ligne_de_lecteur_video(brut):
            p.ignorees.append(brut.strip())
            continue
        ligne, raison = analyser_ligne(brut, libelles)
        if ligne is None:
            if raison == "sans chiffre" or texte_d_interface(brut):
                p.ignorees.append(brut.strip())  # en-têtes, bruit, (v111) textes de la fenêtre d'artisanat
            else:
                p.avertissements.append(f"Ligne rejetée « {brut.strip()} » : {raison}")
            continue
        if ligne.id in vus:
            p.avertissements.append(f"Ligne en double : {ligne.libelle!r} lue deux fois")
            continue
        vus.add(ligne.id)
        if ligne.flou:
            p.avertissements.append(
                f"Libellé « {ligne.libelle} » lu de façon approximative : vérifie la ligne.")
        elif ligne.lu_comme:
            p.notes.append(f"« {ligne.lu_comme} » lu, reconnu comme {ligne.libelle}")
        p.lignes.append(ligne)
    if not p.lignes:
        p.avertissements.append("Aucune ligne d'objet reconnue : mauvaise zone, ou fenêtre non ouverte.")
    return p


def etat_et_poids(p: Panneau, poids: Dict[str, Fraction]):
    """Renvoie (etat, poids_lignes, avertissements) prêts pour forge.engine.

    etat         : {id_ligne: valeur}
    poids_lignes : {id_ligne: poids par point}
    """
    etat, pl, avert = {}, {}, []
    for l in p.lignes:
        if l.cle_poids not in poids:
            avert.append(f"Poids inconnu pour {l.libelle!r} ({l.cle_poids}) : ajoute-le dans data/stats.json")
            continue
        etat[l.id] = l.valeur
        pl[l.id] = poids[l.cle_poids]
    return etat, pl, avert


def poids_objet(p: Panneau, poids: Dict[str, Fraction]) -> Tuple[Fraction, Optional[Fraction]]:
    """(poids actuel, poids du jet maximum). Le max vaut None si une ligne n'a pas de max lu."""
    actuel, maxi = Fraction(0), Fraction(0)
    max_connu = True
    for l in p.lignes:
        w = poids.get(l.cle_poids)
        if w is None or l.malus:
            continue
        actuel += w * l.valeur
        if l.maxi is None:
            max_connu = False
        else:
            maxi += w * l.maxi
    return actuel, (maxi if max_connu else None)


# --- lecture par colonnes (avec la position de chaque morceau de texte) ---------------------

_NOMBRE_SEUL = re.compile(r"^-?\d+$")


def _ressemble(texte: str, mot: str) -> bool:
    """Vrai si `texte` est `mot` ou une lecture à une lettre près (« McX » pour « Max »)."""
    t = _normaliser(texte)
    if t == mot:
        return True
    return len(t) == len(mot) and t[0] == mot[0] and sum(a != b for a, b in zip(t, mot)) <= 1


def _colonne_par_les_chiffres(infos: List[Dict], cy: float, h: float, x_gauche: float, x_droite: float) -> Optional[float]:
    """(OCR v161) Centre de la colonne de nombres seuls située entre x_gauche et x_droite, sous l'en-tête : au moins 3
    nombres, tous alignés à moins d'une demi-hauteur de texte de leur médiane. None sinon (on ne devine pas)."""
    xs = [i["cx"] for i in infos if i["cy"] > cy + 0.8 * h and _NOMBRE_SEUL.match(i["t"].strip())
          and x_gauche < i["cx"] < x_droite]
    if len(xs) < 3:
        return None
    m = statistics.median(xs)
    proches = [x for x in xs if abs(x - m) <= 0.5 * h]
    return m if len(proches) >= 3 and len(proches) >= 0.8 * len(xs) else None


def _entete_partiel(infos: List[Dict]):
    """(OCR v161) En-tête où un seul des mots « Min » / « Max » a été vu par le moteur (petit texte raté : 50 images d'une
    session réelle du 03/11). L'autre colonne est située par les nombres alignés en dessous. Renvoie (a, b) comme
    trouver_entete les attend (a = Min, b = Max, b peut être un élément reconstruit), ou None."""
    effets = [i for i in infos if re.search(r"effets|carac", i["t"], re.I)]
    for e in effets:
        rangee = [i for i in infos if abs(i["cy"] - e["cy"]) <= e["h"] and i["cx"] < e["x0"]]
        mins = [i for i in rangee if _ressemble(i["t"], "min")]
        maxs = [i for i in rangee if _ressemble(i["t"], "max")]
        h = e["h"]
        if len(mins) == 1 and not maxs:
            a = mins[0]
            cx = _colonne_par_les_chiffres(infos, e["cy"], h, a["cx"] + 1.5 * h, e["x0"])
            if cx is None:
                continue
            b = dict(a, t="Max", cx=cx, x0=cx - (a["cx"] - a["x0"]), x1=cx + (a["x1"] - a["cx"]))
        elif len(maxs) == 1 and not mins:
            b = maxs[0]
            cx = _colonne_par_les_chiffres(infos, e["cy"], h, -1e9, b["cx"] - 1.5 * h)
            if cx is None:
                continue
            a = dict(b, t="Min", cx=cx, x0=cx - (b["cx"] - b["x0"]), x1=cx + (b["x1"] - b["cx"]))
        else:
            continue
        sp = b["cx"] - a["cx"]
        # même géométrie que les en-têtes complets du corpus : « Effets » commence 0,5 à 1,3 écart après Max
        if sp > 0 and 0.5 * sp <= e["x0"] - b["cx"] <= 1.3 * sp:
            return a, b
    return None


def trouver_entete(infos: List[Dict]) -> Optional[Dict[str, float]]:
    """Repère les colonnes grâce à l'en-tête « Min  Max  Effets / Carac. »."""
    mins = [i for i in infos if _ressemble(i["t"], "min")]
    maxs = [i for i in infos if _ressemble(i["t"], "max")]
    ent = _trouver_entete(infos, mins, maxs)
    if ent is None:
        partiel = _entete_partiel(infos)
        if partiel is not None:
            ent = _trouver_entete(infos, [partiel[0]], [partiel[1]])
            if ent is not None:
                ent["partiel"] = True
    return ent


def _trouver_entete(infos: List[Dict], mins: List[Dict], maxs: List[Dict]) -> Optional[Dict[str, float]]:
    for a in sorted(mins, key=lambda i: i["cy"]):
        for b in sorted(maxs, key=lambda i: i["cy"]):
            if abs(a["cy"] - b["cy"]) <= max(a["h"], b["h"]) and b["cx"] > a["cx"]:
                sp = b["cx"] - a["cx"]
                cy = (a["cy"] + b["cy"]) / 2
                h = max(a["h"], b["h"])
                meme_rangee = [i for i in infos if abs(i["cy"] - cy) <= h and i["x0"] > b["cx"]]
                modif = next((i for i in meme_rangee if _normaliser(i["t"]).startswith("mod")), None)
                pa = next((i for i in meme_rangee if _normaliser(i["t"]) == "pa"), None)
                ra = next((i for i in meme_rangee if _normaliser(i["t"]) == "ra"
                           and pa is not None and i["cx"] > pa["cx"]), None)
                # Colonne Effets : de x_texte à x_fin. Colonne « Modif. » : de x_fin à x_pa.
                x_fin = modif["x0"] - 0.1 * sp if modif else b["cx"] + 4.7 * sp
                x_pa = pa["x0"] - 0.3 * sp if pa else x_fin + 2.0 * sp
                # Les nombres sous « Pa » / « Ra » (et la case juste avant) sont le STOCK de runes, pas la colonne
                # « Modif. » : celle-ci s'arrête à mi-chemin entre les en-têtes « Modif. » et « Pa ».
                x_modif_fin = (modif["cx"] + pa["cx"]) / 2 if modif and pa else x_fin + 1.0 * sp
                return {"cx_min": a["cx"], "cx_max": b["cx"], "sp": sp, "cy": cy, "h": h,
                        "x_texte": b["cx"] + 0.6 * sp, "x_fin": x_fin, "x_pa": x_pa,
                        "x_modif_fin": x_modif_fin,
                        "cx_pa": pa["cx"] if pa else None, "cx_ra": ra["cx"] if ra else None}
    return None


_NOMBRE_COLLE = re.compile(r"(-?\d+)(\s?%)?")


def _entier(s: str) -> Tuple[int, bool]:
    """'010' -> (10, True) : un zéro en tête est un parasite d'icône, jamais une vraie valeur."""
    neg = s.startswith("-")
    chiffres = s.lstrip("-")
    sans_zero = chiffres.lstrip("0") or "0"
    v = int(sans_zero)
    return (-v if neg else v), (len(chiffres) > 1 and chiffres.startswith("0") and sans_zero != chiffres)


def _valeur_et_libelle(s: str):
    """Dans le texte de la colonne Effets, renvoie (valeur, pct, libellé, zero_parasite) ou None.

    On prend le DERNIER nombre qui précède un libellé : un chiffre parasite venant
    d'une icône (placé avant la vraie valeur) est ainsi ignoré. Les chiffres collés
    aux lettres (« O1Portée », « 010Prospection ») sont acceptés.
    """
    for m in reversed(list(_NOMBRE_COLLE.finditer(s))):
        libelle = _nettoyer_libelle(s[m.end():])
        if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", libelle)) >= 2:
            valeur, zero = _entier(m.group(1))
            suite = s[m.end():]
            if re.match(r"[oO](?=\s*[A-ZÀ-Ý])", suite):
                libelle = _nettoyer_libelle(suite[1:])  # le « o » collé aux chiffres n'est pas dans le libellé
                if re.fullmatch(r"[1-9]", m.group(1)):
                    valeur *= 10  # « O1oProspection » : 10 dont le 0 est lu « o » (vu sur les journaux : 10, pas 1)
            return valeur, bool(m.group(2)), libelle, zero
    return None


def _modif_valide(texte: str) -> str:
    """Garde la pastille « Modif. » (« +11 », « -30 », « [-10] ») ; le reste est du bruit (stocks Pa/Ra)."""
    t = texte.strip()
    m = re.fullmatch(r"[\[\(]?\s*([+-]\s?\d{1,3})\s*[\]\)]?", t)
    return m.group(1).replace(" ", "") if m else ""


def _zero_lu_comme_o(s: str):
    """Un 0 en blanc gras est parfois lu comme la lettre « o » (objet tombé à 0 : « o Vitalité »).

    Renvoie (0, pct, libellé) si le texte commence par un « o » isolé suivi d'un libellé, sinon None.
    N'est appelé que si la ligne a déjà son Min et son Max : la structure de la ligne est donc sûre.
    """
    m = re.match(r"^\W*(?:[a-zA-Z@?*]\s+(?=[oO0]\s+[A-ZÀ-Ý]))?(?:(?:[wWdDqQ](?=[oO]\s*[A-Za-zÀ-ÿ])|[pPvVsS](?=[oO0][oO]?[A-Z]))?[oO0](?:[oO](?=[A-Z]))?|[pP](?=Prosp))\s*(%)?\s*([A-Za-zÀ-ÿ].*)$", s)
    if not m:
        return None
    libelle = _nettoyer_libelle(m.group(2))
    if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", libelle)) < 2:
        return None
    return 0, bool(m.group(1)), libelle


_ZERO_ICONE = re.compile(r"^\W*[a-zA-Z@?*¥￥]\s*[oO0]\s*(%)?\s*([A-Za-zÀ-ÿ].*)$")


def _zero_icone_quelconque(texte: str):
    """(v122) Ligne vide (valeur 0) dont l'icône est lue comme une lettre QUELCONQUE collée au 0 lu « o » :
    « eoDommage Neutre » (30/10 : 24 lectures rejetées de suite, suivi bloqué plus d'une minute). Toujours vérifié
    ensuite contre la liste des libellés connus (_zero_o_libelle_connu), jamais accepté seul."""
    m = _ZERO_ICONE.match(texte)
    if not m:
        return None
    libelle = _nettoyer_libelle(m.group(2))
    if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", libelle)) < 2:
        return None
    return 0, bool(m.group(1)), libelle


def _zero_o_libelle_connu(texte: str, libelles: Dict[str, dict]):
    """Valeur 0 lue « o » SANS Min/Max lus (chiffres seuls souvent ignorés par l'OCR) : on n'accepte que si le
    libellé qui suit est exactement un libellé connu, pour ne pas prendre un « o » de mot pour un zéro."""
    z = _zero_lu_comme_o(texte) or _zero_icone_quelconque(texte)
    if z is None:
        return None
    cle = ("%" if z[1] else "") + _normaliser(z[2])
    cle_sans_espace = cle.replace(" ", "")
    for c in libelles:   # « DommageNeutre » : espace perdu par l'OCR
        if c.replace(" ", "") == cle_sans_espace:
            cle = c
            break
    if re.match(r"^%?dommage[a-z]", cle):
        cle = re.sub(r"^(%?)dommage", r"\1dommage ", cle, count=1)
    if cle in libelles:
        return z
    # le jeu écrit « Dommage Feu » (singulier) quand la valeur est 0 ou 1 : on reconnaît aussi cette forme
    if re.match(r"^%?dommage\b", cle):
        plur = re.sub(r"^(%?)dommage\b", r"\1dommages", cle, count=1)
        if plur in libelles or re.sub(r"critique$", "critiques", plur) in libelles:
            return z
    return None


def rangee_coupee_en_bas(rang, h_entete: float, hauteur_image: Optional[float]) -> bool:
    """(OCR v161) Rangée coupée par le bas du tableau (seule la moitié haute des chiffres est visible : « 11 15 » sans
    libellé, vu ~140 fois de suite le 28/10). Elle touche le bord bas de l'image ET son texte est nettement moins haut
    que l'en-tête. Une telle rangée n'est pas lisible : on l'ignore (comme une ligne hors vue) au lieu de bloquer
    toute la lecture. Une ligne entière (hauteur normale) n'est jamais concernée."""
    if not hauteur_image or not rang or not h_entete:
        return False
    return (max(e["y1"] for e in rang) >= hauteur_image - 3
            and max(e["h"] for e in rang) <= 0.75 * h_entete)


def analyser_elements(
    elements,
    libelles: Optional[Dict[str, dict]] = None,
    relire: Optional[Callable[[str, float, float, float, float], Optional[int]]] = None,
    hauteur_image: Optional[float] = None,
) -> Optional[Panneau]:
    """Analyse le panneau à partir des morceaux de texte positionnés.

    Renvoie None si l'en-tête (Min / Max) est introuvable : l'appelant se rabat alors
    sur analyser_texte. `relire(col, cx, cy, hauteur, largeur)` relit une case vide.
    `hauteur_image` (OCR v161) : hauteur de l'image lue ; sert à reconnaître la rangée coupée par le bas du tableau.
    """
    libelles = libelles or charger_libelles()
    infos = normaliser_elements(elements)
    ent = trouver_entete(infos)
    if ent is None:
        return None
    from forge.ocr import grouper_en_lignes
    p = Panneau(texte_brut=grouper_en_lignes(elements), entete=ent)
    sp, x_texte = ent["sp"], ent["x_texte"]
    for rang in rangees([i for i in infos if i["cy"] < ent["cy"] - ent["h"]]):
        texte_haut = _normaliser(" ".join(e["t"] for e in rang))
        if "reliquat" in texte_haut:
            # (v116, C11) le nombre doit être complet : « 12 4 », « 0, 1 » ou « 1 012,5 » ne deviennent plus 12 / 0 / 1
            # (reliquat inconnu -> aucun conseil, plutôt qu'un conseil calculé sur un faux reliquat). Mesuré sur 5 729 lectures
            # (vidéos + ta session) : 27 refusées (0,5 %), dont 21 « 0, 1 » que l'ancienne lecture prenait pour 0.
            m = re.search(r"reliquat\s*:?\s*(-?\d+(?:[.,]\d+)?)(?![.,\d])", texte_haut)
            if m and not re.search(r"[.,]", m.group(1)) and re.match(r"\s+\d", texte_haut[m.end():]):
                m = None  # entier suivi d'un autre nombre (« 12 4 ») : décimale probablement perdue
            if m:
                p.reliquat = Fraction(m.group(1).replace(",", "."))
            else:
                p.avertissements.append(RELIQUAT_ILLISIBLE)
                mot = next((e for e in rang if "reliq" in _normaliser(e["t"])), None)
                if mot is not None and not re.search(r"\d", mot["t"]):
                    p.reliquat_case = (mot["x1"], mot["cy"], mot["h"])
            break
    corps = [i for i in infos if i["cy"] > ent["cy"] + 0.8 * ent["h"]]
    vus = set()
    for rang in rangees(corps):
        gauche = [e for e in rang if e["x0"] < x_texte - 0.1 * sp]
        droite = [e for e in rang if x_texte - 0.1 * sp <= e["x0"] < ent["x_fin"]]
        colonne_modif = [e for e in rang if ent["x_fin"] <= e["x0"] < min(ent["x_pa"], ent["x_modif_fin"])]
        utiles = gauche + droite + colonne_modif  # le reste (cases de runes) n'est que du bruit
        if not utiles:
            continue
        brut = " ".join(e["t"] for e in utiles)
        if ligne_d_arme(brut) or ligne_de_lecteur_video(brut):
            p.ignorees.append(brut)
            continue
        coupee = rangee_coupee_en_bas(rang, ent["h"], hauteur_image)

        def ignorer_coupee() -> bool:
            # (OCR v161) seulement à la place d'un avertissement : une rangée coupée bien lue reste traitée comme avant
            if coupee:
                p.ignorees.append(brut)
                p.notes.append(f"Ligne coupée par le bas du tableau, ignorée : « {brut} »")
            return coupee
        vl = _valeur_et_libelle(" ".join(e["t"] for e in droite))
        zero_en_o = False
        zero_sans_bornes = False
        if vl is None and len(re.findall(r"-?\d+", " ".join(e["t"] for e in gauche))) >= 2:
            z = (_zero_lu_comme_o(" ".join(e["t"] for e in droite))
                 or _zero_o_libelle_connu(" ".join(e["t"] for e in droite), libelles))
            if z is not None:
                vl, zero_en_o = (z[0], z[1], z[2], False), True
        if vl is None:
            z = _zero_o_libelle_connu(" ".join(e["t"] for e in droite), libelles)
            if z is not None:  # « @oEsquivePA » : ligne à 0 dont le Min/Max n'a pas été lu
                vl, zero_en_o, zero_sans_bornes = (z[0], z[1], z[2], False), True, True
        if vl is None:
            if ignorer_coupee():
                continue
            if re.search(r"\d", brut):
                p.avertissements.append(f"Ligne rejetée « {brut} » : valeur ou libellé non lu")
            else:
                p.ignorees.append(brut)
            continue
        valeur, pct, libelle, zero_parasite = vl
        icone_en_moins = False
        cy = sum(e["cy"] for e in rang) / len(rang)
        h = statistics.median(e["h"] for e in rang) if rang else ent["h"]
        cases: Dict[str, Optional[int]] = {"min": None, "max": None}
        for e in gauche:
            if _NOMBRE_SEUL.match(e["t"].strip()):
                if abs(e["cx"] - ent["cx_min"]) <= 0.5 * sp:
                    cases["min"] = int(e["t"])
                elif abs(e["cx"] - ent["cx_max"]) <= 0.5 * sp:
                    cases["max"] = int(e["t"])
            else:
                deux = re.findall(r"-?\d+", e["t"])
                if len(deux) == 2 and cases["min"] is None and cases["max"] is None:
                    cases["min"], cases["max"] = int(deux[0]), int(deux[1])
        for col in ("min", "max"):
            if cases[col] is None and relire is not None:
                n = relire(col, ent["cx_" + col], cy, h, 0.9 * sp)
                if n is not None:
                    cases[col] = n
                    p.notes.append(f"{libelle} : {col} relu séparément ({n})")
        mini, maxi = cases["min"], cases["max"]
        if valeur < 0 and mini is not None and mini >= 0 and maxi is not None and maxi >= 0:
            # l'icône placée devant la valeur est parfois lue « - » (« -328 Vitalité » pour 328, min 301, max 350) :
            # une ligne de jet normal (min et max positifs) ne peut pas être négative
            valeur, icone_en_moins = -valeur, True
        if mini is not None and maxi is not None and mini > maxi and not (maxi < 0 and valeur < 0):
            if ignorer_coupee():
                continue
            p.avertissements.append(f"Ligne « {libelle} » rejetée : min ({mini}) supérieur au max ({maxi})")
            continue
        ligne, raison = _construire_ligne(mini, maxi, valeur, pct, libelle, libelles, brut)
        if ligne is None:
            if ignorer_coupee():
                continue
            if texte_d_interface(brut):
                p.ignorees.append(brut)   # (v111) « Votre métier Cordomage », « ANNULER »... : pas une ligne d'objet
            else:
                p.avertissements.append(f"Ligne rejetée « {brut} » : {raison}")
            continue
        ligne.cy = cy
        if droite:
            ligne.x_effet = (min(e["x0"] for e in droite), max(e.get("x1", e["x0"]) for e in droite), h)
        ligne.modif = _modif_valide(" ".join(e["t"] for e in colonne_modif))
        ligne.zero_incertain = zero_sans_bornes
        if zero_en_o:
            p.notes.append(f"{ligne.libelle} : valeur lue « o », interprétée comme 0")
        if icone_en_moins:
            p.notes.append(f"{ligne.libelle} : signe « - » venant de l'icône ignoré (valeur {ligne.valeur})")
        if ligne.id in vus:
            p.avertissements.append(f"Ligne en double : {ligne.libelle!r} lue deux fois")
            continue
        vus.add(ligne.id)
        if ligne.flou:
            p.avertissements.append(
                f"Libellé « {ligne.libelle} » lu de façon approximative : vérifie la ligne.")
        elif ligne.lu_comme:
            p.notes.append(f"« {ligne.lu_comme} » lu, reconnu comme {ligne.libelle}")
        if zero_parasite:
            p.notes.append(f"{ligne.libelle} : un 0 parasite devant la valeur a été retiré ({ligne.valeur})")
        if mini is None or maxi is None:
            manque = " et ".join(c for c, v in (("min", mini), ("max", maxi)) if v is None)
            p.manquants.append(f"{ligne.libelle} ({manque})")
        p.lignes.append(ligne)
    if ent.get("partiel") and trou_dans_les_lignes([l.cy for l in p.lignes]):
        # (OCR v161) en-tête déduit des chiffres : un trou entre les lignes (fenêtre « Attention ! » posée sur le
        # tableau) ferait croire à des lignes perdues -> la lecture reste douteuse
        p.avertissements.append("Lignes cachées au milieu du tableau (fenêtre du jeu par-dessus ?) : lecture douteuse")
    if not p.lignes:
        p.avertissements.append("Aucune ligne d'objet reconnue : mauvaise zone, ou fenêtre non ouverte.")
    return p


def trou_dans_les_lignes(cys) -> bool:
    """Vrai si deux lignes lues consécutives sont séparées de plus de 1,6 fois l'écart habituel entre lignes."""
    cys = sorted(c for c in cys if c is not None)
    if len(cys) < 3:
        return False
    ecarts = [b - a for a, b in zip(cys, cys[1:])]
    habituel = statistics.median(ecarts)
    return habituel > 0 and max(ecarts) > 1.6 * habituel


def lire_panneau(image, relire: bool = True):
    """Lit un panneau de forgemagie sur une image (tableau numpy BGR).

    Renvoie (panneau, moteur, texte_brut). `relire=False` saute la relecture des cases
    Min/Max vides (plus rapide : utile en suivi continu, ces valeurs ne changent pas).
    """
    from forge.ocr import grouper_en_lignes, lire_elements, relire_nombre

    elements, moteur = lire_elements(image, tableau=True)   # (OCR v161) modèles du tableau
    texte = grouper_en_lignes(elements)
    cb = (lambda col, cx, cy, h, largeur: relire_nombre(image, cx, cy, h, largeur)) if relire else None
    panneau = analyser_elements(elements, relire=cb, hauteur_image=getattr(image, "shape", (None,))[0])
    if panneau is not None:
        colorer_lignes(panneau, image)
    if panneau is None:  # en-tête « Min / Max » introuvable : lecture par texte seul
        panneau = analyser_texte(texte)
        panneau.notes.append("En-tête Min/Max introuvable : lecture par le texte seul (moins fiable).")
    return panneau, moteur, texte


def couleur_texte(image, x0, x1, cy, h) -> Optional[str]:
    """(v103) Couleur du texte d'une ligne (valeur + libellé) : « verte » (ligne de base), « bleue » (exo), « rouge »
    (malus), « blanche » (plus de stat sur la ligne : valeur 0), ou None (image trop floue). L'icône à gauche est ignorée (on ne regarde que
    la partie à droite de l'icône). Testé sur des captures du jeu (Vitalité, Agilité verts ; -10 % Critique, -6 Tacle rouges)."""
    try:
        import numpy as np
        H, W = image.shape[:2]
        y0, y1 = int(max(0, cy - 0.35 * h)), int(min(H, cy + 0.35 * h))
        xa, xb = int(max(0, x0 + min(0.35 * (x1 - x0), 1.3 * h))), int(min(W, x1))  # saute l'icône
        z = image[y0:y1, xa:xb].reshape(-1, 3).astype(float) / 255.0
        if z.size == 0:
            return None
        b, g, r = z[:, 0], z[:, 1], z[:, 2]
        mx, mn = z.max(1), z.min(1)
        m = ((mx - mn) / np.maximum(mx, 1e-6) > 0.35) & (mx > 0.45)
        blanc = int((((mx - mn) / np.maximum(mx, 1e-6) < 0.15) & (mx > 0.5)).sum())
        if m.sum() < 8:
            return "blanche" if blanc >= 8 else None
        bb, gg, rr, M, d = b[m], g[m], r[m], mx[m], (mx - mn)[m]
        teinte = np.where(M == rr, ((gg - bb) / d) % 6, np.where(M == gg, (bb - rr) / d + 2, (rr - gg) / d + 4)) * 60
        vert = int(((teinte >= 70) & (teinte < 170)).sum())
        bleu = int(((teinte >= 170) & (teinte < 260)).sum())
        rouge = int(((teinte < 25) | (teinte >= 330)).sum())
        tot = vert + bleu + rouge
        if tot < 8:
            return None
        n, nom = max((vert, "verte"), (bleu, "bleue"), (rouge, "rouge"))
        return nom if n >= 0.6 * tot else None
    except Exception:
        from forge.erreurs import noter
        noter("lecture.couleur_texte")
        return None


def colorer_lignes(panneau, image) -> None:
    """(v103) Lit la couleur de chaque ligne. Une PA/PM/PO VERTE (ou BLANCHE : ligne de base vidée) sans Min/Max lu est une
    ligne de base : elle ne doit pas être prise pour une exo.

    (v113, N3) Une ligne de base a un Min et un Max égaux (« 2 2 Portée » sur une ceinture). On suppose donc
    Min = Max = sa valeur lue (au moins 1), et non plus 1 : avec « 1 à 1 », une Portée à 2 était vue en over (fausse alerte
    « exo/over, arrête-toi ici » et 51 de faux puits). La lecture suivante reprend les vraies bornes si elle les lit
    (suivi._completer_bornes)."""
    for l in panneau.lignes:
        if l.x_effet is None or not l.cy:
            continue
        x0, x1, h = l.x_effet
        l.couleur = couleur_texte(image, x0, x1, l.cy, h)
        if l.couleur in ("verte", "blanche") and l.mini is None and l.maxi is None and l.id in ("pa", "pm", "po"):
            l.mini = l.maxi = max(1, l.valeur)
            l.bornes_supposees = True
            panneau.notes.append(f"{l.libelle} : ligne verte (de base), Min/Max non lus : {l.mini} à {l.maxi} supposé.")
