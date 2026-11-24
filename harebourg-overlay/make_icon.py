"""Fabrique icon.ico (le cadran du Comte) pour l'exe et l'installateur. Lancer : python make_icon.py (PyQt6 et Pillow)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication

from dial import Dial

app = QApplication([])
d = Dial(256)
d.set_info({"k": 1, "live": True, "aim_angle": 330.0, "needle_angle": 60.0, "ok": True})
d.settle()
pm = QPixmap(256, 256)
pm.fill(QColor(0, 0, 0, 0))
d.render(pm)
png = Path(__file__).with_name("icon.png")
pm.save(str(png), "PNG")
img = Image.open(png).convert("RGBA")
img.save(Path(__file__).with_name("icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
png.unlink()
print("icon.ico écrit")
