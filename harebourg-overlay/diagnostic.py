"""Diagnostic : « HarebourgOverlay.exe --diagnose [secondes] [fichier] ».

À lancer pendant un combat. Le programme attend quelques secondes (le temps de repasser sur le jeu), prend UNE capture de
l'écran, l'analyse sur place, puis écrit un rapport texte. La capture n'est ni enregistrée ni envoyée, et le rapport ne
contient que des chiffres : tailles d'écran, mode d'affichage du jeu, résultat du calage. Jamais de pixels, ni de texte lu.
"""
import platform
import sys
import time
from pathlib import Path

import autocal
from i18n import _t

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wt


# --- Ce qu'on lit sur la machine -------------------------------------------------------------------
def _elevated(pid):
    """True / False, ou None si on ne peut pas le savoir (accès refusé : processus plus privilégié que nous)."""
    k32, adv = ctypes.windll.kernel32, ctypes.windll.advapi32
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    tok = wt.HANDLE()
    ok = adv.OpenProcessToken(h, 0x8, ctypes.byref(tok))
    val, ret = wt.DWORD(), wt.DWORD()
    ok = ok and adv.GetTokenInformation(tok, 20, ctypes.byref(val), 4, ctypes.byref(ret))
    if tok:
        k32.CloseHandle(tok)
    k32.CloseHandle(h)
    return bool(val.value) if ok else None


def find_game_windows():
    """Les fenêtres visibles des programmes dont le nom contient « dofus » :
    liste de dicts (title, rect = (x, y, largeur, hauteur) de la zone cliente, popup, caption, elevated)."""
    if sys.platform != "win32":
        return []
    user32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def visit(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = k32.OpenProcess(0x1000, False, pid.value)
        if not h:
            return True
        buf, size = ctypes.create_unicode_buffer(520), wt.DWORD(520)
        ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        k32.CloseHandle(h)
        if not ok or "dofus" not in Path(buf.value).name.lower():
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, title, n + 1)
        cr, pt = wt.RECT(), wt.POINT(0, 0)
        user32.GetClientRect(hwnd, ctypes.byref(cr))
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        style = user32.GetWindowLongW(hwnd, -16) & 0xFFFFFFFF
        found.append({"title": title.value, "rect": (pt.x, pt.y, cr.right, cr.bottom), "popup": bool(style & 0x80000000),
                      "caption": bool(style & 0xC00000), "elevated": _elevated(pid.value)})
        return True

    user32.EnumWindows(visit, 0)
    return found


# --- Le rapport (testable avec de fausses données) -------------------------------------------------
def build_report(info):
    """info : version, system, screens [(x, y, l, h, pixels par point)], games, capture, fit, config, hotkeys_error."""
    out, problems = [], []
    add = out.append
    add(_t("Diagnostic de Harebourg Overlay {version}").format(version=info["version"]))
    add(info["system"])
    add("")
    add(_t("Écrans :"))
    for i, (x, y, w, h, dpr) in enumerate(info["screens"]):
        add("  " + _t("écran {n} : {w}x{h} en ({x},{y}), {dpr} pixel(s) par point").format(n=i + 1, w=w, h=h, x=x, y=y, dpr=dpr))
    add("")
    add(_t("Jeu :"))
    games = info["games"]
    if not games:
        add("  " + _t("aucune fenêtre Dofus visible"))
        problems.append(_t("Le jeu n'est pas visible : lance le diagnostic pendant un combat, avec le jeu devant."))
    for g in games:
        x, y, w, h = g["rect"]
        on_screen = [s for s in info["screens"] if (s[0], s[1], s[2], s[3]) == (x, y, w, h)]
        if g["caption"]:
            mode = _t("fenêtré")
        elif g["popup"] and on_screen:
            mode = _t("plein écran sans bordure (compatible)")
        elif g["popup"]:
            mode = _t("sans bordure, plus petit que l'écran (compatible)")
        else:
            mode = _t("mode d'affichage inconnu")
        add("  " + _t("« {title} » : {w}x{h} en ({x},{y}), {mode}").format(title=g["title"], w=w, h=h, x=x, y=y, mode=mode))
        el = g["elevated"]
        add("  " + _t("lancé en administrateur : {answer}").format(
            answer=_t("oui") if el else _t("non") if el is False else _t("inconnu")))
        if el:
            problems.append(_t("Le jeu tourne en administrateur : les raccourcis clavier ne marcheront que si l'overlay l'est aussi."))
    add("")
    cap, fit = info["capture"], info["fit"]
    add(_t("Capture d'écran :"))
    if cap is None:
        add("  " + _t("impossible"))
        problems.append(_t("La capture d'écran est impossible : le calage automatique ne marchera pas (calibre à la main)."))
    else:
        add("  " + _t("{w}x{h} en {ms} ms, luminosité moyenne {mean}/255, pixels bruns {brown} %").format(
            w=cap["w"], h=cap["h"], ms=cap["ms"], mean=cap["mean"], brown=cap["brown"]))
        if cap["black"]:
            problems.append(_t("La capture est toute noire (jeu en plein écran exclusif ?) : passe le jeu en fenêtre sans bordure."))
        add("")
        add(_t("Reconnaissance de la salle :"))
        if fit is None or not fit.confident:
            add("  " + _t("salle non reconnue (score {score})").format(score="-" if fit is None else f"{fit.score:.2f}"))
            problems.append(_t("La salle n'est pas reconnue : ouvre un combat du Comte, bien visible, puis relance."))
        else:
            add("  " + _t("salle reconnue : score {score}, case {cell} px, x0={x0}, y0={y0}").format(
                score=f"{fit.score:.2f}", cell=f"{2 * fit.kx:.0f}x{fit.kx:.0f}", x0=f"{fit.x0:.0f}", y0=f"{fit.y0:.0f}"))
            cfg = info["config"].get("calib")
            if cfg:
                dx, dy, dk = cfg["x0"] - fit.x0, cfg["y0"] - fit.y0, (cfg["kx"] / fit.kx - 1) * 100
                add("  " + _t("ta grille enregistrée est écartée de {dx} px (x), {dy} px (y), taille {dk} %").format(
                    dx=f"{dx:+.0f}", dy=f"{dy:+.0f}", dk=f"{dk:+.1f}"))
                if max(abs(dx), abs(dy)) > 6 or abs(dk) > 2:
                    problems.append(_t("Ta grille enregistrée est décalée : appuie sur F6 (ou « Calibrer la grille »)."))
    add("")
    add(_t("Raccourcis clavier globaux :"))
    err = info["hotkeys_error"]
    add("  " + (_t("installés sans erreur") if not err else _t("erreur : {err}").format(err=err)))
    if err:
        problems.append(_t("Les raccourcis clavier ne s'installent pas : {err}").format(err=err))
    add("")
    add(_t("Réglages :"))
    c = info["config"]
    add("  " + _t("fichier : {path} ({state})").format(path=c["path"], state=_t("inscriptible") if c["writable"] else _t("protégé")))
    if not c["writable"]:
        problems.append(_t("Le dossier des réglages est protégé : tes réglages ne seront pas gardés."))
    if c["dropped"]:
        add("  " + _t("valeurs invalides ignorées : {keys}").format(keys=", ".join(c["dropped"])))
    add("")
    add(_t("Résultat :"))
    add("  " + (_t("tout est bon pour jouer.") if not problems else _t("{n} point(s) à voir :").format(n=len(problems))))
    for p in problems:
        add("  - " + p)
    return "\n".join(out)


# --- Lancement -------------------------------------------------------------------------------------
def collect(version, config_path, config_cfg, config_sane, delay=0.0):
    """Rassemble les informations de la vraie machine (capture comprise) pour build_report."""
    import numpy as np
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QGuiApplication, QImage

    if delay:
        time.sleep(delay)
    screens = [(s.geometry().x(), s.geometry().y(), s.geometry().width(), s.geometry().height(), s.devicePixelRatio())
               for s in QGuiApplication.screens()]
    games = find_game_windows()
    # l'écran du jeu s'il est visible, sinon l'écran principal
    scr = QGuiApplication.primaryScreen()
    if games:
        gx, gy = games[0]["rect"][0] + 10, games[0]["rect"][1] + 10
        scr = QGuiApplication.screenAt(QPoint(gx, gy)) or scr
    cap, fit = None, None
    t0 = time.time()
    img = scr.grabWindow(0).toImage()
    if not img.isNull() and img.width() > 0:
        ms = int((time.time() - t0) * 1000)
        img = img.convertToFormat(QImage.Format.Format_RGB888)
        ptr = img.constBits()
        ptr.setsize(img.sizeInBytes())
        arr = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine())[:, : img.width() * 3]
        arr = arr.reshape(img.height(), img.width(), 3).copy()
        cap = {"w": img.width(), "h": img.height(), "ms": ms, "mean": int(arr.mean()), "black": bool(arr.max() < 8),
               "brown": round(float((autocal.brown_mask(arr) > 0).mean() * 100), 1)}
        fit = autocal.find(arr)
        # la grille enregistrée est en points de l'écran ; la capture en pixels
        scale = img.width() / float(scr.geometry().width())
        cal = config_sane.get("calib")
        if cal and fit is not None:
            config_sane = dict(config_sane, calib={"x0": (cal["x0"] - scr.geometry().x()) * scale, "y0": (cal["y0"] - scr.geometry().y()) * scale,
                                                  "kx": cal["kx"] * scale, "ky": cal["ky"] * scale})
    hk_error = None
    try:
        from pynput import keyboard
        probe = keyboard.GlobalHotKeys({"<f24>": lambda: None})
        probe.start()
        time.sleep(0.3)
        if not probe.is_alive():
            hk_error = "écouteur arrêté"
        probe.stop()
    except Exception as exc:
        hk_error = str(exc) or exc.__class__.__name__
    dropped = sorted(k for k in config_cfg if k not in config_sane)
    return {"version": version,
            "system": f"{platform.platform()} · Python {platform.python_version()} · {sys.platform}",
            "screens": screens, "games": games, "capture": cap, "fit": fit, "hotkeys_error": hk_error,
            "config": {"path": str(config_path), "writable": _config_writable(config_path), "calib": config_sane.get("calib"),
                       "dropped": dropped}}


def _config_writable(path):
    try:
        probe = Path(path).with_name(".harebourg-write-test")
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def run(args, version, config_path, raw_cfg, sane_cfg, notify=True):
    """--diagnose [secondes] [fichier] : écrit le rapport et renvoie son chemin (et l'annonce dans une fenêtre)."""
    from PyQt6.QtWidgets import QApplication, QMessageBox

    delay = 5.0
    out = Path(config_path).with_name("diagnostic.txt")
    for a in args:
        try:
            delay = float(a)
        except ValueError:
            out = Path(a)
    app = QApplication.instance() or QApplication([])      # noqa: F841  (doit rester référencé : la capture en a besoin)
    text = build_report(collect(version, config_path, raw_cfg, sane_cfg, delay))
    out.write_text(text + "\n", encoding="utf-8")
    if notify:
        QMessageBox.information(None, "Harebourg Overlay", _t("Rapport écrit :\n{path}").format(path=out))
    return out
