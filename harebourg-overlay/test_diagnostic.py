"""Tests du diagnostic (diagnostic.py) et de l'auto-contrôle de l'exe. Lancer : python test_diagnostic.py"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import autocal
import diagnostic
import i18n

SCREENS = [(0, 0, 1920, 1080, 1.0), (1920, 0, 1366, 768, 1.0)]
CAP = {"w": 1920, "h": 1080, "ms": 36, "mean": 88, "black": False, "brown": 31.0}
GOOD = autocal.Fit(633.0, 303.0, 44.3, 0.50, 0.08)
BORDERLESS = {"title": "Locket - Sram - Release", "rect": (0, 0, 1920, 1080), "popup": True, "caption": False, "elevated": False}


def info(**kw):
    base = {"version": "1.0", "system": "Windows-11 · Python 3.12", "screens": SCREENS, "games": [BORDERLESS], "capture": CAP,
            "fit": GOOD, "hotkeys_error": None,
            "config": {"path": "C:/x/config.json", "writable": True, "calib": {"x0": 631.0, "y0": 304.0, "kx": 44.0, "ky": 22.0},
                       "dropped": []}}
    base.update(kw)
    return base


def test_report():
    i18n.set_lang("fr")
    ok = diagnostic.build_report(info())
    assert "plein écran sans bordure (compatible)" in ok and "lancé en administrateur : non" in ok
    assert "salle reconnue" in ok and "tout est bon pour jouer." in ok and "point(s) à voir" not in ok
    cases = {
        "aucune fenêtre Dofus visible": dict(games=[]),
        "toute noire": dict(capture=dict(CAP, black=True)),
        "impossible": dict(capture=None, fit=None),
        "salle n'est pas reconnue": dict(fit=autocal.Fit(0, 0, 20, 0.03, 0.0)),
        "administrateur : les raccourcis": dict(games=[dict(BORDERLESS, elevated=True)]),
        "ne s'installent pas": dict(hotkeys_error="boom"),
        "décalée : appuie sur F6": dict(config={"path": "x", "writable": True, "calib": {"x0": 700.0, "y0": 304.0, "kx": 44.0, "ky": 22.0}, "dropped": []}),
        "protégé : tes réglages": dict(config={"path": "x", "writable": False, "calib": None, "dropped": []}),
        "valeurs invalides ignorées : fight": dict(config={"path": "x", "writable": True, "calib": None, "dropped": ["fight"]}),
    }
    for want, kw in cases.items():
        text = diagnostic.build_report(info(**kw))
        assert want in text and "point(s) à voir" in text or want.startswith("valeurs"), (want, text)
    assert "fenêtré" in diagnostic.build_report(info(games=[dict(BORDERLESS, caption=True, popup=False)]))
    i18n.set_lang("en")                                                   # et en anglais, sans mot français
    import re
    for kw in ({}, *cases.values()):
        text = diagnostic.build_report(info(**kw))
        assert not re.search(r"[éèêàùôîç]", text), text
    assert "everything is fine to play." in diagnostic.build_report(info())
    i18n.set_lang("fr")
    print("OK : rapport de diagnostic (cas normal, jeu absent, capture noire, salle non reconnue, administrateur, FR et EN)")


def test_real_machine_queries():
    games = diagnostic.find_game_windows()                               # sur ta machine : peut contenir le vrai jeu
    assert isinstance(games, list)
    for g in games:
        assert set(g) == {"title", "rect", "popup", "caption", "elevated"} and len(g["rect"]) == 4
    print(f"OK : lecture des fenêtres du jeu sur cette machine ({len(games)} trouvée(s))")


def test_selftest_subprocess():
    out = Path(tempfile.mkdtemp()) / "selftest.txt"
    r = subprocess.run([sys.executable, str(HERE / "overlay.py"), "--selftest", str(out)], capture_output=True, timeout=120,
                       env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    assert r.returncode == 0 and out.read_text(encoding="utf-8") == "OK", (r.returncode, r.stderr[-300:])
    print("OK : auto-contrôle (--selftest) : calage, langues, nettoyage des réglages")


if __name__ == "__main__":
    test_report()
    test_real_machine_queries()
    test_selftest_subprocess()
