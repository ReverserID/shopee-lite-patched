# Shopee — Patched
> **🚀 v1.8.0 (2026-11-07)** — Auto-Setup GUI + microG Google Sign-In Unlock:
>
> - **GUI single-exe** (PyQt6, dark reverser.id theme): [`scripts/ShopeeBypass.exe`](scripts/ShopeeBypass.exe) (48 MB, no Python needed)
>   - Auto-detect LDPlayer9 instances via `vms/config/leidian*.config`
>   - 10-step auto-chain: wait boot → root → install Magisk → push frida → emu-mask → spoof props → install Shopee → grant 10+ perms → launch → Frida GMS cert fix
>   - ldconsole CLI integration: `set_root_mode`, `set_writable_disk`, `patch_config`, `install_apk`, `ld_setprop`
> - **microG Google Sign-In unlock** — 4 smali patches force Google button + APPAUTH browser flow (bypass GMS IPC): [`docs/microg/GOOGLE-SIGNIN-UNLOCK.md`](docs/microg/GOOGLE-SIGNIN-UNLOCK.md)
>   - `GoogleSignatureVerifier`: accept microG cert (4 methods return true)
>   - `connect3rd.b.d()`: force show Google button
>   - `helper.c0.a()`: GMS available = true
>   - `GoogleSignInClient.zba()`: APPAUTH flow (bypass GMS binding)
> - **Frida GMS cert spoof v3** — real Shopee cert embedded ([`patches/frida_gms_fix.js`](patches/frida_gms_fix.js) + [`patches/stock_cert_java.txt`](patches/stock_cert_java.txt))
> - **unidbg-sign SPSSDK signer** — Java/unidbg emulator passes WAF signature: [`docs/_SIGNER.md`](docs/_SIGNER.md)
> - **Coin claim automation** (WIP, blocked on `report_token` encryption): [`scripts/claim_auto.py`](scripts/claim_auto.py)
>
> **🔥 v1.7.2 (2025-11-03)** — Mod menu stability patch:
>
> - **Fix "undefined" toast + Beli Sekarang gak jalan** — `hookWebViewTraffic` lama nge-block captcha page Shopee ("/verify/traffic/error" untuk risk-flagged sessions) → infinite loop + JS error. Sekarang captcha render normal, user solve puzzle, lanjut checkout. [`modules/shopee-modmenu-1.7.2.apk`](https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-modmenu-1.7.2.apk)
> - **Fix "data login forum ilang mulu"** — StateStore lama cuma tulis via `su -c` yg fail di Shopee's app context. Sekarang tulis ke `/data/data/com.shopee.id/files/` (app sandbox, no root needed). Login forum sekali → persist across restarts.
> - **Fix tracker over-block** (v1.7.1) — `/receiver/api/v1/receiver/timestamp` endpoint tidak lagi di-block (penting buat sign timing). Only `/log-receiver/`, `/apt-log-receiver/`, `/event-receiver/` paths patronus di-stub.
> - **Feature Scanner** (opt-in toggle, v1.7.0) — tap klaim coin / voucher / checkout di Shopee → URL endpoint ter-log otomatis via logcat & LOGS pane. Capture endpoint TANPA HTTP Toolkit setup.
> - **48 real-device fingerprint profiles** (v1.7.0) — Pixel 6a-9 Pro, Samsung S23/S24/A-series, Xiaomi 14/Redmi Note 13, Oppo/Realme/vivo flagship.
> - **microG install helper** untuk emu non-GApps: [`scripts/install-microg.sh`](scripts/install-microg.sh)
> - **emu_mask Magisk module** buat emulator (resetprop + /proc/cpuinfo bind-mount): [`modules/shopee-emu-mask-1.0.zip`](https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-emu-mask-1.0.zip)
>
> 📋 **Roadmap fitur** (flash sale, auto-claim coin 11.11/Drama Cina, voucher auto-apply, mission bypass): [`FEATURES_ROADMAP.md`](FEATURES_ROADMAP.md). Butuh capture komunitas via Feature Scanner — forum: https://reverser.id/d/54
> 📖 **Setup emulator full automated (Windows/Mac/Linux, tanpa Android Studio)**: [`docs/SETUP-EMULATOR.md`](docs/SETUP-EMULATOR.md) — satu script Python handle SDK + AVD + Magisk patch headless + install stack.



Repackaged **Shopee Indonesia** (main app) and **Shopee Lite** with a built-in mod menu and SSL bypass. Works **without root**.

| Build | Package | Version | ABIs |
|---|---|---|---|
| [Shopee 3.83.36](https://github.com/ReverserID/shopee-lite-patched/releases/tag/v3.83.36) | `com.shopee.id` | 3.83.36 | armeabi-v7a, arm64-v8a |
| [Shopee Lite 2.93.61](https://github.com/ReverserID/shopee-lite-patched/releases/tag/v2.93.61) | `com.shopee.lite.id` | 2.93.61 | armeabi-v7a, arm64-v8a, x86_64 |

Both are single merged APKs — no split APKs / feature-delivery needed, so the classic "dfplugin incomplete install" crash is gone. (The main app does not ship x86_64 libraries; x86_64 emulators run it through their built-in ARM translation.)

## What's inside

- **SSL bypass** — certificate pinning disabled (conscrypt TrustManager, hostname verifier, OkHttp `CertificatePinner`)
- **Mod menu** (floating overlay) with:
  - SSL Unpin toggle
  - Hide Root / Emulator Bypass / SPS-TongDun bypass (anti-detect)
  - user-behavior tracker blocker
  - optional HTTP proxy routing (app traffic or system-wide, root)
  - device fingerprint rotation (root)
- **No root required** — the patches are embedded via [LSPatch](https://github.com/LSPosed/LSPatch). Root only unlocks the extra features marked above.

## Emulator (LDPlayer, MuMu, dst)

APK single-file di atas **crash di emulator** - proteksi runtime Shopee
bereaksi buruk saat APK di-repack jadi satu file. Pakai paket split khusus
emulator: [`shopee-3.83.36-emulator.zip`](https://github.com/ReverserID/shopee-lite-patched/releases/download/v3.83.36/shopee-3.83.36-emulator.zip)

Isinya 3 APK dengan signature sama - install pakai
`adb install-multiple base-487-lspatched.apk split_config.arm64_v8a.apk split_config.xhdpi.apk`
atau SAI. Detail di `README.txt` dalam zip. Shopee Lite tetap tidak jalan di
emulator (proteksinya mematikan process-nya) - paket ini untuk app utama saja.

## Login Google (root + LSPosed)

Karena APK di-sign ulang, tombol **Login with Google** ditolak Google Play
services (SHA-1 cert beda dari yang terdaftar). Fix-nya module Xposed:
[`modules/shopee-gmsfix-1.0.0.apk`](https://github.com/ReverserID/shopee-lite-patched/raw/main/modules/shopee-gmsfix-1.0.0.apk)

1. Install APK-nya, aktifkan di LSPosed, kasih scope **com.google.android.gms**
2. Reboot
3. Login Google jalan normal lagi

Module nge-spoof signature asli Shopee (Garena) di dalam proses Play services.
Tanpa root/LSPosed: tombol Google tetap tidak jalan - login pakai OTP/email/no.
HP tetap normal.

## Install

1. Uninstall the existing app (different signature).
2. Install the APK (allow "install from unknown sources").
3. Launch — the floating ball opens the mod menu. If the ball does not appear, grant **Display over other apps** (overlay) permission to the app, then relaunch — on a fresh install the system silently denies the overlay request.

## Notes

- The mod menu is gated with a reverser.id forum login (free registration link in the menu).
- For research and educational use. Your account, your risk.

## Download

Get the APKs from the [Releases](https://github.com/ReverserID/shopee-lite-patched/releases) page.
