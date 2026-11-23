"""Calibration automatique : retrouve la grille de la salle sur une capture d'écran du jeu.

Le carrelage de la salle est brun et orange, la neige autour est blanche et bleutée, le ciel est violet : la salle
se détache bien. On cherche où poser la forme de la salle (core.ARENA) pour qu'elle recouvre le mieux possible les
pixels bruns. Seul numpy est nécessaire (corrélation par FFT), donc rien de plus à installer.

    fit = find(rgb)                    # rgb : tableau numpy (hauteur, largeur, 3), en pixels
    if fit and fit.confident: ...      # fit.x0, fit.y0, fit.kx, fit.ky : la grille en pixels de la capture

Cette lecture de l'écran ne sert qu'à caler la grille ; rien n'est gardé ni envoyé nulle part.
"""
from dataclasses import dataclass

import numpy as np

import core

MIN_SCORE = 0.30      # part du modèle bien couverte (une vraie salle : 0,41 à 0,51 ; sans salle : moins de 0,08)
MIN_SHARP = 0.030     # chute du score quand la taille change de 15 % : sinon, la taille est ambiguë (salle presque hors champ)

STEP = 0.1                                   # finesse de la grille de travail, en demi-cases
A0, B0, NA, NB = -8.0, -20.0, 360, 400       # sa zone : lignes a de -8 à 28, colonnes b de -20 à 20
_FINE = []


@dataclass
class Fit:
    x0: float
    y0: float
    kx: float
    score: float
    sharp: float = None      # None : calcul impossible (recherche limitée autour d'une taille connue)

    @property
    def ky(self):
        return self.kx / 2

    @property
    def confident(self):
        return self.score >= MIN_SCORE and (self.sharp is None or self.sharp >= MIN_SHARP)


def _fine_arena():
    """La salle sur une grille fine en (ligne a, colonne b), calculée une seule fois."""
    if not _FINE:
        a = A0 + STEP * np.arange(NA)[:, None]
        b = B0 + STEP * np.arange(NB)[None, :]
        i, j = np.floor((a + b) / 2 + 0.5), np.floor((a - b) / 2 + 0.5)
        kind = np.zeros((80, 80), bool)
        for aa, bb in core.ARENA:
            kind[aa + 40, bb + 40] = True
        _FINE.append(kind[np.clip((i + j).astype(int) + 40, 0, 79), np.clip((i - j).astype(int) + 40, 0, 79)])
    return _FINE[0]


def template(kx):
    """Modèle de la salle en pixels : +1 dans la salle, -1 autour. Renvoie (modèle, x0 dedans, y0 dedans)."""
    ky, pad = kx / 2, 1.6
    a_lo, a_hi, b_lo, b_hi = -3 - pad, 25 + pad, -14 - pad, 14 + pad
    h, w = int(np.ceil((a_hi - a_lo) * ky)) + 1, int(np.ceil((b_hi - b_lo) * kx)) + 1
    ay, ax = -a_lo * ky, -b_lo * kx
    ia = np.clip(np.round(((np.arange(h) - ay) / ky - A0) / STEP).astype(int), 0, NA - 1)
    ib = np.clip(np.round(((np.arange(w) - ax) / kx - B0) / STEP).astype(int), 0, NB - 1)
    return np.where(_fine_arena()[ia[:, None], ib[None, :]], 1.0, -1.0).astype(np.float32), ax, ay


def brown_mask(rgb):
    """Pixels bruns ou orange (carrelage, blocs, rebord) : ni la neige, ni le ciel, ni le gris de l'interface."""
    r, g, b = (rgb[..., c].astype(np.int16) for c in range(3))
    return ((r - b > 48) & (r >= g) & (g >= b - 4)).astype(np.float32)


def _downsample(m, k):
    if k == 1:
        return m
    h, w = (m.shape[0] // k) * k, (m.shape[1] // k) * k
    return m[:h, :w].reshape(h // k, k, w // k, k).mean((1, 3))


def _fast(n):
    """Plus petite taille >= n qui ne contient que les facteurs 2, 3 et 5 (la FFT y est rapide)."""
    while True:
        m = n
        for p in (2, 3, 5):
            while m % p == 0:
                m //= p
        if m == 1:
            return n
        n += 1


class _Correlator:
    """Corrèle une image (masque) avec le modèle de la salle à plusieurs tailles. La FFT du masque est faite une fois."""

    def __init__(self, mask, ds, kx_max):
        self.mask, self.ds = mask, ds
        h, w = template(kx_max / ds)[0].shape
        self.shape = (_fast(mask.shape[0] + h), _fast(mask.shape[1] + w))
        self.F = np.fft.rfft2(mask, self.shape)

    def at(self, kx):
        """Carte des scores (par position du coin haut-gauche du modèle) pour la taille kx, en pixels pleins."""
        T, ax, ay = template(kx / self.ds)
        h, w = T.shape
        if h > self.mask.shape[0] * 1.7 or w > self.mask.shape[1] * 1.7:
            return None
        c = np.fft.irfft2(self.F * np.conj(np.fft.rfft2(T, self.shape)), self.shape) / T.size
        # la corrélation est circulaire : on recale pour que c[y, x] soit le modèle posé avec son coin à
        # (x - (w-1), y - (h-1)), y compris quand il dépasse un peu de l'image
        c = np.roll(c, (h - 1, w - 1), axis=(0, 1))[: self.mask.shape[0] + h - 1, : self.mask.shape[1] + w - 1]
        return c, (w - 1) - ax, (h - 1) - ay          # décalages pour retrouver (x0, y0) = (x - ox, y - oy)


def _peak(c, ox, oy, ds, around=None, radius=10):
    """Meilleure position (x0, y0 en pixels pleins) de la carte c, éventuellement près de `around`, avec sous-pixel."""
    if around is None:
        y, x = np.unravel_index(np.argmax(c), c.shape)
    else:
        cx, cy = int(round(around[0] / ds + ox)), int(round(around[1] / ds + oy))
        y0, x0 = max(1, cy - radius), max(1, cx - radius)
        win = c[y0: cy + radius + 1, x0: cx + radius + 1]
        if win.size == 0:
            return None
        yy, xx = np.unravel_index(np.argmax(win), win.shape)
        y, x = y0 + yy, x0 + xx
    if not (0 < y < c.shape[0] - 1 and 0 < x < c.shape[1] - 1):
        return c[y, x], (x - ox) * ds, (y - oy) * ds

    def sub(v0, v1, v2):
        d = v0 - 2 * v1 + v2
        return 0.0 if abs(d) < 1e-12 else 0.5 * (v0 - v2) / d

    dx, dy = sub(c[y, x - 1], c[y, x], c[y, x + 1]), sub(c[y - 1, x], c[y, x], c[y + 1, x])
    return c[y, x], (x + dx - ox) * ds, (y + dy - oy) * ds


def _refine(mask, ds2, kx0, pos0, span=0.06):
    """Affine taille et position (à ds2 fois moins de pixels), autour de la solution grossière."""
    m = _downsample(mask, ds2)
    corr = _Correlator(m, ds2, kx0 * (1 + span))
    rows = []
    for f in np.linspace(1 - span, 1 + span, 13):
        r = corr.at(kx0 * f)
        if r is None:
            continue
        c, ox, oy = r
        p = _peak(c, ox, oy, ds2, around=pos0, radius=12)
        if p is not None:
            rows.append((kx0 * f, p[0], p[1], p[2]))
    if not rows:
        return None
    i = int(np.argmax([r[1] for r in rows]))
    kx, score, x, y = rows[i]
    if 0 < i < len(rows) - 1:                          # taille sous-pixel : parabole sur les trois échelles voisines
        s0, s1, s2 = rows[i - 1][1], rows[i][1], rows[i + 1][1]
        d = s0 - 2 * s1 + s2
        if abs(d) > 1e-12:
            kx = rows[i][0] + 0.5 * (s0 - s2) / d * (rows[i + 1][0] - rows[i - 1][0]) / 2
    return Fit(x, y, kx, score)


def find(rgb, hint=None):
    """Cherche la grille sur `rgb` (tableau numpy hauteur x largeur x 3).

    hint : (x0, y0, kx) d'une calibration approximative, en pixels de la capture. Si elle est donnée, on cherche
    d'abord près d'elle (plus rapide) et on ne passe à la recherche complète que si ça ne donne rien de sûr.
    Renvoie un Fit (à tester avec .confident) ou None.
    """
    mask = brown_mask(rgb)
    H, W = mask.shape
    ds = max(4, int(round(max(H, W) / 480.0)))
    if hint is not None and hint[2] > 0:
        fit = _search(mask, ds, hint[2] * 0.88, hint[2] * 1.12, hint, W)
        if fit is not None and fit.confident:
            return fit
    return _search(mask, ds, W / 100.0, W / 21.0, None, W)


def _search(mask, ds, kx_lo, kx_hi, hint, width):
    m4 = _downsample(mask, ds)
    corr = _Correlator(m4, ds, kx_hi)
    scan, kx = [], kx_lo
    while kx <= kx_hi:
        r = corr.at(kx)
        if r is not None:
            c, ox, oy = r
            if hint is None:
                p = _peak(c, ox, oy, ds)
            else:
                p = _peak(c, ox, oy, ds, around=(hint[0], hint[1]), radius=int(8 * max(1, hint[2] / ds)))
            if p is not None:
                scan.append((kx, p[0], p[1], p[2]))
        kx *= 1.02
    if not scan:
        return None
    best = max(scan, key=lambda r: r[1])
    fit = _refine(mask, max(1, ds // 2), best[0], (best[2], best[3]))
    if fit is None:
        return None
    if hint is None:                                   # netteté : le score doit chuter si la taille change de 15 %
        near = lambda f: [r[1] for r in scan if abs(r[0] / best[0] / f - 1) < 0.02]
        sides = [max(v) for v in (near(0.85), near(1.15)) if v]
        fit.sharp = best[1] - max(sides) if sides else None
    return fit


def selftest():
    """Contrôle rapide (« HarebourgOverlay.exe --selftest fichier ») : retrouve une grille connue sur une image fabriquée."""
    h, w, x0, y0, kx = 540, 960, 480.0, 90.0, 30.0
    ys, xs = np.mgrid[0:h, 0:w]
    a, b = (ys - y0) / (kx / 2), (xs - x0) / kx
    ia, ib = np.round((a - A0) / STEP).astype(int), np.round((b - B0) / STEP).astype(int)
    ok = (ia >= 0) & (ia < NA) & (ib >= 0) & (ib < NB)
    inside = np.zeros((h, w), bool)
    inside[ok] = _fine_arena()[ia[ok], ib[ok]]
    img = np.empty((h, w, 3), np.uint8)
    img[:] = (226, 216, 246)
    img[inside] = (170, 100, 60)
    fit = find(img)
    return bool(fit is not None and fit.confident and abs(fit.x0 - x0) < 2 and abs(fit.y0 - y0) < 2
                and abs(fit.kx / kx - 1) < 0.02)
