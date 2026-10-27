# Shopee Lite — Patched

Repackaged **Shopee Lite** (`com.shopee.lite.id`, v2.93.61) with a built-in mod menu and SSL bypass. Works **without root**.

## What's inside

- **SSL bypass** — certificate pinning disabled (conscrypt TrustManager, hostname verifier, OkHttp `CertificatePinner`)
- **Mod menu** (floating overlay):
  - SSL Unpin toggle
  - Hide Root / Emulator Bypass / SPS-TongDun bypass (anti-detect)
  - user-behavior tracker blocker
  - optional HTTP proxy routing — app traffic or system-wide (root)
  - device fingerprint rotation (root)
- **No root required** — patches are embedded with [LSPatch](https://github.com/LSPosed/LSPatch). Root only unlocks the features marked *(root)* above.

## Install

1. Uninstall the existing Shopee Lite first (the patched APK has a different signature).
2. Install `shopee-lite-2.93.61-patched.apk` (allow install from unknown sources).
3. Launch the app — the floating ball opens the mod menu.

## Notes

- The mod menu is gated behind a [reverser.id](https://reverser.id) forum login.
- For research and educational use. Your account, your risk.

## Download

Get the APK from the [Releases](https://github.com/ReverserID/shopee-lite-patched/releases) page.
