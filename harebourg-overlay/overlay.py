#!/usr/bin/env python3
"""Overlay Comte Harebourg : montre où le sort atterrit vraiment.

Tu choisis ta confusion (menu, ou ligne du chat copiée) ou ta tranche de PV ; l'overlay connaît la carte
de la salle et dessine par-dessus le jeu la case visée par ta souris et la case où le sort atterrit.
Il ne lit pas l'écran, ne clique pas et ne touche pas aux fichiers du jeu : il lit seulement la position
de la souris et, quand tu copies une ligne « Confusion … Pi/4 », le presse-papiers.
"""
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from PyQt6.QtCore import QObject, QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QCursor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter,
                         QPalette, QPen, QPolygonF)
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget)

import autocal
import core
import theme
import view
from dial import Dial

# Dossier du programme : à côté du .exe une fois compilé (sinon config.json serait perdu dans un dossier temporaire)
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG = APP_DIR / "config.json"
DEFAULT_KEYS = {
    "set_me": "<f6>", "clear_me": "<f3>", "conf_next": "<f7>", "new_turn": "<f9>", "hits_plus": "<f10>", "hits_minus": "<f11>",
    "summon": "<f4>", "calibrate": "<f5>", "toggle": "<f8>",
    "snap": "<ctrl>+<shift>+c", "nudge_left": "<ctrl>+<shift>+<left>", "nudge_right": "<ctrl>+<shift>+<right>",
    "nudge_up": "<ctrl>+<shift>+<up>", "nudge_down": "<ctrl>+<shift>+<down>",
    "grid_grow": "<ctrl>+<shift>+<page_up>", "grid_shrink": "<ctrl>+<shift>+<page_down>",
}
KEY_HELP = {
    "set_me": "me placer : souris sur ta case",
    "clear_me": "retirer ma position (pendant que tu te déplaces)",
    "conf_next": "confusion suivante dans le menu",
    "new_turn": "nouveau tour : lignes à 0, confusion à rechoisir",
    "hits_plus": "+1 ligne de dégâts que TU infliges au corps à corps (un sort à 2 lignes = 2)",
    "hits_minus": "-1 ligne de dégâts au corps à corps",
    "summon": "je joue une invocation (aucune confusion) : activer / désactiver",
    "calibrate": "calibrer la grille (automatique)",
    "toggle": "afficher / masquer l'overlay",
    "snap": "grille : caler sur la case sous la souris (pour affiner à la main)",
    "nudge_left": "grille : décaler à gauche (1 px, accélère si tu insistes)",
    "nudge_right": "grille : décaler à droite",
    "nudge_up": "grille : décaler vers le haut",
    "nudge_down": "grille : décaler vers le bas",
    "grid_grow": "grille : agrandir autour de la souris",
    "grid_shrink": "grille : rapetisser autour de la souris",
}


def key_label(combo):
    if not combo:
        return "aucune"
    return combo.replace("<", "").replace(">", "").replace("+", " + ").upper()


# Touches spéciales : code Qt -> nom pynput
_SPECIAL = {
    Qt.Key.Key_Space: "space", Qt.Key.Key_Tab: "tab", Qt.Key.Key_Insert: "insert", Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end", Qt.Key.Key_PageUp: "page_up", Qt.Key.Key_PageDown: "page_down",
    Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right",
    Qt.Key.Key_Pause: "pause", Qt.Key.Key_Print: "print_screen", Qt.Key.Key_ScrollLock: "scroll_lock",
}
_MODIFIER_KEYS = {Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_AltGr}


def qt_to_combo(key, mods):
    """Touche Qt (+ modificateurs) -> raccourci au format pynput (« <ctrl>+<f9> », « <f6> », « g »), ou None."""
    try:
        key = Qt.Key(key)
    except ValueError:
        return None
    v = key.value
    if Qt.Key.Key_F1.value <= v <= Qt.Key.Key_F24.value:
        name = f"<f{v - Qt.Key.Key_F1.value + 1}>"
    elif key in _SPECIAL:
        name = f"<{_SPECIAL[key]}>"
    elif Qt.Key.Key_A.value <= v <= Qt.Key.Key_Z.value or Qt.Key.Key_0.value <= v <= Qt.Key.Key_9.value:
        name = chr(v).lower()
    else:
        return None
    parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        parts.append("<ctrl>")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("<alt>")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        parts.append("<shift>")
    return "+".join(parts + [name])


class KeyButton(QPushButton):
    """Bouton d'un raccourci : clic, puis appuie sur la touche voulue. Échap = annuler, Suppr = aucune touche."""
    started = pyqtSignal()
    captured = pyqtSignal(str, object)     # (action, raccourci ou "" ; None = annulé)

    def __init__(self, action, combo):
        super().__init__(key_label(combo))
        self.action, self.combo, self.recording = action, combo, False
        self.setToolTip("Clique puis appuie sur une touche (ex. F6, Ctrl + F9). Échap = annuler, Suppr = aucune touche")
        self.clicked.connect(self.start)

    def set_combo(self, combo):
        self.combo = combo
        self.setText(key_label(combo))

    def start(self):
        self.recording = True
        self.setProperty("rec", "true")
        repolish(self)
        self.setText("Appuie sur une touche…")
        self.started.emit()
        self.grabKeyboard()

    def _stop(self, result):
        self.recording = False
        self.releaseKeyboard()
        self.setProperty("rec", "false")
        repolish(self)
        self.setText(key_label(self.combo))
        self.captured.emit(self.action, result)

    def keyPressEvent(self, e):
        if not self.recording:
            return super().keyPressEvent(e)
        k = e.key()
        if k in _MODIFIER_KEYS:
            return                                  # on attend la vraie touche
        if k == Qt.Key.Key_Escape:
            return self._stop(None)
        if k in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            return self._stop("")
        combo = qt_to_combo(k, e.modifiers())
        if combo is not None:
            self._stop(combo)

    def focusOutEvent(self, e):
        if self.recording:
            self._stop(None)
        super().focusOutEvent(e)


# --- Dessin -------------------------------------------------------------------------
def _qc(rgba):
    return QColor(*rgba)


def paint_prims(p, prims, ox, oy):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for pr in prims:
        kind = pr[0]
        if kind == "poly":
            _, pts, fill, stroke, w, dash = pr
            poly = QPolygonF([QPointF(x - ox, y - oy) for x, y in pts])
            pen = QPen(_qc(stroke), w) if stroke else QPen(Qt.PenStyle.NoPen)
            if stroke and dash:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QBrush(_qc(fill)) if fill else QBrush(Qt.BrushStyle.NoBrush))
            p.drawPolygon(poly)
        elif kind == "line":
            _, a, b, col, w, dash = pr
            pen = QPen(_qc(col), w)
            if dash:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(a[0] - ox, a[1] - oy), QPointF(b[0] - ox, b[1] - oy))
        elif kind == "text":
            _, x, y, txt, col, size, bg = pr
            f = QFont()
            f.setPixelSize(int(size))
            f.setBold(True)
            p.setFont(f)
            fm = p.fontMetrics()
            w, h = fm.horizontalAdvance(txt), fm.height()
            rect = QRectF(x - ox - w / 2 - 6, y - oy - h / 2 - 2, w + 12, h + 4)
            if bg:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(_qc(bg)))
                p.drawRoundedRect(rect, 4, 4)
            p.setPen(QPen(_qc(col)))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter.value, txt)
        elif kind == "panel":
            _, x, y, lines = pr
            f = QFont()
            f.setPixelSize(14)
            f.setBold(True)
            p.setFont(f)
            fm = p.fontMetrics()
            lh = fm.height() + 6
            w = max(fm.horizontalAdvance(t) for t, _ in lines) + 24
            h = lh * len(lines) + 12
            left = min(max(x - ox - w / 2, 4), max(4, p.device().width() - w - 4))
            top = y - oy
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(_qc(view.LABEL_BG)))
            p.drawRoundedRect(QRectF(left, top, w, h), 8, 8)
            for i, (t, col) in enumerate(lines):
                p.setPen(QPen(_qc(col)))
                p.drawText(QRectF(left + 12, top + 6 + lh * i, w - 24, lh), Qt.AlignmentFlag.AlignVCenter.value, t)


class Overlay(QWidget):
    """Fenêtre transparente plein écran, au-dessus du jeu, sur laquelle on peut cliquer à travers."""

    def __init__(self, geom):
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.geom = geom
        self.setGeometry(geom.adjusted(0, 0, 0, -1))   # 1 px de moins : évite le plein écran exclusif
        self.prims = []
        self.opacity = 1.0           # opacité des dessins (0.1 à 1)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setOpacity(self.opacity)
        o = self.mapToGlobal(QPoint(0, 0))
        paint_prims(p, self.prims, o.x(), o.y())


class FullscreenTool(QWidget):
    """Base des fenêtres interactives plein écran (calibration, placement)."""
    done = pyqtSignal(object)

    def __init__(self, geom):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.geom = geom
        self.setGeometry(geom)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def open(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def finish(self, result):
        self.done.emit(result)
        self.close()

    def _origin(self):
        """Coin haut-gauche réel de la fenêtre à l'écran (même si Windows l'a décalée de quelques pixels)."""
        p = self.mapToGlobal(QPoint(0, 0))
        return p.x(), p.y()

    @staticmethod
    def _g(e):
        """Position de la souris à l'écran (les mêmes coordonnées que la souris du jeu)."""
        g = e.globalPosition()
        return g.x(), g.y()

    def _panel(self, lines):
        ox, oy = self._origin()
        return ("panel", ox + self.width() / 2.0, oy + 10, lines)


class Calibration(FullscreenTool):
    """Calibration en trois temps, avec le contour de la salle pour juger de l'alignement.

    1. clic sur le SOL de la case du milieu tout en HAUT de la salle (pas sur le personnage qui s'y tient) ;
    2. la grille s'étire avec la souris : clic quand la case jaune est celle du milieu tout en BAS ;
    3. réglage fin : le contour cyan doit coller au bord du carrelage (glisser, molette, flèches), puis Entrée.
    """
    MIN_KY, MAX_KY = 6.0, 70.0      # taille plausible d'une case (demi-hauteur en pixels)
    MAX_DX = 40                     # les deux points sont dans la même colonne : au plus 40 px d'écart

    def __init__(self, geom, calib, fight):
        super().__init__(geom)
        self.calib = core.Calib(calib.x0, calib.y0, calib.kx, calib.ky)
        self.fight = fight
        self.step = 0          # 0 : clic en haut, 1 : clic en bas, 2 : réglage fin
        self.top = None
        self.preview = None    # grille étirée par la souris, pendant l'étape 2
        self.drag = None
        self.msg = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _stretch(self, y, x=None):
        """Grille dont le haut est au 1er clic et dont le bas est à la hauteur y de la souris.

        x : colonne du 2e point (au clic, on fait la moyenne des deux colonnes) ; None = la même que le 1er (aperçu).
        """
        if y <= self.top[1]:
            self.msg = "Le 2e point doit être plus bas que le 1er."
            return None
        if x is not None and abs(x - self.top[0]) > self.MAX_DX:
            self.msg = "Le 2e point doit être juste sous le 1er (la case du milieu, même colonne)."
            return None
        new = core.Calib.from_anchors(self.top, (self.top[0] if x is None else x, y))
        if new is None or not (self.MIN_KY <= new.ky <= self.MAX_KY):
            self.msg = "Ces deux points sont trop proches ou trop éloignés pour une salle entière."
            return None
        self.msg = None
        return new

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 40))   # pas totalement transparent : sinon les clics passent au travers
        c = self.preview if (self.step == 1 and self.preview is not None) else self.calib
        prims = view.grid_prims(c, core.FIGHTS[self.fight], strong=True) + view.outline_prims(c)
        if self.step < 2:
            anchor = core.CAL_TOP if self.step == 0 else core.CAL_BOTTOM
            prims.append(("poly", c.polygon(anchor), view.ANCHOR_FILL, view.ANCHOR_LINE, 3, False))
            x, y = c.center(anchor)
            label = "Repère approximatif" if self.step == 0 else "Doit être la case du milieu, en bas"
            dy = -c.ky * 2.2 if self.step == 0 else c.ky * 2.2
            prims.append(("text", x, y + dy, label, view.ANCHOR_LINE, 13, view.LABEL_BG))
        lines = [
            [("1/3 · Clique sur le SOL de la case du milieu, tout en HAUT de la salle", view.TEXT),
             ("Les 3 cases du bord haut : prends celle du milieu. Vise le sol (les pieds), pas le personnage.", view.MUTED)],
            [("2/3 · Descends la souris : la grille s'étire. Clique quand la case jaune est celle du milieu, tout en BAS", view.TEXT),
             ("Le contour cyan doit longer le bord du carrelage. Retour arrière ou clic droit = refaire le 1er point.", view.MUTED)],
            [("3/3 · Fais coller le contour cyan au bord du carrelage (les dents du zigzag), puis Entrée", view.TEXT),
             ("Glisser = déplacer · molette = taille · flèches = 1 pixel (Maj = 10) · retour arrière = tout refaire", view.MUTED),
             ("Regarde surtout les pointes à gauche et à droite : c'est là qu'un décalage de côté se voit le mieux.", view.MUTED)],
        ][self.step]
        if self.msg:
            lines.append((self.msg, view.WARN))
        lines.append(("Entrée = valider · Échap = annuler" if self.step == 2 else "Échap = annuler", view.MUTED))
        prims.append(self._panel(lines))
        paint_prims(p, prims, *self._origin())

    def restart(self):
        self.step, self.top, self.preview, self.msg = 0, None, None, None
        self.update()

    def click(self, x, y):
        """Clic aux coordonnées globales (x, y) : avance d'une étape."""
        c = self.calib
        if self.step == 0:
            # la grille glisse pour que la case du haut tombe sous le clic
            tx, ty = c.center(core.CAL_TOP)
            c.x0 += x - tx
            c.y0 += y - ty
            self.top = (x, y)
            self.step = 1
            self.msg = None
        elif self.step == 1:
            new = self._stretch(y, x)
            if new is not None:
                self.calib, self.preview, self.step = new, None, 2
        else:
            self.drag = (x, y, c.x0, c.y0)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.click(*self._g(e))
        elif e.button() == Qt.MouseButton.RightButton:
            self.restart()

    def mouseMoveEvent(self, e):
        x, y = self._g(e)
        if self.step == 1:
            self.preview = self._stretch(y)
            self.update()
        elif self.drag:
            x1, y1, x0, y0 = self.drag
            self.calib.x0 = x0 + x - x1
            self.calib.y0 = y0 + y - y1
            self.update()

    def mouseReleaseEvent(self, _e):
        self.drag = None

    def wheelEvent(self, e):
        if self.step != 2:
            return
        f = 1.02 ** (e.angleDelta().y() / 120.0)
        c = self.calib
        # la taille change autour du centre de la salle, en gardant des cases deux fois plus larges que hautes
        cx, cy = c.center((11, 0))
        c.kx, c.ky = c.kx * f, c.ky * f
        nx, ny = c.center((11, 0))
        c.x0 += cx - nx
        c.y0 += cy - ny
        self.update()

    def keyPressEvent(self, e):
        k, step = e.key(), (10 if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1)
        if k == Qt.Key.Key_Escape:
            self.finish(None)
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.step == 2:
                self.finish(self.calib)
        elif k == Qt.Key.Key_Backspace:
            self.restart()
        elif self.step == 2:
            dx = {Qt.Key.Key_Left: -step, Qt.Key.Key_Right: step}.get(k, 0)
            dy = {Qt.Key.Key_Up: -step, Qt.Key.Key_Down: step}.get(k, 0)
            if dx or dy:
                self.calib.x0 += dx
                self.calib.y0 += dy
                self.update()


class PlacePicker(FullscreenTool):
    """Clique sur ta case : la grille s'affiche, la case survolée est surlignée."""

    def __init__(self, geom, calib, fight, you):
        super().__init__(geom)
        self.calib, self.fight, self.you = calib, fight, you
        self.hover = None
        self.msg = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 30))
        c, f = self.calib, core.FIGHTS[self.fight]
        prims = view.grid_prims(c, f)
        if self.you is not None:
            prims.append(("poly", c.polygon(self.you), view.YOU_FILL, view.YOU_LINE, 2, False))
        if self.hover is not None:
            ok = core.is_free(f, self.hover)
            prims.append(("poly", c.polygon(self.hover), view.AIM_FILL if ok else None,
                          view.AIM_LINE if ok else view.WARN, 3, False))
        lines = [("Clique sur la case de ton personnage", view.TEXT), ("Échap = annuler", view.MUTED)]
        if self.msg:
            lines.insert(1, (self.msg, view.WARN))
        prims.append(self._panel(lines))
        paint_prims(p, prims, *self._origin())

    def mouseMoveEvent(self, e):
        cell = self.calib.cell_at(*self._g(e))
        if cell != self.hover:
            self.hover = cell
            self.update()

    def click(self, x, y):
        cell = self.calib.cell_at(x, y)
        if cell is None:
            self.msg = "Hors de la salle (si la grille est décalée, calibre-la d'abord)"
        elif not core.is_free(core.FIGHTS[self.fight], cell):
            self.msg = "Cette case est un bloc ou un trou"
        else:
            self.finish(cell)
            return
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.click(*self._g(e))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.finish(None)


# --- Raccourcis clavier globaux -----------------------------------------------------
class Hotkeys(QObject):
    fired = pyqtSignal(str)

    def __init__(self, mapping):
        super().__init__()
        self.listener = None
        self.error = None
        try:
            from pynput import keyboard
            table = {}
            for name, combo in mapping.items():
                if not combo:
                    continue
                try:
                    keyboard.HotKey.parse(combo)
                except ValueError:
                    continue                      # raccourci illisible : ignoré plutôt que tout bloquer
                table[combo] = (lambda n=name: self.fired.emit(n))
            self.listener = keyboard.GlobalHotKeys(table)
            self.listener.start()
        except Exception as exc:   # pynput absent, droits macOS manquants, Wayland...
            self.error = str(exc) or exc.__class__.__name__

    def stop(self):
        if self.listener:
            self.listener.stop()


def repolish(w):
    """Réapplique la feuille de style après un changement de propriété dynamique (sel, rec…)."""
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class Section(QWidget):
    """Carte repliable de la fenêtre de contrôle : une barre de titre cliquable (▾ / ▸) et son contenu."""
    toggled = pyqtSignal()

    def __init__(self, key, title, collapsed=False):
        super().__init__()
        self.key, self.title = key, title
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)
        self.head = QPushButton()
        self.head.setObjectName("head")
        self.head.setCheckable(True)
        self.head.setCursor(Qt.CursorShape.PointingHandCursor)
        self.head.toggled.connect(self._apply)
        outer.addWidget(self.head)
        self.body = QWidget()
        self.lay = QVBoxLayout(self.body)
        self.lay.setContentsMargins(11, 7, 11, 10)
        self.lay.setSpacing(6)
        outer.addWidget(self.body)
        self.head.setChecked(not collapsed)
        self._apply(not collapsed)

    @property
    def collapsed(self):
        return not self.head.isChecked()

    def set_collapsed(self, c):
        self.head.setChecked(not c)
        self._apply(not c)       # hors Qt réel, toggled peut ne pas être émis

    def _apply(self, opened):
        self.head.setText(("▾   " if opened else "▸   ") + self.title)
        self.body.setVisible(opened)
        self.toggled.emit()

    def row(self, *widgets):
        h = QHBoxLayout()
        h.setSpacing(6)
        for x in widgets:
            h.addWidget(x)
        self.lay.addLayout(h)

    def add(self, widget):
        self.lay.addWidget(widget)


class Panel(QWidget):
    """Fenêtre de contrôle sans bordure système : cadre de laiton sur fond vert-bleu.

    Elle se déplace en la prenant par un fond, un titre ou le cadran. Elle se redimensionne en tirant un bord
    (largeur ou hauteur) ou un coin (les deux à la fois), comme une fenêtre ordinaire.
    """
    closed = pyqtSignal()
    moved = pyqtSignal()
    resized = pyqtSignal()
    GRIP = 10          # épaisseur de la zone de prise le long du bord, en pixels

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self._rs = None            # redimensionnement en cours : (bords, point de départ, rectangle de départ)

    def edges_at(self, pos):
        """Bords de la fenêtre sous le point pos (coordonnées locales) : gauche, droite, haut, bas, ou une paire."""
        e, g = Qt.Edge(0), self.GRIP
        if pos.x() <= g:
            e |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - g:
            e |= Qt.Edge.RightEdge
        if pos.y() <= g:
            e |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - g:
            e |= Qt.Edge.BottomEdge
        return e

    @staticmethod
    def cursor_for(e):
        L, R, T, B = Qt.Edge.LeftEdge, Qt.Edge.RightEdge, Qt.Edge.TopEdge, Qt.Edge.BottomEdge
        if (e & L and e & T) or (e & R and e & B):
            return Qt.CursorShape.SizeFDiagCursor
        if (e & R and e & T) or (e & L and e & B):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.SizeHorCursor if e & (L | R) else Qt.CursorShape.SizeVerCursor

    def _resize_to(self, gp):
        e, g0, r0 = self._rs
        dx, dy = gp.x() - g0.x(), gp.y() - g0.y()
        L, R, T, B = Qt.Edge.LeftEdge, Qt.Edge.RightEdge, Qt.Edge.TopEdge, Qt.Edge.BottomEdge
        w = r0.width() + (dx if e & R else -dx if e & L else 0)
        h = r0.height() + (dy if e & B else -dy if e & T else 0)
        w = max(self.minimumWidth(), min(self.maximumWidth(), w))
        h = max(self.minimumHeight(), min(self.maximumHeight(), h))
        x = r0.right() + 1 - w if e & L else r0.left()        # le bord opposé reste où il est
        y = r0.bottom() + 1 - h if e & T else r0.top()
        self.setGeometry(x, y, w, h)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        bg = QLinearGradient(0, 0, 0, r.height())
        bg.setColorAt(0.0, QColor(theme.BG_TOP))
        bg.setColorAt(0.4, QColor(theme.BG_MID))
        bg.setColorAt(1.0, QColor(theme.BG_BOT))
        rim = QLinearGradient(0, 0, r.width(), r.height())
        rim.setColorAt(0.0, QColor(theme.BRASS_LIGHT))
        rim.setColorAt(0.5, QColor(theme.BRASS_DARK))
        rim.setColorAt(1.0, QColor(theme.BRASS))
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QBrush(rim), 3.2))
        p.drawRoundedRect(r, 17, 17)
        p.setBrush(Qt.BrushStyle.NoBrush)                          # filet cyan discret à l'intérieur du cadre
        p.setPen(QPen(QColor(63, 224, 232, 38), 1.0))
        p.drawRoundedRect(r.adjusted(5, 5, -5, -5), 13, 13)
        # petite poignée dans le coin bas-droit : on peut tirer les bords et les coins
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(theme.BRASS_LIGHT)))
        bx, by = r.right() - 9, r.bottom() - 9
        for i in range(3):
            for j in range(i + 1):
                p.drawEllipse(QPointF(bx - 4 * j, by - 4 * (i - j)), 1.1, 1.1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            edges = self.edges_at(e.position().toPoint())
            if edges:
                self._rs = (edges, e.globalPosition().toPoint(), self.geometry())
            elif self.windowHandle() is not None:
                self.windowHandle().startSystemMove()          # un fond, un titre, le cadran : on déplace la fenêtre
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._rs is not None:
            self._resize_to(e.globalPosition().toPoint())
        else:
            edges = self.edges_at(e.position().toPoint())
            if edges:
                self.setCursor(self.cursor_for(edges))
            else:
                self.unsetCursor()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._rs = None
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e):
        if self._rs is None:
            self.unsetCursor()
        super().leaveEvent(e)

    def moveEvent(self, e):
        self.moved.emit()
        super().moveEvent(e)

    def resizeEvent(self, e):
        self.resized.emit()
        super().resizeEvent(e)

    def closeEvent(self, e):
        self.closed.emit()
        e.accept()


# --- Application ---------------------------------------------------------------------
class Controller(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._apply_theme(app)
        self.cfg = self._load()
        saved_keys = {k: v for k, v in self.cfg.get("hotkeys", {}).items() if k in DEFAULT_KEYS}
        self.keys = {**DEFAULT_KEYS, **saved_keys}
        self.screens = QGuiApplication.screens()
        idx = self.cfg.get("screen", 0)
        self.screen_idx = idx if 0 <= idx < len(self.screens) else 0
        g = self.screens[self.screen_idx].geometry()

        calib = self.cfg.get("calib")
        if calib and self.cfg.get("calib_screen", 0) == self.screen_idx:
            cal = core.Calib(**calib)
        else:
            cal = self._default_calib(g)
        self.state = view.State(
            calib=cal, screen_w=g.width(), origin=(g.x(), g.y()), fight=self.cfg.get("fight", 0),
            hp_manual=float(self.cfg.get("hp_manual", 100)), show_grid=self.cfg.get("show_grid", False))
        self.collapsed = dict(self.cfg.get("collapsed", {}))
        self.mini = bool(self.cfg.get("mini", False))     # mode mini : seule la ligne de rotation reste
        size = self.cfg.get("panel_size")                  # taille choisie en tirant les bords (hors mode mini)
        ok = isinstance(size, list) and len(size) == 2 and all(isinstance(v, (int, float)) for v in size)
        self._normal_w = max(320, int(size[0])) if ok else 363
        self._normal_h = max(110, int(size[1])) if ok else None
        self._accel = (0.0, None, 0)
        self.pool = ThreadPoolExecutor(max_workers=1)      # le calage automatique tourne là, pour ne pas figer l'écran
        self._autocal = None            # calage en cours : [résultat à venir, pixels par point, manuel ?, actions ensuite]
        self._msg = None                # message affiché un instant dans la fenêtre : (texte, est-ce un problème ?)
        self._msg_timer = QTimer(self)
        self._msg_timer.setSingleShot(True)
        self._msg_timer.setInterval(6000)
        self._msg_timer.timeout.connect(self._clear_msg)
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.setInterval(2500)
        self._flash_timer.timeout.connect(self._end_flash)
        self.panel_opacity = int(self.cfg.get("panel_opacity", 100))
        self.draw_opacity = int(self.cfg.get("draw_opacity", 100))
        self.overlay_on = True
        self.last_sig = None
        self.tool = None
        self.hotkeys = None
        self.recording_key = False      # un raccourci est en cours d'enregistrement : on ignore les touches

        self.overlay = Overlay(g)
        self.overlay.opacity = self.draw_opacity / 100.0
        self.overlay.show()
        self.panel = self._build_panel()
        self.panel.setWindowOpacity(self.panel_opacity / 100.0)
        self._pos_timer = QTimer(self)
        self._pos_timer.setSingleShot(True)
        self._pos_timer.setInterval(500)
        self._pos_timer.timeout.connect(self.save)
        self._place_panel()
        self._layout_panel(restore=True)
        self.panel.show()

        QGuiApplication.clipboard().dataChanged.connect(self.on_clipboard)
        self.start_hotkeys()
        self.t_ui = QTimer(self)
        self.t_ui.timeout.connect(self.tick)
        self.t_ui.start(33)
        self._boot_timer = QTimer(self)               # au lancement, si un combat est déjà ouvert, on cale la grille
        self._boot_timer.setSingleShot(True)
        self._boot_timer.timeout.connect(self.start_autocal)
        self._boot_timer.start(1500)
        self.refresh()

    @staticmethod
    def _apply_theme(app):
        """Style Fusion et palette sombre du Comte : les flèches et cases gardent la bonne couleur."""
        app.setStyle("Fusion")
        pal = QPalette()
        for role, col in ((QPalette.ColorRole.Window, theme.BG_MID), (QPalette.ColorRole.WindowText, theme.CREAM),
                          (QPalette.ColorRole.Base, "#04191a"), (QPalette.ColorRole.AlternateBase, theme.TEAL_DARK),
                          (QPalette.ColorRole.Text, theme.CREAM), (QPalette.ColorRole.Button, theme.TEAL_DARK),
                          (QPalette.ColorRole.ButtonText, theme.CREAM), (QPalette.ColorRole.Highlight, theme.CYAN_MID),
                          (QPalette.ColorRole.HighlightedText, "#ffffff"), (QPalette.ColorRole.ToolTipBase, "#031516"),
                          (QPalette.ColorRole.ToolTipText, theme.CREAM), (QPalette.ColorRole.PlaceholderText, theme.MUTED)):
            pal.setColor(role, QColor(col))
        app.setPalette(pal)

    # -- raccourcis
    def start_hotkeys(self):
        if self.hotkeys is not None:
            self.hotkeys.stop()
        self.hotkeys = Hotkeys(self.keys)
        self.hotkeys.fired.connect(self.on_hotkey)

    def _key_started(self):
        self.recording_key = True

    def set_key(self, action, combo):
        """Nouveau raccourci pour `action` (None = annulé, "" = aucune touche). Une touche ne sert qu'à une action."""
        self.recording_key = False
        if combo is None:
            return
        for other, c in self.keys.items():
            if combo and other != action and c == combo:
                self.keys[other] = ""             # la touche change d'action : l'ancienne n'en a plus
                self.key_btns[other].set_combo("")
        self.keys[action] = combo
        self.key_btns[action].set_combo(combo)
        single = bool(combo) and "+" not in combo and not combo.startswith("<")
        self.lbl_key_warn.setText(
            f"Attention : « {key_label(combo)} » seule marchera aussi quand tu écris dans le chat. "
            "Préfère une touche F ou Ctrl + touche." if single else "")
        self.start_hotkeys()
        self.save()
        self.refresh()

    # -- configuration
    @staticmethod
    def _default_calib(g):
        cal = core.Calib.default_for(g.width(), g.height())
        cal.x0 += g.x()
        cal.y0 += g.y()
        return cal

    def _load(self):
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self):
        c = self.state.calib
        self.cfg = {
            "calib": {"x0": c.x0, "y0": c.y0, "kx": c.kx, "ky": c.ky}, "calib_screen": self.screen_idx,
            "screen": self.screen_idx, "fight": self.state.fight, "hp_manual": self.state.hp_manual,
            "show_grid": self.state.show_grid, "hotkeys": self.keys,
            "collapsed": self.collapsed, "mini": self.mini,
            "panel_opacity": self.panel_opacity, "draw_opacity": self.draw_opacity,
        }
        if getattr(self, "panel", None) is not None:
            self.cfg["panel_pos"] = [self.panel.x(), self.panel.y()]
            if self._normal_h is not None:
                self.cfg["panel_size"] = [self._normal_w, self._normal_h]
        try:
            CONFIG.write_text(json.dumps(self.cfg, indent=2), encoding="utf-8")
        except Exception:
            pass

    # -- fenêtre de contrôle
    def _build_panel(self):
        w = Panel()
        w.setWindowTitle("Harebourg")
        w.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        w.setStyleSheet(theme.stylesheet())
        w.closed.connect(self.quit)
        w.moved.connect(self._panel_moved)
        w.resized.connect(self._panel_resized)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(7)

        # En-tête : le cadran, la rotation en grand, d'où elle vient, et l'état de ta position
        self.header = QWidget()
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        self.dial = Dial(108)
        hl.addWidget(self.dial, 0, Qt.AlignmentFlag.AlignTop)
        mid = QVBoxLayout()
        mid.setSpacing(4)
        mid.setContentsMargins(0, 6, 0, 0)
        self.lbl_rot = QLabel("—")
        self.lbl_rot.setWordWrap(True)       # la fenêtre peut être étroite : « 90° anti-horaire » passe à la ligne
        self.lbl_src = QLabel("")
        self.lbl_src.setObjectName("pill")
        pill_row = QHBoxLayout()
        pill_row.addWidget(self.lbl_src)
        pill_row.addStretch(1)
        self.lbl = QLabel()
        self.lbl.setTextFormat(Qt.TextFormat.RichText)
        self.lbl.setWordWrap(True)
        self.lbl.setMinimumWidth(140)
        mid.addWidget(self.lbl_rot)
        mid.addLayout(pill_row)
        mid.addWidget(self.lbl)
        mid.addStretch(1)
        hl.addLayout(mid, 1)
        side = QVBoxLayout()
        side.setSpacing(5)
        self.btn_all = QPushButton("–")
        self.btn_all.setObjectName("tiny")
        self.btn_all.clicked.connect(self.toggle_all)
        b_close = QPushButton("×")
        b_close.setObjectName("tiny")
        b_close.setToolTip("Fermer l'overlay")
        b_close.clicked.connect(w.close)
        side.addWidget(self.btn_all)
        side.addWidget(b_close)
        side.addStretch(1)
        hl.addLayout(side)
        lay.addWidget(self.header)

        # Les cartes sont dans une zone qui défile : la fenêtre peut être plus basse que leur contenu
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(70)
        self.scroll.viewport().setAutoFillBackground(False)
        self.host = QWidget()
        sv = QVBoxLayout(self.host)
        sv.setContentsMargins(0, 0, 4, 0)
        sv.setSpacing(7)
        self.scroll.setWidget(self.host)
        lay.addWidget(self.scroll, 1)

        self.sections = {}

        def section(key, title, default_collapsed):
            s = Section(key, title, self.collapsed.get(key, default_collapsed))
            s.toggled.connect(self._section_toggled)
            self.sections[key] = s
            sv.addWidget(s)
            return s

        def note(text):
            lab = QLabel(text)
            lab.setObjectName("note")
            lab.setWordWrap(True)
            lab.setMaximumWidth(290)
            return lab

        # 1. Confusion
        s = section("conf", "Confusion", False)
        self.cb_conf = QComboBox()
        self.cb_conf.addItems([label for _, label in core.CONF_CHOICES])
        self.cb_conf.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_conf.setMinimumContentsLength(26)
        self.cb_conf.setToolTip("Le jeu écrit la rotation de deux façons : « horaire 2 Pi/4 » = « contre horaire 6 Pi/4 »,\n"
                                "« horaire 6 Pi/4 » = « contre horaire 2 Pi/4 ». Les deux donnent le même résultat.")
        self.cb_conf.currentIndexChanged.connect(self.on_conf_index)
        s.add(self.cb_conf)
        self.ed_paste = QLineEdit()
        self.ed_paste.setPlaceholderText("Colle ici la ligne de confusion")
        self.ed_paste.setToolTip("Colle « Confusion horaire : 2 Pi/4 » (la copier dans le chat suffit, c'est automatique)")
        self.ed_paste.textChanged.connect(self.on_paste_text)
        s.add(self.ed_paste)
        self.lbl_paste = note("")
        self.lbl_paste.setVisible(False)
        s.add(self.lbl_paste)

        # 2. Tour : lignes au corps à corps, nouveau tour, invocation
        s = section("turn", "Tour", False)
        b_minus, b_plus = QPushButton("−"), QPushButton("+")
        for b in (b_minus, b_plus):
            b.setFixedWidth(34)
        self.lbl_hits = QLabel("0")
        self.lbl_hits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hits.setMinimumWidth(46)
        self.lbl_hits.setStyleSheet(f"background:#04191a; border:1px solid {theme.TEAL_EDGE}; border-radius:8px; padding:4px 0;")
        b_minus.clicked.connect(lambda: self.add_hits(-1))
        b_plus.clicked.connect(lambda: self.add_hits(1))
        hits_label = QLabel("Lignes càc")
        hits_label.setToolTip("Lignes de dégâts que tu infliges au corps à corps ce tour")
        s.row(hits_label, b_minus, self.lbl_hits, b_plus)
        b_turn = QPushButton("Nouveau tour")
        b_turn.setObjectName("primary")
        b_turn.setToolTip("Lignes à 0, confusion à rechoisir")
        b_turn.clicked.connect(self.new_turn)
        s.add(b_turn)
        self.ck_summon = QCheckBox("Invocation (aucune confusion)")
        self.ck_summon.toggled.connect(self.set_summon)
        s.add(self.ck_summon)

        # 3. PV (utilisés seulement si aucune confusion n'est choisie)
        s = section("pv", "PV", True)
        s.add(note("Utilisés seulement si aucune confusion n'est choisie."))
        self.sp_hp = QSpinBox()
        self.sp_hp.setRange(0, 100)
        self.sp_hp.setSuffix(" %")
        self.sp_hp.setValue(int(self.state.hp_manual))
        self.sp_hp.valueChanged.connect(self.set_hp_manual)
        s.row(QLabel("PV à la main"), self.sp_hp)
        self.tranche_btns = []
        for tr in core.TRANCHES:
            b = QPushButton(f"{tr.hi}–{tr.lo}")
            b.setToolTip(f"{tr.hi} % à {tr.lo} % : {tr.name}")
            b.clicked.connect(lambda _=False, tr=tr: self.pick_tranche(tr))
            self.tranche_btns.append(b)
        s.row(*self.tranche_btns)

        # 4. Position
        s = section("pos", "Position", True)
        b_me = QPushButton("Me placer (clic)")
        b_me.clicked.connect(self.open_place)
        b_clr = QPushButton("Retirer")
        b_clr.setToolTip("Efface ta case et les traits pendant que tu te déplaces ; replace-toi ensuite")
        b_clr.clicked.connect(self.clear_me)
        s.row(b_me, b_clr)

        # 5. Affichage
        s = section("look", "Affichage", True)
        self.sl_panel = QSlider(Qt.Orientation.Horizontal)
        self.sl_panel.setRange(20, 100)
        self.sl_panel.setValue(self.panel_opacity)
        self.sl_panel.valueChanged.connect(self.set_panel_opacity)
        self.lbl_panel_op = QLabel(f"{self.panel_opacity} %")
        s.row(QLabel("Fenêtre"), self.sl_panel, self.lbl_panel_op)
        self.sl_draw = QSlider(Qt.Orientation.Horizontal)
        self.sl_draw.setRange(10, 100)
        self.sl_draw.setValue(self.draw_opacity)
        self.sl_draw.valueChanged.connect(self.set_draw_opacity)
        self.lbl_draw_op = QLabel(f"{self.draw_opacity} %")
        s.row(QLabel("Dessins"), self.sl_draw, self.lbl_draw_op)
        self.ck_grid = QCheckBox("Grille")
        self.ck_grid.setChecked(self.state.show_grid)
        self.ck_grid.toggled.connect(self.set_grid)
        s.add(self.ck_grid)

        # 6. Réglages
        s = section("setup", "Réglages", True)
        b_cal = QPushButton("Calibrer la grille")
        b_cal.setToolTip("Retrouve la salle sur ton écran et cale la grille toute seule")
        b_cal.clicked.connect(self.calibrate_auto)
        b_hand = QPushButton("À la main…")
        b_hand.setToolTip("Calibration en 2 clics, si le calage automatique ne marche pas")
        b_hand.clicked.connect(self.open_calibration)
        s.row(b_cal, b_hand)
        s.add(note("La grille se cale toute seule quand tu fais « Me placer » (et au lancement). "
                   "Ouvre ton combat d'abord."))
        self.cb_fight = QComboBox()
        self.cb_fight.addItems([f.name for f in core.FIGHTS])
        self.cb_fight.setCurrentIndex(self.state.fight)
        self.cb_fight.currentIndexChanged.connect(self.set_fight)
        s.row(QLabel("Combat"), self.cb_fight)
        self.cb_screen = QComboBox()
        self.cb_screen.addItems([f"Écran {i + 1} ({sc.geometry().width()}×{sc.geometry().height()})"
                                 for i, sc in enumerate(self.screens)])
        self.cb_screen.setCurrentIndex(self.screen_idx)
        self.cb_screen.currentIndexChanged.connect(self.set_screen)
        s.row(QLabel("Écran"), self.cb_screen)

        # 7. Raccourcis
        s = section("keys", "Raccourcis", True)
        s.add(note("Clique une touche, puis appuie sur la nouvelle."))
        grid = QGridLayout()
        grid.setSpacing(5)
        self.key_btns = {}
        for i, n in enumerate(DEFAULT_KEYS):
            b = KeyButton(n, self.keys[n])
            b.started.connect(self._key_started)
            b.captured.connect(self.set_key)
            b.setMinimumWidth(104)
            self.key_btns[n] = b
            lab = QLabel(KEY_HELP[n])
            lab.setWordWrap(True)
            lab.setMaximumWidth(185)
            grid.addWidget(b, i, 0)
            grid.addWidget(lab, i, 1)
        s.lay.addLayout(grid)
        self.lbl_key_warn = QLabel("")
        self.lbl_key_warn.setObjectName("warn")
        self.lbl_key_warn.setWordWrap(True)
        self.lbl_key_warn.setMaximumWidth(290)
        s.add(self.lbl_key_warn)

        sv.addStretch(1)
        self._apply_mini()
        return w

    def _layout_panel(self, restore=False):
        """Taille de la fenêtre : l'en-tête seul en mode mini, sinon la taille choisie en tirant les bords."""
        p = self.panel
        self._layouting = True             # ces changements automatiques ne sont pas « ta » taille : on ne les retient pas
        try:
            p.layout().activate()
            if self.mini:
                hint = p.layout().sizeHint()
                p.setMinimumSize(200, hint.height())
                p.setMaximumHeight(hint.height())          # en mode mini, seule la largeur se règle
                p.resize(hint.width(), hint.height())
            else:
                w, h = self._normal_w, self._normal_h
                p.setMinimumSize(320, 110)
                p.setMaximumHeight(16777215)
                if restore and h is not None:
                    p.resize(w, h)
                else:
                    p.resize(w, p.height())
                    QTimer.singleShot(0, self._fit_height)
        finally:
            self._layouting = False

    def _fit_height(self):
        """Ajuste la hauteur au contenu des cartes (sans dépasser l'écran) ; la largeur choisie est gardée."""
        p = getattr(self, "panel", None)
        if p is None or self.mini:
            return
        for sec in self.sections.values():              # Qt garde en mémoire la taille des cartes : on la recalcule
            sec.layout().invalidate()
        self.host.layout().invalidate()
        self.host.layout().activate()
        m, lay = p.layout().contentsMargins(), p.layout()
        want = m.top() + m.bottom() + self.header.sizeHint().height() + lay.spacing() + self.host.sizeHint().height() + 2
        screen = QGuiApplication.screenAt(p.pos()) or self.screens[self.screen_idx]
        p.resize(p.width(), min(want, int(screen.availableGeometry().height() * 0.94)))

    def _panel_resized(self):
        if self.mini or getattr(self, "_layouting", False):
            return
        self._normal_w, self._normal_h = self.panel.width(), self.panel.height()
        if getattr(self, "_pos_timer", None) is not None:
            self._pos_timer.start()

    # -- calage fin de la grille, en jeu : on la compare à la case que le jeu entoure en blanc sous la souris
    def _mouse_pos(self):
        p = QCursor.pos()
        return p.x(), p.y()

    def _accel_step(self, key):
        """Pas du décalage : 1 pixel, puis plus grand (jusqu'à 6) si on appuie vite et longtemps."""
        now = time.monotonic()
        t, k, n = self._accel
        n = n + 1 if (k == key and now - t < 0.7) else 0
        self._accel = (now, key, n)
        return min(6, 1 + n // 3)

    def _calib_changed(self):
        self._pos_timer.start()            # enregistre quand les touches s'arrêtent
        self.refresh()

    def nudge_grid(self, dx, dy):
        step = self._accel_step((dx, dy))
        c = self.state.calib
        c.x0 += dx * step
        c.y0 += dy * step
        self._calib_changed()

    def scale_grid(self, sign):
        """Agrandit (+1) ou rapetisse (-1) la grille autour de la souris : la case sous la souris ne bouge pas."""
        f = 1.0 + 0.004 * self._accel_step(("scale", sign)) * sign
        mx, my = self._mouse_pos()
        c = self.state.calib
        c.x0, c.kx = mx - (mx - c.x0) * f, c.kx * f
        c.y0, c.ky = my - (my - c.y0) * f, c.ky * f
        self._calib_changed()

    def snap_grid(self):
        """Pose le centre de la case la plus proche de la grille exactement sous la souris."""
        mx, my = self._mouse_pos()
        c = self.state.calib
        cell = c.cell_at(mx, my)
        if cell is None:
            return
        cx, cy = c.center(cell)
        c.x0 += mx - cx
        c.y0 += my - cy
        self._calib_changed()

    def _place_panel(self):
        """Remet la fenêtre où tu l'avais mise (sinon en haut à gauche de l'écran du jeu)."""
        g = self.screens[self.screen_idx].geometry()
        x, y = g.x() + 16, g.y() + 60
        pos = self.cfg.get("panel_pos")
        if isinstance(pos, list) and len(pos) == 2 and all(isinstance(v, (int, float)) for v in pos):
            if any(sc.geometry().contains(int(pos[0]) + 30, int(pos[1]) + 30) for sc in self.screens):
                x, y = int(pos[0]), int(pos[1])
        self.panel.move(x, y)

    def _panel_moved(self):
        if getattr(self, "_pos_timer", None) is not None:
            self._pos_timer.start()           # on enregistre la position quand la fenêtre ne bouge plus

    def _update_tranche_buttons(self):
        """Allume (bordure dorée) la tranche des PV, tant que c'est elle qui décide de la confusion."""
        if not getattr(self, "tranche_btns", None):
            return
        cur = core.tranche_of(self.state.hp_manual)
        active = self.state.k_choice is None and not self.state.no_confusion
        for t, b in zip(core.TRANCHES, self.tranche_btns):
            sel = "true" if (active and t.lo == cur.lo) else "false"
            if b.property("sel") != sel:
                b.setProperty("sel", sel)
                repolish(b)

    # -- sections repliables et transparence
    def _section_toggled(self):
        if not hasattr(self, "btn_all") or not getattr(self, "sections", None):
            return
        self.collapsed = {k: s.collapsed for k, s in self.sections.items()}
        if getattr(self, "panel", None) is not None:
            QTimer.singleShot(0, self._fit_height)        # après que Qt a recalculé la taille des cartes
            self.save()

    def _apply_mini(self):
        """Mode mini : l'en-tête seul (petit cadran, rotation, état) ; sinon l'en-tête et toutes les cartes."""
        self.scroll.setVisible(not self.mini)
        side = 62 if self.mini else 108
        self.dial.setFixedSize(side, side)
        self.lbl_src.setVisible(not self.mini)
        px = 17 if self.mini else 22
        self.lbl_rot.setStyleSheet(f"font-size:{px}px; font-weight:700; color:{theme.CREAM};")
        self.btn_all.setText("+" if self.mini else "–")
        self.btn_all.setToolTip("Tout réafficher" if self.mini else
                                "Mode mini : ne garder que le cadran et la rotation")
        if getattr(self, "panel", None) is not None:
            self._layout_panel()

    def toggle_all(self):
        """Mode mini : cache toutes les parties (il ne reste que la rotation), ou les réaffiche telles qu'avant."""
        self.mini = not self.mini
        self._apply_mini()
        self.save()

    def set_panel_opacity(self, v):
        self.panel_opacity = int(v)
        self.lbl_panel_op.setText(f"{v} %")
        self.panel.setWindowOpacity(v / 100.0)
        self.save()

    def set_draw_opacity(self, v):
        self.draw_opacity = int(v)
        self.lbl_draw_op.setText(f"{v} %")
        self.overlay.opacity = v / 100.0
        self.overlay.update()
        self.save()

    # -- état
    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self.state, k, v)
        self.refresh()

    def set_fight(self, i):
        self._set(fight=i)
        self.save()

    def set_screen(self, i):
        self.screen_idx = i
        g = self.screens[i].geometry()
        self.state.calib, self.state.screen_w = self._default_calib(g), g.width()
        self.state.origin = (g.x(), g.y())
        self.overlay.close()
        self.overlay = Overlay(g)
        self.overlay.opacity = self.draw_opacity / 100.0
        self.overlay.show()
        self.save()
        self.refresh()

    def set_summon(self, on):
        self._set(no_confusion=on)

    def set_hp_manual(self, v):
        self._set(hp_manual=float(v))
        self.save()

    def pick_tranche(self, t):
        """Un clic sur la tranche : règle le % au milieu de la tranche et repasse la confusion sur « d'après les PV »."""
        mid = (t.lo + t.hi) // 2
        self.sp_hp.setValue(mid)
        if int(self.state.hp_manual) != mid:      # hors Qt réel, valueChanged n'est pas émis
            self.set_hp_manual(mid)
        self.set_choice_index(0)

    def set_grid(self, on):
        self._set(show_grid=on)
        self.save()

    def add_hits(self, d):
        self._set(hits=max(0, min(12, self.state.hits + d)))

    # -- confusion : menu, collage, presse-papiers
    def set_choice_index(self, i):
        """Change le menu de confusion (et l'état, même si le signal Qt n'est pas émis)."""
        self.cb_conf.blockSignals(True)
        self.cb_conf.setCurrentIndex(i)
        self.cb_conf.blockSignals(False)
        self.on_conf_index(i)

    def on_conf_index(self, i):
        k = core.CONF_CHOICES[i][0] if 0 <= i < len(core.CONF_CHOICES) else None
        self._set(k_choice=k, hits=0)     # nouvelle confusion : on repart de 0 ligne au corps à corps

    def _paste_note(self, text):
        self.lbl_paste.setText(text)
        self.lbl_paste.setVisible(bool(text))

    def apply_pasted(self, k):
        idx = next(i for i, (kk, _) in enumerate(core.CONF_CHOICES) if kk == k)
        self.set_choice_index(idx)
        self._paste_note(f"Ligne reconnue : <b>{core.total_label(k)}</b>")

    def on_paste_text(self, text):
        if not text.strip():
            self._paste_note("")
            return
        k = core.parse_confusion(text, strict=False)
        if k is None:
            self._paste_note("<span style='color:" + theme.WARN + "'>Ligne non reconnue (ex. « Confusion horaire : 2 Pi/4 »)</span>")
        else:
            self.apply_pasted(k)

    def on_clipboard(self):
        """Une ligne de confusion copiée n'importe où (le chat du jeu) est prise tout de suite."""
        try:
            text = QGuiApplication.clipboard().text()
            k = core.parse_confusion(text)
            if k is not None:
                self.ed_paste.blockSignals(True)
                self.ed_paste.setText(text.strip().splitlines()[-1])
                self.ed_paste.blockSignals(False)
                self.apply_pasted(k)
        except Exception:
            traceback.print_exc()

    def new_turn(self):
        self.ed_paste.blockSignals(True)
        self.ed_paste.clear()
        self.ed_paste.blockSignals(False)
        self.set_choice_index(0)
        self._paste_note("Nouveau tour : choisis ou copie ta nouvelle confusion")

    # -- placement
    def place_at_mouse(self):
        """Te place sur la case sous la souris ; en même temps, la grille se recale toute seule."""
        mx, my = self._mouse_pos()
        self._place_at(mx, my)
        self.start_autocal(then=lambda: self._place_at(mx, my))       # on te replace si la grille a bougé

    def _place_at(self, x, y):
        cell = self.state.calib.cell_at(x, y)
        if cell is not None:
            self._set(you=cell, you_cleared=False)

    # -- calibration automatique : la salle est retrouvée sur une capture de l'écran du jeu
    def grab_screen(self):
        """Capture de l'écran du jeu : (tableau numpy hauteur x largeur x 3, pixels par point de l'écran), ou (None, 1)."""
        scr = self.screens[self.screen_idx]
        img = scr.grabWindow(0).toImage()
        if img.isNull() or img.width() == 0:
            return None, 1.0                                # rien à analyser (capture impossible)
        img = img.convertToFormat(QImage.Format.Format_RGB888)
        data = img.constBits()
        data.setsize(img.sizeInBytes())
        arr = np.frombuffer(data, np.uint8).reshape(img.height(), img.bytesPerLine())[:, : img.width() * 3]
        return arr.reshape(img.height(), img.width(), 3).copy(), img.width() / float(scr.geometry().width())

    def calibrate_auto(self):
        """Bouton ou raccourci « Calibrer la grille » : si la salle n'est pas reconnue, on te le dit."""
        self.start_autocal(manual=True)

    def start_autocal(self, manual=False, then=None):
        """Lance le calage automatique en arrière-plan. `then` : à refaire quand la grille a été corrigée."""
        if self._autocal is not None:                      # déjà en cours : on s'y raccroche
            if then is not None:
                self._autocal[3].append(then)
            self._autocal[2] = self._autocal[2] or manual
            return
        try:
            arr, scale = self.grab_screen()
        except Exception:
            traceback.print_exc()
            return
        if arr is None:
            if manual:
                self._say("Impossible de capturer l'écran.", bad=True)
            return
        g, c = self.screens[self.screen_idx].geometry(), self.state.calib
        hint = ((c.x0 - g.x()) * scale, (c.y0 - g.y()) * scale, c.kx * scale)       # la grille actuelle, en pixels de la capture
        self._autocal = [self.pool.submit(autocal.find, arr, hint), scale, manual, [then] if then else []]
        if manual:
            self._say("Recherche de la salle sur ton écran…")

    def _autocal_done(self):
        fut, scale, manual, thens = self._autocal
        self._autocal = None
        try:
            fit = fut.result()
        except Exception:
            traceback.print_exc()
            fit = None
        g, c = self.screens[self.screen_idx].geometry(), self.state.calib
        if fit is not None and fit.confident:
            x0, y0, kx = g.x() + fit.x0 / scale, g.y() + fit.y0 / scale, fit.kx / scale
            if max(abs(x0 - c.x0), abs(y0 - c.y0)) > 3.0 or abs(kx / c.kx - 1) > 0.012:
                c.x0, c.y0, c.kx, c.ky = x0, y0, kx, kx / 2        # sur place : les outils ouverts voient aussi le changement
                self._say("Grille calée automatiquement.")
                self._flash()
                self._pos_timer.start()                             # enregistre la nouvelle calibration
            elif manual:
                self._say("La grille est déjà bien calée.")
                self._flash()
        elif manual:
            self._say("Salle non reconnue sur cet écran. Ouvre ton combat (jeu en fenêtre, sur l'écran choisi dans "
                      "Réglages), ou calibre à la main.", bad=True)
            self.open_calibration()
        for action in thens:
            action()
        self.refresh()

    def _say(self, text, bad=False):
        self._msg = (text, bad)
        self._msg_timer.start()
        self.update_status()

    def _clear_msg(self):
        self._msg = None
        self.update_status()

    def _flash(self):
        """Montre un instant le contour de la salle sur le jeu : on voit tout de suite s'il longe bien le bord."""
        self._set(flash=True)
        self._flash_timer.start()

    def _end_flash(self):
        self._set(flash=False)

    def clear_me(self):
        """Pendant un déplacement : plus de case ni de traits jusqu'à ce que tu te replaces."""
        self._set(you=None, you_cleared=True)

    # -- raccourcis
    def on_hotkey(self, name):
        if self.recording_key:
            return
        try:
            if name == "clear_me":
                self.clear_me()
            elif name == "calibrate":
                self.calibrate_auto()
            elif name == "set_me":
                self.place_at_mouse()
            elif name == "conf_next":
                self.set_choice_index((self.cb_conf.currentIndex() + 1) % len(core.CONF_CHOICES))
            elif name == "toggle":
                self.overlay_on = not self.overlay_on
                self.refresh()
            elif name == "new_turn":
                self.new_turn()
            elif name == "hits_plus":
                self.add_hits(1)
            elif name == "hits_minus":
                self.add_hits(-1)
            elif name == "snap":
                self.snap_grid()
            elif name in ("nudge_left", "nudge_right", "nudge_up", "nudge_down"):
                self.nudge_grid({"nudge_left": -1, "nudge_right": 1}.get(name, 0), {"nudge_up": -1, "nudge_down": 1}.get(name, 0))
            elif name == "grid_grow":
                self.scale_grid(1)
            elif name == "grid_shrink":
                self.scale_grid(-1)
            elif name == "summon":
                new = not self.state.no_confusion
                self.ck_summon.setChecked(new)      # en vrai Qt, cela déclenche set_summon
                if self.state.no_confusion != new:
                    self.set_summon(new)
        except Exception:
            traceback.print_exc()

    # -- fenêtres interactives
    def _open_tool(self, tool, on_done):
        if self.tool is not None:
            return
        self.tool = tool
        self.tool.done.connect(on_done)
        self.overlay.hide()            # l'outil montre déjà la grille : pas de double affichage
        self.tool.open()

    def _tool_closed(self):
        self.tool = None
        self.overlay.show()
        self.refresh()

    def open_calibration(self):
        g = self.screens[self.screen_idx].geometry()
        self._open_tool(Calibration(g, self.state.calib, self.state.fight), self._calibration_done)

    def _calibration_done(self, cal):
        if cal is not None:
            self.state.calib = cal
            self.save()
        self._tool_closed()

    def open_place(self):
        self.start_autocal()
        g = self.screens[self.screen_idx].geometry()
        self._open_tool(PlacePicker(g, self.state.calib, self.state.fight, self.state.you), self._place_done)

    def _place_done(self, cell):
        if cell is not None:
            self.state.you, self.state.you_cleared = cell, False
        self._tool_closed()

    # -- boucle d'affichage
    def tick(self):
        try:
            pos = QCursor.pos()
            s = self.state
            s.mouse = (pos.x(), pos.y())
            c = s.calib
            if self._autocal is not None and self._autocal[0].done():
                self._autocal_done()
            sig = (c.cell_at(*s.mouse), s.you, s.hp_manual, s.hits, s.fight, s.show_grid, s.flash,
                   s.rotation(), self.overlay_on, c.x0, c.y0, c.kx, c.ky)
            if sig != self.last_sig:
                self.refresh()
                self.last_sig = sig
        except Exception:
            traceback.print_exc()

    def refresh(self):
        self.last_sig = None
        self.overlay.prims = view.scene(self.state)[0] if self.overlay_on else []
        self.overlay.update()
        self.lbl_hits.setText(str(self.state.hits))
        self.update_status()
        self._update_tranche_buttons()

    def update_status(self):
        s = self.state
        k, source = s.rotation()
        label = core.total_label(k)
        self.lbl_rot.setText(label[0].upper() + label[1:])
        origin = {"invocation": "Invocation", "choisie": "Confusion choisie", "pv": f"PV {s.hp_manual:.0f} %"}[source]
        self.lbl_src.setText(origin + (f" · {s.hits} càc" if s.hits else ""))

        def dot(color):
            return f"<span style='color:{color}'>●</span>"

        set_me = key_label(self.keys["set_me"])
        if s.you is None and s.you_cleared:
            parts = [f"{dot(theme.AMBER)} Déplacement · <b>{set_me}</b> sur ta case"]
        elif s.you is None:
            parts = [f"{dot(theme.AMBER)} À placer · <b>{set_me}</b> sur ta case"]
        else:
            parts = [f"{dot(theme.CYAN)} Placé · case {s.you[0]},{s.you[1]}"]
        if self._msg:
            text, bad = self._msg
            parts.append(f"<span style='color:{theme.WARN if bad else theme.CYAN_SOFT}'>{text}</span>")
        if self.hotkeys is not None and self.hotkeys.error:
            parts.append(f"<span style='color:{theme.WARN}'>Raccourcis indisponibles ({self.hotkeys.error})</span>")
        self.lbl.setText("<br>".join(parts))
        self.dial.set_info(view.dial_info(s))

    def quit(self):
        if self.hotkeys is not None:
            self.hotkeys.stop()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.app.quit()


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":      # contrôle d'une version compilée, sans fenêtre
        Path(sys.argv[2]).write_text("OK" if autocal.selftest() else "ECHEC", encoding="utf-8")
        return
    # Exe sans console : les erreurs vont dans harebourg.log, à côté du programme.
    if sys.stderr is None or sys.stdout is None:
        try:
            log = open(APP_DIR / "harebourg.log", "a", encoding="utf-8", buffering=1)
        except OSError:
            import io
            log = io.StringIO()
        sys.stderr = sys.stderr or log
        sys.stdout = sys.stdout or log
    # Une exception dans un slot PyQt6 fait planter tout le programme : on l'affiche et on continue.
    sys.excepthook = lambda *a: traceback.print_exception(*a)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = Controller(app)   # noqa: F841  (doit rester référencé)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
