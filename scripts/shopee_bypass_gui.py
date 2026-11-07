#!/usr/bin/env python3
"""
Shopee Anti-Emu Bypass Automator - GUI
Full automated setup for a fresh LDPlayer/AVD instance.

Steps:
  1. Detect/connect emulator via ADB
  2. Verify root (Magisk) presence
  3. Push frida-server
  4. Install Magisk emu-mask module (fake props + fake /proc/cpuinfo)
  5. Reboot + wait boot complete
  6. Install Shopee patched bundle (base + splits)
  7. Launch Shopee + grant overlay + location permissions
  8. (Optional) Start frida-server for runtime hooks

All assets pulled from workspace. Edit CONFIG at top if files move.
"""

import os, sys, time, json, threading, subprocess, zipfile, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# ─── CONFIG ──────────────────────────────────────────────────────────────────
WORKSPACE = Path(r"C:/Users/Administrator/Documents/PROJECT/ReverserID")
SHUPI     = WORKSPACE / "Shupi"
TOOLS     = WORKSPACE / "_tools"

ADB = shutil.which("adb") or "adb"

CONFIG = {
    "adb"             : ADB,
    "patched_base"    : SHUPI / "_patch2" / "base-fullpatched.apk",
    "split_arm64"     : SHUPI / "_patch2" / "orig_bundle" / "split_config.arm64_v8a.apk",
    "split_xhdpi"     : SHUPI / "_patch2" / "orig_bundle" / "split_config.xhdpi.apk",
    "emu_mask_zip"    : SHUPI / "shopee-emu-mask-v2.zip",
    "frida_server"    : TOOLS / "frida-server-17.25.1-android-x86_64",
    "fake_cpuinfo"    : SHUPI / "_mod_patched" / "fake_cpuinfo",
    "service_sh"      : SHUPI / "_mod_patched" / "service.sh",
    "post_fs_data_sh" : SHUPI / "_mod_patched" / "post-fs-data.sh",
    "shopee_pkg"      : "com.shopee.id",
}

# Common emulator ADB ports
CANDIDATE_PORTS = [5555, 5556, 5557, 5558, 5559, 5560, 5562, 5564, 5566,
                   5568, 5570, 5574, 5585, 5597, 7555, 21503]


# ─── CORE HELPERS ────────────────────────────────────────────────────────────
class ADBError(Exception): pass


def run(cmd, timeout=60, check=False):
    """Run shell command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))
        if check and r.returncode != 0:
            raise ADBError(f"cmd failed: {cmd}\n{r.stderr}")
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        raise ADBError(f"timeout: {cmd}")


def adb(serial, *args, timeout=60):
    cmd = [CONFIG["adb"]]
    if serial:
        cmd += ['-s', serial]
    cmd += list(args)
    return run(cmd, timeout=timeout)


def adb_shell(serial, cmd, timeout=60, as_root=False):
    if as_root:
        cmd = f"su -c '{cmd}'"
    rc, out, err = adb(serial, 'shell', cmd, timeout=timeout)
    return rc, out, err


# ─── GUI ─────────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        self.serial = tk.StringVar()
        self.status = tk.StringVar(value="Idle")
        self.working = False

        root.title("Shopee Bypass Automator")
        root.geometry("1000x720")
        root.minsize(900, 600)

        self._build_ui()
        self._set_theme()
        self._log_initial()

    # ────────────── UI construction ──────────────
    def _set_theme(self):
        try:
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('TButton', padding=6)
            style.configure('Big.TButton', padding=10, font=('Segoe UI', 10, 'bold'))
            style.configure('Danger.TButton', foreground='#b00020')
            style.configure('Ok.TLabel', foreground='#1b5e20')
            style.configure('Err.TLabel', foreground='#b71c1c')
        except Exception:
            pass

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill='both', expand=True)

        # Top: device select + status
        top = ttk.LabelFrame(outer, text=" Device ", padding=10)
        top.pack(fill='x', pady=(0, 10))

        ttk.Label(top, text="ADB Target:").grid(row=0, column=0, sticky='w')
        self.serial_combo = ttk.Combobox(top, textvariable=self.serial, width=28,
                                         values=[])
        self.serial_combo.grid(row=0, column=1, padx=6, sticky='w')

        ttk.Button(top, text="Scan devices",
                   command=lambda: self._bg(self.scan_devices)).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Try connect ports",
                   command=lambda: self._bg(self.try_connect_ports)).grid(row=0, column=3, padx=4)
        ttk.Button(top, text="Info",
                   command=lambda: self._bg(self.show_device_info)).grid(row=0, column=4, padx=4)

        ttk.Label(top, text="Status:").grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.status_label = ttk.Label(top, textvariable=self.status, foreground='#1a237e')
        self.status_label.grid(row=1, column=1, columnspan=4, sticky='w', pady=(8, 0))

        # Middle: step buttons
        steps = ttk.LabelFrame(outer, text=" Steps (run manually, or FULL SETUP) ",
                               padding=10)
        steps.pack(fill='x', pady=(0, 10))

        step_defs = [
            ("1. Verify root (Magisk)",      self.step_verify_root),
            ("2. Install emu-mask module",   self.step_install_emumask),
            ("3. Push frida-server",         self.step_push_frida),
            ("4. Reboot + wait",             self.step_reboot_wait),
            ("5. Manual spoof props",        self.step_manual_spoof),
            ("6. Install Shopee bundle",     self.step_install_shopee),
            ("7. Launch Shopee",             self.step_launch_shopee),
            ("8. Grant overlay perm",        self.step_grant_overlay),
            ("9. Start frida-server",        self.step_start_frida),
        ]
        for i, (label, fn) in enumerate(step_defs):
            r, c = i // 3, i % 3
            ttk.Button(steps, text=label, width=28,
                       command=lambda f=fn: self._bg(f)).grid(row=r, column=c, padx=4, pady=3,
                                                              sticky='ew')
        for c in range(3): steps.grid_columnconfigure(c, weight=1)

        # Big full-setup button + utility row
        ctl = ttk.Frame(outer)
        ctl.pack(fill='x', pady=(0, 10))
        ttk.Button(ctl, text="⚡ FULL AUTO SETUP (fresh LDPlayer)",
                   style='Big.TButton',
                   command=lambda: self._bg(self.full_auto)).pack(side='left', padx=4)
        ttk.Button(ctl, text="Uninstall Shopee",
                   command=lambda: self._bg(self.action_uninstall_shopee)).pack(side='left', padx=4)
        ttk.Button(ctl, text="Open LDPlayer screenshot",
                   command=lambda: self._bg(self.action_screenshot)).pack(side='left', padx=4)
        ttk.Button(ctl, text="Clear log",
                   command=lambda: self.logbox.delete(1.0, 'end')).pack(side='right', padx=4)

        # Config paths (editable)
        cfg = ttk.LabelFrame(outer, text=" File Paths (edit if moved) ", padding=10)
        cfg.pack(fill='x', pady=(0, 10))
        self.path_entries = {}
        keys = ["patched_base", "split_arm64", "split_xhdpi", "emu_mask_zip",
                "frida_server", "fake_cpuinfo"]
        for i, k in enumerate(keys):
            ttk.Label(cfg, text=k).grid(row=i, column=0, sticky='w', padx=(0, 6))
            e = ttk.Entry(cfg, width=85)
            e.insert(0, str(CONFIG[k]))
            e.grid(row=i, column=1, sticky='ew', pady=1)
            self.path_entries[k] = e

            ttk.Button(cfg, text="📁", width=3,
                       command=lambda key=k: self._pick_path(key)).grid(row=i, column=2, padx=3)
        cfg.grid_columnconfigure(1, weight=1)

        # Log area
        log_frame = ttk.LabelFrame(outer, text=" Log ", padding=5)
        log_frame.pack(fill='both', expand=True)
        self.logbox = scrolledtext.ScrolledText(log_frame, wrap='word', height=14,
                                                font=('Consolas', 9), bg='#111', fg='#dfe',
                                                insertbackground='#dfe')
        self.logbox.pack(fill='both', expand=True)
        self.logbox.tag_config('ok',   foreground='#9efa8d')
        self.logbox.tag_config('err',  foreground='#ff8a80')
        self.logbox.tag_config('warn', foreground='#ffe082')
        self.logbox.tag_config('info', foreground='#90caf9')

    def _pick_path(self, key):
        initial = str(CONFIG[key])
        if initial and Path(initial).is_file():
            p = filedialog.askopenfilename(initialfile=initial)
        else:
            p = filedialog.askopenfilename()
        if p:
            self.path_entries[key].delete(0, 'end')
            self.path_entries[key].insert(0, p)

    def _sync_paths(self):
        for k, e in self.path_entries.items():
            CONFIG[k] = Path(e.get())

    # ────────────── logging + threading ──────────────
    def log(self, msg, tag=None):
        ts = time.strftime("%H:%M:%S")
        self.logbox.insert('end', f"[{ts}] {msg}\n", tag or '')
        self.logbox.see('end')
        self.root.update_idletasks()

    def _log_initial(self):
        self.log("Shopee Anti-Emu Bypass Automator", 'info')
        self.log(f"ADB: {CONFIG['adb']}")
        self.log(f"Workspace: {SHUPI}")
        self.log("Click 'Scan devices' to begin.", 'info')
        for k in ["patched_base", "split_arm64", "split_xhdpi", "emu_mask_zip",
                  "frida_server", "fake_cpuinfo"]:
            p = Path(str(CONFIG[k]))
            tag = 'ok' if p.exists() else 'warn'
            mark = '✓' if p.exists() else '✗ MISSING'
            self.log(f"  [{mark}] {k} = {p}", tag)

    def _bg(self, fn):
        if self.working:
            self.log("Already running a task.", 'warn')
            return
        def wrapper():
            self.working = True
            self.status.set("Working…")
            try:
                fn()
                self.status.set("Done")
            except ADBError as e:
                self.log(f"ADB error: {e}", 'err')
                self.status.set("Error")
            except Exception as e:
                self.log(f"Unhandled: {type(e).__name__}: {e}", 'err')
                self.status.set("Error")
            finally:
                self.working = False
        threading.Thread(target=wrapper, daemon=True).start()

    # ────────────── device actions ──────────────
    def scan_devices(self):
        self.log("Scanning adb devices…", 'info')
        rc, out, _ = run([CONFIG['adb'], 'devices', '-l'])
        lines = [l for l in out.splitlines() if 'device' in l and 'List of' not in l]
        serials = [l.split()[0] for l in lines]
        self.serial_combo['values'] = serials
        if serials:
            if not self.serial.get() or self.serial.get() not in serials:
                self.serial.set(serials[0])
            self.log(f"Found: {serials}", 'ok')
        else:
            self.log("No devices. Try 'Try connect ports'.", 'warn')

    def try_connect_ports(self):
        self.log("Trying common LDPlayer/MuMu ports…", 'info')
        rc, _, _ = run([CONFIG['adb'], 'start-server'], timeout=15)
        hits = []
        for p in CANDIDATE_PORTS:
            rc, out, err = run([CONFIG['adb'], 'connect', f'127.0.0.1:{p}'], timeout=5)
            if 'connected' in out.lower() and 'cannot' not in out.lower():
                hits.append(f'127.0.0.1:{p}')
                self.log(f"✓ Connected 127.0.0.1:{p}", 'ok')
        self.scan_devices()

    def show_device_info(self):
        s = self.serial.get()
        if not s: return self.log("Pick a device.", 'warn')
        rc, out, _ = adb_shell(s, "getprop ro.product.model; getprop ro.product.manufacturer; "
                               "getprop ro.product.cpu.abi; getprop ro.build.version.sdk; "
                               "getprop ro.build.fingerprint")
        self.log("Device info:\n  " + out.replace('\n', '\n  '), 'info')
        rc, out2, _ = adb_shell(s, "head -2 /proc/cpuinfo")
        self.log("cpuinfo:\n  " + out2.replace('\n', '\n  '))

    # ────────────── step implementations ──────────────
    def _need_serial(self):
        s = self.serial.get()
        if not s:
            raise ADBError("No device selected. Scan devices first.")
        return s

    def step_verify_root(self):
        s = self._need_serial()
        rc, out, _ = adb_shell(s, "id", as_root=True)
        if 'uid=0' in out:
            self.log(f"Root OK: {out}", 'ok')
        else:
            self.log(f"Root NOT available (su returned: {out}).\n"
                     "LDPlayer Settings → Advanced → Root enabled?", 'err')
            raise ADBError("No root")
        rc, out, _ = adb_shell(s, "ls /data/adb/magisk/magisk64")
        if '/data/adb/magisk' in out:
            self.log("Magisk binary present", 'ok')
        else:
            self.log("Magisk NOT installed. Install Magisk Delta or Magisk via LDPlayer.", 'err')

    def step_install_emumask(self):
        self._sync_paths()
        s = self._need_serial()
        src = Path(CONFIG["emu_mask_zip"])
        if not src.exists():
            raise ADBError(f"emu-mask zip missing: {src}")
        self.log(f"Push module zip → device: {src.name}")
        adb(s, 'push', str(src), '/sdcard/')
        self.log("Install via magisk64 --install-module")
        rc, out, _ = adb_shell(s, f"/data/adb/magisk/magisk64 --install-module /sdcard/{src.name}",
                               as_root=True, timeout=60)
        self.log(out.splitlines()[-1] if out else "(no output)")
        # Push scripts manually (install-module sometimes drops them)
        mod_dir = "/data/adb/modules/shopee_emu_mask"
        for key, dest in [("fake_cpuinfo", "fake_cpuinfo"),
                          ("service_sh", "service.sh"),
                          ("post_fs_data_sh", "post-fs-data.sh")]:
            src = Path(CONFIG.get(key, ""))
            if not src.exists():
                self.log(f"  skip {dest} (missing {src})", 'warn')
                continue
            adb(s, 'push', str(src), f'/sdcard/{dest}')
            adb_shell(s, f"cp /sdcard/{dest} {mod_dir}/", as_root=True)
            if dest.endswith('.sh'):
                adb_shell(s, f"chmod 755 {mod_dir}/{dest}", as_root=True)
            self.log(f"  pushed {dest}", 'ok')
        self.log("emu-mask installed. Reboot required to activate post-fs/service scripts.", 'ok')

    def step_push_frida(self):
        self._sync_paths()
        s = self._need_serial()
        src = Path(CONFIG["frida_server"])
        if not src.exists():
            raise ADBError(f"frida-server missing: {src}")
        self.log(f"Push frida-server ({src.stat().st_size/1e6:.1f} MB)…")
        adb(s, 'push', str(src), '/data/local/tmp/frida-server', timeout=120)
        adb_shell(s, "chmod +x /data/local/tmp/frida-server", as_root=True)
        self.log("frida-server pushed. Start with step 9 when needed.", 'ok')

    def step_reboot_wait(self):
        s = self._need_serial()
        self.log("Rebooting device…")
        adb(s, 'reboot')
        time.sleep(5)
        self.log("Waiting boot-complete…")
        adb(s, 'wait-for-device', timeout=120)
        # poll boot_completed
        for _ in range(60):
            rc, out, _ = adb_shell(s, "getprop sys.boot_completed", timeout=10)
            if out.strip() == '1':
                self.log("Boot completed", 'ok')
                return
            time.sleep(2)
        self.log("Timeout waiting boot_completed (continuing).", 'warn')

    def step_manual_spoof(self):
        """Fallback: run resetprop + bind-mount directly (useful if service.sh didn't fire)."""
        s = self._need_serial()
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
            adb_shell(s, c, as_root=True)
        rc, out, _ = adb_shell(s, "getprop ro.product.model; getprop ro.product.cpu.abi")
        self.log("After spoof: " + out.replace('\n', ' | '), 'ok')
        rc, out, _ = adb_shell(s, "head -2 /proc/cpuinfo", as_root=True)
        self.log("cpuinfo: " + out.replace('\n', ' | '))

    def step_install_shopee(self):
        self._sync_paths()
        s = self._need_serial()
        base = Path(CONFIG["patched_base"])
        s_arm = Path(CONFIG["split_arm64"])
        s_res = Path(CONFIG["split_xhdpi"])
        for p in [base, s_arm, s_res]:
            if not p.exists():
                raise ADBError(f"Missing APK: {p}")
        # Uninstall if present
        adb(s, 'uninstall', CONFIG["shopee_pkg"], timeout=30)
        self.log(f"Install bundle: base={base.stat().st_size//1024//1024}MB "
                 f"+ arm={s_arm.stat().st_size//1024//1024}MB "
                 f"+ res={s_res.stat().st_size//1024}KB …")
        rc, out, err = adb(s, 'install-multiple', '-r',
                           str(base), str(s_arm), str(s_res), timeout=180)
        if rc != 0 or 'Failure' in out:
            raise ADBError(f"install failed: {out} {err}")
        self.log("Shopee bundle installed ✓", 'ok')

    def step_launch_shopee(self):
        s = self._need_serial()
        adb_shell(s, f"am force-stop {CONFIG['shopee_pkg']}")
        time.sleep(1)
        adb_shell(s, f"monkey -p {CONFIG['shopee_pkg']} -c android.intent.category.LAUNCHER 1")
        self.log("Shopee launch requested. Waiting 25s…")
        time.sleep(25)
        rc, out, _ = adb_shell(s, "dumpsys window | grep mCurrentFocus")
        self.log(out, 'info' if CONFIG['shopee_pkg'] in out else 'warn')

    def step_grant_overlay(self):
        s = self._need_serial()
        adb_shell(s, f"appops set {CONFIG['shopee_pkg']} SYSTEM_ALERT_WINDOW allow")
        adb_shell(s, f"pm grant {CONFIG['shopee_pkg']} android.permission.ACCESS_FINE_LOCATION")
        adb_shell(s, f"pm grant {CONFIG['shopee_pkg']} android.permission.ACCESS_COARSE_LOCATION")
        adb_shell(s, f"pm grant {CONFIG['shopee_pkg']} android.permission.POST_NOTIFICATIONS")
        self.log("Granted: overlay + location + notifications ✓", 'ok')

    def step_start_frida(self):
        s = self._need_serial()
        adb_shell(s, "pkill frida-server", as_root=True)
        time.sleep(1)
        adb_shell(s, "nohup /data/local/tmp/frida-server -D >/dev/null 2>&1 &",
                  as_root=True)
        time.sleep(2)
        rc, out, _ = adb_shell(s, "ps -A | grep frida", as_root=True)
        if 'frida-server' in out:
            self.log(f"frida-server running: {out.strip()}", 'ok')
            # port forward for host convenience
            run([CONFIG['adb'], '-s', s, 'forward', 'tcp:27042', 'tcp:27042'])
            self.log("adb forward tcp:27042 → tcp:27042 set.")
        else:
            self.log("frida-server not detected after start.", 'err')

    # ────────────── composite actions ──────────────
    def full_auto(self):
        """Run full chain: verify → install module → push frida → reboot →
           manual spoof fallback → install Shopee → launch → grant perms →
           start frida. Each step logs + continues even on soft errors."""
        self.log("=" * 60, 'info')
        self.log("FULL AUTO SETUP — begin", 'info')
        self.log("=" * 60, 'info')
        chain = [
            ("verify root", self.step_verify_root),
            ("install emu-mask", self.step_install_emumask),
            ("push frida-server", self.step_push_frida),
            ("reboot + wait", self.step_reboot_wait),
            ("manual spoof fallback", self.step_manual_spoof),
            ("install Shopee bundle", self.step_install_shopee),
            ("launch Shopee", self.step_launch_shopee),
            ("grant permissions", self.step_grant_overlay),
            ("start frida-server", self.step_start_frida),
        ]
        for name, fn in chain:
            self.log(f"→ {name}", 'info')
            try:
                fn()
            except ADBError as e:
                self.log(f"  soft fail @ {name}: {e}", 'warn')
            except Exception as e:
                self.log(f"  hard fail @ {name}: {e}", 'err')
                break
        self.log("=" * 60, 'ok')
        self.log("FULL AUTO SETUP — complete. Open LDPlayer window to use Shopee.", 'ok')
        self.log("=" * 60, 'ok')

    def action_uninstall_shopee(self):
        s = self._need_serial()
        rc, out, _ = adb(s, 'uninstall', CONFIG["shopee_pkg"])
        self.log(f"uninstall: {out}", 'ok' if 'Success' in out else 'warn')

    def action_screenshot(self):
        s = self._need_serial()
        out_path = Path.home() / "Desktop" / f"shopee_{int(time.time())}.png"
        adb_shell(s, "screencap -p /sdcard/__sc.png")
        adb(s, 'pull', '/sdcard/__sc.png', str(out_path))
        self.log(f"Screenshot saved: {out_path}", 'ok')
        try:
            os.startfile(out_path)  # Windows
        except Exception:
            pass


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    try:
        root.tk.call('tk', 'scaling', 1.2)
    except Exception: pass
    app = App(root)
    root.mainloop()
