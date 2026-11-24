"""Tests de la fenêtre et de la calibration, sans écran (Qt « offscreen »). Lancer : python test_ui.py

Couvre : redimensionnement de la fenêtre par les bords et les coins, zone qui défile, mode mini, taille retenue,
parcours de calibration à la souris, et calage fin de la grille avec les raccourcis (caler, décaler, agrandir).
Chaque test travaille sur une copie vide de config.json : tes réglages ne sont jamais touchés.
"""
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication

import numpy as np

import core
import overlay
import view


class _NoHotkeys(QObject):
    """Les tests n'installent jamais de vrai écouteur de clavier global sur l'ordinateur : on simule les raccourcis
    en appelant directement `Controller.on_hotkey(nom)`. (Les raccourcis, eux, sont vérifiés avec pynput.keyboard.HotKey.parse.)"""
    fired = pyqtSignal(str)

    def __init__(self, mapping):
        super().__init__()
        self.error = None

    def stop(self):
        pass


overlay.Hotkeys = _NoHotkeys

APP = QApplication.instance() or QApplication([])
E = Qt.Edge
REAL = core.Calib(631.0, 304.0, 44.0, 22.0)      # une calibration connue (capture de combat du dépôt)


def fresh(**cfg):
    """Un contrôleur tout neuf, avec sa propre config temporaire."""
    path = Path(tempfile.mkdtemp()) / "config.json"
    cfg.setdefault("lang", "fr")                   # les tests ne dépendent pas de la langue du système
    path.write_text(json.dumps(cfg), encoding="utf-8")
    overlay.CONFIG = path
    ctl = overlay.Controller(APP)
    ctl._boot_timer.stop()                 # pas de calage automatique au lancement pendant les tests
    ctl.state.fight = 0
    return ctl, path


def spin(ms=0):
    t = time.time()
    APP.processEvents()
    while time.time() - t < ms / 1000.0:
        APP.processEvents()
    APP.processEvents()


def mouse(kind, local, glob, button=Qt.MouseButton.LeftButton):
    t = {"p": QEvent.Type.MouseButtonPress, "m": QEvent.Type.MouseMove, "r": QEvent.Type.MouseButtonRelease}[kind]
    held = button if kind == "m" else Qt.MouseButton.NoButton
    return QMouseEvent(t, QPointF(*local), QPointF(*glob), button if kind != "m" else Qt.MouseButton.NoButton,
                       held, Qt.KeyboardModifier.NoModifier)


def test_resize():
    ctl, path = fresh()
    P = ctl.panel
    w, h = P.width(), P.height()
    # zones de prise et curseurs
    assert P.edges_at(QPoint(w // 2, h // 2)) == E(0)
    assert P.edges_at(QPoint(w - 3, h // 2)) == E.RightEdge and P.edges_at(QPoint(2, h // 2)) == E.LeftEdge
    assert P.edges_at(QPoint(w // 2, 3)) == E.TopEdge and P.edges_at(QPoint(w // 2, h - 3)) == E.BottomEdge
    assert P.edges_at(QPoint(w - 3, h - 3)) == E.RightEdge | E.BottomEdge
    assert P.edges_at(QPoint(3, 3)) == E.LeftEdge | E.TopEdge
    assert P.cursor_for(E.RightEdge) == Qt.CursorShape.SizeHorCursor
    assert P.cursor_for(E.BottomEdge) == Qt.CursorShape.SizeVerCursor
    assert P.cursor_for(E.RightEdge | E.BottomEdge) == Qt.CursorShape.SizeFDiagCursor
    assert P.cursor_for(E.RightEdge | E.TopEdge) == Qt.CursorShape.SizeBDiagCursor

    def drag(local, dx, dy):
        g0 = (1000, 600)
        P.mousePressEvent(mouse("p", local, g0))
        P.mouseMoveEvent(mouse("m", local, (g0[0] + dx, g0[1] + dy)))
        P.mouseReleaseEvent(mouse("r", local, (g0[0] + dx, g0[1] + dy)))

    P.move(200, 100)
    x0, y0, w, h = P.x(), P.y(), P.width(), P.height()
    drag((w - 3, h // 2), 80, 0)                                   # largeur
    assert (P.width(), P.height(), P.x(), P.y()) == (w + 80, h, x0, y0)
    w, h = P.width(), P.height()
    drag((w // 2, h - 3), 0, 60)                                   # hauteur
    assert (P.width(), P.height()) == (w, h + 60)
    w, h = P.width(), P.height()
    drag((w - 3, h - 3), 25, 35)                                   # diagonale
    assert (P.width(), P.height()) == (w + 25, h + 35)
    w, h, right = P.width(), P.height(), P.x() + P.width()
    drag((2, h // 2), -50, 0)                                      # bord gauche : le bord droit reste en place
    assert P.width() == w + 50 and P.x() + P.width() == right
    w, h = P.width(), P.height()
    right, bottom = P.x() + w, P.y() + h
    drag((3, 3), -20, -15)                                         # coin haut-gauche
    assert (P.width(), P.height()) == (w + 20, h + 15) and (P.x() + P.width(), P.y() + P.height()) == (right, bottom)
    drag((P.width() - 3, P.height() - 3), -5000, -5000)            # jamais sous la taille minimale
    assert (P.width(), P.height()) == (P.minimumWidth(), P.minimumHeight())

    # plus bas que le contenu : la zone défile
    ctl.sections["keys"].set_collapsed(False)
    spin()
    P.resize(P.width(), 300)
    spin()
    assert ctl.scroll.verticalScrollBar().maximum() > 100
    # replier / déplier ajuste la hauteur au contenu
    for sec in ctl.sections.values():
        sec.set_collapsed(True)
    spin()
    small = P.height()
    ctl.sections["keys"].set_collapsed(False)
    spin()
    assert small < P.height()
    ctl.sections["keys"].set_collapsed(True)
    spin()

    # mode mini : seule la largeur se règle ; on retrouve la taille d'avant
    P.resize(500, 700)
    spin()
    ctl.toggle_all()
    mini = (P.width(), P.height())
    assert ctl.mini and not ctl.scroll.isVisible() and mini[1] < 140
    drag((P.width() - 3, P.height() - 3), 0, 200)
    assert P.height() == mini[1]
    drag((P.width() - 3, P.height() // 2), 60, 0)
    assert P.width() == mini[0] + 60
    ctl.toggle_all()
    spin()
    assert not ctl.mini and P.width() == 500 and ctl.scroll.isVisible()

    # la taille et la position sont gardées d'une fois sur l'autre
    P.resize(430, 520)
    P.move(111, 77)
    spin(900)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["panel_size"] == [430, 520] and saved["panel_pos"] == [111, 77]
    assert "show_hud" not in saved and "ui_scale" not in saved
    ctl.quit()
    ctl2 = overlay.Controller(APP)
    assert (ctl2.panel.width(), ctl2.panel.height()) == (430, 520) and (ctl2.panel.x(), ctl2.panel.y()) == (111, 77)
    ctl2.quit()
    print("OK : fenêtre redimensionnable (bords, coins, défilement, mini, taille retenue)")


def test_fine_calibration():
    ctl, path = fresh()
    s = ctl.state
    # les raccourcis de calage fin existent, sont lisibles par pynput et ne se marchent pas dessus
    from pynput import keyboard
    new = ["snap", "nudge_left", "nudge_right", "nudge_up", "nudge_down", "grid_grow", "grid_shrink"]
    assert all(ctl.keys.get(k) and k in overlay.KEY_HELP and k in ctl.key_btns for k in new)
    for combo in overlay.DEFAULT_KEYS.values():
        keyboard.HotKey.parse(combo)
    assert len(set(ctl.keys.values())) == len(ctl.keys)

    def reset(dx, dy):
        s.calib = core.Calib(REAL.x0 + dx, REAL.y0 + dy, REAL.kx, REAL.ky)

    # caler : souris au centre d'une case, grille décalée de 13 px (le cas relevé sur une vraie capture)
    reset(13, -5)
    pos = REAL.center((18, -2))
    ctl._mouse_pos = lambda: pos
    ctl.on_hotkey("snap")
    assert abs(s.calib.x0 - REAL.x0) < 1e-9 and abs(s.calib.y0 - REAL.y0) < 1e-9
    assert all(s.calib.cell_at(*REAL.center(c)) == c for c in core.ARENA)
    ctl._mouse_pos = lambda: (5.0, 5.0)                            # hors de la salle : rien ne bouge
    before = (s.calib.x0, s.calib.y0)
    ctl.on_hotkey("snap")
    assert (s.calib.x0, s.calib.y0) == before

    # décaler : 1 px, puis de plus en plus vite si on insiste, puis retour à 1 px après une pause
    class Clock:
        t = 100.0

        @classmethod
        def monotonic(cls):
            return cls.t

    real_time, overlay.time = overlay.time, Clock
    try:
        reset(0, 0)
        xs = [s.calib.x0]
        for _ in range(10):
            ctl.on_hotkey("nudge_right")
            xs.append(s.calib.x0)
            Clock.t += 0.1
        assert [round(b - a) for a, b in zip(xs, xs[1:])] == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4]
        Clock.t += 2.0
        x = s.calib.x0
        ctl.on_hotkey("nudge_right")
        assert s.calib.x0 - x == 1
        reset(0, 0)
        Clock.t += 2
        ctl.on_hotkey("nudge_down")
        Clock.t += 2
        ctl.on_hotkey("nudge_up")
        Clock.t += 2
        ctl.on_hotkey("nudge_up")
        assert s.calib.y0 == REAL.y0 - 1 and s.calib.x0 == REAL.x0

        # agrandir / rapetisser autour de la souris : le point sous la souris ne bouge pas
        reset(0, 0)
        pos = (900.0, 500.0)
        ctl._mouse_pos = lambda: pos
        Clock.t += 5
        c = s.calib
        fixed = ((pos[0] - c.x0) / c.kx, (pos[1] - c.y0) / c.ky)
        ctl.on_hotkey("grid_grow")
        c = s.calib
        assert c.kx > 44 and abs(c.kx - 2 * c.ky) < 1e-9
        assert abs((pos[0] - c.x0) / c.kx - fixed[0]) < 1e-9 and abs((pos[1] - c.y0) / c.ky - fixed[1]) < 1e-9
        grown = c.kx
        Clock.t += 5
        ctl.on_hotkey("grid_shrink")
        assert abs(s.calib.kx - 44) < 0.01 and s.calib.kx < grown
        # enregistré après une courte pause
        reset(0, 0)
        Clock.t += 5
        ctl.on_hotkey("nudge_right")
    finally:
        overlay.time = real_time
    spin(900)
    assert abs(json.loads(path.read_text(encoding="utf-8"))["calib"]["x0"] - (REAL.x0 + 1)) < 1e-9
    # pendant qu'on choisit une touche, les raccourcis sont ignorés
    ctl.recording_key = True
    x = s.calib.x0
    ctl.on_hotkey("nudge_right")
    assert s.calib.x0 == x
    ctl.quit()
    print("OK : calage fin en jeu (caler, décaler avec accélération, agrandir autour de la souris)")


def test_calibration_flow():
    ctl, _ = fresh()
    geom = QRect(0, 0, 1277, 946)
    cal = overlay.Calibration(geom, core.Calib(500, 200, 33, 16.5), 0)                # une ancienne grille très fausse
    cal.show()
    top, bot = REAL.center(core.CAL_TOP), REAL.center(core.CAL_BOTTOM)

    def move(x, y):
        cal.mouseMoveEvent(mouse("m", (x, y), (x, y), Qt.MouseButton.NoButton))

    def press(x, y, button=Qt.MouseButton.LeftButton):
        cal.mousePressEvent(mouse("p", (x, y), (x, y), button))

    def key(k):
        cal.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier))

    press(top[0], top[1] - 9)                                       # 1er clic, 9 px trop haut (on a visé le personnage)
    assert cal.step == 1
    move(top[0], top[1] - 50)
    assert cal.preview is None and "plus bas" in cal.msg           # au-dessus du 1er point : message
    move(top[0], top[1] + 40)
    assert cal.preview is None and "trop" in cal.msg               # trop proche : message
    move(top[0], (top[1] + bot[1]) / 2)
    assert cal.preview is not None and cal.msg is None             # la grille s'étire avec la souris
    press(bot[0], bot[1], Qt.MouseButton.RightButton)              # clic droit : on recommence
    assert cal.step == 0 and cal.top is None
    press(top[0], top[1] - 9)
    key(Qt.Key.Key_Return)
    assert cal.step == 1                                            # Entrée avant la fin : ignorée
    press(bot[0] + 60, bot[1] - 9)                                  # 2e point dans une autre colonne : refusé
    assert cal.step == 1 and "juste sous" in cal.msg
    press(bot[0] + 10, bot[1] - 9)                                  # la colonne du 2e clic est moyennée avec celle du 1er
    assert cal.step == 2
    c = cal.calib
    assert abs(c.kx - 2 * c.ky) < 1e-9 and abs(c.x0 - (top[0] + 5)) < 1e-9
    assert abs(c.y0 - (REAL.y0 - 9)) < 1e-9
    # réglage fin avec les flèches, puis Entrée
    for _ in range(round(abs(REAL.x0 - c.x0))):
        key(Qt.Key.Key_Left if c.x0 > REAL.x0 else Qt.Key.Key_Right)
    for _ in range(9):
        key(Qt.Key.Key_Down)
    got = []
    cal.done.connect(got.append)
    key(Qt.Key.Key_Return)
    assert got and abs(got[0].x0 - REAL.x0) < 1e-9 and abs(got[0].y0 - REAL.y0) < 1e-9
    assert all(got[0].cell_at(*REAL.center(c)) == c for c in core.ARENA)
    ctl.quit()
    print("OK : parcours de calibration (aperçu, messages, clic droit, réglage fin)")


def wait_autocal(ctl, seconds=15):
    """Laisse tourner le calage automatique (en arrière-plan) jusqu'à ce qu'il ait rendu son résultat."""
    t = time.time()
    while ctl._autocal is not None and time.time() - t < seconds:
        time.sleep(0.02)
        APP.processEvents()
    APP.processEvents()
    assert ctl._autocal is None, "le calage automatique n'a pas fini"


def test_auto_calibration():
    from test_autocal import synthetic
    ctl, path = fresh()
    s = ctl.state
    truth = core.Calib(560.0, 140.0, 38.0, 19.0)
    img = synthetic(1000, 700, truth.x0, truth.y0, truth.kx)
    ctl.grab_screen = lambda: (img, 1.0)
    # « Me placer » avec une grille décalée de 40 px et un peu trop grande, la souris au centre de la case (12, 4)
    s.calib = core.Calib(truth.x0 - 40, truth.y0 + 6, truth.kx * 1.04, truth.ky * 1.04)
    same_object = s.calib
    pos = truth.center((12, 4))
    ctl._mouse_pos = lambda: pos
    ctl.on_hotkey("set_me")
    assert s.you is not None                                       # placé tout de suite, avant la fin du calage
    wait_autocal(ctl)
    c = s.calib
    print(f"  grille retrouvée : x0={c.x0:.1f} y0={c.y0:.1f} kx={c.kx:.2f}  (vrai {truth.x0}, {truth.y0}, {truth.kx})")
    assert c is same_object                                         # corrigée sur place : les outils ouverts la voient aussi
    assert abs(c.x0 - truth.x0) < 1.5 and abs(c.y0 - truth.y0) < 1.5 and abs(c.kx / truth.kx - 1) < 0.01
    assert s.you == (12, 4) and s.flash and "calée" in ctl._msg[0] and not ctl._msg[1]
    assert "calée" in ctl.lbl.text()
    ctl._end_flash()
    assert not s.flash
    # grille déjà juste : rien ne bouge (pas de tremblement)
    before = (c.x0, c.y0, c.kx)
    ctl.on_hotkey("set_me")
    wait_autocal(ctl)
    assert (c.x0, c.y0, c.kx) == before
    # sauvegarde de la nouvelle calibration
    spin(900)
    assert abs(json.loads(path.read_text(encoding="utf-8"))["calib"]["x0"] - c.x0) < 1e-9

    # bouton « Calibrer la grille » : message quand c'est déjà bon
    ctl.calibrate_auto()
    wait_autocal(ctl)
    assert "déjà bien calée" in ctl._msg[0] and ctl.state.flash

    # écran à double densité (2 pixels par point) : les coordonnées reviennent en points
    ctl._end_flash()
    img2 = synthetic(1400, 900, 2 * 300.0, 2 * 90.0, 2 * 26.0)
    ctl.grab_screen = lambda: (img2, 2.0)
    s.calib = core.Calib(300.0 - 25, 90.0 + 5, 26.0, 13.0)
    ctl.on_hotkey("set_me")
    wait_autocal(ctl)
    c = s.calib
    assert abs(c.x0 - 300.0) < 1.0 and abs(c.y0 - 90.0) < 1.0 and abs(c.kx - 26.0) < 0.3, (c.x0, c.y0, c.kx)

    # salle introuvable : message clair, la grille ne change pas, et la calibration à la main s'ouvre
    ctl.grab_screen = lambda: (np.full((700, 1000, 3), (226, 216, 246), np.uint8), 1.0)
    keep = (c.x0, c.y0, c.kx)
    ctl.calibrate_auto()
    wait_autocal(ctl)
    assert ctl._msg[1] and "non reconnue" in ctl._msg[0] and (c.x0, c.y0, c.kx) == keep
    assert isinstance(ctl.tool, overlay.Calibration)
    ctl.tool.finish(None)
    assert ctl.tool is None
    # « Me placer » sans salle visible : silencieux, il se place quand même avec la grille actuelle
    ctl._msg = None
    ctl.on_hotkey("set_me")
    wait_autocal(ctl)
    assert ctl._msg is None and ctl.tool is None
    # capture impossible (jeu en plein écran exclusif) : pas d'erreur
    ctl.grab_screen = lambda: (None, 1.0)
    ctl.on_hotkey("set_me")
    ctl.calibrate_auto()
    assert ctl._autocal is None and ctl._msg[1]
    ctl.quit()
    print("OK : calibration automatique (Me placer, bouton, double densité, échec avec secours à la main)")


def test_songes_mode():
    from test_autocal import synthetic
    ctl, path = fresh()
    s = ctl.state
    songes = len(core.FIGHTS) - 1
    ctl.cb_fight.setCurrentIndex(songes)                            # menu « Combat » : Songes
    assert s.fight == songes and ctl._is_free()
    assert "Songes" in ctl._msg[0] and "jamais" in ctl.lbl_cal_note.text()
    assert not ctl.ck_grid.isEnabled() and not ctl.btn_hand.isEnabled()
    assert json.loads(path.read_text(encoding="utf-8"))["fight"] == songes
    # la grande grille est toujours dessinée, sans carte
    ctl.refresh()
    assert sum(1 for p in ctl.overlay.prims if p[0] == "line") > 40
    assert not any(p[0] == "poly" and p[2] in (view.BLOCK_FILL, view.PIT_FILL) for p in ctl.overlay.prims)

    # « Me placer » ne recale rien, même avec une capture qui ferait bouger la grille
    truth = core.Calib(560.0, 140.0, 38.0, 19.0)
    img = synthetic(1000, 700, truth.x0, truth.y0, truth.kx)
    ctl.grab_screen = lambda: (img, 1.0)
    s.calib = core.Calib(truth.x0 - 40, truth.y0 + 6, truth.kx * 1.04, truth.ky * 1.04)
    before = (s.calib.x0, s.calib.y0, s.calib.kx, s.calib.ky)
    far = (60, -40)                                                 # bien hors de la salle du Comte
    pos = s.calib.center(far)
    ctl._mouse_pos = lambda: pos
    ctl.on_hotkey("set_me")
    assert ctl._autocal is None and s.you == far
    ctl.start_autocal()                                             # au lancement aussi
    spin(300)
    assert ctl._autocal is None and (s.calib.x0, s.calib.y0, s.calib.kx, s.calib.ky) == before

    # caler sur la case sous la souris marche partout (case que le jeu entoure en blanc)
    mx, my = s.calib.center((30, 12))
    ctl._mouse_pos = lambda: (mx + 9, my - 4)
    ctl.on_hotkey("snap")
    assert abs(s.calib.center((30, 12))[0] - (mx + 9)) < 1e-9 and abs(s.calib.center((30, 12))[1] - (my - 4)) < 1e-9
    before = (s.calib.x0, s.calib.y0, s.calib.kx, s.calib.ky)

    # le bouton « Calibrer la grille » ouvre le calage à la main de la grille libre (jamais l'automatique)
    ctl.calibrate_auto()
    tool = ctl.tool
    assert isinstance(tool, overlay.FreeCalibration) and ctl._autocal is None
    assert not tool.grab().isNull()                                 # il se dessine
    tool.mousePressEvent(mouse("p", (100, 100), (100, 100)))
    tool.mouseMoveEvent(mouse("m", (130, 115), (130, 115)))
    tool.mouseReleaseEvent(mouse("r", (130, 115), (130, 115)))
    c = tool.calib
    assert abs(c.x0 - (before[0] + 30)) < 1e-9 and abs(c.y0 - (before[1] + 15)) < 1e-9
    fixed = ((400 - c.x0) / c.kx, (300 - c.y0) / c.ky)
    tool.zoom(1.1, 400, 300)                                        # la molette : la taille change autour de la souris
    assert abs(c.kx - before[2] * 1.1) < 1e-9 and abs(c.kx - 2 * c.ky) < 1e-9
    assert abs((400 - c.x0) / c.kx - fixed[0]) < 1e-9 and abs((300 - c.y0) / c.ky - fixed[1]) < 1e-9
    x = c.x0
    tool.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier))
    tool.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier))
    assert abs(c.x0 - (x + 1 - 10)) < 1e-9
    tool.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert ctl.tool is None and (s.calib.x0, s.calib.y0, s.calib.kx) == before[:3]       # Échap : rien ne change
    ctl.calibrate_auto()
    tool = ctl.tool
    tool.zoom(1.05, 500, 400)
    want = (tool.calib.x0, tool.calib.y0, tool.calib.kx)
    tool.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert ctl.tool is None and (s.calib.x0, s.calib.y0, s.calib.kx) == want              # Entrée : la grille est gardée
    spin(900)
    assert abs(json.loads(path.read_text(encoding="utf-8"))["calib"]["kx"] - want[2]) < 1e-9

    # placement au clic : n'importe quelle case, même loin de la salle du Comte
    ctl.open_place()
    assert isinstance(ctl.tool, overlay.PlacePicker)
    target = (-6, 30)
    ctl.tool.click(*s.calib.center(target))
    assert ctl.tool is None and s.you == target

    # retour à un combat du Comte : le calage automatique revient
    ctl.cb_fight.setCurrentIndex(0)
    assert not ctl._is_free() and ctl.ck_grid.isEnabled() and ctl.btn_hand.isEnabled()
    assert "toute seule" in ctl.lbl_cal_note.text()
    s.calib = core.Calib(truth.x0 - 40, truth.y0 + 6, truth.kx * 1.04, truth.ky * 1.04)
    pos = truth.center((12, 4))
    ctl._mouse_pos = lambda: pos
    ctl.on_hotkey("set_me")
    wait_autocal(ctl)
    assert abs(s.calib.x0 - truth.x0) < 1.5 and abs(s.calib.kx / truth.kx - 1) < 0.01 and s.you == (12, 4)

    # on passe en Songes pendant que le calcul tourne : son résultat est jeté, la grille ne bouge pas
    s.calib = core.Calib(truth.x0 - 40, truth.y0 + 6, truth.kx * 1.04, truth.ky * 1.04)
    kept = (s.calib.x0, s.calib.y0, s.calib.kx)
    ctl.on_hotkey("set_me")
    assert ctl._autocal is not None
    ctl.cb_fight.setCurrentIndex(songes)
    wait_autocal(ctl)
    assert (s.calib.x0, s.calib.y0, s.calib.kx) == kept
    ctl.quit()
    print("OK : mode Songes (grille libre, jamais recalée seule, calage à la main, placement partout)")


def test_auto_checkbox():
    from test_autocal import synthetic
    ctl, path = fresh()
    s = ctl.state
    assert ctl.ck_auto.isChecked() and ctl.ck_auto.isEnabled() and ctl.auto_calage
    truth = core.Calib(560.0, 140.0, 38.0, 19.0)
    img = synthetic(1000, 700, truth.x0, truth.y0, truth.kx)
    ctl.grab_screen = lambda: (img, 1.0)
    wrong = (truth.x0 - 40, truth.y0 + 6, truth.kx * 1.04)

    def reset():
        s.calib = core.Calib(wrong[0], wrong[1], wrong[2], wrong[2] / 2)

    # case décochée : « Me placer » place, mais ne recale rien ; ni au lancement
    ctl.ck_auto.setChecked(False)
    assert not ctl.auto_calage and "désactivé" in ctl.lbl_cal_note.text()
    assert json.loads(path.read_text(encoding="utf-8"))["auto_calage"] is False
    reset()
    pos = truth.center((12, 4))
    ctl._mouse_pos = lambda: pos
    ctl.on_hotkey("set_me")
    ctl.start_autocal()
    assert ctl._autocal is None and s.you is not None
    spin(300)
    assert (s.calib.x0, s.calib.y0, s.calib.kx) == wrong
    # le bouton « Calibrer la grille » marche toujours
    ctl.calibrate_auto()
    wait_autocal(ctl)
    assert abs(s.calib.x0 - truth.x0) < 1.5 and abs(s.calib.kx / truth.kx - 1) < 0.01 and "calée" in ctl._msg[0]
    # décochée pendant un calcul lancé automatiquement : le résultat est jeté
    ctl.ck_auto.setChecked(True)
    reset()
    ctl.on_hotkey("set_me")
    assert ctl._autocal is not None
    ctl.ck_auto.setChecked(False)
    wait_autocal(ctl)
    assert (s.calib.x0, s.calib.y0, s.calib.kx) == wrong
    # le réglage est retrouvé au lancement suivant ; recochée, le calage automatique revient
    spin(300)
    ctl.quit()
    ctl2 = overlay.Controller(APP)
    ctl2._boot_timer.stop()
    assert not ctl2.ck_auto.isChecked() and not ctl2.auto_calage
    ctl2.ck_auto.setChecked(True)
    ctl2.grab_screen = lambda: (img, 1.0)
    ctl2.state.fight = 0
    ctl2.state.calib = core.Calib(wrong[0], wrong[1], wrong[2], wrong[2] / 2)
    ctl2._mouse_pos = lambda: pos
    ctl2.on_hotkey("set_me")
    wait_autocal(ctl2)
    assert abs(ctl2.state.calib.x0 - truth.x0) < 1.5
    # en mode Songes la case est grisée (rien à décocher : jamais de calage automatique)
    ctl2.cb_fight.setCurrentIndex(len(core.FIGHTS) - 1)
    assert not ctl2.ck_auto.isEnabled()
    ctl2.cb_fight.setCurrentIndex(0)
    assert ctl2.ck_auto.isEnabled()
    ctl2.quit()
    print("OK : case « Calage automatique » (décochée : la grille ne bouge plus, bouton manuel gardé, réglage retenu)")


def test_robust_startup():
    import random
    from PyQt6.QtWidgets import QApplication as _A      # noqa: F401
    # des réglages abîmés ou absurdes n'empêchent jamais de démarrer
    rng = random.Random(11)
    junk = [None, True, 0, -5, 1e300, float("nan"), "", "x", [], [1, 2], {}, {"a": 1}, [[]], {"x0": "a"}]
    keys = ["calib", "calib_screen", "screen", "fight", "hp_manual", "show_grid", "mini", "auto_calage", "panel_opacity",
            "draw_opacity", "lang", "hotkeys", "collapsed", "panel_pos", "panel_size"]
    raws = ["", "{", "[1, 2]", '"texte"', "null", "42", "\x00\x01 pas du json", '{"fight": 99, "calib": {"x0": "a"}}']
    raws += [json.dumps({k: rng.choice(junk) for k in rng.sample(keys, rng.randint(1, len(keys)))}, default=str) for _ in range(25)]
    for raw in raws:
        path = Path(tempfile.mkdtemp()) / "config.json"
        path.write_text(raw, encoding="utf-8", errors="replace")
        overlay.CONFIG = path
        ctl = overlay.Controller(APP)
        ctl._boot_timer.stop()
        s = ctl.state
        assert 0 <= s.fight < len(core.FIGHTS) and s.calib.kx > 0 and 0 <= s.hp_manual <= 100, raw
        assert ctl.panel.width() >= 200 and 20 <= ctl.panel_opacity <= 100 and ctl.lang in ("fr", "en"), (raw, ctl.panel.width(), ctl.panel_opacity, ctl.lang)
        ctl.refresh()
        ctl.save()
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)      # et on réécrit un fichier sain
        ctl.quit()

    # fermeture tout de suite après un changement : rien n'est perdu (taille, position, calage)
    ctl, path = fresh()
    ctl.panel.resize(444, 555)
    ctl.state.calib.x0 += 7
    x = ctl.state.calib.x0
    ctl.quit()                                                      # pas d'attente : la sauvegarde différée n'a pas eu lieu
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert abs(saved["calib"]["x0"] - x) < 1e-9 and saved["panel_size"] == [444, 555]

    # échec d'écriture : pas d'erreur, un seul message, et le programme continue
    ctl, path = fresh()
    overlay.CONFIG = path.parent / "inexistant" / "config.json"
    ctl._msg = None
    ctl.save()
    assert ctl._msg is not None and ctl._msg[1] and "enregistrer" in ctl._msg[0]
    ctl._msg = None
    ctl.save()
    assert ctl._msg is None                                         # on ne prévient qu'une fois
    overlay.CONFIG = path
    ctl.save()
    assert not ctl._save_failed
    ctl.quit()

    # un outil plein écran qui plante à l'ouverture ne laisse pas l'overlay caché
    ctl, _ = fresh()

    class Boom(QObject):
        done = pyqtSignal(object)

        def open(self):
            raise RuntimeError("boum")

    real = sys.stderr
    sys.stderr = io.StringIO()
    try:
        ctl._open_tool(Boom(), lambda r: None)
    finally:
        err, sys.stderr = sys.stderr.getvalue(), real
    assert ctl.tool is None and ctl.overlay.isVisible() and "boum" in err
    ctl.open_calibration()                                          # et l'on peut rouvrir un outil ensuite
    assert ctl.tool is not None
    ctl.tool.finish(None)

    # presse-papiers : un gros texte est ignoré, une ligne de chat est prise
    clip = QGuiApplication.clipboard()
    clip.setText("Confusion horaire : 2 Pi/4 " + "x" * 6000)
    APP.processEvents()
    assert ctl.state.k_choice is None
    clip.setText("[13:52] Locket : Confusion contre horaire : 1 Pi/2 (1")
    APP.processEvents()
    assert ctl.state.k_choice == 3
    # l'overlay ne prend jamais le focus, ne gêne pas les clics
    f = ctl.overlay.windowFlags()
    assert f & Qt.WindowType.WindowDoesNotAcceptFocus and f & Qt.WindowType.WindowTransparentForInput and f & Qt.WindowType.WindowStaysOnTopHint
    ctl.quit()
    print("OK : robustesse au démarrage (réglages absurdes, fermeture immédiate, échec d'écriture, outil qui plante, presse-papiers)")


def test_release_consistency():
    iss = (Path(__file__).parent / "installer.iss").read_text(encoding="utf-8")
    assert f'#define AppVersion "{overlay.APP_VERSION}"' in iss, "version de l'installateur différente de celle du programme"
    vi = Path(__file__).parent / "version_info.txt"
    if vi.exists():
        major_minor = overlay.APP_VERSION.split(".")
        assert f"filevers=({major_minor[0]}, {major_minor[1]}, 0, 0)" in vi.read_text(encoding="utf-8")
    print(f"OK : version {overlay.APP_VERSION} identique dans le programme, l'installateur et l'exe")


if __name__ == "__main__":
    test_resize()
    test_fine_calibration()
    test_calibration_flow()
    test_auto_calibration()
    test_songes_mode()
    test_auto_checkbox()
    test_robust_startup()
    test_release_consistency()
