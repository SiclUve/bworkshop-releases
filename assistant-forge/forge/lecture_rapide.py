"""(v119) Lecture RAPIDE du tableau : on ne relit à l'OCR que les bandes de l'image qui ont changé.

Avant : chaque changement (une rune passée, une fiche ouverte puis refermée) relisait TOUT le tableau, 0,5 s en médiane
et 1,2 s une fois sur dix sur ton PC (journal du 29/10, 267 lectures). Une rune ne change que 1 à 4 lignes : on garde le
texte des lignes qui n'ont pas bougé et on relit seulement les bandes qui ont changé (plus vite : l'OCR coûte selon la
surface de l'image).
Une image déjà lue récemment (le tableau revenu tel quel après une fiche de rune) est reprise sans aucun OCR.

Garde-fous :
  - plus de 45 % de la hauteur changée, image d'une autre taille, ou lecture rapide douteuse -> lecture complète ;
  - VÉRIFICATION : les VERIFICATIONS premières lectures rapides de chaque lancement sont aussi faites en complet et
    comparées (lignes, Min, Max, valeurs, reliquat). Au 2e désaccord, la lecture rapide est coupée jusqu'au prochain
    lancement. Les temps et les désaccords sont notés (journal : chrono lecture_mode, lecture_verif).
Observation seule : capture d'écran et OCR, rien n'est fait dans le jeu.
"""

from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

BANDES_ACTIVES = False   # (v125) coupé : voir HISTORIQUE v125 (jamais plus rapide en jeu, et une ligne manquée)
PART_MAX = 0.45          # au-delà de cette part de la hauteur changée : lecture complète
SEUIL_PIXEL = 30         # écart de luminosité qui compte comme un changement (comme suivi.pixels_changes)
PIXELS_MIN_LIGNE = 3     # pixels changés dans une rangée d'image pour qu'elle compte
VERIFICATIONS = 20       # lectures rapides doublées d'une lecture complète à chaque lancement
DESACCORDS_MAX = 2
MEMOIRE = 3              # images déjà lues gardées (tableau revenu tel quel après une fiche)


def _y_boite(boite) -> Tuple[float, float]:
    ys = [p[1] for p in boite]
    return min(ys), max(ys)


def rangees_changees(a, b, seuil: int = SEUIL_PIXEL, pixels: int = PIXELS_MIN_LIGNE) -> Optional[List[int]]:
    """Indices des rangées de pixels qui ont changé entre deux images de même taille (None si tailles différentes)."""
    import numpy as np
    if a is None or b is None or a.shape != b.shape:
        return None
    ga = a.astype(np.int16).mean(axis=2) if a.ndim == 3 else a.astype(np.int16)
    gb = b.astype(np.int16).mean(axis=2) if b.ndim == 3 else b.astype(np.int16)
    n = (np.abs(ga - gb) > seuil).sum(axis=1)
    return [int(i) for i in np.nonzero(n >= pixels)[0]]


def bandes(rangs: List[int], hauteur_ligne: float, H: int, boites=()) -> List[Tuple[int, int]]:
    """Rangées changées -> bandes [y0, y1) élargies d'une demi-ligne et étendues aux boîtes de texte qu'elles touchent."""
    if not rangs:
        return []
    marge = max(4, int(0.6 * hauteur_ligne))
    res: List[List[int]] = []
    for y in rangs:
        if res and y <= res[-1][1] + marge:
            res[-1][1] = y + 1
        else:
            res.append([y, y + 1])
    out = []
    for y0, y1 in res:
        y0, y1 = max(0, y0 - marge), min(H, y1 + marge)
        for _ in range(3):   # une boîte coupée par la bande est relue en entier
            for b in boites:
                by0, by1 = _y_boite(b)
                if by1 > y0 and by0 < y1:
                    y0, y1 = max(0, min(y0, int(by0) - 2)), min(H, max(y1, int(by1) + 3))
        out.append((y0, y1))
    out.sort()
    fusion: List[List[int]] = []
    for y0, y1 in out:
        if fusion and y0 <= fusion[-1][1]:
            fusion[-1][1] = max(fusion[-1][1], y1)
        else:
            fusion.append([y0, y1])
    return [(a, b) for a, b in fusion]


def ecarts(rapide, complet) -> Optional[List[str]]:
    """(v124) Différences qui comptent entre lecture rapide et lecture complète : [] si d'accord, None si on ne peut
    pas juger (lecture complète elle-même douteuse). Un Min/Max lu d'un côté et sauté de l'autre (chiffres seuls,
    souvent sautés par l'OCR) n'est pas un désaccord ; une valeur, une ligne ou le reliquat différents en sont un."""
    if rapide is None or complet is None:
        return ["tableau absent"]
    if complet.avertissements:
        return None
    a = {l.id: l for l in rapide.lignes}
    b = {l.id: l for l in complet.lignes}
    out = []
    for i in sorted(set(a) | set(b)):
        if i not in a or i not in b:
            out.append(f"ligne {i} : {'absente en rapide' if i not in a else 'en trop en rapide'}")
            continue
        if a[i].valeur != b[i].valeur:
            out.append(f"{i} : valeur {a[i].valeur} au lieu de {b[i].valeur}")
        for att in ("mini", "maxi"):
            va, vb = getattr(a[i], att), getattr(b[i], att)
            if va is not None and vb is not None and va != vb:
                out.append(f"{i} : {att} {va} au lieu de {vb}")
    ra = None if rapide.reliquat is None else float(rapide.reliquat)
    rb = None if complet.reliquat is None else float(complet.reliquat)
    if ra != rb:
        out.append(f"reliquat {ra} au lieu de {rb}")
    return out


def resume(panneau) -> tuple:
    """Ce qui doit être identique entre lecture rapide et lecture complète."""
    if panneau is None:
        return ()
    return (tuple(sorted((l.id, l.valeur, l.mini, l.maxi) for l in panneau.lignes)),
            None if panneau.reliquat is None else float(panneau.reliquat), tuple(panneau.avertissements))


class LecteurIncremental:
    def __init__(self, lire_elements: Optional[Callable] = None, construire: Optional[Callable] = None,
                 verifications: int = VERIFICATIONS, horloge: Callable[[], float] = time.perf_counter):
        self.accel = lire_elements is None   # (v126) lecture réelle : le tableau peut être lu par le calcul accéléré
        if lire_elements is None:
            from forge.ocr import lire_elements as _le

            def lire_elements(image, **options):   # (OCR v161) tableau, bandes comprises : modèles du tableau
                return _le(image, tableau=True, **options)
        self.lire_elements = lire_elements
        self.construire = construire or _construire
        self.verifications = verifications
        self.horloge = horloge
        self.actif = True
        self.desaccords = 0
        self.memoire: List[tuple] = []   # [(image, elements, moteur)] les plus récentes d'abord
        self.derniere: dict = {}
        self.refus: Optional[str] = None
        self.dernier_ecart: List[str] = []
        self.stats = {"complet": 0, "bandes": 0, "memoire": 0, "verif_ok": 0, "verif_ecart": 0}

    def oublier(self):
        self.memoire = []

    # --- lectures -------------------------------------------------------------------------------------------------
    def _juger(self, a, b, image):
        """(v126) Deux lectures du même tableau sont-elles d'accord ? True / False, ou None si ce n'est pas un tableau
        (moins de 3 lignes lues) : on compare alors les textes."""
        pa, _ = self.construire(a, image)
        pb, _ = self.construire(b, image)
        if pa is None or pb is None or len(pa.lignes) < 3 or len(pb.lignes) < 3:
            return None
        return resume(pa) == resume(pb)

    def _complet(self, image):
        if self.accel:
            elements, moteur = self.lire_elements(image, rapide=True, juge=lambda a, b: self._juger(a, b, image))
        else:
            elements, moteur = self.lire_elements(image)
        return elements, moteur

    def _par_bandes(self, image, ref_image, ref_elements, moteur_ref):
        """(elements, moteur, nb_bandes) ou None si la lecture par bandes ne convient pas."""
        from forge.ocr import normaliser_elements
        import statistics
        rangs = rangees_changees(ref_image, image)
        if rangs is None:
            self.refus = "taille"     # (v121) raison notée dans le journal : savoir pourquoi la lecture rapide ne sert pas
            return None
        H = image.shape[0]
        hs = [i["h"] for i in normaliser_elements(ref_elements)] or [12.0]
        bs = bandes(rangs, statistics.median(hs), H, [b for b, _t in ref_elements])
        if not bs:
            return list(ref_elements), moteur_ref, 0
        part = sum(y1 - y0 for y0, y1 in bs) / H
        if part > PART_MAX:
            self.refus = f"part {round(100 * part)} % (pixels {round(100 * len(rangs) / H)} %)"
            return None
        garde = []
        for b, t in ref_elements:
            by0, by1 = _y_boite(b)
            if not any(by1 > y0 and by0 < y1 for y0, y1 in bs):
                garde.append((b, t))
        moteur = moteur_ref
        for y0, y1 in bs:
            els, moteur = self.lire_elements(image[y0:y1])
            for b, t in els:
                garde.append(([[p[0], p[1] + y0] for p in b], t))
        return garde, moteur, len(bs)

    def lire(self, image):
        """(panneau, moteur, texte) comme lecture.lire_panneau(image, relire=False)."""
        t0 = self.horloge()
        mode, nb, verif = "complet", 0, None
        res = None
        self.refus = ("pas d'image d'avant" if not self.memoire else
                      "bandes désactivées" if not BANDES_ACTIVES else ("coupée" if not self.actif else None))
        # 1) image déjà lue (pixels quasi identiques) : aucune lecture
        for img, els, mot in self.memoire:
            r = rangees_changees(img, image)
            if r is not None and not r:
                res, mode = (list(els), mot), "memoire"
                break
        # 2) seules quelques bandes ont changé
        if res is None and BANDES_ACTIVES and self.actif and self.memoire:
            img, els, mot = self.memoire[0]
            pb = self._par_bandes(image, img, els, mot)
            if pb is not None:
                res, nb, mode = (pb[0], pb[1]), pb[2], "bandes"
        if res is None:
            res, mode = self._complet(image), "complet"
        panneau, texte = self.construire(res[0], image)
        # 3) vérification : la lecture rapide est comparée à une lecture complète
        if mode == "bandes" and self.verifications > 0:
            self.verifications -= 1
            plein = self._complet(image)
            p2, t2 = self.construire(plein[0], image)
            ec = None if panneau is not None and panneau.avertissements else ecarts(panneau, p2)
            if ec is None:
                # une des deux lectures est douteuse : rien à juger (la lecture rapide douteuse est de toute façon
                # refaite en complet hors vérification), on garde la lecture complète
                self.verifications += 1
                res, panneau, texte, mode = plein, p2, t2, "complet"
                self.refus = "vérification impossible (lecture douteuse)"
            elif not ec:
                verif = "ok"
                self.stats["verif_ok"] += 1
                for l in panneau.lignes:   # un Min/Max sauté par la lecture rapide mais lu en complet est repris
                    l2 = next((x for x in p2.lignes if x.id == l.id), None)
                    if l2 is not None:
                        l.mini = l.mini if l.mini is not None else l2.mini
                        l.maxi = l.maxi if l.maxi is not None else l2.maxi
            else:
                verif = "ecart"
                self.stats["verif_ecart"] += 1
                self.desaccords += 1
                if self.desaccords >= DESACCORDS_MAX:
                    self.actif = False
                res, panneau, texte, mode = plein, p2, t2, "complet"
                self.refus = "écart à la vérification"
                self.dernier_ecart = ec[:4]
        elif mode == "bandes" and panneau is not None and panneau.avertissements:
            # lecture rapide douteuse : on refait en complet plutôt que de signaler une fausse alerte
            res = self._complet(image)
            panneau, texte = self.construire(res[0], image)
            mode = "complet"
            self.refus = "lecture rapide douteuse"
        self.stats[mode] += 1
        self.memoire = [(image, list(res[0]), res[1])] + [m for m in self.memoire
                                                          if rangees_changees(m[0], image) != []][:MEMOIRE - 1]
        self.derniere = {"lecture_mode": mode, "bandes": nb, "duree_s": round(self.horloge() - t0, 3)}
        if verif:
            self.derniere["lecture_verif"] = verif
            if verif == "ecart":
                self.derniere["lecture_ecart"] = self.dernier_ecart   # (v124) ce qui différait, pour corriger
        if mode == "complet" and self.refus:
            self.derniere["lecture_refus"] = self.refus
        return panneau, res[1], texte


def _construire(elements, image):
    """Même construction que lecture.lire_panneau(relire=False), à partir d'éléments déjà lus."""
    from forge.lecture import analyser_elements, analyser_texte, colorer_lignes
    from forge.ocr import grouper_en_lignes
    texte = grouper_en_lignes(elements)
    panneau = analyser_elements(elements, relire=None,
                                hauteur_image=getattr(image, "shape", (None,))[0])  # (OCR v161) rangée coupée en bas
    if panneau is not None:
        colorer_lignes(panneau, image)
    else:
        panneau = analyser_texte(texte)
        panneau.notes.append("En-tête Min/Max introuvable : lecture par le texte seul (moins fiable).")
    return panneau, texte
