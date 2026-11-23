"""Palette du Comte Harebourg pour la fenêtre de contrôle (chapeau vert-bleu, laiton, lueur cyan, fourrure crème).

Aucune dépendance Qt : ce sont des couleurs et une feuille de style. Les couleurs dessinées sur le jeu
(cases, traits) restent dans view.py.
"""

# Fond de la fenêtre (de haut en bas)
BG_TOP, BG_MID, BG_BOT = "#0d4546", "#082e2f", "#041819"
# Vert-bleu du chapeau
TEAL, TEAL_DARK, TEAL_EDGE = "#14595a", "#0b3b3d", "#1d6f6b"
# Lueur cyan (yeux, gemmes)
CYAN, CYAN_SOFT, CYAN_MID, CYAN_DEEP = "#3fe0e8", "#bff7f4", "#17a4a8", "#0c7c82"
# Laiton des cadrans et des boucles
BRASS_LIGHT, BRASS, BRASS_DARK = "#e0b676", "#b88a55", "#6b4725"
# Cuir et pierre des boutons
STONE_TOP, STONE_BOT, STONE_EDGE = "#6f6040", "#3d3425", "#8a7650"
# Textes
CREAM, MUTED = "#f1e6c8", "#9fb8b4"
AMBER, WARN, INK = "#f2c94c", "#ff7864", "#0a0a0c"

_QSS = """
QWidget { color: @CREAM@; font-family: "Segoe UI", "Segoe UI Variable", "Helvetica Neue", sans-serif; font-size: 12px; }
QLabel { background: transparent; }
QToolTip { background: #031516; color: @CREAM@; border: 1px solid @BRASS@; padding: 4px 6px; }

/* Cartes repliables */
QWidget#card { background: rgba(2, 20, 22, 120); border: 1px solid #14504f; border-radius: 11px; }
QPushButton#head { text-align: left; padding: 6px 12px; font-size: 13px; font-weight: 600; color: @CREAM@;
    border: none; border-radius: 10px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 @TEAL@, stop:1 @TEAL_DARK@); }
QPushButton#head:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1b7273, stop:1 #0f4b4d); }

/* Boutons en laiton et pierre */
QPushButton { color: @CREAM@; padding: 4px 10px; border-radius: 8px; border: 1px solid #2a2316;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 @STONE_TOP@, stop:1 @STONE_BOT@); }
QPushButton:hover { border-color: @BRASS@; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #85734d, stop:1 #4a3f2b); }
QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d3425, stop:1 #5a4d33); }
QPushButton[sel="true"] { border: 1.5px solid @AMBER@; color: @CYAN_SOFT@; font-weight: 600; }
QPushButton[rec="true"] { border: 1.5px solid @CYAN@; color: @CYAN@; }
QPushButton#primary { color: white; font-weight: 700; font-size: 13px; padding: 6px 12px; border: 1px solid #5ee9ee; border-radius: 9px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22bcc0, stop:1 @CYAN_DEEP@); }
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3fd2d6, stop:1 #0e9097); }
QPushButton#primary:pressed { background: @CYAN_DEEP@; }
QPushButton#tiny { padding: 0; font-weight: 700; font-size: 14px; border-radius: 7px; min-width: 24px; max-width: 24px; min-height: 22px; max-height: 22px; }

/* Champs */
QComboBox, QLineEdit { background: #04191a; border: 1px solid @TEAL_EDGE@; border-radius: 8px; padding: 4px 8px;
    selection-background-color: @CYAN_MID@; selection-color: white; }
QLineEdit:focus, QComboBox:focus { border: 1px solid @CYAN@; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #06201f; border: 1px solid @TEAL_EDGE@; color: @CREAM@;
    selection-background-color: @CYAN_DEEP@; selection-color: white; outline: 0; }

/* Cases à cocher */
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #1f8a8a; border-radius: 5px; background: #04191a; }
QCheckBox::indicator:hover { border-color: @CYAN@; }
QCheckBox::indicator:checked { border-color: @CYAN@;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.6, fx:0.5, fy:0.5, stop:0 #9ffcff, stop:0.55 @CYAN_MID@, stop:1 #0a5a5f); }

/* Curseurs */
QSlider::groove:horizontal { height: 6px; border-radius: 3px; background: #04191a; border: 1px solid #14504f; }
QSlider::sub-page:horizontal { border-radius: 3px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @CYAN_DEEP@, stop:1 @CYAN@); }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px; border: 1px solid #4a3118;
    background: qradialgradient(cx:0.4, cy:0.35, radius:0.8, stop:0 @BRASS_LIGHT@, stop:1 @BRASS_DARK@); }

/* Zone qui défile (les cartes) */
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px 0; }
QScrollBar::handle:vertical { background: @TEAL_EDGE@; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: @CYAN_MID@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

/* Textes secondaires */
QLabel#note { color: @MUTED@; font-style: italic; }
QLabel#pill { background: rgba(23, 164, 168, 55); border: 1px solid @CYAN_MID@; border-radius: 9px;
    padding: 2px 9px; color: @CYAN_SOFT@; font-weight: 600; }
QLabel#warn { color: @WARN@; }
"""

_COLORS = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, str) and v.startswith("#")}


def stylesheet():
    """Feuille de style Qt de la fenêtre de contrôle."""
    qss = _QSS
    for name in sorted(_COLORS, key=len, reverse=True):      # les noms longs d'abord (CYAN_SOFT avant CYAN)
        qss = qss.replace(f"@{name}@", _COLORS[name])
    return qss
