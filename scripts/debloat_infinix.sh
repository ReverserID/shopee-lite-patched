#!/bin/bash
# Infinix XOS Debloat Script — remove bloatware, keep essentials
# Tested on Infinix X6873 (Android 15, XOS 15)
# Usage: bash debloat_infinix.sh [device_serial]

D="${1:-143382554V104575}"
ADB="adb -s $D"

echo "=== Infinix XOS Debloat ==="
echo "Device: $D"
echo ""

# ─── TIER 1: Transsion/Infinix/XOS bloat (safe to remove) ───
BLOAT_TRANSION=(
    # AI junk
    "com.transsion.aicore.cv"
    "com.transsion.aicore.cv.matting"
    "com.transsion.aicore.llm"
    "com.transsion.aicore.main"
    "com.transsion.aicore.matting"
    "com.transsion.aicore.ocr"
    "com.transsion.aicore.speech"
    "com.transsion.aisupportercore"
    "com.transsion.aivoiceassistant"
    "com.transsion.aiwallpaper"
    "com.transsion.aiwriting"
    "com.transsion.aiwriting.overlay"
    "com.transsion.overlay.aivoiceassistant"
    "com.transsion.kolun.aiservice"
    "com.transsion.kolun.assistant"
    "com.imaging.aiengine"

    # Live wallpapers (all)
    "com.transsion.livewallpaper.colorart"
    "com.transsion.livewallpaper.fantasy"
    "com.transsion.livewallpaper.gt30"
    "com.transsion.livewallpaper.magictouch"
    "com.transsion.livewallpaper.mondrian"
    "com.transsion.livewallpaper.page"
    "com.transsion.livewallpaper.pictorial"
    "com.transsion.livewallpaper.theme"

    # Theme stuff
    "com.transsion.theme"
    "com.transsion.theme.icon"
    "com.transsion.magicfont"
    "com.transsion.magicshow"
    "com.transsion.os.typeface"
    "com.theme.icondefaultshape"
    "com.theme.icondefaultshape_d40"
    "com.theme.icondefaultshape_mlbb"
    "com.theme.icondefaultshape_pubgm"
    "com.theme.icondefaultshape_rov"
    "com.theme.icondefaultshape_x832"
    "com.theme.icondefaultshape_x833"
    "com.theme.icondefaultshape_x842"
    "com.theme.icondefaultshape_x930"
    "com.android.theme.font.notoserifsource"

    # XOS junk apps
    "com.transsion.magazineservice.xos"
    "com.transsion.personalizedService.xos"
    "com.transsion.globalsearch"
    "com.transsion.gamespace.app"
    "com.transsion.smartpanel"
    "com.transsion.smartpanel.overlay"
    "com.transsion.smartrecognition"
    "com.transsion.smartmessage"
    "com.transsion.dynamicbar"
    "com.transsion.dynamicbar.overlay"
    "com.transsion.aod"
    "com.transsion.tips"
    "com.transsion.manualguide"
    "com.transsion.repaircard"
    "com.transsion.carlcare"
    "com.transsion.trancare"
    "com.trassion.infinix.xclub"

    # AI writing/assistant overlays
    "com.transsion.folax"
    "com.transsion.tranvoicecommand"
    "com.transsion.livecaption"
    "com.transsion.healthlife"
    "com.transsion.inearmonitor"

    # Bloat apps
    "com.transsion.easypic"
    "com.transsion.fmradio"
    "com.transsion.irremote"
    "com.transsion.iotcard"
    "com.transsion.iotservice"
    "com.transsion.compass"
    "com.transsion.batterylab"
    "com.transsion.dualapp"
    "com.transsion.mobilecloner"
    "com.transsion.letswitch"
    "com.transsion.childmode"
    "com.transsion.childmode.resoverlay"
    "com.transsion.applock"
    "com.transsion.cloudserver"
    "com.transsion.pcconnect"
    "com.transsion.airtransfer"
    "com.transsion.connectx.mirror.source"
    "com.transsion.audiosmartconnect"
    "com.transsion.faceid"
    "com.transsion.multiwindow"
    "com.transsion.necessity"
    "com.transsion.nephilim"
    "com.transsion.mol"
    "com.transsion.spl"
    "com.transsion.spld"
    "com.transsion.sru"
    "com.transsion.succ"
    "com.transsion.statisticalsales"
    "com.transsion.tabe"
    "com.transsion.teop"
    "com.transsion.thunderback"
    "com.transsion.tranengine"
    "com.transsion.tranfacmode"
    "com.transsion.tranradionet"
    "com.transsion.uxdetector"
    "com.transsion.zahooc"
    "com.transsion.sk"
    "com.transsion.plat.appupdate"
    "com.transsion.systemupdate"
    "com.transsion.scanningrecharger"
    "com.transsion.spacesaversdk"
    "com.transsion.microintelligence"
    "com.transsion.aftersalecalibrationtool"
    "com.transsion.aichargeprovider"

    # Third-party bloat
    "com.facemoji.lite.transsion"
    "com.funbase.xradio"
    "com.rlk.weathers"
    "com.scorpio.securitycom"
    "com.sh.smart.caller"
    "com.talpa.hiservice"
    "com.hoffnung"
    "com.idea.questionnaire"
    "com.geniex.vsimhelper"
    "id.mjs.etalaseapp"
    "tech.palm.find"
    "tech.palm.id"
    "com.xui.xhide"
    "com.gallery20"
    "com.debug.loggerui"
    "com.westalgo.factorycamera"

    # XOS Launcher (replace with Nova/Lawnchair)
    # "com.transsion.XOSLauncher"  # keep for now — need launcher

    # Theme hub
    "com.transsion.thub.res"
    "com.transsion.thub.res.auto_generated_rro_product__"
)

# ─── TIER 2: Google bloat (keep GMS + Play Store) ───
BLOAT_GOOGLE=(
    "com.google.android.youtube"
    "com.google.android.apps.youtube.music"
    "com.google.android.videos"
    "com.google.android.apps.maps"
    "com.google.android.apps.photos"
    "com.google.android.apps.docs"
    "com.google.android.gm"
    "com.google.android.apps.tachyon"          # Duo
    "com.google.android.apps.wellbeing"
    "com.google.android.apps.safetyhub"
    "com.google.android.apps.nbu.files"        # Files by Google
    "com.google.android.googlequicksearchbox"   # Google app
    "com.google.android.marvin.talkback"        # Accessibility
    "com.google.android.tts"                    # Text-to-speech
    "com.google.android.feedback"
    "com.google.android.partnersetup"
    "com.google.android.projection.gearhead"    # Android Auto
    "com.google.ar.core"                        # AR Core
    "com.google.android.apps.restore"
    "com.google.android.gms.location.history"
    "com.google.android.gms.supervision"
    "com.google.android.health.connect.backuprestore"
    "com.google.android.healthconnect.controller"
    "com.google.android.ondevicepersonalization.services"
    "com.google.android.federatedcompute"
    "com.google.android.appsearch.apk"
    "com.google.android.as"                     # Android System Intelligence
    "com.google.android.as.oss"
    "com.google.android.devicelockcontroller"
    "com.google.android.hotspot2.osulogin"
    "com.google.android.printservice.recommendation"
    "com.google.android.modulemetadata"
    "com.google.android.configupdater"
    "com.google.android.onetimeinitializer"
    "com.google.mainline.telemetry"
)

# ─── TIER 3: MediaTek bloat (keep telephony/IMS essential) ───
BLOAT_MTK=(
    "com.mediatek.engineermode"
    "com.mediatek.ygps"
    "com.mediatek.voiceunlock"
    "com.mediatek.mdmlsample"
    "com.mediatek.omacp"
    "com.mediatek.batterywarning"
    "com.mediatek.gbaservice"
    "com.mediatek.gnss.nonframeworklbs"
    "com.mediatek.location.lppe.main"
    "com.mediatek.location.mtkgeofence"
    "com.mediatek.mdmconfig"
    "com.mediatek.schpwronoff"
    "com.mediatek.simprocessor"
    "com.mediatek.atmwifimeta"
)

# ─── KEEP (do not remove) ───
# com.android.* (core system)
# com.google.android.gms (Google Play Services)
# com.google.android.vending (Play Store)
# com.google.android.gsf (Google Services Framework)
# com.google.android.webview (WebView)
# com.google.android.packageinstaller
# com.google.android.permissioncontroller
# com.google.android.documentsui
# com.google.android.networkstack*
# com.google.android.captiveportallogin
# com.google.android.ext.services
# com.google.android.ext.shared
# com.google.android.cellbroadcast*
# com.google.android.sdksandbox
# com.google.android.rkpdapp
# com.google.android.safetycenter.resources
# com.google.android.server.deviceconfig.resources
# com.google.android.setupwizard
# com.google.android.syncadapters.*
# com.google.android.wifi.*
# com.google.android.connectivity.resources
# com.google.android.overlay.* (overlays needed for GMS)
# com.google.mainline.adservices
# com.android.chrome (browser — keep or replace)
# com.mediatek.ims (VoLTE — essential)
# com.mediatek.telephony (essential)
# com.transsion.camera (camera — keep or replace)
# com.transsion.calculator (keep or replace)
# com.transsion.calendar (keep or replace)
# com.transsion.deskclock (keep or replace)
# com.transsion.notebook (keep or replace)
# com.transsion.soundrecorder (keep or replace)
# com.transsion.screenrecorder (keep or replace)
# com.transsion.screencapture (keep or replace)
# com.transsion.filemanagerx (keep or replace)
# com.transsion.settings.* (system settings — keep)
# com.transsion.tele.settings (essential)
# com.transsion.net.wifi (essential)
# com.transsion.resolver (essential)
# com.transsion.XOSLauncher (launcher — replace later)

echo "[1/3] Tier 1: Transsion/XOS bloat (${#BLOAT_TRANSION[@]} packages)"
for pkg in "${BLOAT_TRANSION[@]}"; do
    $ADB shell "pm uninstall --user 0 $pkg" 2>/dev/null && echo "  ✓ $pkg" || echo "  ✗ $pkg (not found or protected)"
done

echo ""
echo "[2/3] Tier 2: Google bloat (${#BLOAT_GOOGLE[@]} packages)"
for pkg in "${BLOAT_GOOGLE[@]}"; do
    $ADB shell "pm uninstall --user 0 $pkg" 2>/dev/null && echo "  ✓ $pkg" || echo "  ✗ $pkg (not found or protected)"
done

echo ""
echo "[3/3] Tier 3: MediaTek bloat (${#BLOAT_MTK[@]} packages)"
for pkg in "${BLOAT_MTK[@]}"; do
    $ADB shell "pm uninstall --user 0 $pkg" 2>/dev/null && echo "  ✓ $pkg" || echo "  ✗ $pkg (not found or protected)"
done

echo ""
echo "=== Done! Reboot recommended ==="
echo "Remaining packages: $($ADB shell 'pm list packages -s | wc -l')"
