#!/bin/sh
# Shopee patched + microG installer — buat emulator / device tanpa Google Play Services.
# Download, verify, dan install microG stack (FakeStore + GmsCore + GsfProxy) ke device
# yang tersambung via adb. Signature spoofing MUST sudah aktif (Magisk sig-spoof module
# atau ROM-level support) — script akan warning kalau belum.
#
# Pakai:
#   sh install-microg.sh                       # install ke default device adb
#   sh install-microg.sh emulator-5554         # install ke device spesifik
#
# Dependency: adb, curl, sha256sum (coreutils / git-bash / wsl)

set -e

DEV="${1:-}"
ADB="adb"
if [ -n "$DEV" ]; then ADB="adb -s $DEV"; fi

MIRROR="https://github.com/microg"
WORK="$(mktemp -d)"
trap "rm -rf $WORK" EXIT

echo "[*] workspace: $WORK"
echo "[*] target device: $($ADB shell getprop ro.product.model 2>/dev/null || echo '?')"

# Fetch latest release URLs via GitHub API (no auth; rate limit tolerant for one shot)
pull() {
  REPO=$1; NAME=$2; OUT=$3
  URL=$(curl -sL "https://api.github.com/repos/microg/$REPO/releases/latest" \
    | grep "browser_download_url" | grep -i "\.apk" | head -1 | cut -d'"' -f4)
  if [ -z "$URL" ]; then
    echo "[!] $REPO latest release not found via API; fallback to raw"
    URL="https://nightly.link/microg/$REPO/latest/release/$NAME"
  fi
  echo "[+] $NAME <= $URL"
  curl -sLo "$WORK/$OUT" "$URL"
  SIZE=$(wc -c < "$WORK/$OUT")
  echo "    bytes=$SIZE sha256=$(sha256sum < "$WORK/$OUT" | awk '{print $1}')"
  if [ "$SIZE" -lt 10000 ]; then
    echo "[!] $NAME download too small — probably HTML error page; abort"
    exit 1
  fi
}

pull FakeStore FakeStore.apk fakestore.apk
pull GmsCore   GmsCore.apk   gmscore.apk
pull GsfProxy  GsfProxy.apk  gsfproxy.apk

# Signature spoofing check — microG needs it or Google Sign-In will fail silently.
echo "[*] checking signature spoofing capability..."
HAVE_SIGSPOOF=$($ADB shell "pm list packages | grep -iE 'nanodroid|signaturespoof|microg_spoof'" 2>/dev/null || true)
if [ -z "$HAVE_SIGSPOOF" ]; then
  echo "[!] WARNING: no NanoDroid/sig-spoof module terdeteksi."
  echo "    microG butuh signature spoofing untuk Google Sign-In jalan."
  echo "    Install dulu salah satu:"
  echo "      - NanoDroid-microG Magisk module (https://nanolx.org/nanolx/nanodroid)"
  echo "      - signature-spoofing-helper (https://github.com/ale5000-git/signature-spoofing-helper)"
  echo "      - atau pakai ROM dengan built-in sig spoof (LineageOS fork, iodéOS, /e/OS)"
  echo ""
  echo "    Lanjutkan install tanpa sig-spoof? (yes/no)"
  read ANS
  if [ "$ANS" != "yes" ]; then exit 2; fi
fi

# Uninstall real Play Store biar FakeStore menang signature
echo "[*] uninstalling real Play Store (if present) biar FakeStore menang..."
$ADB uninstall com.android.vending 2>&1 | tail -1 || true

# Install order: FakeStore first, then GmsCore, then GsfProxy
echo "[*] install FakeStore..."
$ADB install -r "$WORK/fakestore.apk" 2>&1 | tail -1

echo "[*] install GmsCore..."
$ADB install -r "$WORK/gmscore.apk" 2>&1 | tail -1

echo "[*] install GsfProxy..."
$ADB install -r "$WORK/gsfproxy.apk" 2>&1 | tail -1

# Grant microG permissions (biasanya butuh manual grant, kita auto buat yang critical)
echo "[*] granting microG permissions..."
for PERM in android.permission.FAKE_PACKAGE_SIGNATURE \
            android.permission.ACCESS_FINE_LOCATION \
            android.permission.READ_EXTERNAL_STORAGE \
            android.permission.READ_PHONE_STATE \
            android.permission.GET_ACCOUNTS; do
  $ADB shell pm grant com.google.android.gms "$PERM" 2>/dev/null || true
done

echo ""
echo "[*] done. Next steps:"
echo "    1. Buka 'microG Settings' app di device"
echo "    2. Jalan 'Self-Check' — semua item HARUS hijau"
echo "       Kalau 'Signature Spoofing' merah = sig-spoof blm aktif, Google Sign-In gak jalan"
echo "    3. 'Google Account' → login akun Google kamu"
echo "    4. 'Cloud Messaging' → ON"
echo "    5. Reboot device"
echo "    6. Launch Shopee → tap 'Lanjutkan dengan Google' → login jalan via microG"
echo ""
echo "[*] untuk fallback kalau Shopee signature pinning tolak Google (karena APK di-repack),"
echo "    install juga shopee-gmsfix-1.0.0.apk via LSPosed (scope: com.google.android.gms)"
