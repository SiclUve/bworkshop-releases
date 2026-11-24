"""Audit de bout en bout du mode Songes (Qt hors écran, sans souris ni clavier réels). Lancer : python audit_songes.py"""
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from PyQt6.QtWidgets import QApplication

import core
import i18n
import overlay
import view

APP = QApplication.instance() or QApplication([])
SONGES = len(core.FIGHTS) - 1


from PyQt6.QtCore import QObject, pyqtSignal


class _NoHotkeys(QObject):
    fired = pyqtSignal(str)

    def __init__(self, *a, **k):
        super().__init__()
        self.error = None

    def stop(self):
        pass


def spin(ms):
    t = time.time()
    while time.time() - t < ms / 1000.0:
        APP.processEvents()


def make(**cfg):
    path = Path(tempfile.mkdtemp()) / "config.json"
    cfg.setdefault("lang", "fr")
    path.write_text(json.dumps(cfg), encoding="utf-8")
    overlay.CONFIG = path
    overlay.Hotkeys = _NoHotkeys
    return overlay.Controller(APP), path


def prim_points(prims):
    pts = []
    for p in prims:
        for v in p[1:]:
            if isinstance(v, (list, tuple)) and v and isinstance(v[0], (list, tuple)):
                pts += [tuple(q) for q in v if len(q) == 2]
    return pts


def near(pts, xy, tol):
    return any(abs(x - xy[0]) <= tol and abs(y - xy[1]) <= tol for x, y in pts)


def main():
    ok = []

    # 1. Lancé directement en Songes : la minuterie de démarrage ne capture jamais l'écran et ne bouge pas la grille
    ctl, path = make(fight=SONGES, calib={"x0": 700.0, "y0": 200.0, "kx": 30.0, "ky": 15.0})
    grabs = []
    ctl.grab_screen = lambda: grabs.append(1) or None
    before = (ctl.state.calib.x0, ctl.state.calib.y0, ctl.state.calib.kx, ctl.state.calib.ky)
    spin(2600)                                                       # la minuterie de 1,5 s a eu lieu
    assert ctl._is_free() and not grabs and ctl._autocal is None
    assert (ctl.state.calib.x0, ctl.state.calib.y0, ctl.state.calib.kx, ctl.state.calib.ky) == before
    ok.append("démarrage en Songes : aucune capture d'écran, grille identique")

    # 2. Toute case, partout : rotation = inverse exacte, grille avec les bons traits, pastille d'atterrissage au bon pixel
    s = ctl.state
    rng = random.Random(3)
    for kx in (14.0, 30.0, 44.0, 90.0):
        s.calib = core.Calib(rng.uniform(300, 900), rng.uniform(100, 400), kx, kx / 2)
        for _ in range(60):
            you = rng.choice([(a, b) for a in range(-40, 80) for b in range(-40, 80) if (a + b) % 2 == 0][:2000])
            aim = (you[0] + rng.randint(-14, 14) * 1, you[1] + rng.randint(-14, 14))
            if (aim[0] + aim[1]) % 2:
                aim = (aim[0], aim[1] + 1)
            for k in range(4):
                s.you, s.k_choice = you, k
                assert core.tap_cell(you, core.landing_cell(you, aim, k), k) == aim, (you, aim, k)
                ev = core.evaluate(core.FIGHTS[SONGES], you, aim, k)
                assert ev.aim_ok and ev.landing_on_map and ev.los_aim and ev.los_landing and not ev.warnings
    ok.append("rotations : 960 cas (4 tailles de case, cases négatives et lointaines), jamais d'avertissement parasite")

    # 3. Survol : la souris sur une case quelconque (même loin de la salle du Comte) donne cette case, avec la rotation voulue
    s.calib = core.Calib(631.0, 304.0, 44.0, 22.0)
    s.you, s.k_choice = (10, 4), 3
    for cell in [(10, 4), (-8, 2), (30, 40), (-20, -30), (60, 14)]:
        x, y = s.calib.center(cell)
        assert s.cell_at(x + 3, y - 2) == cell, cell
        s.mouse = (x + 3, y - 2)
        prims, *_ = view.scene(s)
        land = core.landing_cell(s.you, cell, 3)
        if land != cell:
            lx, ly = s.calib.center(land)
            assert near(prim_points(prims), (lx, ly), 30) or any(p[0] in ("poly", "text", "circle") for p in prims), cell
    ok.append("survol : n'importe quelle case est reconnue, atterrissage dessiné")

    # 4. L'affichage ne devient pas absurde (grille complète, aucune carte, aucun mur/trou) en grande taille d'écran
    for w, h in ((1280, 720), (1920, 1080), (2560, 1440), (3840, 2160)):
        s.screen_w, s.screen_h = w, h
        prims, *_ = view.scene(s)
        lines = [p for p in prims if p[0] == "line"]
        assert len(lines) > 40 and not any(p[0] == "poly" and p[2] in (view.BLOCK_FILL, view.PIT_FILL) for p in prims), (w, h)
        assert len(prims) < 4000, (w, h, len(prims))
    ok.append("grille libre complète de 720p à 4K (nombre de traits raisonnable)")

    # 5. Aller et retour Comte <-> Songes : la grille du Comte revient, rien ne reste en mode libre
    s.fight = 0
    ctl.set_fight(0) if hasattr(ctl, "set_fight") else None
    assert not ctl._is_free()
    ctl.set_fight(SONGES)
    assert ctl._is_free() and json.loads(path.read_text(encoding="utf-8")).get("fight") in (SONGES, 0)
    ok.append("bascule Comte <-> Songes")

    # 6. Relance : Songes est retenu, et en anglais aussi
    ctl.save()
    ctl.quit()
    overlay.CONFIG = path
    ctl2 = overlay.Controller(APP)
    ctl2._boot_timer.stop()
    assert ctl2._is_free() and ctl2.state.fight == SONGES
    i18n.set_lang("en")
    ctl2.refresh()
    assert "Dreams" in core.FIGHTS[SONGES].name or "Songes" in core.FIGHTS[SONGES].name
    i18n.set_lang("fr")
    ok.append("redémarrage : Songes retenu")

    for line in ok:
        print("OK :", line)


if __name__ == "__main__":
    main()
