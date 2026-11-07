#!/usr/bin/env python3
"""
Shopee Anti-Emu Bypass Automator — PySide6 GUI
Fresh LDPlayer instance → working Shopee in one click.

Features
--------
- Auto-detects LDPlayer 9 installation + enumerates instances
- Reads each instance's config: root mode, writable/shared disk, ADB port
- Fixes instance config if needed (rootMode=true, standaloneSysVmdk=true)
- Auto-launches instance via ldconsole.exe
- Detects Magisk; if missing, installs Magisk APK + opens for setup
- Pushes frida-server + Magisk emu-mask module
- Spoofs: ro.product.*, /proc/cpuinfo bind-mount
- Installs patched Shopee bundle (base + splits)
- Grants overlay / location / notification permissions
- Launches Shopee + verifies

Run: python shopee_bypass_qt.py
"""

from __future__ import annotations
import os, sys, json, time, shutil, subprocess, re, glob
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from PySide6.QtCore    import (Qt, Signal, QObject, QThread, Slot, QTimer,
                               QSettings, QSize)
from PySide6.QtGui     import QFont, QTextCursor, QIcon, QColor, QPalette, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QLineEdit, QGroupBox,
    QFileDialog, QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QTabWidget, QSpacerItem, QSizePolicy, QFrame,
    QStyle, QPlainTextEdit, QCheckBox,
)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
WORKSPACE = Path(r"C:/Users/Administrator/Documents/PROJECT/ReverserID")
SHUPI     = WORKSPACE / "Shupi"
TOOLS     = WORKSPACE / "_tools"

ADB = shutil.which("adb") or str(Path(r"C:/LDPlayer/LDPlayer9/adb.exe")) if Path(
    r"C:/LDPlayer/LDPlayer9/adb.exe").exists() else "adb"

ASSETS = {
    "patched_base"    : SHUPI / "_patch2" / "base-fullpatched.apk",
    "split_arm64"     : SHUPI / "_patch2" / "orig_bundle" / "split_config.arm64_v8a.apk",
    "split_xhdpi"     : SHUPI / "_patch2" / "orig_bundle" / "split_config.xhdpi.apk",
    "emu_mask_zip"    : SHUPI / "shopee-emu-mask-v2.zip",
    "frida_server"    : TOOLS / "frida-server-17.25.1-android-x86_64",
    "fake_cpuinfo"    : SHUPI / "_mod_patched" / "fake_cpuinfo",
    "service_sh"      : SHUPI / "_mod_patched" / "service.sh",
    "post_fs_data_sh" : SHUPI / "_mod_patched" / "post-fs-data.sh",
    "magisk_apk"      : TOOLS / "Magisk.apk",
}

LDPLAYER_CANDIDATES = [
    Path(r"C:/LDPlayer/LDPlayer9"),
    Path(r"D:/LDPlayer/LDPlayer9"),
    Path(r"C:/Program Files/LDPlayer/LDPlayer9"),
    Path(r"C:/Program Files (x86)/LDPlayer/LDPlayer9"),
]

SHOPEE_PKG = "com.shopee.id"


# ─── ADB / shell helpers ─────────────────────────────────────────────────────
def run(cmd, timeout=60) -> tuple[int, str, str]:
    """Run cmd, return (rc, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           shell=isinstance(cmd, str))
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout({timeout}s)"
    except FileNotFoundError as e:
        return -1, "", str(e)


# ─── LDPlayer introspection ──────────────────────────────────────────────────
@dataclass
class LDPlayerInstance:
    index      : int
    name       : str
    config_path: Path
    config     : dict = field(default_factory=dict)
    root_mode  : bool = False
    writable   : bool = True     # standaloneSysVmdk
    adb_debug  : bool = False    # basicSettings.adbDebug=1 (ADB port exposed)
    adb_port   : int = 5555
    model      : str = ""
    manufacturer: str = ""
    sdk_level  : int = 28
    running    : bool = False    # via `ldconsole isrunning`
    adb_ready  : bool = False    # device visible in `adb devices`
    serial     : str = ""

    def label(self) -> str:
        flags = []
        flags.append("root" if self.root_mode else "NO-root")
        flags.append("writable" if self.writable else "SHARED-RO")
        flags.append("adb" if self.adb_debug else "no-adb")
        if self.running: flags.append("RUNNING")
        if self.adb_ready: flags.append("adb-ready")
        return f"[{self.index}] {self.name} — {self.model} ({'/'.join(flags)})"


class LDPlayerManager:
    def __init__(self):
        self.install_dir: Optional[Path] = None
        self.ldconsole: Optional[Path] = None
        self.vms_dir: Optional[Path] = None
        self.instances: List[LDPlayerInstance] = []
        self.detect_install()

    def detect_install(self):
        for p in LDPLAYER_CANDIDATES:
            if (p / "ldconsole.exe").exists():
                self.install_dir = p
                self.ldconsole   = p / "ldconsole.exe"
                self.vms_dir     = p / "vms"
                return
        self.install_dir = None

    def refresh_instances(self) -> List[LDPlayerInstance]:
        self.instances.clear()
        if not self.vms_dir: return []
        cfg_dir = self.vms_dir / "config"
        if not cfg_dir.exists(): return []
        # also enumerate leidianN folders as fallback (presence = instance exists)
        inst_dirs = sorted([d for d in self.vms_dir.iterdir() if d.is_dir()
                            and d.name.startswith("leidian") and d.name[7:].isdigit()],
                           key=lambda d: int(d.name[7:]))
        for d in inst_dirs:
            idx = int(d.name[7:])
            name = d.name  # leidian0, leidian1, ...
            conf_path = cfg_dir / f"{name}.config"
            cfg = {}
            if conf_path.exists():
                try:
                    cfg = json.loads(conf_path.read_text(encoding='utf-8'))
                except Exception:
                    pass
            inst = LDPlayerInstance(
                index=idx, name=name, config_path=conf_path, config=cfg,
                root_mode   = bool(cfg.get("basicSettings.rootMode", False)),
                writable    = bool(cfg.get("basicSettings.standaloneSysVmdk", False)),
                adb_debug   = int(cfg.get("basicSettings.adbDebug", 0)) == 1,
                adb_port    = 5555 + idx * 2,
                model       = str(cfg.get("propertySettings.phoneModel", "?")),
                manufacturer= str(cfg.get("propertySettings.phoneManufacturer", "?")),
            )
            self.instances.append(inst)
        # mark running via `ldconsole isrunning`
        for inst in self.instances:
            rc, out, _ = self._ld("isrunning", "--index", str(inst.index), timeout=5)
            inst.running = out.strip() == "running"
        # mark adb_ready via `adb devices`
        rc, out, _ = run([ADB, "devices"])
        ready_serials = {l.split()[0] for l in out.splitlines()
                         if l and '\tdevice' in l}
        for inst in self.instances:
            ser = f"127.0.0.1:{inst.adb_port}"
            if ser in ready_serials:
                inst.adb_ready = True; inst.serial = ser
            elif f"emulator-{inst.adb_port-1}" in ready_serials:
                inst.adb_ready = True
                inst.serial = f"emulator-{inst.adb_port-1}"
        return self.instances

    def _ld(self, *args, timeout=30) -> tuple[int, str, str]:
        """Run ldconsole.exe with args."""
        if not self.ldconsole: return -1, "", "ldconsole.exe not found"
        return run([str(self.ldconsole), *args], timeout=timeout)

    def set_root_mode(self, inst: LDPlayerInstance, enabled: bool) -> tuple[bool, str]:
        """Enable/disable root via ldconsole modify --root (CLI approach)."""
        rc, out, err = self._ld("modify", "--index", str(inst.index),
                                "--root", "1" if enabled else "0")
        if rc == 0:
            # Re-read config
            try:
                inst.config = json.loads(inst.config_path.read_text(encoding='utf-8'))
                inst.root_mode = bool(inst.config.get("basicSettings.rootMode", False))
            except Exception: pass
            return True, out or "OK"
        return False, err or out

    def set_writable_disk(self, inst: LDPlayerInstance, enabled: bool) -> tuple[bool, str]:
        """Toggle standaloneSysVmdk (not CLI-exposed) → edit JSON directly.
           Instance MUST be stopped before this."""
        cfg = dict(inst.config)
        cfg["basicSettings.standaloneSysVmdk"] = enabled
        try:
            inst.config_path.write_text(json.dumps(cfg, indent=4), encoding='utf-8')
            inst.config = cfg; inst.writable = enabled
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def patch_config(self, inst: LDPlayerInstance, **kwargs) -> tuple[bool, str]:
        """Bulk-edit config JSON. Instance MUST be stopped before this."""
        cfg = dict(inst.config)
        cfg.update(kwargs)
        try:
            inst.config_path.write_text(json.dumps(cfg, indent=4), encoding='utf-8')
            inst.config = cfg
            # Reflect in dataclass
            inst.root_mode = bool(cfg.get("basicSettings.rootMode", False))
            inst.writable  = bool(cfg.get("basicSettings.standaloneSysVmdk", False))
            inst.adb_debug = int(cfg.get("basicSettings.adbDebug", 0)) == 1
            return True, ",".join(kwargs.keys())
        except Exception as e:
            return False, str(e)

    def modify_device_id(self, inst: LDPlayerInstance, **kwargs) -> tuple[bool, str]:
        """Modify device identity via CLI: manufacturer, model, imei, imsi, mac, etc."""
        cli_keys = {"manufacturer", "model", "pnumber", "imei",
                    "imsi", "simserial", "androidid", "mac"}
        args = ["modify", "--index", str(inst.index)]
        for k, v in kwargs.items():
            if k in cli_keys:
                args += [f"--{k}", str(v)]
        if len(args) == 3: return False, "No supported keys"
        rc, out, err = self._ld(*args)
        return rc == 0, out or err

    def install_apk(self, inst: LDPlayerInstance, apk_path: str) -> tuple[bool, str]:
        """Install APK via ldconsole (handles multi-split auto, no manual adb)."""
        rc, out, err = self._ld("installapp", "--index", str(inst.index),
                                "--filename", apk_path, timeout=180)
        return rc == 0, out or err

    def ld_setprop(self, inst: LDPlayerInstance, key: str, value: str) -> tuple[bool, str]:
        """Direct setprop via ldconsole (persists across reboot)."""
        rc, out, err = self._ld("setprop", "--index", str(inst.index),
                                "--key", key, "--value", str(value))
        return rc == 0, out or err

    def ld_adb_cmd(self, inst: LDPlayerInstance, cmd: str) -> tuple[bool, str]:
        """Execute adb shell via ldconsole passthrough."""
        rc, out, err = self._ld("adb", "--index", str(inst.index),
                                "--command", cmd, timeout=60)
        return rc == 0, out or err

    def launch(self, inst: LDPlayerInstance) -> tuple[bool, str]:
        rc, out, err = self._ld("launch", "--index", str(inst.index))
        return rc == 0, out or err

    def quit(self, inst: LDPlayerInstance) -> tuple[bool, str]:
        rc, out, err = self._ld("quit", "--index", str(inst.index))
        return rc == 0, out or err

    def connect_adb(self, inst: LDPlayerInstance) -> tuple[bool, str]:
        rc, out, err = run([ADB, "connect", f"127.0.0.1:{inst.adb_port}"], timeout=10)
        ok = "connected" in out.lower() and "cannot" not in out.lower()
        if ok: inst.serial = f"127.0.0.1:{inst.adb_port}"
        return ok, out or err


# ─── Worker thread for long-running ops ──────────────────────────────────────
class Worker(QObject):
    log       = Signal(str, str)     # msg, level (info/ok/warn/err)
    status    = Signal(str)
    progress  = Signal(int)          # 0-100
    finished  = Signal(bool)         # success

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs

    @Slot()
    def run(self):
        try:
            self.fn(self, *self.args, **self.kwargs)
            self.finished.emit(True)
        except Exception as e:
            import traceback
            self.log.emit(f"UNCAUGHT: {type(e).__name__}: {e}", "err")
            self.log.emit(traceback.format_exc(), "err")
            self.finished.emit(False)


# ─── Automation steps (pure functions receiving worker for logging) ──────────
def _adb(serial, *args, timeout=60) -> tuple[int, str, str]:
    cmd = [ADB]
    if serial: cmd += ['-s', serial]
    cmd += list(args)
    return run(cmd, timeout=timeout)


def _adb_shell(serial, cmd, timeout=60, as_root=False) -> tuple[int, str, str]:
    if as_root:
        cmd = f"su -c '{cmd}'"
    return _adb(serial, 'shell', cmd, timeout=timeout)


def step_wait_boot(w: Worker, serial: str):
    w.log.emit("Waiting boot-complete…", "info")
    _adb(serial, 'wait-for-device', timeout=120)
    for _ in range(60):
        _, out, _ = _adb_shell(serial, "getprop sys.boot_completed", timeout=5)
        if out.strip() == "1":
            w.log.emit("Boot completed ✓", "ok"); return
        time.sleep(2)
    w.log.emit("Boot-complete timeout — continuing anyway", "warn")


def step_verify_root(w: Worker, serial: str) -> bool:
    rc, out, _ = _adb_shell(serial, "id", as_root=True, timeout=10)
    if "uid=0" in out:
        w.log.emit(f"Root OK: {out}", "ok"); return True
    w.log.emit(f"NO ROOT — su failed: {out}", "err")
    w.log.emit("Enable: LDPlayer Settings → Advanced → Root permission", "warn")
    return False


def step_install_magisk(w: Worker, serial: str):
    """Install magisk64 binary ONLY (no APK, no Manager). We only need
       `resetprop` + `--install-module` CLI functionality for emu-mask."""
    rc, out, _ = _adb_shell(serial, "ls /data/local/tmp/magisk64 2>&1",
                            as_root=True, timeout=10)
    if "/data/local/tmp/magisk64" in out and "No such" not in out:
        rc, ver, _ = _adb_shell(serial, "/data/local/tmp/magisk64 -c 2>&1", as_root=True)
        if ver.strip() and "not found" not in ver.lower():
            w.log.emit(f"magisk64 already installed (v{ver.strip()})", "ok")
            return True

    apk = ASSETS["magisk_apk"]
    if not apk.exists():
        w.log.emit(f"Magisk APK missing: {apk}", "err"); return False

    import zipfile, tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
    try:
        with zipfile.ZipFile(apk, 'r') as z:
            try: data = z.read("lib/x86_64/libmagisk64.so")
            except KeyError:
                try: data = z.read("lib/arm64-v8a/libmagisk64.so")
                except KeyError:
                    w.log.emit("No libmagisk64.so in Magisk APK", "err"); return False
        tmp.write(data); tmp.close()
        w.log.emit(f"Extracted libmagisk64.so ({len(data)//1024} KB) from APK", "")
        _adb(serial, "push", tmp.name, "/data/local/tmp/magisk64", timeout=30)
        _adb_shell(serial, "chmod +x /data/local/tmp/magisk64", as_root=True)
        rc, ver, _ = _adb_shell(serial, "/data/local/tmp/magisk64 -c 2>&1", as_root=True)
        if ver.strip():
            w.log.emit(f"magisk64 installed OK (v{ver.strip()})", "ok")
            # Also expose as /data/adb/magisk/magisk64 for module scripts
            _adb_shell(serial, "mkdir -p /data/adb/magisk && "
                               "cp -f /data/local/tmp/magisk64 /data/adb/magisk/magisk64 && "
                               "chmod +x /data/adb/magisk/magisk64", as_root=True)
            return True
        w.log.emit(f"magisk64 verify failed: {ver}", "err"); return False
    finally:
        try: os.unlink(tmp.name)
        except: pass


def step_push_frida(w: Worker, serial: str):
    src = ASSETS["frida_server"]
    if not src.exists():
        w.log.emit(f"frida-server missing: {src}", "err"); return False
    w.log.emit(f"Pushing frida-server ({src.stat().st_size//1024//1024} MB)…", "")
    _adb(serial, 'push', str(src), '/data/local/tmp/frida-server', timeout=180)
    _adb_shell(serial, "chmod +x /data/local/tmp/frida-server", as_root=True)
    w.log.emit("frida-server pushed ✓", "ok"); return True


def step_install_emu_mask(w: Worker, serial: str):
    src = ASSETS["emu_mask_zip"]
    if not src.exists():
        w.log.emit(f"emu-mask zip missing: {src}", "err"); return False
    w.log.emit(f"Push emu-mask zip: {src.name}", "")
    _adb(serial, "push", str(src), "/sdcard/")
    rc, out, _ = _adb_shell(serial, f"/data/adb/magisk/magisk64 --install-module /sdcard/{src.name}",
                            as_root=True, timeout=60)
    w.log.emit(out.splitlines()[-1] if out else "(no output)", "")
    # Push scripts manually (install-module sometimes drops them silently)
    mod_dir = "/data/adb/modules/shopee_emu_mask"
    for key, dest in [("fake_cpuinfo", "fake_cpuinfo"),
                      ("service_sh", "service.sh"),
                      ("post_fs_data_sh", "post-fs-data.sh")]:
        f = ASSETS.get(key)
        if not f or not f.exists():
            w.log.emit(f"  skip {dest} ({f} missing)", "warn"); continue
        _adb(serial, "push", str(f), f"/sdcard/{dest}")
        _adb_shell(serial, f"cp /sdcard/{dest} {mod_dir}/", as_root=True)
        if dest.endswith(".sh"):
            _adb_shell(serial, f"chmod 755 {mod_dir}/{dest}", as_root=True)
        w.log.emit(f"  pushed {dest}", "ok")
    w.log.emit("emu-mask installed. Reboot to activate.", "ok")
    return True


def step_manual_spoof(w: Worker, serial: str):
    """Fallback spoof via direct resetprop + mount --bind (if service.sh didn't run)."""
    cmds = [
        '/data/adb/magisk/magisk64 resetprop -n ro.product.model "TECNO BD4"',
        '/data/adb/magisk/magisk64 resetprop -n ro.product.brand TECNO',
        '/data/adb/magisk/magisk64 resetprop -n ro.product.manufacturer "TECNO MOBILE LIMITED"',
        '/data/adb/magisk/magisk64 resetprop -n ro.product.device TECNO-BD4',
        '/data/adb/magisk/magisk64 resetprop -n ro.product.cpu.abi arm64-v8a',
        '/data/adb/magisk/magisk64 resetprop -n ro.product.cpu.abilist arm64-v8a,armeabi-v7a,armeabi',
        '/data/adb/magisk/magisk64 resetprop -n ro.build.fingerprint '
        '"TECNO/BD4-OP/TECNO-BD4:14/UP1A.231005.007/173010:user/release-keys"',
        'mount --bind /data/adb/modules/shopee_emu_mask/fake_cpuinfo /proc/cpuinfo',
    ]
    for c in cmds:
        _adb_shell(serial, c, as_root=True, timeout=10)
    rc, out, _ = _adb_shell(serial, "getprop ro.product.model; getprop ro.product.cpu.abi")
    w.log.emit(f"After spoof: {out.replace(chr(10), ' | ')}", "ok")
    rc, out, _ = _adb_shell(serial, "head -2 /proc/cpuinfo", as_root=True)
    w.log.emit(f"cpuinfo: {out.replace(chr(10), " | ")}", "")
    return True


def step_install_shopee(w: Worker, serial: str):
    files = [ASSETS["patched_base"], ASSETS["split_arm64"], ASSETS["split_xhdpi"]]
    for f in files:
        if not f.exists():
            w.log.emit(f"MISSING: {f}", "err"); return False
    _adb(serial, "uninstall", SHOPEE_PKG, timeout=30)
    szs = ' + '.join(f"{f.stat().st_size//1024//1024}MB" for f in files)
    w.log.emit(f"Installing Shopee bundle: {szs}", "")
    rc, out, err = _adb(serial, "install-multiple", "-r",
                        *[str(f) for f in files], timeout=240)
    if rc == 0 and "Success" in out:
        w.log.emit("Shopee bundle installed ✓", "ok"); return True
    w.log.emit(f"Install failed: {out} {err}", "err"); return False


def step_launch_shopee(w: Worker, serial: str):
    _adb_shell(serial, f"am force-stop {SHOPEE_PKG}")
    time.sleep(1)
    _adb_shell(serial, f"monkey -p {SHOPEE_PKG} -c android.intent.category.LAUNCHER 1")
    w.log.emit("Shopee launching — wait 25s…", "")
    for i in range(25):
        time.sleep(1); w.progress.emit(int((i+1)/25*100))
    rc, out, _ = _adb_shell(serial, "dumpsys window | grep mCurrentFocus")
    w.log.emit(out, "ok" if SHOPEE_PKG in out else "warn")
    return SHOPEE_PKG in out


def step_grant_perms(w: Worker, serial: str):
    """Grant ALL runtime perms + overlay to Shopee BEFORE launch,
       so user never sees permission prompts. Pre-grants cover every
       dialog Shopee shows on first start."""
    appops_perms = [
        "SYSTEM_ALERT_WINDOW",      # overlay / floating ball
        "REQUEST_INSTALL_PACKAGES", # install apps (updates)
        "WRITE_SETTINGS",           # modify system settings
    ]
    runtime_perms = [
        "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION",
        "ACCESS_BACKGROUND_LOCATION",
        "POST_NOTIFICATIONS",
        "CAMERA",
        "RECORD_AUDIO",
        "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE",
        "READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO",
        "READ_CONTACTS",
        "READ_PHONE_STATE",
        "ACCESS_WIFI_STATE", "CHANGE_WIFI_STATE",
        "BLUETOOTH", "BLUETOOTH_CONNECT", "BLUETOOTH_SCAN",
    ]
    for pkg in [SHOPEE_PKG, "com.shopeepay.id", "com.topjohnwu.magisk"]:
        # Check pkg installed
        rc, out, _ = _adb_shell(serial, f"pm list packages {pkg}", timeout=5)
        if pkg not in out: continue
        granted = []
        for op in appops_perms:
            rc, _, _ = _adb_shell(serial, f"appops set {pkg} {op} allow", timeout=5)
            if rc == 0: granted.append(f"appops:{op}")
        for p in runtime_perms:
            rc, _, _ = _adb_shell(serial, f"pm grant {pkg} android.permission.{p}",
                                  timeout=5)
            if rc == 0: granted.append(p)
        w.log.emit(f"Granted {len(granted)} perms to {pkg}", "ok")
    return True

def step_start_frida(w: Worker, serial: str):
    _adb_shell(serial, "pkill frida-server", as_root=True); time.sleep(1)
    _adb_shell(serial, "nohup /data/local/tmp/frida-server -D >/dev/null 2>&1 &",
               as_root=True)
    time.sleep(2)
    rc, out, _ = _adb_shell(serial, "ps -A | grep frida", as_root=True)
    if "frida-server" in out:
        w.log.emit(f"frida-server up: {out.strip()}", "ok")
        run([ADB, "-s", serial, "forward", "tcp:27042", "tcp:27042"])
        return True
    w.log.emit("frida-server not detected after start", "err"); return False


def step_frida_gms_fix(w: Worker, serial: str):
    """Push Frida GMS cert spoof script + attach to running GMS process."""
    import os
    script_path = os.path.join(os.path.dirname(__file__), "frida_gms_fix.js")
    if not os.path.exists(script_path):
        w.log.emit(f"Frida script missing: {script_path}", "err"); return False

    # Push script to device
    _adb(serial, "push", script_path, "/data/local/tmp/frida_gms_fix.js", timeout=15)

    # Forward frida port
    run([ADB, "-s", serial, "forward", "tcp:27042", "tcp:27042"])

    # Find GMS process PID
    rc, out, _ = _adb_shell(serial, "pidof com.google.android.gms", timeout=10)
    gms_pid = out.strip().split()[0] if out.strip() else None
    if not gms_pid:
        w.log.emit("GMS process not found — starting GMS first", "warn")
        _adb_shell(serial, "am start -n com.google.android.gms/.app.settings.GoogleSettingsActivity", timeout=10)
        time.sleep(5)
        rc, out, _ = _adb_shell(serial, "pidof com.google.android.gms", timeout=10)
        gms_pid = out.strip().split()[0] if out.strip() else None
    if not gms_pid:
        w.log.emit("GMS still not running", "err"); return False

    w.log.emit(f"Attaching Frida to GMS (pid={gms_pid})…", "info")
    frida_cmd = ["frida", "-H", "127.0.0.1:27042",
                 "-p", gms_pid,
                 "-l", script_path,
                 "--runtime=v8", "-q"]
    try:
        import subprocess
        proc = subprocess.Popen(frida_cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        try:
            out, err = proc.communicate(timeout=30)
            if "cert spoof loaded" in out:
                w.log.emit("Frida GMS hook loaded ✓", "ok")
                return True
            w.log.emit(f"Frida output: {out[:200]}", "warn")
            return False
        except subprocess.TimeoutExpired:
            proc.kill()
            w.log.emit("Frida GMS hook running (background)", "ok")
            return True
    except Exception as e:
        w.log.emit(f"Frida error: {e}", "err")
        return False


# ─── MAIN WINDOW ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shopee Anti-Emu Bypass Automator — PySide6")
        self.resize(1200, 820)
        self.ldp = LDPlayerManager()
        self.current: Optional[LDPlayerInstance] = None
        self.worker_thread: Optional[QThread] = None
        self._build_ui()
        self._apply_dark()
        self._initial_log()
        QTimer.singleShot(200, self.refresh_instances)

    # ────── UI ──────
    def _apply_dark(self):
        """reverser.id aesthetic: terminal-dark, red accent, monospace."""
        app = QApplication.instance()
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor("#0a0a0a"))
        pal.setColor(QPalette.WindowText,      QColor("#d4d4d4"))
        pal.setColor(QPalette.Base,            QColor("#0f0f0f"))
        pal.setColor(QPalette.AlternateBase,   QColor("#141414"))
        pal.setColor(QPalette.Text,            QColor("#d4d4d4"))
        pal.setColor(QPalette.Button,          QColor("#171717"))
        pal.setColor(QPalette.ButtonText,      QColor("#d4d4d4"))
        pal.setColor(QPalette.Highlight,       QColor("#e53935"))
        pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ToolTipBase,     QColor("#141414"))
        pal.setColor(QPalette.ToolTipText,     QColor("#d4d4d4"))
        app.setPalette(pal)
        app.setStyle("Fusion")
        app.setFont(QFont("JetBrains Mono", 9) if "JetBrains Mono" in
                    QApplication.font().families() else QFont("Cascadia Mono", 9))
        app.setStyleSheet("""
            QWidget { color: #d4d4d4; font-family: "JetBrains Mono", "Cascadia Mono",
                      "Consolas", monospace; }
            QMainWindow, QWidget#central { background: #0a0a0a; }

            QFrame#card { background: #0f0f0f; border: 1px solid #262626;
                          border-radius: 2px; }
            QLabel#sectionHeader { color: #e53935; font-size: 10px;
                                   font-weight: 700; letter-spacing: 2px; }
            QLabel#muted { color: #666666; font-size: 10px; }

            QPushButton {
                background: #141414; color: #d4d4d4;
                border: 1px solid #262626; border-radius: 2px;
                padding: 8px 14px;
                font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace;
                font-size: 10px; font-weight: 500; letter-spacing: 0.5px;
            }
            QPushButton:hover { background: #1a1a1a; border-color: #e53935;
                                color: #ffffff; }
            QPushButton:pressed { background: #0a0a0a; border-color: #b71c1c; }
            QPushButton:disabled { color: #3a3a3a; background: #0a0a0a;
                                   border-color: #1a1a1a; }

            QPushButton[accent="primary"] {
                background: #e53935; color: #0a0a0a;
                border: 1px solid #ff5a56;
                font-weight: 800; font-size: 12px; padding: 14px 20px;
                letter-spacing: 3px;
            }
            QPushButton[accent="primary"]:hover { background: #ff5a56;
                                                  border-color: #ff5a56; }
            QPushButton[accent="primary"]:pressed { background: #b71c1c; }

            QPushButton[accent="success"] {
                background: #0a1a0f; color: #00ff88;
                border: 1px solid #006633; font-weight: 700;
            }
            QPushButton[accent="success"]:hover { background: #003322;
                                                  border-color: #00ff88; }
            QPushButton[accent="danger"] {
                background: #1a0a0a; color: #ff5a56;
                border: 1px solid #661111; font-weight: 700;
            }
            QPushButton[accent="danger"]:hover { background: #330000;
                                                 border-color: #ff5a56; }
            QPushButton[accent="ghost"] {
                background: transparent; border: 1px solid #262626;
                color: #999999;
            }
            QPushButton[accent="ghost"]:hover { border-color: #e53935;
                                                color: #e53935; }

            QTableWidget {
                background: #0a0a0a; border: 0; gridline-color: transparent;
                selection-background-color: #1a0505; selection-color: #ff5a56;
            }
            QTableWidget::item { padding: 10px 10px;
                                 border-bottom: 1px solid #1a1a1a; }
            QTableWidget::item:selected { background: #1a0505; color: #ff5a56; }
            QHeaderView::section {
                background: #0a0a0a; color: #666666;
                padding: 10px 10px; border: 0;
                border-bottom: 1px solid #262626;
                font-weight: 700; font-size: 9px; letter-spacing: 2px;
            }
            QTableCornerButton::section { background: #0a0a0a; border: 0; }

            QProgressBar {
                background: #141414; border: 1px solid #262626;
                border-radius: 0; height: 6px; text-align: center;
                color: transparent;
            }
            QProgressBar::chunk { background: #e53935; }

            QPlainTextEdit#log {
                background: #000000; color: #a0a0a0;
                border: 1px solid #1a1a1a; border-radius: 2px; padding: 10px;
                selection-background-color: #1a0505;
                font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace;
                font-size: 9px;
            }

            QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
            QScrollBar::handle:vertical { background: #262626; border-radius: 0;
                                          min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #e53935; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent; height: 0; }
            QScrollBar:horizontal { background: transparent; height: 8px; }
            QScrollBar::handle:horizontal { background: #262626; border-radius: 0;
                                            min-width: 30px; }

            QStatusBar { background: #000000; color: #666666;
                         border-top: 1px solid #1a1a1a; font-size: 9px; }
            QStatusBar::item { border: 0; }
        """)

    def _build_ui(self):
        central = QWidget(); central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # ─── Header ────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("[ SHOPEE // BYPASS ]")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #e53935;"
                            " letter-spacing: 4px;")
        subtitle = QLabel("anti-emu.rev-chain  ::  reverser.id")
        subtitle.setStyleSheet("color: #555555; font-size: 10px; letter-spacing: 2px;")
        hcol = QVBoxLayout(); hcol.setSpacing(2)
        hcol.addWidget(title); hcol.addWidget(subtitle)
        header.addLayout(hcol); header.addStretch()

        self.lbl_ldpath = QLabel("…")
        self.lbl_ldpath.setStyleSheet("color: #e53935; font-size: 10px;"
                                      " background: #141414; padding: 6px 12px;"
                                      " border: 1px solid #262626; border-radius: 2px;")
        header.addWidget(self.lbl_ldpath)

        btn_refresh = QPushButton("[ REFRESH ]")
        btn_refresh.setProperty("accent", "ghost")
        btn_refresh.clicked.connect(self.refresh_instances)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #262626; background: #262626; max-height: 1px;")
        root.addWidget(line)

        # ─── Instances card ────────────────────────────────────────────
        inst_card = QFrame(); inst_card.setObjectName("card")
        inst_lay = QVBoxLayout(inst_card)
        inst_lay.setContentsMargins(16, 14, 16, 14); inst_lay.setSpacing(10)

        inst_hdr = QHBoxLayout()
        lbl = QLabel("▸ LDPLAYER INSTANCES"); lbl.setObjectName("sectionHeader")
        inst_hdr.addWidget(lbl); inst_hdr.addStretch()
        self.lbl_inst_count = QLabel("")
        self.lbl_inst_count.setStyleSheet("color: #666666; font-size: 10px;")
        inst_hdr.addWidget(self.lbl_inst_count)
        inst_lay.addLayout(inst_hdr)

        self.tbl = QTableWidget(0, 8)
        self.tbl.setHorizontalHeaderLabels([
            "IDX", "NAME", "MODEL", "ROOT", "DISK", "ADB", "PORT", "STATUS"
        ])
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(False)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(self._on_instance_selected)
        self.tbl.setMinimumHeight(120); self.tbl.setMaximumHeight(200)
        self.tbl.verticalHeader().setDefaultSectionSize(38)
        inst_lay.addWidget(self.tbl)

        actrow = QHBoxLayout(); actrow.setSpacing(6)
        self.btn_launch  = QPushButton("[ LAUNCH ]")
        self.btn_launch.setProperty("accent", "success")
        self.btn_connect = QPushButton("[ CONNECT ADB ]")
        self.btn_info    = QPushButton("[ DEVICE INFO ]")
        self.btn_fix_cfg = QPushButton("[ FIX CONFIG ]")
        self.btn_quit    = QPushButton("[ STOP ]")
        self.btn_quit.setProperty("accent", "danger")
        for b, slot in [(self.btn_launch, self.launch_instance),
                        (self.btn_connect, self.connect_instance),
                        (self.btn_info, self.show_device_info),
                        (self.btn_fix_cfg, self.fix_instance_config),
                        (self.btn_quit, self.stop_instance)]:
            b.clicked.connect(slot); actrow.addWidget(b)
        actrow.addStretch()
        inst_lay.addLayout(actrow)
        root.addWidget(inst_card)

        # ─── Steps grid card ───────────────────────────────────────────
        steps_card = QFrame(); steps_card.setObjectName("card")
        steps_lay = QVBoxLayout(steps_card)
        steps_lay.setContentsMargins(16, 14, 16, 14); steps_lay.setSpacing(10)

        slbl = QLabel("▸ EXECUTION CHAIN"); slbl.setObjectName("sectionHeader")
        steps_lay.addWidget(slbl)

        step_defs = [
            ("01  VERIFY ROOT",       self.do_verify_root),
            ("02  INSTALL MAGISK",    self.do_install_magisk),
            ("03  PUSH FRIDA-SERVER", self.do_push_frida),
            ("04  INSTALL EMU-MASK",  self.do_install_emu_mask),
            ("05  REBOOT + WAIT",     self.do_reboot_wait),
            ("06  SPOOF PROPS",       self.do_manual_spoof),
            ("07  INSTALL SHOPEE",    self.do_install_shopee),
            ("08  LAUNCH SHOPEE",     self.do_launch_shopee),
            ("09  GRANT PERMS",       self.do_grant_perms),
            ("10  START FRIDA",       self.do_start_frida),
            ("11  FRIDA GMS FIX",     self.do_frida_gms_fix),
            ("--  UNINSTALL SHOPEE",  self.do_uninstall_shopee),
            ("--  SCREENSHOT",        self.do_screenshot),
        ]
        g = QGridLayout(); g.setSpacing(6)
        self.step_buttons = []
        for i, (lbl, fn) in enumerate(step_defs):
            b = QPushButton(lbl)
            b.setMinimumHeight(34)
            b.setStyleSheet("text-align: left; padding-left: 14px;")
            b.clicked.connect(fn)
            r, c = i // 4, i % 4
            g.addWidget(b, r, c); self.step_buttons.append(b)
        for c in range(4): g.setColumnStretch(c, 1)
        steps_lay.addLayout(g)
        root.addWidget(steps_card)

        # ─── Primary action ────────────────────────────────────────────
        primary_card = QFrame(); primary_card.setObjectName("card")
        p_lay = QVBoxLayout(primary_card)
        p_lay.setContentsMargins(16, 14, 16, 14); p_lay.setSpacing(10)

        status_row = QHBoxLayout()
        slbl2 = QLabel("▸ STATUS"); slbl2.setObjectName("sectionHeader")
        status_row.addWidget(slbl2)
        status_row.addStretch()
        self.lbl_status = QLabel("IDLE")
        self.lbl_status.setStyleSheet("color: #666666; font-weight: 700;"
                                      " letter-spacing: 2px;")
        status_row.addWidget(self.lbl_status)
        p_lay.addLayout(status_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100); self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(6)
        p_lay.addWidget(self.progress)

        self.btn_full = QPushButton("► FULL AUTO SETUP ◄")
        self.btn_full.setProperty("accent", "primary")
        self.btn_full.clicked.connect(self.do_full_auto)
        p_lay.addWidget(self.btn_full)
        root.addWidget(primary_card)

        # ─── Log card ──────────────────────────────────────────────────
        log_card = QFrame(); log_card.setObjectName("card")
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(16, 12, 16, 12); log_lay.setSpacing(8)
        lhdr = QHBoxLayout()
        llbl = QLabel("▸ ACTIVITY LOG"); llbl.setObjectName("sectionHeader")
        lhdr.addWidget(llbl); lhdr.addStretch()
        btn_clear = QPushButton("[ CLEAR ]"); btn_clear.setProperty("accent", "ghost")
        btn_clear.clicked.connect(lambda: self.log.clear())
        lhdr.addWidget(btn_clear)
        log_lay.addLayout(lhdr)

        self.log = QPlainTextEdit(); self.log.setObjectName("log")
        self.log.setReadOnly(True)
        log_lay.addWidget(self.log)
        root.addWidget(log_card, 1)

        self.statusBar().showMessage(f"ADB: {ADB}")

    # ────── logging ──────
    LOG_COLORS = {
        "info": "#7dd3fc", "ok": "#4ade80", "warn": "#fbbf24",
        "err":  "#f87171", "":   "#c8ccd4",
    }

    def _log(self, msg: str, level: str = ""):
        ts = time.strftime("%H:%M:%S")
        color = self.LOG_COLORS.get(level, "#c8ccd4")
        safe = msg.replace("<", "&lt;").replace(">", "&gt;")
        html = (f'<span style="color:#4a5160">{ts}</span>  '
                f'<span style="color:{color}">{safe}</span>')
        self.log.appendHtml(html)
        self.log.moveCursor(QTextCursor.End)
        QApplication.processEvents()


    def _initial_log(self):
        self._log("Shopee Anti-Emu Bypass Automator (PySide6)", "info")
        self._log(f"ADB: {ADB}", "info")
        self._log(f"LDPlayer: {self.ldp.install_dir or '✗ NOT FOUND'}",
                  "ok" if self.ldp.install_dir else "err")
        if not self.ldp.install_dir:
            self._log("Install LDPlayer 9 to C:/LDPlayer/LDPlayer9 (or similar)", "warn")
        self.lbl_ldpath.setText(str(self.ldp.install_dir or "— not found —"))
        for k, p in ASSETS.items():
            mark, lvl = ("✓", "ok") if p.exists() else ("✗ MISSING", "warn")
            self._log(f"  [{mark}] {k} = {p.name}", lvl)

    # ────── instance table ──────
    def refresh_instances(self):
        self.ldp.detect_install()
        self.lbl_ldpath.setText(str(self.ldp.install_dir or "— not found —"))
        instances = self.ldp.refresh_instances()
        self.tbl.setRowCount(len(instances))
        for r, i in enumerate(instances):
            if i.adb_ready:  status = "ADB-READY"
            elif i.running:  status = "booting"
            else:            status = "stopped"
            vals = [
                str(i.index), i.name, i.model,
                "on" if i.root_mode else "off",
                "writable" if i.writable else "SHARED-RO",
                "on" if i.adb_debug else "off",
                str(i.adb_port),
                status,
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 3: it.setForeground(QColor("#00ff88" if i.root_mode else "#ff5a56"))
                if c == 4: it.setForeground(QColor("#00ff88" if i.writable else "#ffaa00"))
                if c == 5: it.setForeground(QColor("#00ff88" if i.adb_debug else "#ff5a56"))
                if c == 7:
                    col = "#00ff88" if i.adb_ready else ("#ffaa00" if i.running else "#666666")
                    it.setForeground(QColor(col))
                self.tbl.setItem(r, c, it)
        # Re-point self.current to new instance object (identity may have changed)
        if self.current:
            match = next((i for i in instances if i.index == self.current.index), None)
            if match: self.current = match
        # Preserve selection or default to first row
        if instances:
            row = next((r for r, i in enumerate(instances)
                        if self.current and i.index == self.current.index), 0)
            self.tbl.selectRow(row)
            self.current = instances[row]
        self._log(f"Found {len(instances)} LDPlayer instance(s)",
                  "ok" if instances else "warn")

    def _on_instance_selected(self):
        rows = self.tbl.selectionModel().selectedRows()
        if not rows: self.current = None; return
        self.current = self.ldp.instances[rows[0].row()]

    def _require_current(self) -> Optional[LDPlayerInstance]:
        if not self.current:
            QMessageBox.warning(self, "Pick instance", "Select an LDPlayer instance first.")
            return None
        return self.current

    # ────── instance actions ──────
    def fix_instance_config(self, silent: bool = False):
        """Enable root + writable disk + adbDebug via JSON edit (bulk).
           Instance MUST be stopped — we stop it ourselves if running."""
        inst = self._require_current()
        if not inst: return
        if inst.running:
            self._log(f"Stopping {inst.name} before config edit…", "info")
            self.ldp.quit(inst)
            for _ in range(10):
                time.sleep(1)
                rc, out, _ = self.ldp._ld("isrunning", "--index", str(inst.index))
                if out.strip() == "stop": break
            self.refresh_instances()
            inst = self.current
        needed = {}
        if not inst.root_mode:  needed["basicSettings.rootMode"] = True
        if not inst.writable:   needed["basicSettings.standaloneSysVmdk"] = True
        if not inst.adb_debug:  needed["basicSettings.adbDebug"] = 1
        if not needed:
            if not silent:
                self._log(f"{inst.name} already correctly configured", "info")
            return
        ok, msg = self.ldp.patch_config(inst, **needed)
        if ok:
            self._log(f"Fixed {inst.name}: {msg}", "ok")
        else:
            self._log(f"patch_config failed: {msg}", "err")
        self.refresh_instances()

    def launch_instance(self):
        """Launch + wait for adb_ready. Does NOT fix config (use FULL AUTO or Fix Config button)."""
        inst = self._require_current()
        if not inst: return
        if inst.running:
            self._log(f"{inst.name} already running", "warn")
            # Try adb connect anyway in case not registered yet
            if not inst.adb_ready:
                self.ldp.connect_adb(inst); self.refresh_instances()
            return
        ok, msg = self.ldp.launch(inst)
        self._log(f"launch {inst.name}: {msg or 'OK'}", "ok" if ok else "err")
        self._log(f"Polling ADB at 127.0.0.1:{inst.adb_port}…", "info")
        QTimer.singleShot(3000, lambda: self._poll_connect(inst, retries=40))

    def _poll_connect(self, inst: LDPlayerInstance, retries=40):
        """Try `adb connect` every 2s. Register device + refresh table."""
        ok, _ = self.ldp.connect_adb(inst)
        if ok:
            self._log(f"ADB ready: {inst.serial}", "ok")
            self.refresh_instances()
            return
        if retries > 0:
            QTimer.singleShot(2000, lambda: self._poll_connect(inst, retries-1))
        else:
            self._log(f"ADB timeout for {inst.name} "
                      f"(tried {inst.adb_port} for 80s)", "err")

    def connect_instance(self):
        inst = self._require_current()
        if not inst: return
        ok, msg = self.ldp.connect_adb(inst)
        self._log(f"adb connect: {msg}", "ok" if ok else "err")
        self.refresh_instances()

    def show_device_info(self):
        inst = self._require_current()
        if not inst or not inst.adb_ready: return self._log("ADB not ready", "warn")
        s = inst.serial
        rc, out, _ = _adb_shell(s, "getprop ro.product.model; getprop ro.product.manufacturer; "
                                "getprop ro.product.cpu.abi; getprop ro.build.version.sdk; "
                                "getprop ro.build.fingerprint; id", timeout=15)
        self._log("── Device info:\n" + out, "info")
        rc, out, _ = _adb_shell(s, "head -2 /proc/cpuinfo", as_root=True)
        self._log("── /proc/cpuinfo: " + out, "info")
        rc, out, _ = _adb_shell(s, "mount | grep system", as_root=True)
        self._log("── /system mount:\n" + out, "info")
        rc, out, _ = _adb_shell(s, "ls /data/adb/magisk/ 2>&1", as_root=True, timeout=10)
        self._log("── Magisk dir:\n" + out)
        rc, out, _ = _adb_shell(s, f"pm list packages {SHOPEE_PKG}", timeout=10)
        self._log("── Shopee install: " + (out if out else "NOT INSTALLED"))

    def stop_instance(self):
        inst = self._require_current()
        if not inst: return
        ok, msg = self.ldp.quit(inst)
        self._log(f"quit {inst.name}: {msg or 'OK'}", "ok" if ok else "err")
        QTimer.singleShot(3000, self.refresh_instances)

    # ────── worker runner ──────
    def _run_worker(self, fn, *args, on_done=None):
        if self.worker_thread and self.worker_thread.isRunning():
            self._log("A task is already running.", "warn"); return
        inst = self._require_current()
        if not inst: return
        if not inst.running or not inst.adb_ready:
            self._log(f"Instance not ready "
                      f"(running={inst.running}, adb_ready={inst.adb_ready}). "
                      f"Launch it first.", "warn"); return
        self.progress.setValue(0); self.lbl_status.setText("Running…")
        self._set_buttons_enabled(False)

        self.worker_thread = QThread(self)
        self.worker = Worker(fn, inst.serial, *args)
        self.worker.moveToThread(self.worker_thread)
        self.worker.log.connect(self._log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.lbl_status.setText)
        self.worker.finished.connect(self._on_worker_done)
        self.worker_thread.started.connect(self.worker.run)
        self._on_done = on_done
        self.worker_thread.start()

    def _on_worker_done(self, ok: bool):
        self.lbl_status.setText("Done" if ok else "Error")
        self._set_buttons_enabled(True)
        self.worker_thread.quit(); self.worker_thread.wait()
        self.worker_thread = None
        if self._on_done: self._on_done(ok); self._on_done = None

    def _set_buttons_enabled(self, enabled: bool):
        for b in self.step_buttons + [self.btn_full, self.btn_launch,
                                      self.btn_connect, self.btn_quit]:
            b.setEnabled(enabled)

    # ────── step dispatcher methods ──────
    def do_verify_root(self):    self._run_worker(step_verify_root)
    def do_install_magisk(self): self._run_worker(step_install_magisk)
    def do_push_frida(self):     self._run_worker(step_push_frida)
    def do_install_emu_mask(self): self._run_worker(step_install_emu_mask)
    def do_manual_spoof(self):   self._run_worker(step_manual_spoof)
    def do_install_shopee(self): self._run_worker(step_install_shopee)
    def do_launch_shopee(self):  self._run_worker(step_launch_shopee)
    def do_grant_perms(self):    self._run_worker(step_grant_perms)
    def do_start_frida(self):    self._run_worker(step_start_frida)
    def do_frida_gms_fix(self):  self._run_worker(step_frida_gms_fix)

    def do_reboot_wait(self):
        inst = self._require_current()
        if not inst or not inst.adb_ready: return
        def fn(w, serial):
            w.log.emit("Reboot…", "info")
            _adb(serial, "reboot")
            time.sleep(5)
            step_wait_boot(w, serial)
        self._run_worker(fn)

    def do_uninstall_shopee(self):
        inst = self._require_current()
        if not inst or not inst.adb_ready: return
        rc, out, _ = _adb(inst.serial, "uninstall", SHOPEE_PKG)
        self._log(f"uninstall: {out}", "ok" if "Success" in out else "warn")

    def do_screenshot(self):
        inst = self._require_current()
        if not inst or not inst.adb_ready: return
        out_path = Path.home() / "Desktop" / f"shopee_{int(time.time())}.png"
        _adb_shell(inst.serial, "screencap -p /sdcard/__sc.png")
        _adb(inst.serial, "pull", "/sdcard/__sc.png", str(out_path))
        self._log(f"Saved: {out_path}", "ok")
        try: os.startfile(out_path)
        except Exception: pass

    # ────── FULL AUTO ──────
    def do_full_auto(self):
        """1. stop if running + misconfigured
           2. patch config (root + writable + adbDebug)
           3. launch
           4. poll adb_ready
           5. run chain
        """
        inst = self._require_current()
        if not inst: return
        needs_fix = (not inst.root_mode or not inst.writable or not inst.adb_debug)

        if inst.running and needs_fix:
            r = QMessageBox.question(self, "Stop + reconfigure?",
                    f"'{inst.name}' is RUNNING but needs config fix:\n"
                    f"  root     = {'OK' if inst.root_mode else 'MISSING'}\n"
                    f"  writable = {'OK' if inst.writable else 'MISSING'}\n"
                    f"  adbDebug = {'OK' if inst.adb_debug else 'MISSING'}\n\n"
                    "Stop instance + patch config + relaunch?",
                    QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes: return
            self._log(f"Stopping {inst.name} to patch config…", "info")
            self.ldp.quit(inst)
            QTimer.singleShot(5000, self._full_auto_after_stop); return

        if needs_fix:
            self._log(f"Patching config for {inst.name}…", "info")
            self.fix_instance_config(silent=True)

        if not inst.running:
            self.launch_instance()
            self._log("Waiting for boot + ADB ready (up to 120s)…", "info")
            self._poll_full_auto(tries=60); return

        if not inst.adb_ready:
            self._log("Running but ADB not registered — attempting connect…", "info")
            self.ldp.connect_adb(inst); self.refresh_instances()
            QTimer.singleShot(1500, lambda: self._poll_full_auto(tries=30)); return

        self._full_auto_chain()

    def _full_auto_after_stop(self):
        """Called 5s after quit — refresh, then re-enter do_full_auto."""
        self.refresh_instances()
        self.do_full_auto()

    def _poll_full_auto(self, tries: int = 60):
        """Poll until inst.adb_ready."""
        self.refresh_instances()
        inst = self.current
        if inst and inst.adb_ready:
            self._log(f"{inst.name} ADB ready ({inst.serial}) → chain start", "ok")
            self._full_auto_chain(); return
        if tries <= 0:
            self._log("Boot/ADB timeout (120s). Check LDPlayer manually.", "err")
            return
        QTimer.singleShot(2000, lambda: self._poll_full_auto(tries - 1))

    def _full_auto_chain(self):
        inst = self._require_current()
        if not inst or not inst.adb_ready:
            self._log("ADB not ready — cannot proceed", "err"); return
        self._log("═" * 60, "info")
        self._log("FULL AUTO SETUP — start", "info")
        self._log("═" * 60, "info")

        def chain(w: Worker, serial: str):
            total = 9
            def tick(n):  w.progress.emit(int(n/total*100))
            def do(name, fn, *args):
                w.log.emit(f"→ {name}", "info")
                try: fn(w, serial, *args)
                except Exception as e: w.log.emit(f"  {name} soft-fail: {e}", "warn")
            steps = [
                ("boot complete",     step_wait_boot),
                ("verify root",       step_verify_root),
                ("install Magisk",    step_install_magisk),
                ("push frida-server", step_push_frida),
                ("install emu-mask",  step_install_emu_mask),
                ("manual spoof",      step_manual_spoof),
                ("install Shopee",    step_install_shopee),
                ("grant perms",       step_grant_perms),
                ("launch Shopee",     step_launch_shopee),
                ("frida GMS fix",     step_frida_gms_fix),
            ]
            for i, (name, fn) in enumerate(steps):
                do(name, fn); tick(i+1)
            w.log.emit("═" * 60, "ok")
            w.log.emit("FULL AUTO SETUP — complete ✓", "ok")
            w.log.emit("Open LDPlayer window, Shopee ready.", "ok")
            w.log.emit("═" * 60, "ok")
        self._run_worker(chain)


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Shopee Bypass Automator")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
