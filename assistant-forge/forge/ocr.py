"""Lecture de texte sur une image. Tout est local, aucune API en ligne.

Moteurs essayés dans l'ordre :
  1. RapidOCR (recommandé sur Windows : s'installe avec pip, rien d'autre à installer)
  2. Tesseract via pytesseract (repli, nécessite le programme Tesseract)

Un « élément » est un morceau de texte avec sa position : (boite, texte), où boite
est une liste de 4 points [[x, y], ...]. Garder la position permet de savoir dans quelle
COLONNE (Min, Max, Effets) se trouve chaque chiffre, ce qui est bien plus fiable que
de se fier à l'ordre du texte.

Sur la capture réelle, RapidOCR a été exécuté sur ton PC ; Tesseract sert ici de
moteur de test dans l'environnement de développement.
"""

from __future__ import annotations

import re
import statistics
from typing import Dict, List, Optional, Sequence, Tuple
from forge.erreurs import noter as _noter_erreur

Boite = Sequence[Sequence[float]]
Element = Tuple[Boite, str]


def normaliser_elements(elements: List[Element]) -> List[Dict]:
    """Transforme (boite, texte) en dictionnaires avec les coordonnées utiles."""
    infos = []
    for boite, texte in elements:
        xs = [p[0] for p in boite]
        ys = [p[1] for p in boite]
        infos.append({
            "x0": min(xs), "x1": max(xs), "cx": (min(xs) + max(xs)) / 2,
            "y0": min(ys), "y1": max(ys), "cy": (min(ys) + max(ys)) / 2,
            "h": max(ys) - min(ys), "t": texte,
        })
    return infos


def rangees(infos: List[Dict]) -> List[List[Dict]]:
    """Regroupe les éléments situés à peu près à la même hauteur (une rangée = une ligne d'écran)."""
    if not infos:
        return []
    tolerance = max(4.0, 0.6 * statistics.median(i["h"] for i in infos))
    sortis = sorted(infos, key=lambda i: i["cy"])
    res: List[List[Dict]] = []
    for i in sortis:
        if res and abs(i["cy"] - statistics.mean(e["cy"] for e in res[-1])) <= tolerance:
            res[-1].append(i)
        else:
            res.append([i])
    return [sorted(r, key=lambda e: e["x0"]) for r in res]


def grouper_en_lignes(elements: List[Element]) -> str:
    """Texte brut : une ligne par rangée, lue de gauche à droite."""
    return "\n".join(" ".join(e["t"] for e in r) for r in rangees(normaliser_elements(elements)))


# --- moteurs ------------------------------------------------------------------------------

_MOTEUR_RAPIDOCR = None  # le moteur est chargé UNE fois (le recharger à chaque image coûtait de l'ordre d'une seconde)
_MOTEUR_TABLEAU = None   # (OCR v161) moteur du TABLEAU seulement (modèles PP-OCRv5), chargé une fois aussi

# (OCR v161) Modèles PP-OCRv5 (détection + reconnaissance « latin », RapidAI/RapidOCR v3.10.0, SHA-256 officiels
# vérifiés) utilisés pour lire le TABLEAU seulement. Mesuré sur corpus_ocr, partie gardée de côté : +4,2 points de
# tableaux lisibles, IC 95 % [+0,8 ; +18,8] ; contrôle à l'œil 18/18 justes. Ils lisent MAL les chiffres seuls des
# cases de stock (1 225 cases illisibles contre 563 sur 80 images) : stocks, chiffres relus, historique, reliquat
# et localisation gardent l'ancien modèle. Fichiers absents, chargement en échec ou FORGE_OCR_ANCIEN=1 : ancien partout.
from forge.chemins import chemin_data as _chemin_data
DOSSIER_MODELES = _chemin_data("modeles_ocr")
FICHIERS_TABLEAU = {"det_model_path": "ch_PP-OCRv5_det_mobile.onnx", "rec_model_path": "latin_PP-OCRv5_rec_mobile.onnx"}
MODELE_TABLEAU = ["non chargé"]   # affiché/diagnostic : « PP-OCRv5 latin » ou « ancien (raison) »


def _options_tableau() -> dict:
    import os
    if os.environ.get("FORGE_OCR_ANCIEN"):
        return {}
    chemins = {k: str(DOSSIER_MODELES / f) for k, f in FICHIERS_TABLEAU.items()}
    return chemins if all(os.path.isfile(c) for c in chemins.values()) else {}


def _preparer_accel(moteur):
    try:
        from forge import accel
        accel.preparer(moteur)
    except Exception:
        _noter_erreur("ocr.accel")


def _moteur_tableau():
    """(OCR v161) Moteur de lecture du tableau : PP-OCRv5 si possible, sinon le moteur habituel (rien ne change).
    C'est lui que l'accélération OpenVINO (vérifiée) accompagne, puisque seule la lecture du tableau est accélérée."""
    global _MOTEUR_TABLEAU
    if _MOTEUR_TABLEAU is None:
        options = _options_tableau()
        if options:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore
                _MOTEUR_TABLEAU = (RapidOCR(**options), True)
                MODELE_TABLEAU[0] = "PP-OCRv5 latin"
            except Exception as e:
                _noter_erreur("ocr.modele_tableau")
                MODELE_TABLEAU[0] = f"ancien (PP-OCRv5 refusé : {type(e).__name__})"
        else:
            MODELE_TABLEAU[0] = "ancien"
        if _MOTEUR_TABLEAU is None:
            _MOTEUR_TABLEAU = _moteur_rapidocr()
    if _MOTEUR_TABLEAU[1]:
        _preparer_accel(_MOTEUR_TABLEAU[0])
    return _MOTEUR_TABLEAU


def _moteur_rapidocr():
    """Renvoie (fonction de lecture, ancienne_api). Chargé au premier appel puis gardé en mémoire."""
    global _MOTEUR_RAPIDOCR
    if _MOTEUR_RAPIDOCR is None:
        try:  # ancienne API (celle installée par Installer_une_fois.bat)
            from rapidocr_onnxruntime import RapidOCR  # type: ignore
            _MOTEUR_RAPIDOCR = (RapidOCR(), True)
        except ImportError as e1:
            # (v137) avant : seule l'erreur de la nouvelle API était gardée (« No module named 'rapidocr' »), la vraie
            # cause (souvent un fichier de onnxruntime refusé par Windows) était perdue. Les deux sont maintenant écrites.
            try:
                from rapidocr import RapidOCR  # type: ignore  # nouvelle API
                _MOTEUR_RAPIDOCR = (RapidOCR(), False)
            except ImportError as e2:
                raise ImportError(f"rapidocr_onnxruntime : {e1} | rapidocr : {e2}") from e1
    # (v126) mêmes modèles calculés par OpenVINO si possible, vérifié ; sinon rien ne change.
    # (OCR v161) avec les modèles du tableau, l'accélération va au moteur du tableau (_moteur_tableau).
    if _MOTEUR_RAPIDOCR[1] and not _options_tableau():
        _preparer_accel(_MOTEUR_RAPIDOCR[0])
    return _MOTEUR_RAPIDOCR


def _elements_rapidocr(image, rapide: bool = False, juge=None, tableau: bool = False) -> List[Element]:
    moteur, ancienne = _moteur_tableau() if (tableau or rapide) else _moteur_rapidocr()
    if ancienne:
        def lire_brut(img):
            try:
                resultat, _ = moteur(img, use_cls=False)  # pas de détection d'orientation : texte toujours droit
            except TypeError:
                resultat, _ = moteur(img)
            return [(b, t) for b, t, _s in (resultat or [])]
        from forge import accel
        if accel._ACCEL is not None:   # (v126) rapide=True : lecture du tableau seulement, vérifiée ; sinon calcul d'origine
            return accel._ACCEL.lire_mode(image, lire_brut, rapide, juge)
        return lire_brut(image)
    try:
        sortie = moteur(image, use_cls=False)
    except TypeError:
        sortie = moteur(image)
    boites = getattr(sortie, "boxes", None)
    textes = getattr(sortie, "txts", None)
    if boites is None or textes is None:
        return []
    boites = boites.tolist() if hasattr(boites, "tolist") else boites
    return list(zip(boites, textes))


def _elements_tesseract(image, agrandir: int = 3) -> List[Element]:
    import cv2
    import pytesseract
    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gris = cv2.resize(gris, None, fx=agrandir, fy=agrandir, interpolation=cv2.INTER_CUBIC)
    # Texte clair sur fond sombre : on isole le texte (noir sur blanc), ce qui rend la lecture
    # indépendante des marges et du fond de l'interface.
    _, gris = cv2.threshold(gris, 120, 255, cv2.THRESH_BINARY_INV)
    d = pytesseract.image_to_data(gris, config="--psm 6", output_type=pytesseract.Output.DICT)
    elements = []
    for i, t in enumerate(d["text"]):
        if not t.strip() or float(d["conf"][i]) < 0:
            continue
        x, y, w, h = (d[k][i] / agrandir for k in ("left", "top", "width", "height"))
        elements.append(([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], t))
    return elements


MOTEURS = (("RapidOCR", _elements_rapidocr), ("Tesseract", _elements_tesseract))


def lire_elements(image, agrandir: int = 3, rapide: bool = False, juge=None,
                  tableau: bool = False) -> Tuple[List[Element], str]:
    """Lit les éléments de texte d'une image (tableau numpy BGR). Renvoie (elements, moteur).
    (v126) `rapide=True` : lecture du TABLEAU, calculée par OpenVINO si possible et vérifiée par `juge` au début.
    (OCR v161) `tableau=True` (ou `rapide=True`) : modèles du tableau (PP-OCRv5) ; sinon l'ancien modèle."""
    erreurs = []
    for nom, fn in MOTEURS:
        try:
            if nom == "Tesseract":
                return fn(image, agrandir), nom
            if nom == "RapidOCR":
                return fn(image, rapide=rapide, juge=juge, tableau=tableau), nom
            return fn(image), nom
        except ImportError as e:
            erreurs.append(f"{nom} non installé ({e})")
        except Exception as e:  # moteur installé mais en échec
            _noter_erreur("ocr.lire_elements")
            erreurs.append(f"{nom} a échoué : {e}")
    raise RuntimeError("Aucun moteur de lecture disponible : " + " | ".join(erreurs))


def lire_texte(image) -> Tuple[str, str]:
    """Compatibilité : texte brut (une ligne par rangée) et nom du moteur."""
    elements, moteur = lire_elements(image)
    return grouper_en_lignes(elements), moteur


def relire_nombre(image, cx: float, cy: float, hauteur: float, largeur: float) -> Optional[int]:
    """Relit UN nombre dans une petite zone (2e passe, zone agrandie). None si rien de net."""
    import cv2
    H, W = image.shape[:2]
    x0, x1 = max(0, int(cx - largeur / 2)), min(W, int(cx + largeur / 2))
    y0, y1 = max(0, int(cy - hauteur)), min(H, int(cy + hauteur))
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    crop = cv2.copyMakeBorder(crop, 12, 12, 12, 12, cv2.BORDER_REPLICATE)
    crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    try:
        elements, _ = lire_elements(crop, agrandir=1)
    except RuntimeError:
        return None
    nombres = re.findall(r"-?\d+", " ".join(t for _, t in elements))
    return int(nombres[0]) if len(nombres) == 1 else None
