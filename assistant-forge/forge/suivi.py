"""Suivi en continu : repère le panneau, détecte les changements, compare avant/après.

Ce module ne fait QUE traiter des images qu'on lui donne. Il n'agit jamais dans le jeu.
Principe de fiabilité : une lecture douteuse ne remplace jamais l'état connu, elle est signalée.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from dataclasses import replace

from forge.defilement import lire_defilement as _lire_defilement
from forge.historique import (detecter_icones, entrees_depuis_rangees, entrees_depuis_texte, nouvelles_entrees, runes_par_position,
                              nouvelles_entrees_structurees)
from forge.lecture import Panneau, lire_panneau, normaliser_elements, poids_objet, trouver_entete
from forge.erreurs import noter as _noter_erreur


INTERVALLE_STOCKS = 10.0  # secondes minimum entre deux lectures des cases de runes


# --- repérage du panneau --------------------------------------------------------------------

@dataclass
class Region:
    x0: int
    y0: int
    x1: int
    y1: int
    historique: Optional["Region"] = None  # panneau d'historique des runes (à gauche du tableau)
    # (v138) où était l'en-tête « Min Max » (pixels de l'image entière) et taille de l'image quand la zone a été calculée :
    # sert à voir que la découpe ne correspond plus (vidéo agrandie, fenêtre déplacée sur un autre écran...)
    sp: float = 0.0
    cx_min: float = 0.0
    cy: float = 0.0
    taille: Optional[Tuple[int, int]] = None

    def decouper(self, image):
        return image[self.y0:self.y1, self.x0:self.x1]


def localiser_panneau(image) -> Optional[Region]:
    """Trouve le panneau de forgemagie dans une image de fenêtre entière.

    On repère l'en-tête « Min  Max  Effets / Carac. » ; le reste de la zone se déduit de
    l'écartement des colonnes, ce qui suit automatiquement la taille de l'interface.
    """
    from forge.ocr import lire_elements
    elements, _ = lire_elements(image)
    ent = trouver_entete(normaliser_elements(elements))
    if ent is None:
        return None
    H, W = image.shape[:2]
    sp = ent["sp"]
    # La zone inclut la ligne « reliquat : N » (au-dessus de l'en-tête) et environ 13 lignes
    # d'objet ; elle s'arrête avant l'interface du bas du jeu (chat, barre d'objets...).
    y1 = min(H, int(ent["cy"] + 9.3 * sp))
    return Region(
        x0=max(0, int(ent["cx_min"] - 0.6 * sp)),
        y0=max(0, int(ent["cy"] - 2.0 * sp)),
        x1=min(W, int(ent["cx_min"] + 9.6 * sp)),
        y1=y1,
        historique=Region(
            x0=max(0, int(ent["cx_min"] - 4.95 * sp)), y0=max(0, int(ent["cy"] - 0.4 * sp)),
            x1=max(1, int(ent["cx_min"] - 0.65 * sp)), y1=y1),
        sp=float(sp), cx_min=float(ent["cx_min"]), cy=float(ent["cy"]), taille=(int(H), int(W)),
    )


DECALAGE_MAX = 0.5        # (v138) écart toléré de l'en-tête, en écarts Min-Max
ECHELLE_MAX = 0.15        # (v138) changement de taille toléré de l'écart Min-Max (15 %)
DECALAGES_AVANT_RECADRAGE = 1   # une image identique n'est pas relue : attendre 2 lectures pouvait bloquer pour toujours
SANS_ENTETE_AVANT_RECADRAGE = 8


def cadrage_decale(region: Region, entete) -> Optional[bool]:
    """(v138) L'en-tête lu dans la zone est-il ailleurs que là où la zone l'attend ? None si on ne peut pas juger
    (zone sans repère, en-tête non lu). Cas du 31/10 (vidéo) : zone calculée sur une vidéo plus petite, puis vidéo
    agrandie 1,5 fois ; l'en-tête était tout en haut de la zone, l'historique lu coupé (« -8 Fo », « - reliq »)."""
    if region is None or not region.sp or not entete:
        return None
    dx = entete["cx_min"] + region.x0 - region.cx_min
    dy = entete["cy"] + region.y0 - region.cy
    ds = entete["sp"] / region.sp
    return abs(ds - 1) > ECHELLE_MAX or abs(dx) > DECALAGE_MAX * region.sp or abs(dy) > DECALAGE_MAX * region.sp


# --- image stable ----------------------------------------------------------------------------

def pixels_changes(a, b, seuil: int = 30) -> int:
    """Nombre de pixels dont la luminosité diffère nettement entre deux images."""
    import cv2
    import numpy as np
    ga = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    gb = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    if ga.shape != gb.shape:
        return ga.size
    return int(np.count_nonzero(np.abs(ga.astype(np.int16) - gb.astype(np.int16)) > seuil))


class Stabilisateur:
    """Dit quand l'image vient de changer ET s'est stabilisée (donc prête à être lue).

    Évite de lire pendant une animation, et ne relit pas une image déjà lue.
    """

    def __init__(self, images_stables: int = 2, min_pixels: int = 6):
        self.images_stables = images_stables
        self.min_pixels = min_pixels
        self.precedente = None
        self.derniere_lue = None
        self.compteur = 0

    def pousser(self, image) -> bool:
        if self.precedente is not None and self.precedente.shape == image.shape:
            if pixels_changes(self.precedente, image) < self.min_pixels:
                self.compteur += 1
            else:
                self.compteur = 0
        else:
            self.compteur = 0
        self.precedente = image
        if self.compteur >= self.images_stables or (self.derniere_lue is None and self.compteur >= 1):
            if self.derniere_lue is None or (
                    self.derniere_lue.shape != image.shape
                    or pixels_changes(self.derniere_lue, image) >= self.min_pixels):
                self.derniere_lue = image
                return True
        return False


# --- comparaison avant / après ---------------------------------------------------------------

@dataclass
class Difference:
    changements: List[Tuple[str, int, int]] = field(default_factory=list)  # (libellé, avant, après)
    apparues: List[str] = field(default_factory=list)
    disparues: List[str] = field(default_factory=list)
    reliquat: Optional[Tuple[object, object]] = None  # (avant, après) si le reliquat affiché a changé
    historique: Optional[List[str]] = None  # lignes ajoutées en bas de l'historique (None = inconnu)
    bilan: Optional[dict] = None  # bilan du puits entre les deux lectures (voir bilan_puits)
    entrees: Optional[list] = None  # runes passées entre les deux lectures, lues dans l'historique (None = inconnu)

    @property
    def vide(self) -> bool:
        return not (self.changements or self.apparues or self.disparues or self.reliquat)


def comparer_panneaux(avant: Panneau, apres: Panneau) -> Difference:
    a, b = avant.par_id(), apres.par_id()
    d = Difference()
    for id_ in a.keys() & b.keys():
        if a[id_].valeur != b[id_].valeur:
            d.changements.append((b[id_].libelle, a[id_].valeur, b[id_].valeur))
    d.apparues = [b[i].libelle for i in b.keys() - a.keys()]
    d.disparues = [a[i].libelle for i in a.keys() - b.keys()]
    d.changements.sort()
    if avant.reliquat is not None and apres.reliquat is not None and avant.reliquat != apres.reliquat:
        d.reliquat = (avant.reliquat, apres.reliquat)
    return d


def bilan_puits(avant: Panneau, apres: Panneau, poids) -> Optional[dict]:
    """Compare la variation du reliquat à la variation de poids de l'objet.

    Règle vérifiée sur des données réelles (4 intervalles) : le reliquat baisse du poids ajouté à
    l'objet (gains moins pertes) ET du poids de chaque rune qui n'a rien donné (écart négatif).
        ecart = (reliquat après - reliquat avant) + (poids objet après - poids objet avant)
    ecart = 0 : toutes les runes ont donné quelque chose ; ecart = -P : des runes sans effet pesant P
    au total. Renvoie None si une donnée manque (reliquat illisible, poids inconnu, lignes en plus/moins).
    """
    if avant.reliquat is None or apres.reliquat is None:
        return None
    if {l.id for l in avant.lignes} != {l.id for l in apres.lignes}:
        return None
    if any(l.cle_poids not in poids for l in apres.lignes if not l.malus):
        return None
    d_poids = poids_objet(apres, poids)[0] - poids_objet(avant, poids)[0]
    d_reliquat = apres.reliquat - avant.reliquat
    ecrase = all(l.valeur == 0 for l in apres.lignes if not l.malus) and any(
        l.valeur != 0 for l in avant.lignes if not l.malus)
    return {"delta_poids": d_poids, "delta_reliquat": d_reliquat, "ecart": d_reliquat + d_poids,
            "plancher": apres.reliquat == 0 or avant.reliquat == 0, "ecrase": ecrase,
            "reliquat_avant": avant.reliquat,
            "hors_vue": sum(1 for l in apres.lignes if l.hors_vue)}


@dataclass
class Evenement:
    type: str  # panneau_introuvable | premiere_lecture | nouvel_objet | changement | lecture_douteuse | reliquat_instable | fenetre_recouverte | panneau_perdu
    message: str
    panneau: Optional[Panneau] = None
    difference: Optional[Difference] = None
    heure: float = field(default_factory=time.time)
    texte: str = ""  # texte brut lu par le moteur (utile pour comprendre une lecture douteuse)
    avant: Optional[Panneau] = None  # événement « historique » : panneau stable précédent
    chrono: Optional[dict] = None  # durées mesurées (secondes) : lecture_s, historique_s, attente_s
    stocks: Optional[dict] = None  # événement « stabilise » : stock de runes lu sur les cases {id de ligne: {taille: quantité}}
    zone = None  # image de la zone lue (sauvegardée par le journal quand la lecture est douteuse)


def _infobulle_d_objet(texte: str) -> bool:
    """Fiche de l'objet (souris sur l'amulette...) : liste d'effets « valeur Libellé [min à max] »,
    poids, prix, quantité. Ses lignes ressemblent à celles du tableau mais ne sont PAS l'état forgé."""
    import re
    t = texte.lower()
    return ("quantite en inventaire" in t or "quantité en inventaire" in t) and len(re.findall(r"\[[^\]]*\]", texte)) >= 3


def _fenetre_assistant_visible(texte: str) -> bool:
    """Vrai si l'OCR lit la fenêtre de l'assistant elle-même (posée par-dessus le jeu).

    Signes propres à notre fenêtre : colonnes « Cible / État », « source de puits », nos messages d'alerte.
    """
    t = " ".join(texte.lower().replace("é", "e").replace("è", "e").split())
    marques = ("cible etat", "source de puits", "lecture douteuse", "etat precedent est conserve",
               "tableau des lignes", "presque parfait")
    if sum(m in t for m in marques) >= 1 and ("cible" in t or "source de puits" in t or "lecture douteuse" in t):
        return True
    # (OCR v161) notre message « La fenêtre de l'assistant recouvre le tableau » et nos cases d'options : textes propres
    # à notre fenêtre, lus sans espaces ni accents (« afenetre de I'assistant recouvre... »). Vu sur corpus_ocr : notre
    # fenêtre lue comme un tableau du jeu (11-01_112504/douteux_024627).
    c = _compact(texte)
    return "assistantrecouvre" in c or ("sonsdalerte" in c and "cadresansanimation" in c)


def _compact(texte: str) -> str:
    """Texte sans accents, sans espaces ni chiffres, en minuscules : « QUANTITEEN BANQUE0 » -> « quantiteenbanque »."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", t)


def _infobulle_de_rune_stricte(texte: str) -> bool:
    """Règle d'origine (avant v161), gardée telle quelle."""
    t = texte.lower()
    return "carac" in t and "densit" in t and ("poids" in t or "prix moyen" in t)


def _infobulle_de_rune(texte: str) -> bool:
    if _infobulle_de_rune_stricte(texte):
        return True
    # (OCR v161) même fiche lue avec les espaces perdus ou une lettre changée (« Caroc. », « PRIXMOYEN », « POIDS1-LOT »).
    # « densit » n'apparaît jamais dans le tableau : c'est la marque propre à la fiche de rune.
    import re
    c = _compact(texte)
    return "densit" in c and ("poids" in c or "prixmoyen" in c) and bool(re.search(r"car[aeo]c|effets?|fusionn|reliq", c))


# (OCR v161) Marques d'une fiche d'objet, d'un menu ou d'une infobulle du jeu (jamais écrites dans le tableau lui-même).
_MARQUES_FICHE = ("quantiteen", "prixmoyen", "epingler", "valeurstheoriques", "partagerlobjet", "partagerlarecette",
                  "compareravec", "lieaupersonnage", "panoplie", "poids")


def _fiche_par_dessus(texte: str) -> bool:
    """(OCR v161) Fiche d'objet (orbe, potion, équipement...) ou menu du clic droit posé sur le tableau, non reconnu par
    _infobulle_d_objet (crochets perdus, espaces perdus). Mesuré sur corpus_ocr : cause n° 1 des lectures douteuses par
    session. Utilisé SEULEMENT quand la lecture est déjà douteuse : l'évènement reste « lecture_douteuse » (rien n'est
    appris de cette fiche, l'état précédent est conservé), seul le message dit la cause. Les fiches de rune sont
    traitées à part (_infobulle_de_rune)."""
    c = _compact(texte)
    return any(m in c for m in _MARQUES_FICHE) and not _infobulle_de_rune(texte)


def _fenetre_impossible(texte: str) -> bool:
    """Fenêtre d'erreur du jeu « Cette forgemagie est impossible » (elle cache une partie du tableau)."""
    t = texte.lower()
    return "impossible" in t and "forgemagie" in t


def _completer_bornes(panneau: Panneau, precedent: Optional[Panneau]):
    """Un Min/Max mal lu (« * » à la place de « 30 ») est repris de la lecture précédente de la même ligne."""
    if precedent is None:
        return
    anciennes = {l.id: l for l in precedent.lignes}
    communes = sum(1 for l in panneau.lignes if l.id in anciennes)
    if 2 * communes <= len(panneau.lignes):
        # (v120, C2) la plupart des lignes sont nouvelles : c'est un AUTRE objet, ses bornes ne sont pas celles d'avant
        return
    for l in panneau.lignes:
        a = anciennes.get(l.id)
        if a is None:
            continue
        if l.mini is None and a.mini is not None:
            l.mini = a.mini
        if l.maxi is None and a.maxi is not None:
            l.maxi = a.maxi
        if getattr(l, "bornes_supposees", False) and a.maxi is not None:
            # (v113, N3) bornes d'une ligne de base supposées (= sa valeur) : la lecture d'avant les connaît mieux si elle
            # les a lues, ou si elle supposait plus haut (Portée lue 2 puis tombée à 1 : son Max reste 2)
            if not getattr(a, "bornes_supposees", False) or a.maxi > l.maxi:
                l.mini, l.maxi = a.mini, a.maxi
                l.bornes_supposees = bool(getattr(a, "bornes_supposees", False))


def _zeros_incertains(panneau: Panneau, precedent: Optional[Panneau], compteur: Optional[dict] = None):
    """Une ligne lue « o » (0) sans Min/Max alors qu'elle valait plus avant : on garde l'ancienne valeur la première
    fois (l'OCR peut se tromper), on accepte le 0 s'il est lu deux fois de suite (la ligne est vraiment tombée)."""
    compteur = compteur if compteur is not None else {}
    anciennes = {l.id: l for l in precedent.lignes} if precedent is not None else {}
    for l in panneau.lignes:
        a = anciennes.get(l.id)
        if not (l.zero_incertain and a is not None and a.valeur > 0):
            compteur.pop(l.id, None)
            continue
        if l.modif.replace("−", "-").replace("–", "-") == f"-{a.valeur}":
            compteur.pop(l.id, None)  # la colonne Modif. confirme la chute (ex. 2 -> 0, modif « -2 ») : le 0 est vrai
            continue
        compteur[l.id] = compteur.get(l.id, 0) + 1
        if compteur[l.id] < 2:
            l.valeur = a.valeur
            panneau.notes.append(f"{l.libelle} : lue à 0 sans Min/Max (elle valait {a.valeur}) : valeur gardée, "
                                 "confirmation à la prochaine lecture.")
        else:
            compteur.pop(l.id, None)


def _lire_historique_complet(zone, etat: Optional[dict] = None):
    """Une seule lecture OCR de l'historique : (texte brut, entrées structurées par rune).
    (v143) Fenêtre de coopération : la zone est coupée au-dessus de son pied (« VIDER L'HISTORIQUE », sac d'ingrédients,
    paiement), pour le texte ET pour les icônes ; `etat["coop"]` dit si c'était le cas."""
    from forge.ocr import grouper_en_lignes, lire_elements, normaliser_elements, rangees
    elements, _ = lire_elements(zone)
    infos = normaliser_elements(elements)
    coop = False
    try:
        from forge.cooperation import haut_du_pied
        y = haut_du_pied(infos)
        if y is not None:
            coop = True
            garde = [i for i, inf in enumerate(infos) if inf.get("cy", 0) < y]
            elements, infos = [elements[i] for i in garde], [infos[i] for i in garde]
            zone = zone[:max(1, int(y) - 2)]
    except Exception:
        _noter_erreur("suivi._lire_historique_complet")
    if etat is not None:
        etat["coop"] = coop
    rs = [(sum(e["cy"] for e in r) / len(r), " ".join(e["t"] for e in r)) for r in rangees(infos)]
    icones = detecter_icones(zone)
    entrees = entrees_depuis_rangees(rs, icones, coop)
    # (v133) chaque entrée garde la bande de SON icône : identification par position, même quand une icône n'a donné
    # aucune entrée (avant : rien n'était identifié dès que les nombres différaient ; 76 % des échecs vidéo sans rune)
    if entrees:
        try:
            from forge.icones_historique import identifier_en_cache, recadrer_icone
            from forge import icones_apprises as IA
            for e, bande in ((e, e.bande) for e in entrees if e.bande is not None):
                r = identifier_en_cache(zone, bande)
                # (v117) icônes apprises sur tes passes sûres : comparées à l'ancienne méthode, retenues seulement si
                # elles font mieux (journaux/icones_stats.json)
                crop = recadrer_icone(zone, bande)
                crop = crop[0] if crop is not None else None
                r2 = IA.identifier(crop) if crop is not None else None
                vrai = _rune_sure(e)
                if vrai is not None and crop is not None:
                    IA.noter_comparaison(vrai, r[0] if r else None, r2[0] if r2 else None)
                    IA.apprendre(vrai, crop)
                choix = IA.choisir(r, r2)
                e.rune = choix[0] if choix else None
        except Exception:
            _noter_erreur("suivi._lire_historique_complet")
            pass
    return grouper_en_lignes(elements), entrees


def _rune_sure(e) -> Optional[str]:
    """(v117) Rune certaine d'une entrée : un seul gain, d'un montant qui est EXACTEMENT une taille de rune de la ligne
    (« +15 Vitalité » = Pa Vi). Sinon None (un gain mal lu ne doit pas apprendre une mauvaise icône)."""
    try:
        if len(e.gains) != 1 or e.incomplete:
            return None
        g = e.gains[0]
        from forge.cout import _ligne_id, _tailles
        from forge.runes_jeu import nom_rune
        r = _ligne_id(g.libelle, g.pct)
        if r is None:
            return None
        if r[0] in ("pa", "pm", "po", "invocation"):
            return None   # exo, remise ou rune spéciale : on n'apprend pas sur ces cas rares
        for taille, montant in ((_tailles().get(r[1]) or {}).get("runes") or {}).items():
            if montant == g.valeur:
                return nom_rune(r[0], taille)
    except Exception:
        _noter_erreur("suivi._rune_sure")
    return None


class Suivi:
    """Transforme un flux d'images en événements.

    lire : fonction image -> (panneau, moteur, texte). Par défaut la lecture réelle,
    sans relecture des cases Min/Max (elles ne changent pas pendant une session).
    """

    def __init__(self, lire: Optional[Callable] = None, periode_localisation: int = 10,
                 stabilisateur: Optional[Stabilisateur] = None,
                 lire_historique: Optional[Callable] = None, poids=None,
                 attente: float = 2.0, horloge: Callable[[], float] = time.time,
                 attente_rapide: Optional[float] = None, lire_defilement: Optional[Callable] = None,
                 lecture_forcee: Optional[float] = None):
        # (v119) lecture rapide : seules les bandes changées sont relues (forge/lecture_rapide.py), vérifiée contre la
        # lecture complète au début de chaque lancement ; absente quand `lire` est fourni (tests)
        self.lecteur = None
        if lire is None:
            from forge.lecture_rapide import LecteurIncremental
            self.lecteur = LecteurIncremental()
            lire = self.lecteur.lire
        self.lire = lire
        # relecture lente des cases Min/Max vides (chiffres seuls que l'OCR rapide ignore : 4/5, 1/1, 4/6...),
        # faite une seule fois par objet ; absente quand `lire` est fourni (tests).
        self.lire_complet = (lambda img: lire_panneau(img, relire=True)) if lire is None else None
        self._relecture_faite = None
        self._zeros = {}  # ligne -> nombre de lectures « 0 sans Min/Max » consécutives
        self.lire_historique = lire_historique  # None = lecture complète (texte + entrées par rune)
        self.derniere_zone_historique = None
        self.dernier_historique = None
        self.lire_defilement = lire_defilement or _lire_defilement
        if poids is None:
            from forge.engine import charger_poids
            poids = charger_poids()
        self.poids = poids
        # Le jeu affiche d'abord les stats, puis le reliquat et l'historique quelques secondes plus tard.
        # Le bilan et le conseil ne sont donc calculés qu'après `attente` secondes sans nouveau changement.
        self.attente = attente
        # Quand le reliquat a déjà changé, le jeu a fini de mettre l'affichage à jour : on peut conclure plus vite.
        self.attente_rapide = attente if attente_rapide is None else min(attente_rapide, attente)
        # (v87) quand tu enchaînes les runes, l'affichage ne reste jamais immobile : sans cette règle l'historique n'était
        # lu qu'à tes pauses, et au-delà de 6-7 runes d'un coup les plus anciennes sortaient de la fenêtre (passes perdues).
        # Avec `lecture_forcee` (secondes), on conclut et on lit l'historique au plus tard toutes les `lecture_forcee` s.
        self.lecture_forcee = lecture_forcee
        # (v93) lecture du texte d'une zone élargie pour les fiches de rune ; absente quand `lire` est fourni (tests)
        if lire is None:
            def _txt(img):
                from forge.ocr import lire_texte
                return lire_texte(img)[0]
            self.lire_texte_large = _txt
        else:
            self.lire_texte_large = None
        self._rafale_debut: Optional[float] = None   # heure du 1er changement depuis la dernière lecture
        self.horloge = horloge
        self.attente_depuis: Optional[float] = None
        self.etat_stable: Optional[Panneau] = None
        self._hist_attente = None  # (panneau, panneau stable précédent) : historique à lire au prochain passage
        self._image_etat = None    # (C1) image d'où vient le tableau self.etat
        self.derniere_fiche_rune = None  # (heure, texte) de la dernière fiche de rune vue
        self.derniere_alerte = ""  # évite de répéter indéfiniment la même lecture douteuse
        self.periode_localisation = periode_localisation
        self.stab = stabilisateur or Stabilisateur(images_stables=1)  # 1 paire d'images identiques suffit (0,15 s)
        self.region: Optional[Region] = None
        self.etat: Optional[Panneau] = None
        self.n_images = 0
        self.derniere_lecture_s = 0.0
        self.change_depuis: Optional[float] = None  # heure du dernier changement vu (pour mesurer l'attente réelle)
        self.signale_introuvable = False
        self.doute = False  # une lecture douteuse a eu lieu depuis le dernier état fiable
        # Garde-fou « reliquat qui clignote » : le chiffre du reliquat est parfois lu 7 puis 1 puis 7... alors
        # que les lignes ne bougent pas. Après deux allers-retours on cesse de lui faire confiance.
        self.rel_avant: object = None  # valeur du reliquat avant le dernier changement « reliquat seul »
        self.rel_aller_retours = 0
        self.rel_instable = False

    def traiter(self, image) -> List[Evenement]:
        evs = []
        retard = self._lire_historique_en_retard(image)
        if retard is not None:
            evs.append(retard)
        evs += self._traiter_image(image)
        if getattr(self, "historique_meme_image", False) and self._hist_attente is not None:
            # (v107, vidéo) l'historique est lu sur la MÊME image que le tableau : en vidéo le joueur clique vite, et lire
            # l'historique à l'image suivante décalait tableau et historique (état « avant » faux 9 fois sur 10 le 24/10)
            meme = self._lire_historique_en_retard(image)
            if meme is not None:
                evs.append(meme)
        for e in evs:
            # (v112, J1) on AJOUTE la durée de lecture du tableau : avant, ce remplacement effaçait `historique_s`
            e.chrono = dict(e.chrono or {}, lecture_s=round(self.derniere_lecture_s, 3))
            if self.lecteur is not None and self.lecteur.derniere:
                e.chrono.update({k: v for k, v in self.lecteur.derniere.items() if k != "duree_s"})
            try:   # (v126) quel calcul a servi à lire (openvino / origine) : pour comparer les temps dans le diagnostic
                from forge.accel import etat as _etat_accel
                e.chrono["ocr_moteur"] = _etat_accel()
            except Exception:
                _noter_erreur("suivi.etat_accel")
            if e.type in ("premiere_lecture", "nouvel_objet"):
                self._lignes_cy = {}
                self.etat_stable = None  # autre objet ou première lecture : rien à comparer
                self._rafale_debut = self.horloge()
                self.attente_depuis = self.horloge()
                self.change_depuis = self.horloge()
            elif e.type in ("changement", "reliquat_instable"):
                if self._rafale_debut is None:
                    self._rafale_debut = self.horloge()
                self.attente_depuis = self.horloge()
                self.change_depuis = self.horloge()
            elif e.type in ("panneau_perdu", "panneau_introuvable"):
                self.etat_stable, self.attente_depuis, self._rafale_debut = None, None, None
        stable = self._verifier_stabilise(image)
        if stable is not None:
            evs.append(stable)
        return evs

    def _lancer_stocks(self, image, panneau):
        """Lecture des cases de runes dans un fil à part : elle ne retarde jamais le conseil."""
        import threading
        if getattr(self, "sans_stocks", False):
            return  # (v97) mode analyse vidéo : on ne lit pas les cases de runes
        if getattr(self, "_fil_stocks", None) is not None and self._fil_stocks.is_alive():
            return  # la lecture précédente n'est pas finie : la suivante prendra le relais
        if getattr(panneau, "entete", None) is None or self.region is None:
            return
        zone = self.region.decouper(image).copy()
        panneau = self._avec_lignes_connues(panneau)
        self._zone_stocks = (zone, panneau)
        # La lecture des cases partage le processeur avec la lecture du tableau : elle la ralentissait de moitié.
        # On ne la lance donc qu'une fois toutes les INTERVALLE_STOCKS secondes (le stock baisse de toute façon à
        # chaque rune passée) ; le bouton « Relire les cases maintenant » la force.
        if time.time() - getattr(self, "_fiche_vue", 0.0) < 3.0:
            return  # une fiche (souris sur une rune) cache les cases : leurs « chiffres » seraient ceux de la fiche
        if time.time() - getattr(self, "_dernier_stock", 0.0) < INTERVALLE_STOCKS:
            return
        self._dernier_stock = time.time()

        def travail():
            res = self._lire_stocks(zone, panneau)
            self.stocks_resultat = (time.time(), res, self.diag_stocks)

        self._fil_stocks = threading.Thread(target=travail, daemon=True)
        self._fil_stocks.start()

    def _avec_lignes_connues(self, panneau):
        """Le tableau du jeu met en surbrillance la dernière ligne forgée, ce qui la rend parfois illisible : on
        retrouve alors sa hauteur grâce à une lecture précédente, tant que les autres lignes n'ont pas bougé."""
        from types import SimpleNamespace
        vues = {l.id: l for l in panneau.lignes if l.cy and not getattr(l, "hors_vue", False)}
        connues = getattr(self, "_lignes_cy", {})
        if any(i in connues and abs(connues[i].cy - l.cy) > 4 for i, l in vues.items()):
            connues = {}  # la disposition du tableau a changé : on repart de zéro
        connues = dict(connues)
        connues.update(vues)
        self._lignes_cy = connues
        manquantes = [l for i, l in connues.items() if i not in vues]
        if not manquantes:
            return panneau
        return SimpleNamespace(entete=panneau.entete, lignes=list(panneau.lignes) + manquantes)

    def relire_stocks(self) -> bool:
        """Relit toutes les cases (mémoire effacée) à partir de la dernière image du tableau."""
        from forge.cases_runes import _CACHE
        z = getattr(self, "_zone_stocks", None)
        if z is None:
            return False
        _CACHE.clear()
        if getattr(self, "_fil_stocks", None) is not None and self._fil_stocks.is_alive():
            return True
        import threading

        def travail():
            res = self._lire_stocks(*z)
            self.stocks_resultat = (time.time(), res, self.diag_stocks)
        self._fil_stocks = threading.Thread(target=travail, daemon=True)
        self._fil_stocks.start()
        return True

    def _lire_stocks(self, zone, panneau) -> Optional[dict]:
        """Stock de runes lu sur les cases Ba/Pa/Ra du tableau (une fois par stabilisation). Jamais d'erreur."""
        self.diag_stocks = ""
        if getattr(panneau, "entete", None) is None:
            self.diag_stocks = "en-tête Min/Max introuvable"
            return None
        try:
            from forge.cases_runes import lire_stocks
            from forge.conseil import charger_infos
            infos = charger_infos()
            tailles = {k: v["runes"] for k, v in infos.items() if v.get("runes")}
            res = lire_stocks(zone, panneau, tailles)
            if not res:
                self.diag_stocks = "aucun nombre lu dans les cases (voir journaux/diag_cases.png)"
                try:
                    from forge.cases_runes import sauver_diagnostic
                    sauver_diagnostic(zone, panneau, tailles)
                except Exception:
                    _noter_erreur("suivi._lire_stocks")
                    pass
            return res or None
        except Exception as e:
            _noter_erreur("suivi._lire_stocks")
            self.diag_stocks = f"erreur : {e}"
            return None

    def _lire_fiche_large(self, image, texte: str) -> str:
        """Texte d'une zone élargie autour du tableau (fiche de rune qui déborde). '' si impossible ou pas encore lu.

        (v109) La lecture élargie (OCR lent) se fait dans un fil à part et UNE fois par rune survolée (clé = nom de la rune,
        pas le texte complet qui change à chaque image) : avant, chaque survol bloquait la lecture du tableau."""
        import re as _re
        import threading
        if self.region is None or self.lire_texte_large is None:
            return ""
        m = _re.search(r"rune\s*[a-zé]+(?:\s*[a-zé]+){0,3}", (texte or "").lower())
        if m:
            cle = _re.sub(r"\s+", "", m.group(0))
        else:
            # (v162) nom de la rune coupé par le bord du tableau (cas habituel) : avant, la clé était le début du texte
            # (« reliquat : 2.2 FUSIONNER... »), le même pour toutes les runes -> la fiche de la rune précédente restait
            # gardée 30 s. La clé est maintenant la partie FICHE du texte (dès « EFFET », « POIDS », « DENSITE »...).
            t = texte or ""
            # (v165c) clé STABLE : densité + 3 premiers chiffres du prix moyen. La clé v162 (tout le texte de la fiche)
            # changeait à presque chaque image à cause du bruit de lecture (617 changements sur 642 fiches, session du
            # 06/11) : la lecture large était relancée sans cesse et son résultat jamais transmis (0 fiche sur 642).
            d = _re.search(r"DENSIT\S*\s*(\d{1,3})", t, _re.I)
            p = _re.search(r"PRIX\s*MOYEN\s*(\d[\d  .]{0,12})", t, _re.I)
            if d or p:
                cle = "fiche:" + (d.group(1) if d else "?") + "/" + (_re.sub(r"\D", "", p.group(1))[:3] if p else "?")
            else:
                i = min([j for j in (t.upper().find(k) for k in ("EFFET", "POIDS", "DENSIT", "PRIX")) if j >= 0] or [0])
                cle = _re.sub(r"\s+", "", t[i:])
        now = time.time()
        if cle == getattr(self, "_fiche_large_pour", None) and now - getattr(self, "_fiche_large_t", 0.0) < 30.0:
            return getattr(self, "_fiche_large_texte", "")
        fil = getattr(self, "_fil_fiche", None)
        if fil is not None and fil.is_alive():
            return ""
        self._fiche_large_pour, self._fiche_large_t, self._fiche_large_texte = cle, now, ""
        try:
            r = self.region
            H, W = image.shape[:2]
            l, h = r.x1 - r.x0, r.y1 - r.y0
            x0, x1 = r.x0 + int(0.45 * l), min(W, r.x1 + int(0.75 * l))
            y0, y1 = r.y0, min(H, r.y1 + int(0.35 * h))
            zone = image[y0:y1, x0:x1].copy()
        except Exception:
            _noter_erreur("suivi._lire_fiche_large")
            return ""
        lire = self.lire_texte_large

        coupe = texte or ""

        def travail():
            try:
                self._fiche_large_texte = lire(zone) or ""
                if self._fiche_large_texte and self._fiche_large_pour == cle:
                    # (v162) la fiche reste souvent immobile : aucune nouvelle image ne venait reprendre ce texte.
                    # On le donne tout de suite (la fenêtre le lit avec _verifier_fiche).
                    self.derniere_fiche_rune = (time.time(), self._fiche_large_texte + "\n" + coupe)
            except Exception:
                _noter_erreur("suivi._lire_fiche_large")
        self._fil_fiche = threading.Thread(target=travail, daemon=True)
        self._fil_fiche.start()
        return ""

    def _verifier_stabilise(self, image) -> Optional[Evenement]:
        """Événement « stabilise » : l'objet n'a plus bougé depuis `attente` secondes, on peut conclure."""
        if self.attente_depuis is None or self.etat is None or self.region is None:
            return None
        p = self.etat
        rapide = (self.etat_stable is not None and p.reliquat is not None
                  and p.reliquat != self.etat_stable.reliquat)
        t = self.horloge()
        force = bool(self.lecture_forcee and self._rafale_debut is not None and t - self._rafale_debut >= self.lecture_forcee)
        if t - self.attente_depuis < (self.attente_rapide if rapide else self.attente) and not force:
            return None
        self._rafale_debut = None
        self.attente_depuis = None
        p = self.etat
        ev = Evenement("stabilise", "Objet stabilisé.", p)
        ev.chrono = {"lecture_s": round(self.derniere_lecture_s, 3), "historique_s": 0.0,
                     "attente_s": round(self.horloge() - self.change_depuis, 3) if self.change_depuis else None}
        if self.etat_stable is not None:
            ev.difference = comparer_panneaux(self.etat_stable, p)
        self._lancer_stocks(image, p)
        # Le conseil part tout de suite ; l'historique (lent) est lu au passage suivant.
        # (v109, bug B6) ... mais sur L'IMAGE DE CE TABLEAU, gardée de côté : lu sur l'image suivante, l'historique contenait
        # parfois déjà la passe d'après (tableau et historique décalés, ~10 % des lectures le 24/10 à 17h24).
        # (v112, bug C1, 29/10) ... et pas l'image du moment où « stabilise » part : si une 2e rune est passée entre-temps,
        # son effet était déjà dans l'historique mais pas dans le tableau (80 % des passes « avant / après » fausses du 26 au
        # 28/10). On garde l'image d'où vient le tableau `p` (self._image_etat), lue au moment où `p` a été accepté.
        img = getattr(self, "_image_etat", None)
        if img is None:
            try:
                img = image.copy()
            except Exception:
                _noter_erreur("suivi._verifier_stabilise")
                img = None
        self._hist_attente = (p, self.etat_stable, img)
        self.etat_stable = p
        return ev

    def _cadrage_a_revoir(self, panneau) -> bool:
        """(v138) Vrai quand la zone ne correspond plus au panneau : en-tête lu ailleurs, ou jamais lu
        pendant SANS_ENTETE_AVANT_RECADRAGE lectures (alors on vérifie une fois en repérant de nouveau le panneau)."""
        r = self.region
        if r is None or not getattr(r, "sp", 0):
            return False
        decale = cadrage_decale(r, getattr(panneau, "entete", None))
        if decale is None:
            self._sans_entete = getattr(self, "_sans_entete", 0) + 1
            if self._sans_entete >= SANS_ENTETE_AVANT_RECADRAGE:
                self._sans_entete = 0
                return True
            return False
        self._sans_entete = 0
        self._decalages = getattr(self, "_decalages", 0) + 1 if decale else 0
        return self._decalages >= DECALAGES_AVANT_RECADRAGE

    def _recadrer(self, image, raison: str) -> Optional[bool]:
        """(v138) Repère de nouveau le panneau sur l'image entière, sans oublier l'objet suivi.
        None : introuvable (rien ne change) ; False : même découpe qu'avant ; True : découpe changée."""
        self._decalages = self._sans_entete = 0
        nouvelle = localiser_panneau(image)
        if nouvelle is None:
            return None
        ancienne = self.region
        self.region = nouvelle
        if ancienne is not None and (ancienne.x0, ancienne.y0, ancienne.x1, ancienne.y1) == (
                nouvelle.x0, nouvelle.y0, nouvelle.x1, nouvelle.y1):
            return False
        self.recadrages = getattr(self, "recadrages", []) + [(time.time(), raison)]
        if self.lecteur is not None:
            self.lecteur.oublier()   # autre cadrage : les images gardées ne servent plus
        self.stab = Stabilisateur(self.stab.images_stables, self.stab.min_pixels)
        self._image_etat = None      # les images gardées avaient l'ancienne découpe : on lira sur l'image du moment
        if self._hist_attente is not None:
            self._hist_attente = tuple(self._hist_attente[:2]) + (None,)
        return True

    def _lire_historique_en_retard(self, image) -> Optional[Evenement]:
        """Lit l'historique laissé en attente par « stabilise » et émet l'événement « historique »."""
        if self._hist_attente is None:
            return None
        p, avant, img = (tuple(self._hist_attente) + (None,))[:3]
        self._hist_attente = None
        if self.region is None or self.etat is None:
            return None
        if img is not None and getattr(img, "shape", None) == getattr(image, "shape", None):
            image = img
        t0 = time.perf_counter()
        self._joindre_historique(image, p)
        historique_s = time.perf_counter() - t0
        ev = Evenement("historique", "Historique lu.", p)
        ev.avant = avant
        ev.chrono = {"historique_s": round(historique_s, 3)}
        if avant is not None:
            d = comparer_panneaux(avant, p)
            d.historique = nouvelles_entrees(avant.historique, p.historique)
            d.entrees = nouvelles_entrees_structurees(avant.entrees, p.entrees)
            if d.entrees is None and getattr(self, "tolerant", False) and d.historique:
                d.entrees = entrees_depuis_texte(d.historique, [l.libelle for l in p.lignes],  # vidéo : icônes non vues, on découpe le texte
                                                 coop=bool(getattr(p, "coop", False)))
                try:   # (v133) rune de l'icône de la lecture en cours, si les effets sont exactement les mêmes
                    runes_par_position(d.entrees, p.entrees or [])
                except Exception:
                    _noter_erreur("suivi._lire_historique_en_retard")
            d.bilan = bilan_puits(avant, p, self.poids)
            ev.difference = d
        return ev

    def _traiter_image(self, image) -> List[Evenement]:
        self.n_images += 1
        if self.region is None:
            if (self.n_images - 1) % self.periode_localisation != 0:
                return []
            self.region = localiser_panneau(image)
            if self.lecteur is not None:
                self.lecteur.oublier()   # autre cadrage : les images gardées ne servent plus
            if self.region is None:
                if self.signale_introuvable:
                    return []
                self.signale_introuvable = True
                return [Evenement("panneau_introuvable",
                                  "Panneau de forgemagie introuvable : ouvre l'atelier de forgemagie "
                                  "et vérifie qu'aucune fenêtre ne le recouvre.")]
            self.signale_introuvable = False
            self.stab = Stabilisateur(self.stab.images_stables, self.stab.min_pixels)

        taille = getattr(self.region, "taille", None)
        if taille is not None and tuple(image.shape[:2]) != tuple(taille):
            # (v138) la fenêtre a changé de taille (agrandie, déplacée sur un écran d'une autre taille ou échelle) :
            # l'ancienne découpe ne correspond plus, on repère de nouveau le panneau (l'objet suivi est gardé)
            if self._recadrer(image, "taille de la fenêtre changée") is None:
                self.region = None   # introuvable sur la nouvelle taille : recherche normale (toutes les 10 images)
                return []

        zone = self.region.decouper(image)
        if zone.size == 0 or not self.stab.pousser(zone):
            return []

        t0 = time.perf_counter()
        panneau, _moteur, texte = self.lire(zone)
        self._relire_reliquat_coop(panneau, zone, texte)
        self.derniere_lecture_s = time.perf_counter() - t0
        if self._cadrage_a_revoir(panneau) and self._recadrer(image, "en-tête du tableau déplacé"):
            return []   # zone recalculée : la prochaine image est lue avec la bonne découpe
        if _fenetre_assistant_visible(texte):
            # L'OCR lit l'assistant lui-même : on ne touche pas à l'état, on demande de déplacer la fenêtre.
            if texte == self.derniere_alerte:
                return []
            self.derniere_alerte = texte
            ev = Evenement("fenetre_recouverte",
                           "La fenêtre de l'assistant recouvre le tableau du jeu : déplace-la à côté "
                           "(la lecture reprend toute seule).", texte=texte)
            ev.zone = zone
            return [ev]
        if _fenetre_impossible(texte):
            # Le jeu a refusé la rune : rien n'a changé, la fenêtre cache le tableau.
            if texte == self.derniere_alerte:
                return []
            self.derniere_alerte = texte
            ev = Evenement("forgemagie_impossible",
                           "Le jeu répond « Cette forgemagie est impossible » : rien n'a changé. "
                           "Clique sur OK ; la lecture reprend ensuite.", texte=texte)
            ev.zone = zone
            return [ev]
        _completer_bornes(panneau, self.etat)
        self._bornes_du_catalogue(panneau)
        self._relire_bornes(panneau, zone)
        _zeros_incertains(panneau, self.etat, self._zeros)
        self._fusionner_defilement(panneau, zone)
        if _infobulle_de_rune(texte) or _infobulle_d_objet(texte):
            self._fiche_vue = time.time()  # une fiche recouvre le tableau : on ne lit pas les cases de runes
        if _infobulle_de_rune(texte):
            # (v93) la fiche déborde souvent à droite / en bas du tableau (sur l'inventaire) : « PRIX MOYEN » et la quantité
            # étaient coupés. On relit une zone plus large, une seule fois par fiche.
            large = self._lire_fiche_large(image, texte)
            self.derniere_fiche_rune = (time.time(), (large + "\n" + texte) if large else texte)
        if _infobulle_d_objet(texte):
            # Les lignes de la fiche (« 347 Vitalité [301 à 350] ») peuvent passer pour des lignes du tableau :
            # on suspend toujours la lecture, sans toucher à l'état connu.
            if texte == self.derniere_alerte:
                return []
            self.derniere_alerte = texte
            ev = Evenement("infobulle", "Fiche de l'objet affichée (souris sur l'objet) : "
                           "lecture suspendue, l'état précédent est conservé.", texte=texte)
            ev.zone = zone
            return [ev]
        connues = {l.id for l in self.etat.lignes} if self.etat is not None else set()
        lues = {l.id for l in panneau.lignes}
        if panneau.avertissements and panneau.lignes and (
                (_infobulle_de_rune(texte) and connues and connues <= lues
                 # (OCR v161) fiche reconnue seulement par la nouvelle règle : on exige en plus qu'aucune ligne
                 # inconnue ne soit apparue (une ligne de la fiche ne doit pas entrer dans l'état)
                 and (_infobulle_de_rune_stricte(texte) or lues == connues))
                or (getattr(self, "tolerant", False) and self.etat is None and len(panneau.lignes) >= 4
                    and not any("double" in a or "approximative" in a for a in panneau.avertissements))):
            # (v99) fiche de rune ouverte mais tout le tableau relu : les lignes rejetées sont celles de la fiche
            # (POIDS, DENSITÉ, PRIX...) ; et en vidéo, première lecture acceptée si 4 lignes ou plus sont sûres.
            panneau.notes.extend(panneau.avertissements)
            panneau.avertissements = []
        if _infobulle_de_rune(texte) and (panneau.avertissements or not panneau.lignes):
            # Survol d'une rune : le jeu affiche une fiche (poids, densité, prix) sous le
            # tableau. Si le tableau reste lisible on continue normalement ; sinon on suspend la
            # lecture sans toucher à l'état connu, et on garde la fiche.
            if texte == self.derniere_alerte:
                return []
            self.derniere_alerte = texte
            ev = Evenement("infobulle", "Fiche de rune affichée (souris sur une rune) : "
                           "lecture suspendue, l'état précédent est conservé.", texte=texte)
            ev.zone = zone
            return [ev]
        if not panneau.lignes:
            self.region, self.etat = None, None
            self._image_etat = None
            return [Evenement("panneau_perdu", "Le panneau de forgemagie n'est plus visible.", panneau)]
        if panneau.avertissements and getattr(self, "tolerant", False) and self.etat is not None:
            # (v98) mode vidéo : l'image est souvent abîmée (compression, libellés coupés). Si toutes les lignes connues
            # sont relues, les lignes rejetées sont du bruit (doublons, historique collé) : on ne bloque pas.
            if {l.id for l in self.etat.lignes} <= {l.id for l in panneau.lignes}:
                panneau.notes.extend(panneau.avertissements)
                panneau.avertissements = []
        if panneau.avertissements:
            self.doute = True
            msg = ("Lecture douteuse, l'état précédent est conservé : "
                   + " | ".join(panneau.avertissements))
            if _fiche_par_dessus(texte):
                # (OCR v161) fiche d'objet ou menu du jeu sur le tableau : même évènement qu'avant (rien n'est appris de
                # la fiche, l'état est conservé) ; le message dit la cause et les cases de runes cachées ne sont pas lues.
                self._fiche_vue = time.time()
                msg = ("Lecture douteuse, l'état précédent est conservé : fiche ou menu du jeu affiché sur le tableau "
                       "(souris sur un objet) | " + " | ".join(panneau.avertissements))
            if msg == self.derniere_alerte:
                return []
            self.derniere_alerte = msg
            ev = Evenement("lecture_douteuse", msg, panneau, texte=texte)
            ev.zone = zone
            return [ev]
        self.derniere_alerte = ""
        if self.etat is None:
            self.etat, self.doute = panneau, False
            self._image_etat = image  # (C1) image d'où vient ce tableau
            self._joindre_historique(image, panneau)
            return [Evenement("premiere_lecture", "Objet lu.", panneau, texte=texte)]
        avant = self.etat
        diff = comparer_panneaux(avant, panneau)
        lignes_bougent = bool(diff.changements or diff.apparues or diff.disparues)
        alerte_reliquat = None
        if lignes_bougent:
            self.rel_aller_retours, self.rel_avant, self.rel_instable = 0, None, False
        elif self.rel_instable:
            panneau.reliquat = None  # toujours instable : on ne retient aucune valeur
            diff = comparer_panneaux(avant, panneau)
        elif diff.reliquat is not None:
            ancien, nouveau = diff.reliquat
            self.rel_aller_retours = self.rel_aller_retours + 1 if nouveau == self.rel_avant else 0
            self.rel_avant = ancien
            if self.rel_aller_retours >= 2:
                self.rel_instable = True
                panneau.reliquat = None
                diff = comparer_panneaux(avant, panneau)
                alerte_reliquat = Evenement(
                    "reliquat_instable",
                    f"Le reliquat saute entre {ancien:g} et {nouveau:g} alors que les lignes ne bougent pas : "
                    "chiffre mal lu (clignotement de l'affichage). Je ne m'en sers plus tant qu'aucune rune "
                    "n'a changé une ligne ; le conseil de rune est suspendu.", panneau)
        incertain = self.doute
        # Une rune ne change que quelques lignes ; si beaucoup apparaissent ou disparaissent
        # d'un coup, c'est un autre objet (on repart de zéro au lieu d'inventer des pertes).
        structure = len(diff.apparues) + len(diff.disparues)
        if structure >= 4 and structure >= len(self.etat.lignes) / 2:
            self.etat, self.doute = panneau, False
            self._image_etat = image  # (C1) image d'où vient ce tableau
            self._joindre_historique(image, panneau)
            return [Evenement("nouvel_objet", "Nouvel objet détecté : le suivi repart de zéro.", panneau,
                              texte=texte)]
        self.etat, self.doute = panneau, False
        self._image_etat = image  # (C1) image d'où vient ce tableau
        if alerte_reliquat is not None:
            return [alerte_reliquat]
        if diff.vide:
            # (v167b) l'image du tableau a changé mais pas l'objet : souvent les quantités des cases de runes (achat,
            # banque). Avant, les cases n'étaient relues qu'après une rune passée (« stabilise »). Même limite qu'avant :
            # au plus une lecture toutes les INTERVALLE_STOCKS secondes, jamais sous une fiche.
            self._lancer_stocks(image, panneau)
            return []
        modifs = [f"{l.libelle} : « {l.modif} »" for l in panneau.lignes if l.modif]
        msg = "Changement détecté."
        if incertain:
            msg += " (Une lecture douteuse a eu lieu entre-temps : plusieurs runes ont pu passer.)"
        if modifs:
            msg += " Colonne Modif. : " + " ; ".join(modifs)
        self._joindre_historique(image, panneau)
        diff.historique = nouvelles_entrees(avant.historique, panneau.historique)
        return [Evenement("changement", msg, panneau, diff, texte=texte)]

    def _relire_reliquat_coop(self, panneau, zone, texte) -> None:
        """(v143) Vidéo, fenêtre de coopération : « reliquat : » lu sans son chiffre (collé aux cases de runes). On relit
        la petite zone du chiffre ; il n'est gardé que si deux lectures donnent le même nombre bien formé. Sinon rien ne
        change : le reliquat reste inconnu (avertissement gardé). Le mode solo ne passe jamais ici."""
        case = getattr(panneau, "reliquat_case", None)
        if case is None or getattr(panneau, "reliquat", None) is not None or not getattr(self, "tolerant", False):
            return
        try:
            from forge.cooperation import relire_reliquat, table_coop
            from forge.lecture import RELIQUAT_ILLISIBLE
            from fractions import Fraction
            if not (table_coop(texte) or getattr(self, "_dernier_coop", False)):
                return
            n = relire_reliquat(zone, case)
            if n is None:
                return
            panneau.reliquat = Fraction(n)
            panneau.avertissements = [a for a in panneau.avertissements if a != RELIQUAT_ILLISIBLE]
            panneau.notes.append(f"Reliquat relu séparément (coopération) : {n}")
        except Exception:
            _noter_erreur("suivi._relire_reliquat_coop")

    def _bornes_du_catalogue(self, panneau: Panneau):
        """(v123) Objet reconnu (catalogue appris ou DofusDB) : ses Min/Max complètent ceux que l'OCR n'a pas lus
        (« 4 5 » de la Fuite, chiffres seuls souvent sautés). Un Min/Max lu n'est jamais changé."""
        cat = getattr(self, "catalogue", None)
        if cat is None or not any(l.mini is None or l.maxi is None for l in panneau.lignes):
            return
        try:
            r = cat.reconnaitre(panneau)
            if r is not None:
                from forge.objets import completer_bornes
                faits = completer_bornes(panneau, r[1])
                if faits:
                    panneau.notes.append("Min/Max repris de l'objet reconnu : " + ", ".join(faits))
        except Exception:
            _noter_erreur("suivi._bornes_du_catalogue")

    def _relire_bornes(self, panneau: Panneau, zone):
        """Min/Max manquants : une relecture lente, une seule fois pour ces lignes-là (jamais bloquante)."""
        if not panneau.manquants or self.lire_complet is None:
            return
        cle = tuple(sorted(panneau.manquants))
        if cle == self._relecture_faite:
            return
        self._relecture_faite = cle
        try:
            lent = self.lire_complet(zone)[0]
        except Exception:
            _noter_erreur("suivi._relire_bornes")
            return
        anciennes = {l.id: l for l in lent.lignes}
        for l in panneau.lignes:
            a = anciennes.get(l.id)
            if a is None:
                continue
            if l.mini is None and a.mini is not None:
                l.mini = a.mini
            if l.maxi is None and a.maxi is not None:
                l.maxi = a.maxi
        panneau.manquants = [f"{l.libelle} ({' et '.join(c for c, v in (('min', l.mini), ('max', l.maxi)) if v is None)})"
                             for l in panneau.lignes if l.mini is None or l.maxi is None]

    def _fusionner_defilement(self, p: Panneau, zone) -> None:
        """Objet à beaucoup de lignes : le tableau défile et seules ~12 lignes sont visibles.

        Une ligne qui sort de la vue n'est PAS perdue : on garde sa dernière valeur connue (marquée « hors vue »)
        au lieu de la compter comme disparue. Une ligne visible avant et absente maintenant, sans que la barre ait
        bougé, est en revanche une vraie disparition. Le programme ne défile jamais lui-même.
        """
        dfl = self.lire_defilement(zone)
        p.defilement = dfl
        if dfl is None:
            return  # pas de barre : tout tient dans le tableau
        prev = self.etat
        vus = p.par_id()
        if prev is not None and prev.lignes:
            connus = prev.par_id()
            commun = [i for i in vus if i in connus]
            accord = [i for i in commun if None in (vus[i].mini, vus[i].maxi, connus[i].mini, connus[i].maxi)
                      or (vus[i].mini, vus[i].maxi) == (connus[i].mini, connus[i].maxi)]
            if len(commun) >= 2 and len(accord) >= 0.7 * len(commun):  # même objet
                absentes = [l for i, l in connus.items() if i not in vus]
                nouvelles = len([i for i in vus if i not in connus])
                avant = prev.defilement
                if avant is not None and dfl.a_bouge(avant) and not dfl.longueur_a_change(avant):
                    garder = absentes  # simple défilement : tout ce qui est sorti de la vue est conservé
                elif avant is not None and not dfl.a_bouge(avant) and not dfl.longueur_a_change(avant):
                    garder = [l for l in absentes if l.hors_vue]  # rien n'a bougé : une ligne vue a vraiment disparu
                elif nouvelles >= len(absentes):
                    garder = absentes  # une ligne est apparue : elle a poussé les autres hors de la vue
                else:
                    garder = [l for l in absentes if l.hors_vue]
                for l in garder:
                    p.lignes.append(replace(l, hors_vue=True))
                if garder:
                    p.notes.append(f"{len(garder)} ligne(s) hors vue (tableau défilé) : dernière valeur lue conservée")
        estimees = len(vus) * (dfl.piste / dfl.long) if dfl.long else 0
        inconnues = estimees - len(p.lignes)
        p.non_lues = inconnues if inconnues >= 0.7 else 0.0

    def _joindre_historique(self, image, panneau: Panneau):
        """Lit le panneau d'historique des runes : texte brut + une entrée par rune (repérée par son icône)."""
        h = self.region.historique if self.region else None
        if h is None:
            return
        zone = h.decouper(image)
        if zone.size == 0:
            return
        # même image que la lecture précédente : inutile de relancer l'OCR (le plus coûteux)
        if (self.dernier_historique is not None and self.derniere_zone_historique is not None
                and self.derniere_zone_historique.shape == zone.shape
                and pixels_changes(self.derniere_zone_historique, zone) < self.stab.min_pixels):
            panneau.historique, panneau.entrees = self.dernier_historique
            panneau.coop = getattr(self, "_dernier_coop", False)
            return
        etat = {}
        try:
            if self.lire_historique is not None:
                panneau.historique, panneau.entrees = self.lire_historique(zone), []
            else:
                panneau.historique, panneau.entrees = _lire_historique_complet(zone, etat)
        except RuntimeError:
            panneau.historique, panneau.entrees = "", []
        panneau.coop = bool(etat.get("coop"))
        self._dernier_coop = panneau.coop
        self.derniere_zone_historique = zone
        self.dernier_historique = (panneau.historique, panneau.entrees)
