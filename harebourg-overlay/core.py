"""Logique du Comte Harebourg : carte de la salle, rotation de la confusion, ligne de vue.

Aucune dépendance graphique ici, tout se teste sans lancer le jeu.

Système de coordonnées (le même que le simulateur) :
  une case est un couple (a, b). a est la ligne (demi-hauteur de case), b la colonne
  (demi-largeur de case). a + b est toujours pair.
  Axes de la grille : i vers le bas-droite, j vers le bas-gauche, avec
  i = (a + b) / 2 et j = (a - b) / 2.
"""
import math
import re
from dataclasses import dataclass

# Pour chaque ligne a, les colonnes vont de -m à +m de 2 en 2.
EXT = {
    -2: 2, -1: 5, 0: 8, 1: 9, 2: 10, 3: 11, 4: 10, 5: 11, 6: 12, 7: 11, 8: 12,
    9: 13, 10: 12, 11: 13, 12: 12, 13: 13, 14: 12, 15: 11, 16: 12, 17: 11, 18: 10,
    19: 11, 20: 10, 21: 9, 22: 8, 23: 5, 24: 2,
}
ARENA = {(a, b) for a, m in EXT.items() for b in range(-m, m + 1, 2)}


def _outline():
    """Contour de la salle : les côtés de cases qui n'ont pas de voisine dans la salle, en demi-cases (ligne, colonne).

    Une case (a, b) a pour sommets haut (a-1, b), droite (a, b+1), bas (a+1, b) et gauche (a, b-1).
    """
    edges = []
    for a, b in sorted(ARENA):
        top, right, bottom, left = (a - 1, b), (a, b + 1), (a + 1, b), (a, b - 1)
        if (a - 1, b + 1) not in ARENA:
            edges.append((top, right))
        if (a + 1, b + 1) not in ARENA:
            edges.append((right, bottom))
        if (a + 1, b - 1) not in ARENA:
            edges.append((bottom, left))
        if (a - 1, b - 1) not in ARENA:
            edges.append((left, top))
    return edges


ARENA_OUTLINE = _outline()


def _c(txt):
    a, b = txt.split(",")
    return (int(a), int(b))


def _cells(lst):
    return [_c(t) for t in lst]


# Les quatre variantes de la salle selon le combat. Les blocs bloquent la ligne de vue,
# les trous empêchent seulement d'y viser.
_RAW_FIGHTS = [
    ("Comte seul",
     [["0,-8", "1,-9", "1,-7", "2,-8"], ["12,-8", "13,-9", "13,-7", "14,-8"],
      ["10,0", "11,-1", "11,1", "12,0"], ["7,7", "8,6", "8,8", "9,7"], ["22,-2"], ["16,12"]],
     ["2,-6", "14,-6", "15,-7", "6,8", "9,5", "10,6", "21,-1"]),
    ("Comte + Nileza",
     [["5,-11", "6,-12"], ["3,-3"], ["12,-8", "13,-7"], ["10,0", "11,-1", "11,1", "12,0"],
      ["12,8"], ["23,5"]],
     ["2,-4", "11,7"]),
    ("Comte + Klime",
     [["-1,-5"], ["3,-11"], ["6,-12"], ["7,-7", "8,-6", "9,-5"], ["9,-7"], ["9,-1"],
      ["9,1", "10,0", "10,2", "11,1"], ["10,10", "11,9"], ["6,12"], ["7,13"], ["23,5"]],
     ["10,-8", "10,-6", "11,-7", "11,-1", "12,0", "12,2", "11,3", "9,9", "10,8", "11,11",
      "12,10", "17,-3", "18,-2"]),
    ("Comte + Sylargh",
     [["3,-11", "2,-10"], ["12,-8", "11,-7", "10,-6"], ["8,8", "9,7", "9,9", "10,8"],
      ["8,0", "9,-1", "10,-2", "9,1", "10,0", "11,-1"], ["10,2", "11,1"], ["23,5"]],
     ["13,-7", "12,-6", "10,10", "12,0"]),
]


@dataclass(frozen=True)
class Fight:
    name: str
    blocks: frozenset   # cases qui bloquent la ligne de vue
    pits: frozenset     # trous
    block_groups: tuple  # les mêmes blocs, regroupés (pour le dessin)


FIGHTS = [
    Fight(n, frozenset(c for g in bl for c in _cells(g)), frozenset(_cells(pt)),
          tuple(tuple(_cells(g)) for g in bl))
    for n, bl, pt in _RAW_FIGHTS
]


# --- Tranches de vitalité ---------------------------------------------------------
@dataclass(frozen=True)
class Tranche:
    lo: int
    hi: int
    base: int   # quarts de tour, + = horaire, - = anti-horaire
    name: str


TRANCHES = [
    Tranche(90, 100, 1, "90° horaire"),
    Tranche(75, 89, -1, "90° anti-horaire"),
    Tranche(45, 74, 2, "180°"),
    Tranche(30, 44, -1, "90° anti-horaire"),
    Tranche(0, 29, 1, "90° horaire"),
]


def tranche_of(pct):
    p = max(0, min(100, int(math.floor(pct))))
    for t in TRANCHES:
        if t.lo <= p <= t.hi:
            return t
    return TRANCHES[-1]


def near_border(pct):
    """Vrai si le % est à moins de 1 point d'une limite de tranche (risque d'erreur de lecture)."""
    p = max(0.0, min(100.0, pct))
    return any(abs(p - b) < 1.0 for b in (30, 45, 75, 90))


def quarter_turns(pct, hits):
    """Nombre de quarts de tour k du simulateur : (base de la tranche - coups au corps à corps) mod 4."""
    return (tranche_of(pct).base - hits) % 4


def total_label(k):
    return {0: "aucune rotation", 1: "90° horaire", 2: "180°", 3: "90° anti-horaire"}[k % 4]


# --- Confusion choisie ou copiée -----------------------------------------------------
# Choix du menu déroulant : (quarts de tour horaires ou None, libellé). None = d'après la tranche de PV.
CONF_CHOICES = [
    (None, "Confusion : selon mes PV"),
    (1, "Confusion horaire 2 Pi/4 → 90° horaire"),
    (2, "Confusion horaire 4 Pi/4 → 180°"),
    (3, "Confusion horaire 6 Pi/4 → 90° anti-horaire"),
    (0, "Confusion 0 Pi/4 → aucune rotation"),
]

# Ligne du chat de combat : « Confusion horaire : 2 Pi/4 », « Confusion contre horaire : 6 Pi/4 ».
_CONF = re.compile(
    r"c[o0]nf[uv]s[il1][o0]n\s*((?:c[o0]ntr[e3]|anti)[\s\-]*)?h[o0]ra[il1|!]r[e3]"
    r"\s*[:.;]?\s*(\d+)\s*(?:pi|p[il1]|π)\s*/\s*(\d+)", re.I)


def parse_confusion(text, strict=True):
    """Rotation d'une ligne de confusion, en quarts de tour horaires (0 à 3), ou None.

    Plusieurs lignes : la dernière l'emporte. Hors mode strict, le mot « Confusion » peut manquer
    (« contre horaire : 6 Pi/4 »), pratique quand on tape la ligne à la main.
    """
    if not text:
        return None
    if not strict and "confusion" not in text.lower():
        text = "Confusion " + text
    last = None
    for m in _CONF.finditer(text):
        num, den = int(m.group(2)), int(m.group(3))
        if den and (2 * num) % den == 0:             # n/d x 180° doit être un multiple de 90°
            quarters = (2 * num) // den
            last = (-quarters if m.group(1) else quarters) % 4
    return last


# --- Géométrie de la grille -------------------------------------------------------
def to_ij(cell):
    a, b = cell
    return ((a + b) // 2, (a - b) // 2)


def from_ij(i, j):
    return (i + j, i - j)


def rot(v, k):
    """Quart de tour du simulateur : (i, j) -> (j, -i), répété k fois."""
    i, j = v
    for _ in range(k % 4):
        i, j = j, -i
    return (i, j)


def tap_cell(you, mon, k):
    """Case sur laquelle cliquer pour que le sort atterrisse sur `mon` (formule du simulateur)."""
    y, m = to_ij(you), to_ij(mon)
    r = rot((m[0] - y[0], m[1] - y[1]), k)
    return from_ij(y[0] + r[0], y[1] + r[1])


def landing_cell(you, aim, k):
    """Case où le sort atterrit réellement quand on clique `aim` (inverse de tap_cell)."""
    y, c = to_ij(you), to_ij(aim)
    r = rot((c[0] - y[0], c[1] - y[1]), (4 - k) % 4)
    return from_ij(y[0] + r[0], y[1] + r[1])


def _seg_hits_square(p, q, c, half):
    t0, t1 = 0.0, 1.0
    for d in (0, 1):
        lo, hi = c[d] - half, c[d] + half
        dp = q[d] - p[d]
        if abs(dp) < 1e-12:
            if p[d] < lo or p[d] > hi:
                return False
        else:
            u, v = (lo - p[d]) / dp, (hi - p[d]) / dp
            if u > v:
                u, v = v, u
            t0, t1 = max(t0, u), min(t1, v)
            if t0 > t1:
                return False
    return True


def has_los(fight, src, dst):
    """Ligne de vue : aucun bloc (hors les deux extrémités) ne coupe le segment src -> dst."""
    p, q = to_ij(src), to_ij(dst)
    return not any(
        blk != src and blk != dst and _seg_hits_square(p, q, to_ij(blk), 0.45)
        for blk in fight.blocks
    )


def is_free(fight, cell):
    return cell in ARENA and cell not in fight.blocks and cell not in fight.pits


@dataclass
class Evaluation:
    k: int
    aim: tuple
    landing: tuple
    aim_ok: bool           # la case visée est une case libre de la carte
    landing_on_map: bool   # le sort atterrit dans la salle
    los_aim: bool          # ligne de vue vers la case visée
    los_landing: bool      # ligne de vue vers la case d'atterrissage

    @property
    def warnings(self):
        w = []
        if not self.aim_ok:
            w.append("Case visée : hors de la carte" if self.aim not in ARENA else "Case visée : mur ou trou")
        if not self.landing_on_map:
            w.append("Le sort atterrit hors de la carte")
        if not self.los_aim:
            w.append("Pas de ligne de vue vers la case visée")
        if not self.los_landing and self.landing_on_map:
            w.append("Pas de ligne de vue vers la case d'atterrissage")
        return w


def evaluate(fight, you, aim, k):
    land = landing_cell(you, aim, k)
    return Evaluation(
        k=k, aim=aim, landing=land,
        aim_ok=is_free(fight, aim),
        landing_on_map=land in ARENA,
        los_aim=has_los(fight, you, aim),
        los_landing=has_los(fight, you, land) if land in ARENA else True,
    )


# --- Calibration : cases <-> pixels de l'écran -------------------------------------
# Les deux repères cliqués pendant la calibration : la case du milieu tout en haut de la salle
# et celle du milieu tout en bas (les deux pointes, faciles à reconnaître).
CAL_TOP = (-2, 0)
CAL_BOTTOM = (24, 0)

@dataclass
class Calib:
    """x = x0 + kx * b ; y = y0 + ky * a. Un pas de b ou de a vaut une demi-case."""
    x0: float
    y0: float
    kx: float
    ky: float

    def center(self, cell):
        a, b = cell
        return (self.x0 + self.kx * b, self.y0 + self.ky * a)

    def polygon(self, cell):
        x, y = self.center(cell)
        return [(x, y - self.ky), (x + self.kx, y), (x, y + self.ky), (x - self.kx, y)]

    def cell_at(self, x, y):
        af, bf = (y - self.y0) / self.ky, (x - self.x0) / self.kx
        best, best_d = None, 1e9
        for a in range(math.floor(af) - 1, math.floor(af) + 3):
            for b in range(math.floor(bf) - 2, math.floor(bf) + 4):
                if (a + b) % 2:
                    continue
                d = abs(a - af) + abs(b - bf)
                if d < best_d:
                    best, best_d = (a, b), d
        return best if best in ARENA else None

    @staticmethod
    def from_anchors(top_xy, bottom_xy):
        """Calibration à partir de deux clics : le centre de CAL_TOP et celui de CAL_BOTTOM.

        Les cases de Dofus font exactement deux fois plus large que haut : la largeur se déduit de la hauteur.
        """
        (xt, yt), (xb, yb) = top_xy, bottom_xy
        ky = (yb - yt) / float(CAL_BOTTOM[0] - CAL_TOP[0])
        if ky <= 2:
            return None                       # clics inversés ou trop proches
        return Calib(x0=(xt + xb) / 2.0, y0=yt - ky * CAL_TOP[0], kx=2 * ky, ky=ky)

    @staticmethod
    def default_for(screen_w, screen_h):
        """Calibration de départ, mesurée sur une capture réelle de 1918 x 1037 : la carte est centrée
        un peu à gauche de l'écran, ses cases font environ 88 x 44 px. À ajuster avec la calibration."""
        s = min(screen_w / 1918.0, screen_h / 1037.0)
        return Calib(x0=0.4885 * screen_w, y0=0.2565 * screen_h, kx=44.0 * s, ky=22.0 * s)
