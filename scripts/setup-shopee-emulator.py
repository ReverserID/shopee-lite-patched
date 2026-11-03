#!/usr/bin/env python3
"""
setup-shopee-emulator.py — interactive installer Shopee patched di Android emulator.

Jalanin tanpa argument untuk menu interaktif, atau pakai --preset untuk mode batch.

Menu:
  1. Setup emulator baru from scratch (SDK + AVD + Magisk + stack) — ~15 min, ~3 GB
  2. Install stack ke emulator existing yang sudah rooted Magisk — ~3 min
  3. Patch Magisk ke AVD existing (SDK + AVD sudah ada, tinggal rootinginnya) — ~2 min
  4. Install cuma Shopee + modmenu + gmsfix (skip LSPosed/emu-mask) — ~1 min
  5. Install microG stack (buat emulator non-GApps / login Google alt) — ~2 min
  6. Verify current state (adb check, module list, hook trace)
  7. Launch Shopee + grab screenshot
  8. Reset state checkpoint (buat rerun semua fresh)
  0. Exit

Preset non-interactive:
  --preset full-fresh      = menu 1
  --preset install-stack   = menu 2
  --preset patch-magisk    = menu 3
  --preset shopee-only     = menu 4
  --preset microg          = menu 5
  --preset verify          = menu 6

Dependency: Python 3.8+. Script auto-download semua tool (SDK, Magisk, modules).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

# ---- Konfigurasi ----

CMDLINE_TOOLS_VERSION = "11076708"
CMDLINE_TOOLS_URL = {
    "windows": f"https://dl.google.com/android/repository/commandlinetools-win-{CMDLINE_TOOLS_VERSION}_latest.zip",
    "darwin":  f"https://dl.google.com/android/repository/commandlinetools-mac-{CMDLINE_TOOLS_VERSION}_latest.zip",
    "linux":   f"https://dl.google.com/android/repository/commandlinetools-linux-{CMDLINE_TOOLS_VERSION}_latest.zip",
}
SDK_PACKAGES = [
    "platform-tools",
    "emulator",
    "platforms;android-34",
    "system-images;android-34;google_apis_playstore;x86_64",
]
AVD_NAME       = "ShopeeAVD"
AVD_DEVICE     = "pixel_7"
AVD_SYSIMG     = "system-images;android-34;google_apis_playstore;x86_64"
AVD_RAM_MB     = 4096
AVD_HEAP_MB    = 512
AVD_DISK_MB    = 8192
AVD_SDCARD_MB  = 2048

MAGISK_URL      = "https://github.com/topjohnwu/Magisk/releases/download/v27.0/Magisk-v27.0.apk"
VECTOR_URL      = "https://github.com/JingMatrix/LSPosed/releases/download/v1.9.2/LSPosed-v1.9.2-7024-zygisk-release.zip"
MODMENU_URL     = "https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-modmenu-1.7.0.apk"
GMSFIX_URL      = "https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-gmsfix-1.0.0.apk"
EMUMASK_URL     = "https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-emu-mask-1.0.zip"
SHOPEE_APK_URL  = "https://github.com/ReverserID/shopee-lite-patched/releases/download/v3.83.36/shopee-3.83.36-patched.apk"

MICROG_URLS = {
    "FakeStore.apk": "https://github.com/microg/FakeStore/releases/latest/download/FakeStore.apk",
    "GmsCore.apk":   "https://github.com/microg/GmsCore/releases/latest/download/com.google.android.gms-237816016.apk",
    "GsfProxy.apk":  "https://github.com/microg/GsfProxy/releases/latest/download/GsfProxy.apk",
}

HOME        = Path.home()
SDK_HOME    = Path(os.environ.get("ANDROID_HOME", HOME / "android-sdk-shopee"))
CACHE_HOME  = HOME / ".shupi-setup"
STATE_FILE  = CACHE_HOME / "state.json"

OS = platform.system().lower()
IS_WIN = OS == "windows"
EXE_BAT = ".bat" if IS_WIN else ""
EXE_EXE = ".exe" if IS_WIN else ""

# ---- Logging ----

def c(s: str, color: str) -> str:
    codes = {"r": "31", "g": "32", "y": "33", "b": "34", "m": "35", "cy": "36", "w": "37", "bld": "1"}
    if not sys.stdout.isatty() or IS_WIN:
        return s
    return f"\033[{codes.get(color, '0')}m{s}\033[0m"

def log(msg: str, color: str = "cy") -> None:
    print(c(f"[*] {msg}", color), flush=True)

def ok(msg: str) -> None:
    print(c(f"[+] {msg}", "g"), flush=True)

def warn(msg: str) -> None:
    print(c(f"[!] {msg}", "y"), flush=True)

def die(msg: str, code: int = 1) -> None:
    print(c(f"[x] {msg}", "r"), file=sys.stderr, flush=True)
    sys.exit(code)

def section(title: str) -> None:
    bar = "═" * (len(title) + 4)
    print()
    print(c(bar, "b"))
    print(c(f"  {title}", "bld"))
    print(c(bar, "b"))

# ---- State ----

def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}

def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def mark(key: str, value=True) -> None:
    state = load_state()
    state[key] = value
    save_state(state)

def done(key: str) -> bool:
    return bool(load_state().get(key))

# ---- Download ----

def download(url: str, out: Path, min_bytes: int = 1024) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size >= min_bytes:
        log(f"cached: {out.name} ({out.stat().st_size:,} bytes)")
        return out
    log(f"download {url}")
    tmp = out.with_suffix(out.suffix + ".tmp")
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        die(f"download failed: {e}")
    size = tmp.stat().st_size
    if size < min_bytes:
        tmp.unlink()
        die(f"download too small ({size} bytes), kemungkinan URL mati / redirect: {url}")
    tmp.rename(out)
    ok(f"saved: {out.name} ({size:,} bytes)")
    return out

def unzip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out_dir)

def chmodx(path: Path) -> None:
    if not IS_WIN and path.exists():
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

# ---- Shell ----

def run(cmd, check: bool = True, timeout: int = None, env: dict = None, cwd: Path = None,
        stdin: str = None, quiet: bool = False) -> subprocess.CompletedProcess:
    if not quiet:
        log(f"$ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(
        [str(x) for x in cmd],
        capture_output=True, text=True,
        check=False, timeout=timeout,
        env=env or os.environ, cwd=cwd, input=stdin,
    )
    if r.stdout.strip() and not quiet:
        print(r.stdout.rstrip())
    if r.stderr.strip() and not quiet:
        print(r.stderr.rstrip(), file=sys.stderr)
    if check and r.returncode != 0:
        die(f"command failed (exit {r.returncode}): {' '.join(str(x) for x in cmd)}")
    return r

def run_async(cmd, env: dict = None, cwd: Path = None) -> subprocess.Popen:
    log(f"$ {' '.join(str(x) for x in cmd)} &")
    return subprocess.Popen(
        [str(x) for x in cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env or os.environ, cwd=cwd,
    )

# ---- Device discovery ----

def adb_bin() -> Path:
    p = SDK_HOME / "platform-tools" / f"adb{EXE_EXE}"
    if not p.exists():
        # Fallback: system adb
        sys_adb = shutil.which("adb")
        if sys_adb:
            return Path(sys_adb)
        die(f"adb tidak ditemukan di {p} atau PATH. Jalanin phase SDK dulu.")
    return p

def adb(args: list, device: str = None, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    cmd = [adb_bin()]
    if device:
        cmd += ["-s", device]
    cmd += args
    return run(cmd, check=check, timeout=timeout, quiet=True)

def list_devices() -> list:
    """Returns list of (serial, status) tuples."""
    try:
        r = adb(["devices"], check=False)
    except SystemExit:
        return []
    devices = []
    for line in r.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) == 2:
            devices.append((parts[0], parts[1]))
    return devices

def pick_device() -> str:
    devs = list_devices()
    online = [(s, st) for s, st in devs if st == "device"]
    if not online:
        die("no device online. Boot emulator dulu (menu 1 atau 3), atau connect physical via adb.")
    if len(online) == 1:
        return online[0][0]
    print()
    log("multiple devices connected, pilih:")
    for i, (s, st) in enumerate(online, 1):
        prop = adb(["-s", s, "shell", "getprop", "ro.product.model"], check=False)
        model = prop.stdout.strip() if prop.returncode == 0 else "?"
        print(f"  {i}. {s} ({model})")
    while True:
        ans = input(c("Pilih (nomor): ", "y")).strip()
        try:
            return online[int(ans) - 1][0]
        except (ValueError, IndexError):
            print(c("input invalid, coba lagi", "r"))

def is_rooted(dev: str) -> bool:
    r = adb(["-s", dev, "shell", "su", "-c", "id"], check=False)
    return r.returncode == 0 and "uid=0" in r.stdout

# ---- Flows ----

def flow_sdk() -> None:
    section("Download & setup Android SDK (cmdline-tools)")
    if done("sdk_installed") and (SDK_HOME / "platform-tools" / f"adb{EXE_EXE}").exists():
        ok("SDK sudah installed, skip")
        return

    SDK_HOME.mkdir(parents=True, exist_ok=True)
    if OS not in CMDLINE_TOOLS_URL:
        die(f"OS tidak didukung: {OS}")
    zip_cache = CACHE_HOME / f"cmdline-tools-{OS}.zip"
    download(CMDLINE_TOOLS_URL[OS], zip_cache, min_bytes=50 * 1024 * 1024)

    tgt = SDK_HOME / "cmdline-tools" / "latest"
    if not (tgt / "bin").exists():
        with tempfile.TemporaryDirectory() as tmp:
            unzip(zip_cache, Path(tmp))
            src = Path(tmp) / "cmdline-tools"
            if tgt.exists():
                shutil.rmtree(tgt)
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(tgt))
        ok(f"extracted cmdline-tools -> {tgt}")

    sdkmanager = tgt / "bin" / f"sdkmanager{EXE_BAT}"
    chmodx(sdkmanager)
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_HOME)
    env["ANDROID_SDK_ROOT"] = str(SDK_HOME)

    log("accepting SDK licenses...")
    subprocess.run([str(sdkmanager), "--licenses", f"--sdk_root={SDK_HOME}"],
                   input="y\n" * 20, text=True, env=env,
                   capture_output=True, timeout=120)

    log(f"installing packages: {', '.join(SDK_PACKAGES)} (~2 GB)")
    run([str(sdkmanager), f"--sdk_root={SDK_HOME}", "--install"] + SDK_PACKAGES,
        env=env, timeout=1800)

    mark("sdk_installed")
    ok("SDK installed")

def flow_avd() -> None:
    section("Create AVD (Pixel 7, API 34)")
    if done("avd_created"):
        ok("AVD sudah dibikin, skip")
        return
    avdmanager = SDK_HOME / "cmdline-tools" / "latest" / "bin" / f"avdmanager{EXE_BAT}"
    chmodx(avdmanager)
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_HOME)
    env["ANDROID_SDK_ROOT"] = str(SDK_HOME)
    log(f"creating AVD '{AVD_NAME}'")
    subprocess.run([str(avdmanager), "create", "avd", "-n", AVD_NAME,
                    "-k", AVD_SYSIMG, "-d", AVD_DEVICE, "--force"],
                   input="no\n", text=True, env=env,
                   capture_output=False, timeout=120)

    cfg = HOME / ".android" / "avd" / f"{AVD_NAME}.avd" / "config.ini"
    if cfg.exists():
        lines = cfg.read_text().splitlines()
        updates = {
            "hw.ramSize": str(AVD_RAM_MB),
            "vm.heapSize": str(AVD_HEAP_MB),
            "disk.dataPartition.size": f"{AVD_DISK_MB}M",
            "sdcard.size": f"{AVD_SDCARD_MB}M",
            "hw.gpu.enabled": "yes",
            "hw.gpu.mode": "auto",
        }
        seen, new = set(), []
        for ln in lines:
            if "=" in ln:
                k = ln.split("=", 1)[0].strip()
                if k in updates:
                    new.append(f"{k} = {updates[k]}")
                    seen.add(k)
                    continue
            new.append(ln)
        for k, v in updates.items():
            if k not in seen:
                new.append(f"{k} = {v}")
        cfg.write_text("\n".join(new) + "\n")
        ok(f"patched {cfg.name}: RAM={AVD_RAM_MB}MB disk={AVD_DISK_MB}MB")

    mark("avd_created")
    ok("AVD created")

def flow_magisk_patch() -> None:
    section("Patch system-image ramdisk pakai Magisk (headless)")
    if done("magisk_patched"):
        ok("ramdisk sudah di-patch, skip")
        return

    magisk_apk = CACHE_HOME / "Magisk.apk"
    download(MAGISK_URL, magisk_apk, min_bytes=5 * 1024 * 1024)

    work = CACHE_HOME / "magisk_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    with zipfile.ZipFile(magisk_apk) as z:
        host_abi = "x86_64"
        if platform.machine() in ("arm64", "aarch64"):
            host_abi = "arm64-v8a"
        for n in z.namelist():
            if n.startswith(f"lib/{host_abi}/lib") and n.endswith(".so"):
                tgt = work / Path(n).name.replace("lib", "", 1).replace(".so", "")
                tgt.write_bytes(z.read(n))
                chmodx(tgt)

    magiskboot = work / "magiskboot"
    if not magiskboot.exists():
        die(f"magiskboot binary tidak ketemu di Magisk.apk (lib/{host_abi}/)")

    sysimg_dir = SDK_HOME / "system-images" / "android-34" / "google_apis_playstore" / "x86_64"
    ramdisk = sysimg_dir / "ramdisk.img"
    if not ramdisk.exists():
        die(f"ramdisk.img tidak ketemu di {ramdisk}. Install system image dulu (menu SDK).")

    orig = sysimg_dir / "ramdisk.img.orig"
    if not orig.exists():
        shutil.copy2(ramdisk, orig)
        ok(f"backed up ramdisk.img -> {orig.name}")

    work_patch = CACHE_HOME / "ramdisk_patch"
    if work_patch.exists():
        shutil.rmtree(work_patch)
    work_patch.mkdir()
    shutil.copy2(orig, work_patch / "ramdisk.cpio")
    for n in ["magiskinit", "magisk32", "magisk64", "magiskboot", "busybox"]:
        p = work / n
        if p.exists():
            shutil.copy2(p, work_patch / n)

    env = os.environ.copy()
    env["KEEPVERITY"] = "true"
    env["KEEPFORCEENCRYPT"] = "true"

    for binname in ("magisk32", "magisk64"):
        if (work_patch / binname).exists():
            run([str(magiskboot), "compress=xz", binname, f"{binname}.xz"],
                cwd=work_patch, env=env, check=False, quiet=True)

    (work_patch / "config").write_text("KEEPVERITY=true\nKEEPFORCEENCRYPT=true\nRECOVERYMODE=false\n")

    cpio_cmds = [
        ["add", "0750", "init", "magiskinit"],
        ["mkdir", "0750", "overlay.d"],
        ["mkdir", "0750", "overlay.d/sbin"],
    ]
    if (work_patch / "magisk32.xz").exists():
        cpio_cmds.append(["add", "0644", "overlay.d/sbin/magisk32.xz", "magisk32.xz"])
    if (work_patch / "magisk64.xz").exists():
        cpio_cmds.append(["add", "0644", "overlay.d/sbin/magisk64.xz", "magisk64.xz"])
    cpio_cmds += [
        ["patch"],
        ["backup", "ramdisk.cpio"],
        ["mkdir", "000", ".backup"],
        ["add", "000", ".backup/.magisk", "config"],
    ]
    for args in cpio_cmds:
        run([str(magiskboot), "cpio", "ramdisk.cpio"] + args,
            cwd=work_patch, env=env, check=False, quiet=True)

    shutil.copy2(work_patch / "ramdisk.cpio", ramdisk)
    ok(f"patched ramdisk written: {ramdisk}")
    mark("magisk_patched")

def start_emulator(wait: bool = True, timeout: int = 300) -> str:
    """Returns device serial. Starts emulator if not running."""
    devs = [d for d, st in list_devices() if st == "device" and "emulator" in d]
    if devs:
        ok(f"emulator sudah jalan: {devs[0]}")
        return devs[0]
    emu_bin = SDK_HOME / "emulator" / f"emulator{EXE_EXE}"
    if not emu_bin.exists():
        die(f"emulator binary tidak ketemu: {emu_bin}")
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_HOME)
    env["ANDROID_SDK_ROOT"] = str(SDK_HOME)
    log("starting emulator...")
    run_async([str(emu_bin), "-avd", AVD_NAME, "-no-snapshot-load",
               "-writable-system", "-no-boot-anim"], env=env)
    if not wait:
        return ""
    log(f"waiting for boot (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        for s, st in list_devices():
            if st == "device" and "emulator" in s:
                r = adb(["-s", s, "shell", "getprop", "sys.boot_completed"], check=False)
                if r.stdout.strip() == "1":
                    ok(f"boot complete: {s}")
                    return s
        time.sleep(5)
    die("boot timeout")

def flow_install_stack(dev: str = None) -> None:
    section("Install stack (Magisk Manager + Shopee + modmenu + gmsfix + LSPosed + emu-mask)")
    if not dev:
        dev = pick_device()
    log(f"target device: {dev}")

    files = {
        "Magisk.apk":         download(MAGISK_URL, CACHE_HOME / "Magisk.apk", 5 * 1024 * 1024),
        "LSPosed.zip":        download(VECTOR_URL, CACHE_HOME / "LSPosed.zip", 2 * 1024 * 1024),
        "modmenu.apk":        download(MODMENU_URL, CACHE_HOME / "shopee-modmenu.apk", 50 * 1024),
        "gmsfix.apk":         download(GMSFIX_URL, CACHE_HOME / "shopee-gmsfix.apk", 5 * 1024),
        "emu-mask.zip":       download(EMUMASK_URL, CACHE_HOME / "shopee-emu-mask.zip", 500),
        "shopee-patched.apk": download(SHOPEE_APK_URL, CACHE_HOME / "shopee-patched.apk", 50 * 1024 * 1024),
    }

    for apk_key in ("Magisk.apk", "shopee-patched.apk", "modmenu.apk", "gmsfix.apk"):
        log(f"adb install {apk_key}")
        adb(["-s", dev, "install", "-r", str(files[apk_key])], check=False, timeout=180)

    if is_rooted(dev):
        for zip_key in ("LSPosed.zip", "emu-mask.zip"):
            adb(["-s", dev, "push", str(files[zip_key]), f"/data/local/tmp/{zip_key}"], check=False)
            adb(["-s", dev, "shell", "su", "-c",
                 f"magisk --install-module /data/local/tmp/{zip_key}"], check=False, timeout=60)
            ok(f"magisk module installed: {zip_key}")
    else:
        warn("device belum rooted — skip LSPosed + emu-mask install (butuh root).")
        warn("Buka Magisk app di device → Install → patch boot image. Atau menu 3 (patch AVD).")

    ok("stack install done")
    mark("apps_installed")

def flow_install_microg(dev: str = None) -> None:
    section("Install microG stack (FakeStore + GmsCore + GsfProxy)")
    if not dev:
        dev = pick_device()
    log(f"target device: {dev}")

    files = {}
    for name, url in MICROG_URLS.items():
        files[name] = download(url, CACHE_HOME / name, 50 * 1024)

    # Uninstall real Play Store biar FakeStore menang signature
    log("uninstall real Play Store (biar FakeStore menang signature)")
    adb(["-s", dev, "uninstall", "com.android.vending"], check=False)

    # Install order: FakeStore -> GmsCore -> GsfProxy
    for name in ("FakeStore.apk", "GmsCore.apk", "GsfProxy.apk"):
        adb(["-s", dev, "install", "-r", str(files[name])], check=False, timeout=120)

    for perm in ("android.permission.FAKE_PACKAGE_SIGNATURE",
                 "android.permission.ACCESS_FINE_LOCATION",
                 "android.permission.READ_PHONE_STATE",
                 "android.permission.GET_ACCOUNTS"):
        adb(["-s", dev, "shell", "pm", "grant", "com.google.android.gms", perm], check=False)

    ok("microG installed")
    warn("Buka 'microG Settings' app → Self-Check (semua harus hijau)")
    warn("'Google Account' → login akun → 'Cloud Messaging' ON → reboot")

def flow_shopee_only(dev: str = None) -> None:
    section("Install cuma Shopee + modmenu + gmsfix (skip LSPosed/emu-mask)")
    if not dev:
        dev = pick_device()
    log(f"target device: {dev}")
    shopee = download(SHOPEE_APK_URL, CACHE_HOME / "shopee-patched.apk", 50 * 1024 * 1024)
    modmenu = download(MODMENU_URL, CACHE_HOME / "shopee-modmenu.apk", 50 * 1024)
    gmsfix = download(GMSFIX_URL, CACHE_HOME / "shopee-gmsfix.apk", 5 * 1024)
    for apk in (shopee, modmenu, gmsfix):
        adb(["-s", dev, "install", "-r", str(apk)], check=False, timeout=180)
    ok("Shopee + modmenu + gmsfix installed")

def flow_verify(dev: str = None) -> None:
    section("Verify current state")
    if not dev:
        dev = pick_device()

    # Device info
    model = adb(["-s", dev, "shell", "getprop", "ro.product.model"], check=False).stdout.strip()
    sdk = adb(["-s", dev, "shell", "getprop", "ro.build.version.sdk"], check=False).stdout.strip()
    hw = adb(["-s", dev, "shell", "getprop", "ro.hardware"], check=False).stdout.strip()
    qemu = adb(["-s", dev, "shell", "getprop", "ro.kernel.qemu"], check=False).stdout.strip()
    print(f"  Device: {dev}  Model: {model}  SDK: {sdk}")
    print(f"  ro.hardware: {hw}  ro.kernel.qemu: {qemu}")

    # Root
    rooted = is_rooted(dev)
    print(f"  Rooted (Magisk): {'✓' if rooted else '✗'}")

    # Shopee + modmenu installed?
    pkgs = adb(["-s", dev, "shell", "pm", "list", "packages"], check=False).stdout
    for p, label in [
        ("com.shopee.id", "Shopee"),
        ("com.shopee.lite.id", "Shopee Lite"),
        ("id.reverser.modmenu", "modmenu"),
        ("id.reverser.shopee.gmsfix", "gmsfix"),
        ("com.topjohnwu.magisk", "Magisk Manager"),
        ("com.google.android.gms", "GMS/microG"),
    ]:
        installed = p in pkgs
        print(f"  {label} ({p}): {'✓' if installed else '✗'}")

    # Emu mask active?
    if rooted:
        mask = adb(["-s", dev, "shell", "su", "-c", "mount | grep /proc/cpuinfo"], check=False)
        print(f"  /proc/cpuinfo bind-mount: {'✓' if 'cpuinfo' in mask.stdout else '✗'}")

    # Modmenu hook trace
    if rooted:
        trace = adb(["-s", dev, "shell", "su", "-c",
                     "/data/adb/lspd/cli log cat 2>&1 | grep ShopeeMod | tail -5"],
                    check=False, timeout=15)
        if trace.stdout.strip():
            print(c("  Hook trace (last 5 lines):", "g"))
            for line in trace.stdout.strip().splitlines():
                print(f"    {line}")
        else:
            warn("Hook trace kosong — modmenu belum attach ke Shopee (atau Shopee belum buka)")

def flow_launch(dev: str = None) -> None:
    section("Launch Shopee + screenshot")
    if not dev:
        dev = pick_device()
    adb(["-s", dev, "shell", "am", "force-stop", "com.shopee.id"], check=False)
    adb(["-s", dev, "shell", "monkey", "-p", "com.shopee.id",
         "-c", "android.intent.category.LAUNCHER", "1"], check=False)
    log("waiting 15s untuk Shopee ready...")
    time.sleep(15)
    CACHE_HOME.mkdir(parents=True, exist_ok=True)
    out = CACHE_HOME / f"shopee-launch-{int(time.time())}.png"
    r = subprocess.run([str(adb_bin()), "-s", dev, "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=30)
    out.write_bytes(r.stdout)
    ok(f"screenshot: {out}")

def flow_reset() -> None:
    section("Reset state checkpoint")
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        ok(f"deleted {STATE_FILE}")
    else:
        warn("state file tidak ada, nothing to reset")

# ---- Menu ----

MENU = [
    ("Setup emulator baru from scratch (SDK + AVD + Magisk + stack)", "full-fresh",
     "~15 min, ~3 GB download. Buat yg belum punya Android Studio / SDK."),
    ("Install stack ke emulator existing yang sudah rooted Magisk", "install-stack",
     "~3 min. Skip SDK/AVD/Magisk, install cuma apps + modules."),
    ("Patch Magisk ke AVD existing (SDK + AVD sudah ada)", "patch-magisk",
     "~2 min. Rooting-nya aja; apps install via menu 2."),
    ("Install cuma Shopee + modmenu + gmsfix (skip LSPosed/emu-mask)", "shopee-only",
     "~1 min. Buat yg sudah punya LSPosed/Vector sendiri."),
    ("Install microG stack (emu non-GApps / login Google alt)", "microg",
     "~2 min. Butuh signature spoofing di-enable duluan."),
    ("Verify current state (device, root, modules, hook trace)", "verify",
     "Diagnostic — check semua terpasang + jalan."),
    ("Launch Shopee + grab screenshot", "launch",
     "Smoke test akhir."),
    ("Reset state checkpoint (buat rerun semua fresh)", "reset",
     "Hapus state.json aja; cache file + SDK tetap."),
]

PRESETS = {name: idx for idx, (_, name, _) in enumerate(MENU)}

def run_preset(preset: str) -> None:
    if preset not in PRESETS:
        die(f"preset tidak dikenal: {preset}. Valid: {', '.join(PRESETS)}")
    idx = PRESETS[preset]
    dispatch(idx)

def dispatch(idx: int) -> None:
    if idx == 0:
        flow_sdk(); flow_avd(); flow_magisk_patch()
        start_emulator()
        flow_install_stack()
    elif idx == 1:
        flow_install_stack()
    elif idx == 2:
        flow_magisk_patch()
        start_emulator()
    elif idx == 3:
        flow_shopee_only()
    elif idx == 4:
        flow_install_microg()
    elif idx == 5:
        flow_verify()
    elif idx == 6:
        flow_launch()
    elif idx == 7:
        flow_reset()

def print_menu() -> None:
    print()
    print(c("┌─────────────────────────────────────────────────────────────────┐", "b"))
    print(c("│  Shopee Emulator Setup — reverser.id                            │", "bld"))
    print(c("├─────────────────────────────────────────────────────────────────┤", "b"))
    for i, (title, _, desc) in enumerate(MENU, 1):
        print(c(f"│  {i}. {title[:60]:60}│", "cy"))
        print(c(f"│     {desc[:60]:60}│", "w"))
    print(c("│  0. Exit                                                        │", "r"))
    print(c("└─────────────────────────────────────────────────────────────────┘", "b"))
    print()
    print(c(f"  State: ", "w") + c(str(STATE_FILE), "y"))
    print(c(f"  SDK:   ", "w") + c(str(SDK_HOME), "y"))
    print(c(f"  Cache: ", "w") + c(str(CACHE_HOME), "y"))
    st = load_state()
    if st:
        done_items = [k for k, v in st.items() if v]
        print(c("  Done:  ", "w") + c(", ".join(done_items), "g"))
    print()

def interactive_loop() -> None:
    while True:
        print_menu()
        ans = input(c("Pilih (0-8): ", "y")).strip()
        if ans == "0":
            print("bye.")
            return
        try:
            idx = int(ans) - 1
            if not 0 <= idx < len(MENU):
                raise ValueError
        except ValueError:
            print(c("input invalid, coba lagi", "r"))
            continue
        try:
            dispatch(idx)
        except KeyboardInterrupt:
            print(c("\ninterrupted — kembali ke menu", "y"))
        except SystemExit:
            raise
        except Exception as e:
            print(c(f"error: {e}", "r"))
        input(c("\nTekan Enter untuk balik ke menu...", "cy"))

# ---- Main ----

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=list(PRESETS.keys()),
                    help="run spesifik flow tanpa menu interaktif")
    args = ap.parse_args()

    print(c("Shopee Emulator Setup — reverser.id", "bld"))
    print(c(f"OS: {OS} ({platform.machine()})  Python: {platform.python_version()}", "cy"))

    if args.preset:
        run_preset(args.preset)
    else:
        interactive_loop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        die("interrupted")
