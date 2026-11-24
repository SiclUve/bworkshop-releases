"""Robustesse de l'application : réglages à l'épreuve des fichiers abîmés, écriture sûre, journal qui ne grossit pas.

Rien ici ne dépend de Qt ni du reste du programme, pour pouvoir tout tester sans écran (test_safety.py).
"""
import json
import math
import os
import shutil
import sys
import time
import traceback
from pathlib import Path


# --- Où vivent les réglages ----------------------------------------------------------------------
def _writable(folder):
    try:
        probe = folder / ".harebourg-write-test"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def pick_config_path(app_dir):
    """config.json à côté du programme ; si ce dossier est protégé (installé à la main dans Program Files par exemple),
    dans %LOCALAPPDATA%\\HarebourgOverlay."""
    if _writable(app_dir):
        return app_dir / "config.json"
    alt = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "HarebourgOverlay"
    try:
        alt.mkdir(parents=True, exist_ok=True)
    except OSError:
        return app_dir / "config.json"
    return alt / "config.json" if _writable(alt) else app_dir / "config.json"


# --- Lire et écrire config.json ------------------------------------------------------------------
def load_config(path):
    """Le contenu de config.json, ou {} si absent ou illisible. Si le fichier est abîmé, on essaie la copie de sécurité."""
    for candidate in (Path(path), Path(str(path) + ".bak")):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def write_json_atomic(path, data):
    """Écrit le fichier d'un coup (fichier temporaire puis remplacement) : une coupure en plein milieu ne l'abîme jamais.
    La version précédente est gardée en .bak."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if path.exists():
        try:
            shutil.copyfile(path, str(path) + ".bak")
        except OSError:
            pass
    os.replace(tmp, path)


# --- Nettoyer les réglages -----------------------------------------------------------------------
def _number(v, lo, hi):
    """v comme nombre fini entre lo et hi, ou None (les booléens ne sont pas des nombres ici)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v if math.isfinite(v) and lo <= v <= hi else None


def sanitize_config(cfg, n_fights, hotkeys, langs):
    """Garde ce qui est valide dans les réglages lus et jette le reste : un config.json abîmé ou modifié à la main ne doit
    jamais empêcher le démarrage. Une valeur invalide retombe sur la valeur par défaut du programme."""
    if not isinstance(cfg, dict):
        return {}
    out = {}
    calib = cfg.get("calib")
    if isinstance(calib, dict):
        vals = {k: _number(calib.get(k), -50000, 50000) for k in ("x0", "y0", "kx", "ky")}
        if None not in vals.values() and 4 <= vals["kx"] <= 400 and 2 <= vals["ky"] <= 200:
            out["calib"] = {k: float(v) for k, v in vals.items()}
    for key in ("screen", "calib_screen"):
        v = _number(cfg.get(key), 0, 16)
        if v is not None and float(v).is_integer():
            out[key] = int(v)
    v = _number(cfg.get("fight"), 0, n_fights - 1)
    if v is not None and float(v).is_integer():
        out["fight"] = int(v)
    v = _number(cfg.get("hp_manual"), 0, 100)
    if v is not None:
        out["hp_manual"] = float(v)
    for key in ("show_grid", "mini", "auto_calage"):
        if isinstance(cfg.get(key), bool):
            out[key] = cfg[key]
    for key, lo in (("panel_opacity", 20), ("draw_opacity", 10)):
        v = _number(cfg.get(key), lo, 100)
        if v is not None:
            out[key] = int(v)
    if isinstance(cfg.get("lang"), str) and cfg["lang"] in langs:
        out["lang"] = cfg["lang"]
    keys = cfg.get("hotkeys")
    if isinstance(keys, dict):
        out["hotkeys"] = {k: v for k, v in keys.items() if k in hotkeys and isinstance(v, str)}
    collapsed = cfg.get("collapsed")
    if isinstance(collapsed, dict):
        out["collapsed"] = {k: v for k, v in collapsed.items() if isinstance(k, str) and isinstance(v, bool)}
    pos = cfg.get("panel_pos")
    if isinstance(pos, list) and len(pos) == 2 and all(_number(p, -100000, 100000) is not None for p in pos):
        out["panel_pos"] = [int(p) for p in pos]
    size = cfg.get("panel_size")
    if isinstance(size, list) and len(size) == 2 and all(_number(p, 100, 20000) is not None for p in size):
        out["panel_size"] = [int(p) for p in size]
    return out


# --- Journal d'erreurs ---------------------------------------------------------------------------
class ErrorLog:
    """Écrit les erreurs sur sys.stderr, sans jamais le noyer : trois fois chaque erreur identique, puis un compteur
    (10e, 100e, 1000e…). Sans ça, une erreur qui se répète à chaque image (30 par seconde) remplirait le disque."""

    def __init__(self):
        self.counts = {}

    def report(self, exc_info=None, tag=""):
        et, ev, tb = exc_info or sys.exc_info()
        if et is None:
            return False
        key = f"{tag}|{et.__name__}|{ev}"
        n = self.counts[key] = self.counts.get(key, 0) + 1
        if n > 3 and n not in (10, 100, 1000, 10000):
            return False
        text = "".join(traceback.format_exception(et, ev, tb))
        suffix = f"(cette erreur s'est répétée {n} fois)\n" if n > 3 else ""
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {tag}\n{text}{suffix}", file=sys.stderr, flush=True)
        except Exception:
            pass
        return True


ERRORS = ErrorLog()


def rotate_log(path, max_bytes=512 * 1024):
    """Au démarrage : si le journal est devenu trop gros, on garde l'ancien en .1 et on repart d'un journal vide."""
    path = Path(path)
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            os.replace(path, str(path) + ".1")
    except OSError:
        pass
