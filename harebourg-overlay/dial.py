"""Le cadran du Comte : un anneau de laiton à dents, une face vert-bleu, et l'aiguille noire.

L'aiguille noire montre où part ton sort. Le repère cyan montre où tu vises. L'arc cyan entre les deux montre
de combien (et dans quel sens) la confusion tourne ton sort. Les angles viennent de view.dial_info.
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QPainter, QPainterPath, QPen, QPolygonF,
                         QRadialGradient)
from PyQt6.QtWidgets import QWidget

import theme
from i18n import _t

def tooltip():
    return _t("Aiguille noire : où part ton sort.\nRepère cyan : où tu vises.\n"
              "Sans visée (pas placé, souris hors de la salle), le repère reste en haut et l'aiguille\n"
              "montre la rotation : si tu vises en haut, le sort part là où elle pointe.")


def _pt(c, r, deg):
    """Point à la distance r du centre c, dans la direction deg (horaire depuis le haut)."""
    a = math.radians(deg)
    return QPointF(c.x() + r * math.sin(a), c.y() - r * math.cos(a))


def _approach(cur, target, rate=0.32):
    """Rapproche cur de target par le plus court chemin. Renvoie (nouvel angle, arrivé ?)."""
    delta = (target - cur + 180.0) % 360.0 - 180.0
    if abs(delta) < 0.25:
        return target % 360.0, True
    return (cur + delta * rate) % 360.0, False


class Dial(QWidget):
    def __init__(self, size=108):
        super().__init__()
        self.setFixedSize(size, size)
        self.setToolTip(tooltip())
        self.info = {"k": 0, "live": False, "aim_angle": 0.0, "needle_angle": 0.0, "ok": True}
        self.shown_needle = 0.0
        self.shown_aim = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._step)

    # -- données
    def set_info(self, info):
        self.info = dict(info)
        if not self.timer.isActive():
            self.timer.start()
        self.update()

    def settle(self):
        """Pose l'aiguille tout de suite, sans animation (pour les tests et les captures)."""
        self.timer.stop()
        self.shown_needle = self.info["needle_angle"] % 360
        self.shown_aim = self.info["aim_angle"] % 360
        self.update()

    def _step(self):
        self.shown_needle, d1 = _approach(self.shown_needle, self.info["needle_angle"])
        self.shown_aim, d2 = _approach(self.shown_aim, self.info["aim_angle"])
        if d1 and d2:
            self.timer.stop()
        self.update()

    # -- dessin
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        c = QPointF(w / 2, w / 2)
        R = w / 2 - 1.5
        Rf = R * 0.74                       # rayon de la face
        small = w < 80
        self._teeth(p, c, R, 12 if small else 16)
        self._ring(p, c, R * 0.90, R * 0.755)
        self._face(p, c, Rf)
        self._ticks(p, c, Rf)
        k = self.info.get("k", 0)
        if k % 4:
            self._arc(p, c, Rf * 0.56, k)
        self._aim_marker(p, c, Rf)
        self._needle(p, c, Rf)
        self._jewel(p, c, max(5.0, R * 0.12))

    def _teeth(self, p, c, R, n):
        p.setPen(QPen(QColor("#3b2612"), 0.9))
        p.setBrush(QBrush(QColor(theme.BRASS)))
        t = R * 0.075
        for i in range(n):
            p.save()
            p.translate(c)
            p.rotate(i * 360.0 / n)
            p.drawPolygon(QPolygonF([QPointF(-t, -R * 0.88), QPointF(t, -R * 0.88),
                                     QPointF(t * 0.55, -R), QPointF(-t * 0.55, -R)]))
            p.restore()

    def _ring(self, p, c, r_out, r_in):
        g = QConicalGradient(c, 120)
        for pos, col in ((0.0, theme.BRASS_LIGHT), (0.22, theme.BRASS_DARK), (0.5, "#d9ab6b"),
                         (0.78, theme.BRASS_DARK), (1.0, theme.BRASS_LIGHT)):
            g.setColorAt(pos, QColor(col))
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor("#3b2612"), 1.1))
        p.drawEllipse(c, r_out, r_out)
        p.setBrush(QBrush(QColor("#10100f")))                 # fond du creux sous la face
        p.drawEllipse(c, r_in, r_in)

    def _face(self, p, c, Rf):
        g = QRadialGradient(c, Rf)
        g.setColorAt(0.0, QColor("#12605f"))
        g.setColorAt(0.62, QColor("#083d3f"))
        g.setColorAt(1.0, QColor("#031516"))
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor("#021011"), 1.6))
        p.drawEllipse(c, Rf, Rf)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(63, 224, 232, 70), 1.0))
        p.drawEllipse(c, Rf - 1.8, Rf - 1.8)

    def _ticks(self, p, c, Rf):
        for deg in (0, 90, 180, 270):                         # les quatre repères cyan, comme sur la maquette
            a, b = _pt(c, Rf * 0.70, deg), _pt(c, Rf * 0.93, deg)
            p.setPen(QPen(QColor(63, 224, 232, 70), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(a, b)
            p.setPen(QPen(QColor(theme.CYAN), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(a, b)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(63, 224, 232, 110)))
        for deg in (45, 135, 225, 315):
            p.drawEllipse(_pt(c, Rf * 0.84, deg), 1.5, 1.5)

    def _arc(self, p, c, r, k):
        """Arc cyan du repère à l'aiguille, dans le sens de la rotation (le plus court : 3 quarts = 90° anti-horaire)."""
        sweep = {1: 90.0, 2: 180.0, 3: -90.0}[k % 4]
        start = self.shown_aim
        rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(63, 224, 232, 190), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int((90.0 - start) * 16), int(-sweep * 16))
        end = start + sweep
        sign = 1.0 if sweep > 0 else -1.0
        tip = _pt(c, r, end)
        e = math.radians(end)
        tx, ty = math.cos(e) * sign, math.sin(e) * sign        # tangente dans le sens du mouvement
        nx, ny = -ty, tx
        head = QPolygonF([QPointF(tip.x() + tx * 5.5, tip.y() + ty * 5.5),
                          QPointF(tip.x() - tx * 1.5 + nx * 3.6, tip.y() - ty * 1.5 + ny * 3.6),
                          QPointF(tip.x() - tx * 1.5 - nx * 3.6, tip.y() - ty * 1.5 - ny * 3.6)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(63, 224, 232, 220)))
        p.drawPolygon(head)

    def _aim_marker(self, p, c, Rf):
        """Petit losange cyan : la direction que tu vises."""
        m = _pt(c, Rf * 0.84, self.shown_aim)
        s = max(3.6, Rf * 0.085)
        p.save()
        p.translate(m)
        p.rotate(self.shown_aim)
        p.setPen(QPen(QColor("white"), 1.1))
        p.setBrush(QBrush(QColor(theme.CYAN)))
        p.drawPolygon(QPolygonF([QPointF(0, -s * 1.5), QPointF(s, 0), QPointF(0, s * 1.5), QPointF(-s, 0)]))
        p.restore()

    def _needle(self, p, c, Rf):
        """L'aiguille noire du Comte : un losange effilé, avec son petit anneau au talon."""
        L = Rf * 0.93
        w = Rf * 0.115
        tail = L * 0.30
        kite = QPolygonF([QPointF(0, -L), QPointF(w, -L * 0.20), QPointF(0, tail), QPointF(-w, -L * 0.20)])
        live, ok = self.info.get("live", False), self.info.get("ok", True)
        p.save()
        p.translate(c)
        p.rotate(self.shown_needle)
        if live:                                                # halo : cyan si le sort est valide, rouge sinon
            glow = QColor(63, 224, 232, 70) if ok else QColor(255, 120, 100, 110)
            path = QPainterPath()
            path.addPolygon(kite)
            p.setPen(QPen(glow, 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.translate(1.4, 1.8)                                    # ombre portée
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 130)))
        p.drawPolygon(kite)
        p.translate(-1.4, -1.8)
        p.setPen(QPen(QColor(241, 230, 200, 215), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(QColor(theme.INK)))
        p.drawPolygon(kite)
        p.setBrush(Qt.BrushStyle.NoBrush)                        # l'anneau du talon, comme sur le chapeau
        p.drawEllipse(QPointF(0, tail + 3.6), 3.2, 3.2)
        p.restore()

    def _jewel(self, p, c, r):
        g = QRadialGradient(QPointF(c.x() - r * 0.3, c.y() - r * 0.3), r * 1.5)
        g.setColorAt(0.0, QColor(theme.BRASS_LIGHT))
        g.setColorAt(1.0, QColor(theme.BRASS_DARK))
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor("#2a1a0c"), 1.0))
        p.drawEllipse(c, r, r)
        ri = r * 0.68
        g2 = QRadialGradient(QPointF(c.x() - ri * 0.25, c.y() - ri * 0.3), ri * 1.3)
        g2.setColorAt(0.0, QColor("#b5fdff"))
        g2.setColorAt(0.5, QColor(theme.CYAN_MID))
        g2.setColorAt(1.0, QColor("#08565a"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g2))
        p.drawEllipse(c, ri, ri)
        p.setBrush(QBrush(QColor(255, 255, 255, 170)))
        p.drawEllipse(QPointF(c.x() - ri * 0.3, c.y() - ri * 0.35), ri * 0.22, ri * 0.22)
