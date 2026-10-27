# Shopee — Patched

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

## Install

1. Uninstall the existing app (different signature).
2. Install the APK (allow "install from unknown sources").
3. Launch — the floating ball opens the mod menu. If the ball does not appear, grant **Display over other apps** (overlay) permission to the app, then relaunch — on a fresh install the system silently denies the overlay request.

## Notes

- The mod menu is gated with a reverser.id forum login (free registration link in the menu).
- For research and educational use. Your account, your risk.

## Download

Get the APKs from the [Releases](https://github.com/ReverserID/shopee-lite-patched/releases) page.
