"""Ce qu'on dessine par-dessus le jeu, sous forme de primitives simples.

Aucun Qt ici : `scene(state)` renvoie une liste de primitives que la fenêtre Qt dessine
telles quelles. Ça permet de tester le résultat sans écran.

Primitives (couleurs en RGBA) :
  ("poly",  points, fill|None, stroke|None, largeur, pointillé)
  ("line",  p, q, couleur, largeur, pointillé)
  ("text",  x, y, texte, couleur, taille, fond|None)       centré sur (x, y)
  ("panel", x, y, [(texte, couleur), ...])                 boîte de lignes, centrée en haut sur (x, y)
"""
import math
from dataclasses import dataclass, field

import core
from i18n import _t

GRID = (255, 255, 255, 55)
BLOCK_FILL, BLOCK_LINE = (15, 15, 15, 170), (255, 130, 90, 220)
PIT_FILL, PIT_LINE = (0, 0, 0, 190), (120, 130, 255, 230)
AIM_FILL, AIM_LINE = (60, 150, 255, 45), (90, 175, 255, 255)
LAND_FILL, LAND_LINE = (255, 175, 0, 120), (255, 205, 70, 255)
ANCHOR_FILL, ANCHOR_LINE = (255, 215, 0, 150), (255, 235, 90, 255)
YOU_FILL, YOU_LINE = (255, 255, 255, 90), (255, 255, 255, 255)
OUTLINE, OUTLINE_HALO = (63, 224, 232, 255), (0, 0, 0, 150)
GRID_STRONG = (255, 255, 255, 130)
GRID_FREE, GRID_FREE_STRONG = (255, 255, 255, 62), (255, 255, 255, 130)     # grande grille du mode Songes
WARN = (255, 120, 100, 255)
TEXT = (245, 245, 245, 255)
MUTED = (170, 190, 195, 255)
LABEL_BG = (10, 20, 26, 215)


@dataclass
class State:
    calib: core.Calib
    screen_w: int = 1920
    screen_h: int = 1080
    fight: int = 0
    you: tuple = None
    hp_manual: float = 100.0
    hits: int = 0                              # lignes de dégâts infligées au corps à corps ce tour
    k_choice: int = None                       # confusion choisie (menu) ou copiée ; None = d'après les PV
    no_confusion: bool = False                 # on joue une invocation : aucune confusion
    you_cleared: bool = False                  # position retirée exprès (déplacement en cours)
    flash: bool = False                        # montre le contour de la salle un instant (après un calage de la grille)
    mouse: tuple = (0, 0)
    show_grid: bool = False
    calibrating: bool = False                  # n'affiche que la grille et les obstacles
    origin: tuple = (0, 0)                     # coin haut-gauche de l'écran du jeu (coordonnées globales)

    @property
    def free(self):
        """Mode Songes : grille libre, sans carte."""
        return core.FIGHTS[self.fight].free

    def cell_at(self, x, y):
        """Case sous le point (x, y) : dans la salle, ou n'importe où en mode Songes."""
        return self.calib.cell_at(x, y, free=self.free)

    def rotation(self):
        """(quarts de tour, origine). Origine : « invocation », « choisie » ou « pv »."""
        if self.no_confusion:
            return 0, "invocation"
        if self.k_choice is not None:
            # Chaque ligne infligée au corps à corps après le choix retire un quart de tour.
            return (self.k_choice - self.hits) % 4, "choisie"
        return core.quarter_turns(self.hp_manual, self.hits), "pv"


def _poly(c, cell, fill, stroke, w=2, dash=False):
    return ("poly", c.polygon(cell), fill, stroke, w, dash)


def outline_prims(c):
    """Le contour de la salle, à faire coller au bord du carrelage pendant la calibration (un zigzag, facile à juger)."""
    def pt(v):
        return (c.x0 + c.kx * v[1], c.y0 + c.ky * v[0])
    halo = [("line", pt(a), pt(b), OUTLINE_HALO, 6, False) for a, b in core.ARENA_OUTLINE]
    main = [("line", pt(a), pt(b), OUTLINE, 3.0, False) for a, b in core.ARENA_OUTLINE]
    return halo + main


def free_grid_prims(c, rect, strong=False):
    """Une grande grille qui couvre tout le rectangle rect = (x, y, largeur, hauteur) : le mode Songes.

    Les côtés des cases sont sur deux familles de droites : ligne - colonne = impair, et ligne + colonne = impair
    (en demi-cases). On ne trace que celles qui traversent le rectangle.
    """
    rx, ry, rw, rh = rect
    xl, xr, yt, yb = rx - c.kx, rx + rw + c.kx, ry - c.ky, ry + rh + c.ky
    col, width = (GRID_FREE_STRONG, 1.2) if strong else (GRID_FREE, 1.0)
    prims = []
    for sign in (1, -1):                          # pente descendante (ligne - colonne), puis montante (ligne + colonne)
        s0, s1 = sign * c.ky * (xl - c.x0) / c.kx, sign * c.ky * (xr - c.x0) / c.kx
        lo = math.ceil((yt - c.y0 - max(s0, s1)) / c.ky)
        hi = math.floor((yb - c.y0 - min(s0, s1)) / c.ky)
        for m in range(lo, hi + 1):
            if m % 2:
                y = c.y0 + c.ky * m
                prims.append(("line", (xl, y + s0), (xr, y + s1), col, width, False))
    return prims


def grid_prims(c, f, strong=False, rect=None):
    """La grille de la salle avec ses blocs et ses trous (strong : traits plus visibles, pour la calibration).

    En mode Songes (f.free), c'est une grande grille sur tout le rectangle rect de l'écran, sans carte.
    """
    if f.free:
        if rect is None:
            rect = (c.x0 - 30 * c.kx, c.y0 - 14 * c.ky, 60 * c.kx, 40 * c.ky)
        return free_grid_prims(c, rect, strong)
    prims = [_poly(c, cell, None, GRID_STRONG if strong else GRID, 1.2 if strong else 1) for cell in sorted(core.ARENA)]
    prims += [_poly(c, cell, BLOCK_FILL, BLOCK_LINE, 1) for cell in sorted(f.blocks & core.ARENA)]
    prims += [_poly(c, cell, PIT_FILL, PIT_LINE, 1) for cell in sorted(f.pits)]
    return prims


def cell_angle(src, dst):
    """Direction de `src` vers `dst` à l'écran, en degrés dans le sens horaire depuis le haut (0 = haut, 90 = droite).

    On compte en demi-cases (colonne b, ligne a) : les quatre directions des cases voisines tombent alors sur
    45°, 135°, 225° et 315°, et un quart de tour du jeu est un vrai quart de tour de 90° à l'écran.
    """
    da, db = dst[0] - src[0], dst[1] - src[1]
    return math.degrees(math.atan2(db, -da)) % 360


def dial_info(s):
    """Ce que montre le cadran : l'aiguille noire (où part ton sort) et le repère cyan (où tu vises).

    Sans visée (pas placé, souris hors de la salle ou sur ta case), le repère reste en haut et l'aiguille montre
    seulement la rotation : « si tu vises en haut, le sort part par là ». Avec une visée, les deux suivent la souris.
    """
    k, source = s.rotation()
    info = {"k": k, "source": source, "live": False, "aim_angle": 0.0, "needle_angle": (90.0 * k) % 360, "ok": True}
    if s.you is None:
        return info
    aim = s.cell_at(*s.mouse)
    if aim is None or aim == s.you:
        return info
    theta = cell_angle(s.you, aim)
    ev = core.evaluate(core.FIGHTS[s.fight], s.you, aim, k)
    info.update(live=True, aim_angle=theta, needle_angle=(theta + 90.0 * k) % 360, ok=not ev.warnings)
    return info


def scene(s):
    """Renvoie (primitives, infos). `infos` sert aux tests et à la fenêtre de contrôle."""
    c, f = s.calib, core.FIGHTS[s.fight]
    rect = (s.origin[0], s.origin[1], s.screen_w, s.screen_h)
    prims = grid_prims(c, f, rect=rect) if (s.show_grid or s.calibrating or f.free) else []   # Songes : grille toujours là
    info = {"aim": None, "landing": None, "k": None, "source": None, "warnings": []}
    if s.calibrating:
        return prims, info
    if s.flash and not f.free:
        prims = prims + outline_prims(c)

    k, source = s.rotation()
    info["k"], info["source"] = k, source

    if s.you is not None:
        prims.append(_poly(c, s.you, YOU_FILL, YOU_LINE, 2))
        x, y = c.center(s.you)
        prims.append(("text", x, y, _t("TOI"), TEXT, 11, None))

    # Case visée par la souris et case d'atterrissage réelle
    aim = s.cell_at(*s.mouse)
    if s.you is not None and aim is not None:
        ev = core.evaluate(f, s.you, aim, k)
        info.update(aim=aim, landing=ev.landing, warnings=ev.warnings)
        prims.append(_poly(c, aim, AIM_FILL, AIM_LINE, 2))
        prims.append(("line", c.center(s.you), c.center(aim), AIM_LINE, 1.5, True))
        if ev.landing_on_map:
            prims.append(_poly(c, ev.landing, LAND_FILL, LAND_LINE, 3))
            prims.append(("line", c.center(s.you), c.center(ev.landing), LAND_LINE, 2.5, False))
            x, y = c.center(ev.landing)
            label = _t("ATTERRIT ICI") if ev.landing != aim else _t("ATTERRIT SUR LA CASE VISÉE")
            prims.append(("text", x, y - c.ky * 1.8, label, LAND_LINE, 12, LABEL_BG))
        if ev.warnings:
            x, y = c.center(aim)
            prims.append(("panel", x, y + c.ky * 1.6, [(w, WARN) for w in ev.warnings]))

    return prims, info
