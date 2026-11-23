"""Stock de runes lu sur les CASES de la fenêtre de forgemagie (Ba / Pa / Ra à droite de chaque ligne).

Chaque ligne a 1 à 3 cases (une par taille de rune, de la plus petite à la plus grosse). Une case pleine affiche
la quantité en haut à gauche ; une case vide est une boîte sombre. Une pile de 1 n'affiche peut-être pas de
nombre : « rien lu » veut donc dire 0 ou 1 (on garde 0, prudent).

Lecture seule : on regarde l'image, on ne touche à rien.
"""

from __future__ import annotations

import time
from typing import Dict, Optional
from forge.erreurs import noter as _noter_erreur

# Réglage fait sur une vraie capture (14 cases sur 15 justes). Les chiffres sont blancs ; l'icône de la rune
# est en couleur et gêne la lecture : on isole donc les chiffres (pixels blancs, même hauteur, côte à côte).
SEUIL_BLANC = 170
SEUILS = (170, 150, 190)  # trois seuils de « blanc » : chacun lit les chiffres avec les 6 réglages
ACCORD_MINI = 4  # lectures identiques minimum (sur 18 : 3 seuils × 6 réglages) pour accepter un nombre
MIN_CHIFFRES_LUS = 2  # en dessous, la lecture est jugée ratée et ne change rien
VARIANTES = (("w", 4, 3, 5), ("w", 6, 0, 0), ("w", 6, 3, 0), ("b", 8, 0, 5), ("w", 4, 0, 5), ("b", 6, 0, 0))
_CONFUSIONS = str.maketrans("LlIi|OoQDSsBZ?", "11111000055822")


def centres_cases(entete: dict, n: int):
    """Abscisses des n cases d'une ligne : la 1re est une case avant l'en-tête « Pa »."""
    pa, ra = entete.get("cx_pa"), entete.get("cx_ra")
    if pa is None and entete.get("x_fin") and entete.get("sp"):  # « Pa » mal lu : position habituelle
        pa = entete["x_fin"] + 2.35 * entete["sp"]
    if pa is None:
        return []
    if ra is None or ra <= pa:  # « Ra » mal lu : écart habituel entre cases, proportionnel à l'écart Min/Max
        sp = entete.get("sp")
        if not sp:
            return []
        ra = pa + 0.68 * sp
    pas = ra - pa
    return [pa + (k - 1) * pas + 6 for k in range(n)]


def _masque_chiffres(image, cx: float, cy: float, seuil: int = SEUIL_BLANC):
    """Image binaire ne contenant que les chiffres de la case (None si aucun chiffre)."""
    import collections
    import cv2
    import numpy as np
    H, W = image.shape[:2]
    y0, y1, x0, x1 = max(0, int(cy - 9)), min(H, int(cy + 6)), max(0, int(cx - 14)), min(W, int(cx + 18))
    c = image[y0:y1, x0:x1]
    if c.size == 0:
        return None
    m = (c.min(axis=2) > seuil).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    comps = [(i, st[i]) for i in range(1, n) if 5 <= st[i][3] <= 12 and st[i][2] <= 9 and st[i][4] >= 4]
    if not comps:
        return None
    meilleur = None
    for h0 in {int(s[3]) for _, s in comps}:
        g = [(i, s) for i, s in comps if abs(int(s[3]) - h0) <= 1]
        t0 = collections.Counter(int(s[1]) for _, s in g).most_common(1)[0][0]
        g = sorted([(i, s) for i, s in g if abs(int(s[1]) - t0) <= 2], key=lambda t: t[1][0])
        if not g:
            continue
        suite = [g[0]]
        for a in g[1:]:
            if a[1][0] - (suite[-1][1][0] + suite[-1][1][2]) <= 4:
                suite.append(a)
        if meilleur is None or len(suite) > len(meilleur):
            meilleur = suite
    keep = np.zeros_like(m)
    for i, _ in meilleur:
        keep[lab == i] = 255
    return keep


def _etat_case(image, cx: float, cy: float) -> str:
    """« pleine » (icône + nombre), « vide » (boîte sombre unie) ou « autre » (fiche posée par-dessus, hors cadre...).

    Mesuré sur une capture réelle : case vide = fond uni (écart-type < 4, clarté médiane 50-60) ; case pleine =
    écart-type > 35, clarté médiane 65-90. Une fiche (fond très sombre, texte blanc) tombe dans « autre ».
    """
    import numpy as np
    H, W = image.shape[:2]
    zone = image[max(0, int(cy - 15)):min(H, int(cy + 15)), max(0, int(cx - 19)):min(W, int(cx + 19))]
    if zone.size == 0:
        return "autre"
    v = zone.max(axis=2)
    ecart, mediane = float(v.std()), float(np.median(v))
    if mediane < 45 or mediane > 110:
        return "autre"
    if ecart < 6:
        return "vide"
    return "pleine" if ecart >= 20 else "autre"


def _case_vide(image, cx: float, cy: float) -> bool:
    return _etat_case(image, cx, cy) == "vide"


# --- reconnaissance directe des chiffres (police du jeu) -----------------------------------------
# Les chiffres des cases sont toujours dessinés de la même façon : on compare leur forme à des modèles
# (data/chiffres.json, relevés sur de vraies captures). C'est instantané et ne dépend d'aucun moteur de lecture.
# Un chiffre inconnu repasse par la lecture classique. Les modèles ne sont PAS appris automatiquement : une
# lecture classique fausse aurait fini par fausser les modèles.
SEUIL_FORME = 3  # écart maximal (en pixels) avec un modèle
ECART_FORME = 2  # le modèle d'un autre chiffre doit être au moins aussi plus loin
_MODELES: Optional[list] = None


def _forme(bool_img):
    import numpy as np
    out = np.zeros((9, 9), np.uint8)
    h, w = bool_img.shape
    out[:min(h, 9), :min(w, 9)] = bool_img[:9, :9]
    return out


def _depuis_texte(t):
    import numpy as np
    return np.array([1 if ch == "#" else 0 for ch in t], np.uint8).reshape(9, 9)


def _modeles():
    """[(chiffre, forme 9x9)] lus dans data/chiffres.json."""
    global _MODELES
    if _MODELES is None:
        import json
        from forge.chemins import chemin_data
        _MODELES = []
        try:
            with open(chemin_data("chiffres.json"), encoding="utf-8") as f:
                for d, formes in json.load(f).items():
                    _MODELES += [(d, _depuis_texte(t)) for t in formes]
        except Exception:
            _noter_erreur("cases_runes._modeles")
            pass
    return _MODELES


def _composantes(masque):
    """Chiffres du masque, de gauche à droite (tableaux 0/1)."""
    import cv2
    import numpy as np
    n, lab, st, _ = cv2.connectedComponentsWithStats((masque > 0).astype(np.uint8), 8)
    comps = sorted(((int(st[i][0]), (lab[st[i][1]:st[i][1] + st[i][3], st[i][0]:st[i][0] + st[i][2]] == i).astype(np.uint8))
                    for i in range(1, n)), key=lambda t: t[0])
    return [b for _, b in comps]


def _reconnaitre(comps) -> Optional[str]:
    """Texte des chiffres reconnus par leur forme, None si l'un d'eux est inconnu ou ambigu."""
    import numpy as np
    modeles = _modeles()
    if not modeles or not comps or len(comps) > 5:
        return None
    texte = ""
    for b in comps:
        f = _forme(b).astype(np.int16)
        ecarts = sorted((int(np.abs(f - m.astype(np.int16)).sum()), d) for d, m in modeles)
        meilleur = ecarts[0]
        autre = next((e for e, d in ecarts if d != meilleur[1]), 99)
        if meilleur[0] > SEUIL_FORME or autre - meilleur[0] < ECART_FORME:
            return None
        texte += meilleur[1]
    return texte


def lire_case(image, cx: float, cy: float) -> Optional[int]:
    """Nombre affiché dans une case (None si illisible ou si la case n'est pas une vraie case de rune)."""
    etat = _etat_case(image, cx, cy)
    if etat == "vide":
        METHODE[0] = "vide"
        return 0
    if etat != "pleine":
        METHODE[0] = "illisible"
        return None
    return _lire_case(image, cx, cy)


def _lire_case(image, cx: float, cy: float) -> Optional[int]:
    """Nombre affiché dans une case, None si aucun nombre net (case vide ou pile de 1)."""
    masques = [m for m in (_masque_chiffres(image, cx, cy, s) for s in SEUILS) if m is not None]
    if not masques:
        METHODE[0] = "vide" if _case_vide(image, cx, cy) else "illisible"
        return 0 if METHODE[0] == "vide" else None
    comps = _composantes(masques[0])
    direct = _reconnaitre(comps)
    if direct is not None:  # forme connue : pas de lecture, instantané
        METHODE[0] = "forme"
        return int(direct)
    METHODE[0] = "lecture"
    cle = masques[0].tobytes() + bytes(str(masques[0].shape), "ascii")
    if cle in _CACHE:  # même chiffres qu'à la lecture d'avant : inutile de relire
        return _CACHE[cle]
    resultat = _lire_masques(masques, image, cx, cy)
    if len(_CACHE) > 4000:
        _CACHE.clear()
    _CACHE[cle] = resultat
    return resultat


_CACHE: dict = {}
METHODE = [""]  # comment la dernière case a été lue : forme / lecture / vide / illisible
DERNIERE = {"lues": 0, "illisibles": 0, "liste_illisibles": [], "detail": []}  # bilan de la dernière lecture (affiché dans l'onglet Stock)


def _lire_masques(masques, image, cx, cy) -> Optional[int]:
    """Lit les chiffres : d'abord un tour rapide (3 réglages) ; s'ils s'accordent on s'arrête, sinon on insiste."""
    import cv2
    import numpy as np
    from forge.ocr import lire_elements
    lectures = []

    def essayer(masque, pol, fx, dil, flou):
        out = masque if pol == "w" else 255 - masque
        out = cv2.resize(out, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
        if dil:
            noyau = np.ones((dil, dil), np.uint8)
            out = cv2.dilate(out, noyau) if pol == "w" else cv2.erode(out, noyau)
        if flou:
            out = cv2.GaussianBlur(out, (flou, flou), 0)
        out = cv2.copyMakeBorder(out, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=0 if pol == "w" else 255)
        try:
            elements, _ = lire_elements(cv2.cvtColor(out, cv2.COLOR_GRAY2BGR), agrandir=1)
        except RuntimeError:
            return False
        texte = "".join(t for _, t in elements).translate(_CONFUSIONS)
        if texte.isdigit() and len(texte) <= 5:
            lectures.append(texte)
        return True

    # tour rapide : 3 réglages ; trois lectures identiques = lecture sûre
    for v in VARIANTES[:3]:
        if essayer(masques[0], *v) is False:
            return None
    if len(lectures) == 3 and len(set(lectures)) == 1:
        return int(lectures[0])
    for masque, v in ((m, v) for m in masques for v in VARIANTES):
        if (masque is masques[0] and v in VARIANTES[:3]):
            continue
        essayer(masque, *v)
    return _vote(lectures)


def _vote(lectures) -> Optional[int]:
    import collections
    if not lectures:
        return None
    vote = collections.Counter(lectures).most_common(2)
    valeur, nb = vote[0]
    second = vote[1][1] if len(vote) > 1 else 0
    return int(valeur) if nb >= ACCORD_MINI and nb >= 2 * second else None


def lire_stocks(image, panneau, tailles_par_cle: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """{id de ligne: {taille: quantité}} pour les lignes dont les cases ont pu être lues.

    `tailles_par_cle` : {cle_poids: {"simple": 1, "pa": 3, "ra": 10}} (tailles de rune par caractéristique).
    Renvoie {} si l'en-tête Pa/Ra est introuvable ou si presque rien n'a été lu.
    """
    ent = getattr(panneau, "entete", None)
    if not ent:
        return {}
    res: Dict[str, Dict[str, int]] = {}
    lus = 0
    DERNIERE["lues"] = DERNIERE["illisibles"] = 0
    DERNIERE["liste_illisibles"], DERNIERE["detail"] = [], []
    for l in panneau.lignes:
        if not l.cy or getattr(l, "hors_vue", False):
            continue
        tailles = sorted(((tailles_par_cle.get(l.cle_poids) or {}).items()), key=lambda t: t[1])
        if not tailles:
            continue
        centres = centres_cases(ent, len(tailles))
        if not centres:
            return {}
        stock = {}
        for (taille, _), cx in zip(tailles, centres):
            time.sleep(0.02)  # laisse la main à la lecture du tableau
            n = lire_case(image, cx, l.cy)
            DERNIERE["illisibles" if n is None else "lues"] += 1
            DERNIERE["detail"].append((l.libelle, taille, n, METHODE[0] if n is not None else "illisible"))
            if n is None:
                DERNIERE["liste_illisibles"].append((l.id, taille))
            if n is not None:  # case illisible : on ne touche pas au stock connu
                stock[taille] = n
                lus += 1 if n > 0 else 0  # seuls les vrais nombres comptent : un écran noir ne vide pas le stock
        if stock:
            res[l.id] = stock
    return res if lus >= MIN_CHIFFRES_LUS else {}


def sauver_diagnostic(image, panneau, tailles_par_cle, chemin=None) -> str:
    """Dessine les cases visées sur l'image et l'enregistre : permet de voir pourquoi rien n'est lu."""
    import os
    import cv2
    if chemin is None:
        from forge.chemins import dossier_journaux
        dossier = dossier_journaux()
        os.makedirs(dossier, exist_ok=True)
        chemin = os.path.join(dossier, "diag_cases.png")
    DEMI_LARGEUR, HAUTEUR = 14, 14   # (v111) constantes manquantes : l'image de diagnostic plantait (NameError)
    ent = getattr(panneau, "entete", None)
    img = image.copy()
    if ent:
        for l in panneau.lignes:
            n = len((tailles_par_cle.get(l.cle_poids) or {}))
            for cx in centres_cases(ent, n):
                cv2.rectangle(img, (int(cx - DEMI_LARGEUR), int(l.cy - HAUTEUR)), (int(cx + DEMI_LARGEUR), int(l.cy + 2)), (0, 0, 255), 1)
    cv2.imwrite(chemin, img)
    return chemin
