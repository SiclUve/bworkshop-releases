"""Tests de robustesse (safety.py et démarrage avec des réglages abîmés). Lancer : python test_safety.py"""
import io
import json
import os
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import safety

FIGHTS, HOTKEYS, LANGS = 5, {"set_me": "<f6>", "snap": "<ctrl>+<shift>+c"}, {"fr": "Français", "en": "English"}


def clean(cfg):
    return safety.sanitize_config(cfg, FIGHTS, HOTKEYS, LANGS)


def test_sanitize():
    good = {"calib": {"x0": 631.0, "y0": 304.0, "kx": 44.0, "ky": 22.0}, "calib_screen": 0, "screen": 1, "fight": 4,
            "hp_manual": 14.0, "show_grid": True, "mini": False, "auto_calage": False, "panel_opacity": 80, "draw_opacity": 50,
            "lang": "en", "hotkeys": {"set_me": "<f6>", "snap": ""}, "collapsed": {"conf": False, "pv": True},
            "panel_pos": [10, 20], "panel_size": [400, 600]}
    assert clean(good) == good                                            # une config valide ne change pas
    assert clean([]) == {} and clean("x") == {} and clean(None) == {} and clean(12) == {}
    bad = {"calib": {"x0": "a", "y0": 1, "kx": 44, "ky": 22}, "fight": 99, "hp_manual": 150, "show_grid": "oui", "lang": "de",
           "panel_opacity": 5, "draw_opacity": "x", "hotkeys": {"inconnue": "<f1>", "set_me": 5}, "collapsed": {"conf": "x"},
           "panel_pos": [1], "panel_size": [10, 10], "screen": -1, "mini": 1, "auto_calage": None}
    assert clean(bad) == {"hotkeys": {}, "collapsed": {}}                  # tout le reste retombe sur les valeurs par défaut
    # valeurs extrêmes ou non finies
    assert "calib" not in clean({"calib": {"x0": float("nan"), "y0": 0, "kx": 44, "ky": 22}})
    assert "calib" not in clean({"calib": {"x0": 0, "y0": 0, "kx": 0, "ky": 0}})
    assert "calib" not in clean({"calib": {"x0": 0, "y0": 0, "kx": 1e9, "ky": 1e9}})
    assert "fight" not in clean({"fight": 1.5}) and clean({"fight": 2.0})["fight"] == 2
    assert "hp_manual" not in clean({"hp_manual": float("inf")}) and "hp_manual" not in clean({"hp_manual": True})
    # n'importe quoi : jamais d'exception
    rng = random.Random(5)
    junk = [None, True, 0, -1, 1e300, float("nan"), "", "x", [], [1, 2], {}, {"a": 1}, [[]], {"x0": {}}]
    keys = ["calib", "calib_screen", "screen", "fight", "hp_manual", "show_grid", "mini", "auto_calage", "panel_opacity",
            "draw_opacity", "lang", "hotkeys", "collapsed", "panel_pos", "panel_size", "autre"]
    for _ in range(3000):
        out = clean({k: rng.choice(junk) for k in rng.sample(keys, rng.randint(1, len(keys)))})
        assert isinstance(out, dict)
        json.dumps(out)                                                    # et le résultat s'enregistre toujours
    print("OK : réglages nettoyés (valides gardés, invalides écartés, 3000 configs absurdes sans erreur)")


def test_files():
    d = Path(tempfile.mkdtemp())
    p = d / "config.json"
    assert safety.load_config(p) == {}                                     # absent
    safety.write_json_atomic(p, {"a": 1})
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1} and not (d / "config.json.tmp").exists()
    safety.write_json_atomic(p, {"a": 2})
    assert json.loads((d / "config.json.bak").read_text(encoding="utf-8")) == {"a": 1}   # la version précédente est gardée
    p.write_text('{"a": 2', encoding="utf-8")                              # fichier coupé en plein milieu
    assert safety.load_config(p) == {"a": 1}                               # on retrouve la copie de sécurité
    p.write_text("[1, 2]", encoding="utf-8")                               # ce n'est pas un dictionnaire
    assert safety.load_config(p) == {"a": 1}
    p.write_text("\x00\x01 pas du json", encoding="utf-8")
    (d / "config.json.bak").write_text("aussi abîmé", encoding="utf-8")
    assert safety.load_config(p) == {}                                     # tout est abîmé : réglages par défaut, sans erreur
    # un dossier protégé : l'écriture échoue proprement (exception), et le dossier de repli est choisi
    try:
        safety.write_json_atomic(d / "inexistant" / "config.json", {})
        raise AssertionError("aurait dû échouer")
    except OSError:
        pass
    old = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = str(d / "appdata")
    try:
        assert safety.pick_config_path(d) == d / "config.json"             # dossier du programme inscriptible : on le garde
        orig = safety._writable
        safety._writable = lambda folder: folder != d                      # simule un dossier protégé
        assert safety.pick_config_path(d) == d / "appdata" / "HarebourgOverlay" / "config.json"
        safety._writable = orig
    finally:
        if old is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = old
    print("OK : écriture sûre (atomique, copie de sécurité, fichier abîmé, dossier protégé)")


def test_error_log():
    log = safety.ErrorLog()
    real, buf = sys.stderr, io.StringIO()
    sys.stderr = buf
    try:
        for _ in range(5000):                                              # la même erreur, 30 fois par seconde pendant des minutes
            try:
                1 / 0
            except ZeroDivisionError:
                log.report(tag="tick")
        try:
            {}["x"]
        except KeyError:
            assert log.report(tag="autre")                                 # une erreur différente est toujours écrite
    finally:
        sys.stderr = real
    out = buf.getvalue()
    assert out.count("Traceback") == 3 + 3 + 1 and len(out) < 12000, (out.count("Traceback"), len(out))   # 3 premières, puis 10e, 100e, 1000e, et l'autre erreur
    assert "répétée 10 fois" in out and "répétée 1000 fois" in out
    assert log.report(exc_info=(None, None, None)) is False
    d = Path(tempfile.mkdtemp())
    big = d / "harebourg.log"
    big.write_text("x" * 600_000, encoding="utf-8")
    safety.rotate_log(big)
    assert not big.exists() and (d / "harebourg.log.1").stat().st_size == 600_000
    small = d / "petit.log"
    small.write_text("ok", encoding="utf-8")
    safety.rotate_log(small)
    assert small.exists()
    print("OK : journal d'erreurs (trois exemplaires puis un compteur, rotation du journal trop gros)")


if __name__ == "__main__":
    test_sanitize()
    test_files()
    test_error_log()
