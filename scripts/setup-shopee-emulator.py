#!/usr/bin/env python3
"""
setup-shopee-emulator.py — one-shot headless setup Shopee patched di Android
emulator di Windows / Mac / Linux, tanpa Android Studio GUI.

Yang di-automate (end-to-end):
  1. Download Android commandline-tools (OS-specific) ke ~/android-sdk-shopee
  2. sdkmanager install: platform-tools, emulator, Android 34 system image
  3. avdmanager create Pixel 7 AVD
  4. Download Magisk APK -> extract magiskboot
  5. Patch system-image ramdisk.img pakai magiskboot (headless, bukan GUI)
  6. Download Shopee patched + modmenu + gmsfix + emu_mask + Vector LSPosed
  7. Boot AVD, install stack, enable modules, reboot
  8. Launch Shopee + verify

Pakai:
    python3 setup-shopee-emulator.py                    # full flow
    python3 setup-shopee-emulator.py --skip-sdk         # SDK udah ada
    python3 setup-shopee-emulator.py --skip-avd         # AVD udah dibikin
    python3 setup-shopee-emulator.py --phase sdk        # cuma SDK
    python3 setup-shopee-emulator.py --phase apps       # cuma install apps
    python3 setup-shopee-emulator.py --phase launch     # cuma boot + launch

Semua state di-persist di ~/android-sdk-shopee (SDK) + ~/.shupi-setup/ (cache,
checkpoint). Script idempotent — aman di-rerun.

Dependency: Python 3.8+. Nggak butuh adb/emulator pre-install (script yang
install). Nggak butuh Android Studio.
"""

from __future__ import annotations

import argparse
import hashlib
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

# ---- Konfigurasi: URL + versi (ganti kalau mau pin ke version lain) ----

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
AVD_SDCARD_MB  = 2048
AVD_RAM_MB     = 4096
AVD_HEAP_MB    = 512
AVD_DISK_MB    = 8192

MAGISK_URL      = "https://github.com/topjohnwu/Magisk/releases/download/v27.0/Magisk-v27.0.apk"
VECTOR_URL      = "https://github.com/JingMatrix/LSPosed/releases/download/v1.9.2/LSPosed-v1.9.2-7024-zygisk-release.zip"
MODMENU_URL     = "https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-modmenu-1.7.0.apk"
GMSFIX_URL      = "https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-gmsfix-1.0.0.apk"
EMUMASK_URL     = "https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-emu-mask-1.0.zip"
SHOPEE_APK_URL  = "https://github.com/ReverserID/shopee-lite-patched/releases/download/v3.83.36/shopee-3.83.36-patched.apk"

HOME        = Path.home()
SDK_HOME    = HOME / "android-sdk-shopee"
CACHE_HOME  = HOME / ".shupi-setup"
STATE_FILE  = CACHE_HOME / "state.json"

# ---- Platform detection ----

def detect_os() -> str:
    sys_name = platform.system().lower()
    if sys_name not in ("windows", "darwin", "linux"):
        die(f"Unsupported OS: {sys_name}")
    return sys_name

OS = detect_os()
IS_WIN = OS == "windows"
EXE = ".bat" if IS_WIN else ""

# ---- Logging + state ----

def log(msg: str, prefix: str = "*") -> None:
    print(f"[{prefix}] {msg}", flush=True)

def die(msg: str, code: int = 1) -> "NoReturn":
    log(msg, prefix="!")
    sys.exit(code)

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

# ---- Download helpers ----

def download(url: str, out: Path, min_bytes: int = 1024) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size >= min_bytes:
        log(f"cached: {out.name} ({out.stat().st_size:,} bytes)")
        return out
    log(f"downloading {url}")
    tmp = out.with_suffix(out.suffix + ".tmp")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    size = tmp.stat().st_size
    if size < min_bytes:
        tmp.unlink()
        die(f"download too small ({size} bytes) — URL dead or redirected: {url}")
    tmp.rename(out)
    log(f"saved: {out.name} ({size:,} bytes)")
    return out

def unzip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out_dir)

def chmodx(path: Path) -> None:
    if not IS_WIN:
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

# ---- Shell runners ----

def run(cmd, check: bool = True, timeout: int = None, env: dict = None, cwd: Path = None, stdin: str = None) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(str(c) for c in cmd)}", prefix="$")
    r = subprocess.run(
        [str(c) for c in cmd],
        capture_output=True, text=True,
        check=False, timeout=timeout,
        env=env or os.environ, cwd=cwd, input=stdin,
    )
    if r.stdout.strip():
        print(r.stdout.rstrip())
    if r.stderr.strip():
        print(r.stderr.rstrip(), file=sys.stderr)
    if check and r.returncode != 0:
        die(f"command failed (exit {r.returncode}): {' '.join(str(c) for c in cmd)}")
    return r

def run_async(cmd, env: dict = None, cwd: Path = None) -> subprocess.Popen:
    log(f"$ {' '.join(str(c) for c in cmd)} &", prefix="$")
    return subprocess.Popen(
        [str(c) for c in cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env or os.environ, cwd=cwd,
    )

# ---- Phase 1: SDK setup ----

def phase_sdk() -> None:
    if done("sdk_installed"):
        log("SDK sudah installed, skip")
        return
    log("=== PHASE 1: Android SDK ===", prefix=">")
    SDK_HOME.mkdir(parents=True, exist_ok=True)

    # Download + extract commandline-tools ke SDK_HOME/cmdline-tools/latest
    zip_cache = CACHE_HOME / f"cmdline-tools-{OS}.zip"
    download(CMDLINE_TOOLS_URL[OS], zip_cache, min_bytes=50 * 1024 * 1024)

    tgt = SDK_HOME / "cmdline-tools" / "latest"
    if not (tgt / "bin").exists():
        with tempfile.TemporaryDirectory() as tmp:
            unzip(zip_cache, Path(tmp))
            # Zip extracts to "cmdline-tools/..." — pindahkan ke SDK/cmdline-tools/latest
            src = Path(tmp) / "cmdline-tools"
            if tgt.exists():
                shutil.rmtree(tgt)
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(tgt))
        log(f"extracted cmdline-tools -> {tgt}")

    # Install packages via sdkmanager (dgn auto-accept license)
    sdkmanager = tgt / "bin" / f"sdkmanager{EXE}"
    chmodx(sdkmanager)
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_HOME)
    env["ANDROID_SDK_ROOT"] = str(SDK_HOME)

    # Accept all licenses (dengan 'yes' feed stdin)
    log("accepting SDK licenses...")
    r = subprocess.run(
        [str(sdkmanager), "--licenses", f"--sdk_root={SDK_HOME}"],
        input="y\n" * 20, text=True, env=env,
        capture_output=True, timeout=120,
    )
    if r.returncode != 0 and "All SDK package licenses accepted" not in r.stdout:
        log(f"license output: {r.stdout}")

    # Install packages
    log(f"installing: {', '.join(SDK_PACKAGES)} (~2 GB download)")
    run([str(sdkmanager), f"--sdk_root={SDK_HOME}", "--install"] + SDK_PACKAGES,
        env=env, timeout=1800)

    mark("sdk_installed")
    log("SDK installed OK")

# ---- Phase 2: AVD creation ----

def phase_avd() -> None:
    if done("avd_created"):
        log("AVD sudah dibikin, skip")
        return
    log("=== PHASE 2: AVD creation ===", prefix=">")

    avdmanager = SDK_HOME / "cmdline-tools" / "latest" / "bin" / f"avdmanager{EXE}"
    chmodx(avdmanager)
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_HOME)
    env["ANDROID_SDK_ROOT"] = str(SDK_HOME)

    # Create AVD (echo "no" buat skip custom hardware prompt)
    log(f"creating AVD '{AVD_NAME}' (device={AVD_DEVICE}, img={AVD_SYSIMG})")
    r = subprocess.run(
        [str(avdmanager), "create", "avd",
         "-n", AVD_NAME,
         "-k", AVD_SYSIMG,
         "-d", AVD_DEVICE,
         "--force"],
        input="no\n", text=True, env=env,
        capture_output=True, timeout=120,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        die("avdmanager create failed")

    # Tweak AVD config.ini biar RAM + disk layak
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
        seen = set()
        new_lines = []
        for ln in lines:
            if "=" in ln:
                k = ln.split("=", 1)[0].strip()
                if k in updates:
                    new_lines.append(f"{k} = {updates[k]}")
                    seen.add(k)
                    continue
            new_lines.append(ln)
        for k, v in updates.items():
            if k not in seen:
                new_lines.append(f"{k} = {v}")
        cfg.write_text("\n".join(new_lines) + "\n")
        log(f"patched {cfg.name}: RAM={AVD_RAM_MB}MB disk={AVD_DISK_MB}MB")

    mark("avd_created")
    log("AVD created OK")

# ---- Phase 3: Magisk ramdisk patch (HEADLESS, no GUI) ----

def phase_magisk() -> None:
    if done("magisk_patched"):
        log("ramdisk sudah di-patch Magisk, skip")
        return
    log("=== PHASE 3: Magisk ramdisk patch (headless) ===", prefix=">")

    # Download Magisk APK
    magisk_apk = CACHE_HOME / "Magisk.apk"
    download(MAGISK_URL, magisk_apk, min_bytes=5 * 1024 * 1024)

    # Extract magiskboot + lain-lain dari APK (ini binary native, langsung dipake di host)
    work = CACHE_HOME / "magisk_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    with zipfile.ZipFile(magisk_apk) as z:
        # Pilih ABI yg cocok sama host OS
        host_abi = "x86_64" if platform.machine() in ("x86_64", "AMD64") else "arm64-v8a"
        # Mac arm = arm64, Mac x86 = x86_64. Linux x86 = x86_64. Windows x86 = x86_64.
        if OS == "darwin" and platform.machine() == "arm64":
            host_abi = "arm64-v8a"
        for n in z.namelist():
            if n.startswith(f"lib/{host_abi}/lib") and n.endswith(".so"):
                tgt = work / Path(n).name.replace("lib", "").replace(".so", "")
                tgt.write_bytes(z.read(n))
                chmodx(tgt)
                log(f"extracted {n} -> {tgt.name}")

    magiskboot = work / "magiskboot"
    if not magiskboot.exists():
        die(f"magiskboot binary not found in Magisk.apk (lib/{host_abi}/)")

    # Find system-image ramdisk.img
    sysimg_dir = SDK_HOME / "system-images" / "android-34" / "google_apis_playstore" / "x86_64"
    ramdisk = sysimg_dir / "ramdisk.img"
    if not ramdisk.exists():
        die(f"ramdisk.img not found at {ramdisk} — pastikan Phase 1 beres")

    # Backup original (one-time)
    orig = sysimg_dir / "ramdisk.img.orig"
    if not orig.exists():
        shutil.copy2(ramdisk, orig)
        log(f"backed up ramdisk.img -> {orig.name}")

    # Patch ramdisk: pakai magiskboot cpio untuk inject Magisk init ke dalam ramdisk
    # (AVD punya ramdisk standalone, bukan boot.img)
    work_patch = CACHE_HOME / "ramdisk_patch"
    if work_patch.exists():
        shutil.rmtree(work_patch)
    work_patch.mkdir()

    shutil.copy2(orig, work_patch / "ramdisk.cpio")
    for n in ["magiskinit", "magisk32", "magisk64", "magiskboot", "busybox"]:
        p = work / n
        if p.exists():
            shutil.copy2(p, work_patch / n)

    # Jalanin magiskboot cpio patch (sama kaya boot_patch.sh langkah terakhir)
    env = os.environ.copy()
    env["KEEPVERITY"] = "true"
    env["KEEPFORCEENCRYPT"] = "true"
    env["PATCHVBMETAFLAG"] = "false"
    env["RECOVERYMODE"] = "false"

    cmd = [str(magiskboot), "compress=xz", "magisk32", "magisk32.xz"]
    run(cmd, cwd=work_patch, env=env, check=False)
    cmd = [str(magiskboot), "compress=xz", "magisk64", "magisk64.xz"]
    run(cmd, cwd=work_patch, env=env, check=False)

    # Inject magisk payload ke ramdisk cpio
    cpio_cmds = [
        "add 0750 init magiskinit",
        "mkdir 0750 overlay.d",
        "mkdir 0750 overlay.d/sbin",
        "add 0644 overlay.d/sbin/magisk32.xz magisk32.xz",
        "add 0644 overlay.d/sbin/magisk64.xz magisk64.xz",
        "patch",
        "backup ramdisk.cpio",
        "mkdir 000 .backup",
        "add 000 .backup/.magisk config",
    ]
    # Write Magisk config
    (work_patch / "config").write_text(
        "KEEPVERITY=true\nKEEPFORCEENCRYPT=true\nRECOVERYMODE=false\n"
    )
    for cmd_line in cpio_cmds:
        run([str(magiskboot), "cpio", "ramdisk.cpio"] + cmd_line.split(),
            cwd=work_patch, env=env, check=False)

    # Replace ramdisk.img dgn versi patched
    patched = work_patch / "ramdisk.cpio"
    shutil.copy2(patched, ramdisk)
    log(f"patched ramdisk written: {ramdisk} ({ramdisk.stat().st_size:,} bytes)")

    mark("magisk_patched")
    log("Magisk patch applied")

# ---- Phase 4: Boot AVD + install stack ----

def adb(args: list, device: str = None, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    adb_bin = SDK_HOME / "platform-tools" / f"adb{EXE[:-1] + '.exe' if IS_WIN else ''}"
    cmd = [str(adb_bin)]
    if device:
        cmd += ["-s", device]
    cmd += args
    return run(cmd, check=check, timeout=timeout)

def start_emulator() -> subprocess.Popen:
    emu_bin = SDK_HOME / "emulator" / f"emulator{EXE[:-1] + '.exe' if IS_WIN else ''}"
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_HOME)
    env["ANDROID_SDK_ROOT"] = str(SDK_HOME)
    return run_async([str(emu_bin), "-avd", AVD_NAME, "-no-snapshot-load",
                      "-writable-system", "-no-boot-anim"], env=env)

def wait_boot(timeout: int = 300) -> str:
    log(f"waiting for emulator boot (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        r = adb(["devices"], check=False, timeout=10)
        for line in r.stdout.splitlines():
            if line.endswith("\tdevice") and "emulator" in line:
                dev = line.split("\t")[0]
                # Check boot complete
                r2 = adb(["-s", dev, "shell", "getprop", "sys.boot_completed"],
                         check=False, timeout=10)
                if r2.stdout.strip() == "1":
                    log(f"boot complete: {dev}")
                    return dev
        time.sleep(5)
    die("emulator boot timeout")

def phase_apps() -> None:
    if done("apps_installed"):
        log("stack sudah ter-install, skip")
        return
    log("=== PHASE 4: Boot AVD + install stack ===", prefix=">")

    # Download semua binary dulu
    files = {
        "Magisk.apk":        download(MAGISK_URL, CACHE_HOME / "Magisk.apk", 5 * 1024 * 1024),
        "LSPosed.zip":       download(VECTOR_URL, CACHE_HOME / "LSPosed.zip", 2 * 1024 * 1024),
        "modmenu.apk":       download(MODMENU_URL, CACHE_HOME / "shopee-modmenu.apk", 50 * 1024),
        "gmsfix.apk":        download(GMSFIX_URL, CACHE_HOME / "shopee-gmsfix.apk", 5 * 1024),
        "emu-mask.zip":      download(EMUMASK_URL, CACHE_HOME / "shopee-emu-mask.zip", 500),
        "shopee-patched.apk": download(SHOPEE_APK_URL, CACHE_HOME / "shopee-patched.apk", 50 * 1024 * 1024),
    }

    # Boot emulator
    log("starting emulator...")
    start_emulator()
    dev = wait_boot()

    time.sleep(10)  # biar system services settle

    # Install Magisk Manager APK (biar user bisa manage via GUI nanti)
    adb(["-s", dev, "install", "-r", str(files["Magisk.apk"])])

    # Install Shopee patched
    adb(["-s", dev, "install", "-r", str(files["shopee-patched.apk"])])

    # Install modmenu + gmsfix
    adb(["-s", dev, "install", "-r", str(files["modmenu.apk"])])
    adb(["-s", dev, "install", "-r", str(files["gmsfix.apk"])])

    # Push LSPosed + emu-mask ke tmp, install via Magisk CLI
    for name, local in [("LSPosed.zip", files["LSPosed.zip"]),
                         ("emu-mask.zip", files["emu-mask.zip"])]:
        adb(["-s", dev, "push", str(local), f"/data/local/tmp/{name}"])
        adb(["-s", dev, "shell", "su", "-c",
             f"magisk --install-module /data/local/tmp/{name}"], check=False)

    log("stack installed. Rebooting emulator...")
    adb(["-s", dev, "reboot"])
    time.sleep(5)
    dev = wait_boot()

    mark("apps_installed")
    log("All apps installed + modules enabled")

# ---- Phase 5: Launch + verify ----

def phase_launch() -> None:
    log("=== PHASE 5: Launch Shopee + verify ===", prefix=">")
    dev = None
    r = adb(["devices"], check=False)
    for line in r.stdout.splitlines():
        if "emulator" in line and line.endswith("\tdevice"):
            dev = line.split("\t")[0]
            break
    if not dev:
        die("no emulator running — jalankan phase_apps dulu")

    adb(["-s", dev, "shell", "monkey", "-p", "com.shopee.id",
         "-c", "android.intent.category.LAUNCHER", "1"], check=False)
    time.sleep(10)
    log("Shopee launched. Buka emulator window, tap mod menu ball di kiri atas.")
    log("Login via OTP/password/Google (dengan gmsfix enabled).")

# ---- Main ----

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["sdk", "avd", "magisk", "apps", "launch", "all"], default="all")
    ap.add_argument("--skip-sdk", action="store_true")
    ap.add_argument("--skip-avd", action="store_true")
    ap.add_argument("--skip-magisk", action="store_true")
    ap.add_argument("--reset", action="store_true", help="hapus semua state checkpoint")
    args = ap.parse_args()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        log("state reset — next run akan rerun semua phase")
        return

    log(f"OS: {OS} ({platform.machine()})")
    log(f"Python: {platform.python_version()}")
    log(f"SDK:   {SDK_HOME}")
    log(f"Cache: {CACHE_HOME}")
    log("")

    if args.phase == "all":
        if not args.skip_sdk:    phase_sdk()
        if not args.skip_avd:    phase_avd()
        if not args.skip_magisk: phase_magisk()
        phase_apps()
        phase_launch()
    elif args.phase == "sdk":
        phase_sdk()
    elif args.phase == "avd":
        phase_avd()
    elif args.phase == "magisk":
        phase_magisk()
    elif args.phase == "apps":
        phase_apps()
    elif args.phase == "launch":
        phase_launch()

    log("")
    log("DONE 🎉", prefix=">")
    log("Buka emulator window → mod menu ball (kiri atas) → semua toggle ready")
    log("Shopee login (OTP / email / Google via gmsfix) → test shopping")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("interrupted")
