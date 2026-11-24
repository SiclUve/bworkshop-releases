"""Tests de la calibration automatique (autocal.py). Lancer : python test_autocal.py   (nécessite Pillow)

On fabrique de fausses captures du jeu (neige autour, salle brune, interface et personnages qui gênent) avec une
grille connue, puis on vérifie que la détection la retrouve. Une vraie capture de combat sert de dernier contrôle.
"""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))

import autocal
import core


def synthetic(w, h, x0, y0, kx, seed=0, clutter=True):
    """Fausse capture de w x h pixels avec la grille (x0, y0, kx). Dessinée avec core.Calib, donc indépendante de autocal."""
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h), (226, 216, 246))                       # neige et ciel clair
    d = ImageDraw.Draw(img)
    cal = core.Calib(x0, y0, kx, kx / 2)
    d.ellipse((x0 - 16 * kx, y0 - 6 * kx, x0 + 16 * kx, y0 + 16 * kx), outline=(150, 95, 60), width=max(2, int(kx / 4)))
    for cell in sorted(core.ARENA):                                       # carreaux clairs et sombres en alternance
        shade = (232, 152, 112) if (cell[0] // 2 + cell[1] // 2) % 2 else (186, 108, 76)
        d.polygon(cal.polygon(cell), fill=shade)
    if clutter:
        for cell in ((10, 0), (11, -1), (11, 1), (12, 0)):                # un bloc sombre, des trous, des personnages
            d.polygon(cal.polygon(cell), fill=(110, 66, 42))
        for cell in ((6, 8), (21, -1)):
            d.polygon(cal.polygon(cell), fill=(200, 205, 210))
        for _ in range(9):
            cx, cy = cal.center(list(core.ARENA)[int(rng.integers(len(core.ARENA)))])
            col = tuple(int(v) for v in rng.integers(20, 255, 3))
            d.ellipse((cx - kx * 0.3, cy - kx * 0.9, cx + kx * 0.3, cy), fill=col)
        d.rectangle((0, 0, w * 0.22, h * 0.14), fill=(40, 40, 46))        # interface du jeu : cadres sombres,
        d.rectangle((w * 0.55, 0, w * 0.88, h * 0.1), fill=(60, 50, 50))  # barre d'ordre de jeu,
        d.rectangle((0, h * 0.72, w * 0.2, h), fill=(35, 35, 40))         # chat
        for _ in range(12):                                               # icônes orange hors de la salle
            ix, iy = int(rng.integers(0, int(w * 0.2))), int(rng.integers(0, int(h * 0.12)))
            d.rectangle((ix, iy, ix + 12, iy + 12), fill=(235, 130, 40))
    return np.asarray(img)


def test_synthetic():
    cases = [(1280, 720, 640, 150, 40), (1920, 1080, 960, 200, 64), (1024, 600, 500, 90, 28), (1600, 900, 700, 120, 52),
             (2560, 1440, 1280, 250, 84)]
    for w, h, x0, y0, kx in cases:
        img = synthetic(w, h, x0, y0, kx)
        t = time.time()
        fit = autocal.find(img)
        dt = time.time() - t
        assert fit is not None and fit.confident, (w, h, fit)
        err = (abs(fit.x0 - x0), abs(fit.y0 - y0), abs(fit.kx / kx - 1) * 100)
        print(f"  {w}x{h} kx={kx}: erreur x {err[0]:.2f} px, y {err[1]:.2f} px, taille {err[2]:.2f} %  ({dt:.1f} s)")
        assert err[0] < 1.5 and err[1] < 1.5 and err[2] < 1.0, err
        assert dt < 10
        # recherche locale depuis une grille décalée de 40 px (le cas relevé en jeu) : même résultat, plus vite
        t = time.time()
        loc = autocal.find(img, hint=(x0 - 40, y0 + 8, kx * 1.05))
        assert loc is not None and loc.confident and abs(loc.x0 - x0) < 1.5 and abs(loc.y0 - y0) < 1.5, loc
        # un très mauvais indice : on retombe sur la recherche complète
        far = autocal.find(img, hint=(30, 30, kx * 0.4))
        assert far is not None and far.confident and abs(far.x0 - x0) < 1.5
    print("OK : détection sur de fausses captures (5 tailles d'écran, interface et personnages qui gênent)")


def test_partial_and_negative():
    # salle en partie hors de l'image : soit refusée, soit juste (jamais « sûre » et fausse)
    w, h, x0, y0, kx = 1280, 720, 1150, 150, 40
    fit = autocal.find(synthetic(w, h, x0, y0, kx))
    assert fit is None or not fit.confident or (abs(fit.x0 - x0) < 2 and abs(fit.y0 - y0) < 2), fit
    # pas de salle : rien de « sûr »
    rng = np.random.default_rng(3)
    for name, img in {
        "neige": np.full((720, 1280, 3), (226, 216, 246), np.uint8),
        "bruit": rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8),
        "bureau": np.concatenate([np.full((680, 1280, 3), (30, 90, 160), np.uint8), np.full((40, 1280, 3), (25, 25, 30), np.uint8)]),
        "interface sans salle": synthetic(1280, 720, 5000, 5000, 40),
    }.items():
        f = autocal.find(img)
        assert f is None or not f.confident, (name, f)
    print("OK : salle hors champ ou absente jamais prise pour une vraie salle")


def test_selftest():
    assert autocal.selftest()
    print("OK : auto-contrôle intégré")


def test_real_screenshot():
    path = Path(__file__).parent / "exemples" / "combat_comte_seul.webp"
    if not path.exists():
        print("(capture d'exemple absente : test ignoré)")
        return
    fit = autocal.find(np.asarray(Image.open(path).convert("RGB")))
    assert fit is not None and fit.confident
    print(f"  capture réelle : x0={fit.x0:.1f} y0={fit.y0:.1f} kx={fit.kx:.2f}   (référence : 631, 304, 44)")
    assert abs(fit.x0 - 631) < 3.5 and abs(fit.y0 - 304) < 3.5 and abs(fit.kx / 44 - 1) < 0.02
    print("OK : détection sur une vraie capture de combat")


if __name__ == "__main__":
    test_synthetic()
    test_partial_and_negative()
    test_selftest()
    test_real_screenshot()
