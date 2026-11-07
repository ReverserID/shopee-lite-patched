#!/bin/bash
# Infinix XOS Debloat v2 — CONSERVATIVE
# Only removes clearly-safe bloat. Keeps all system essentials.
# Tested: Infinix X6873 (Android 15, XOS 15)
#
# Categories:
#   SAFE    = no system dependency, pure bloat
#   OPTIONAL = user preference (camera/calc/clock apps)
#   KEEP    = system essential, DO NOT REMOVE

D="${1:-143382554V104575}"
ADB="adb -s $D"

echo "=== Infinix XOS Debloat v2 (conservative) ==="
echo "Device: $D"
echo ""

# ─── SAFE: Pure bloat, zero system dependency ───
SAFE=(
    # AI junk (no system dependency)
    "com.transsion.aicore.cv"
    "com.transsion.aicore.cv.matting"
    "com.transsion.aicore.llm"
    "com.transsion.aicore.main"
    "com.transsion.aicore.matting"
    "com.transsion.aicore.ocr"
    "com.transsion.aicore.speech"
    "com.transsion.aisupportercore"
    "com.transsion.aiwriting"
    "com.transsion.aiwriting.overlay"
    "com.transsion.aiwallpaper"
    "com.transsion.aivoiceassistant"
    "com.transsion.overlay.aivoiceassistant"
    "com.transsion.kolun.aiservice"
    "com.transsion.kolun.assistant"
    "com.imaging.aiengine"
    "com.transsion.aichargeprovider"

    # Live wallpapers (pure cosmetic)
    "com.transsion.livewallpaper.colorart"
    "com.transsion.livewallpaper.fantasy"
    "com.transsion.livewallpaper.gt30"
    "com.transsion.livewallpaper.magictouch"
    "com.transsion.livewallpaper.mondrian"
    "com.transsion.livewallpaper.page"
    "com.transsion.livewallpaper.pictorial"
    "com.transsion.livewallpaper.theme"

    # Theme engine + fonts (cosmetic)
    "com.transsion.magicfont"
    "com.transsion.os.typeface"
    "com.transsion.theme"
    "com.transsion.theme.icon"
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

    # XOS bloat apps
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
    "com.transsion.folax"
    "com.transsion.tranvoicecommand"
    "com.transsion.livecaption"
    "com.transsion.healthlife"
    "com.transsion.inearmonitor"
    "com.transsion.magicshow"

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
    "com.transsion.multiwindow"
    "com.transsion.spacesaversdk"
    "com.transsion.scanningrecharger"
    "com.transsion.microintelligence"
    "com.transsion.aftersalecalibrationtool"
    "com.transsion.nephilim"
    "com.transsion.mol"
    "com.transsion.sk"
    "com.xui.xhide"
    "com.gallery20"
    "com.debug.loggerui"
    "com.westalgo.factorycamera"
    "com.transsion.zahooc"
    "com.transsion.keyguardclock"
    "com.transsion.keyguardtheme"
    "com.transsion.tranfacmode"
    "com.transsion.tranradionet"
    "com.transsion.uxdetector"
    "com.transsion.tabe"
    "com.transsion.spl"
    "com.transsion.spld"
    "com.transsion.sru"
    "com.transsion.succ"
    "com.transsion.statisticalsales"
    "com.transsion.thunderback"
    "com.transsion.tranengine"
    "com.transsion.teop"
    "com.hoffnung"
    "com.idea.questionnaire"
    "com.geniex.vsimhelper"
    "com.facemoji.lite.transsion"
    "com.funbase.xradio"
    "com.rlk.weathers"
    "com.scorpio.securitycom"
    "com.sh.smart.caller"
    "com.talpa.hiservice"
    "id.mjs.etalaseapp"
    "tech.palm.find"
    "tech.palm.id"

    # Google bloat (keep GMS + Play Store + WebView)
    "com.google.android.youtube"
    "com.google.android.apps.youtube.music"
    "com.google.android.videos"
    "com.google.android.apps.maps"
    "com.google.android.apps.photos"
    "com.google.android.apps.docs"
    "com.google.android.gm"
    "com.google.android.apps.tachyon"
    "com.google.android.apps.wellbeing"
    "com.google.android.apps.safetyhub"
    "com.google.android.apps.nbu.files"
    "com.google.android.googlequicksearchbox"
    "com.google.android.marvin.talkback"
    "com.google.android.tts"
    "com.google.android.feedback"
    "com.google.android.partnersetup"
    "com.google.android.projection.gearhead"
    "com.google.ar.core"
    "com.google.android.apps.restore"
    "com.google.android.gms.location.history"
    "com.google.android.gms.supervision"
    "com.google.android.health.connect.backuprestore"
    "com.google.android.healthconnect.controller"
    "com.google.android.ondevicepersonalization.services"
    "com.google.android.federatedcompute"
    "com.google.android.appsearch.apk"
    "com.google.android.as"
    "com.google.android.as.oss"
    "com.google.android.devicelockcontroller"
    "com.google.android.hotspot2.osulogin"
    "com.google.android.printservice.recommendation"

    # MediaTek debug tools (not essential)
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

# ─── KEEP: DO NOT REMOVE (system essentials) ───
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
# com.google.android.overlay.*
# com.google.mainline.adservices
# com.google.android.modulemetadata (CRITICAL - GMS module metadata!)
# com.google.android.configupdater
# com.google.android.onetimeinitializer
# com.android.chrome (browser)
# com.mediatek.ims (VoLTE - essential)
# com.mediatek.telephony (essential)
# com.mediatek.* (all remaining MTK framework)
# com.transsion.camera (camera)
# com.transsion.calculator
# com.transsion.calendar
# com.transsion.deskclock
# com.transsion.notebook
# com.transsion.soundrecorder
# com.transsion.screenrecorder
# com.transsion.screencapture
# com.transsion.filemanagerx
# com.transsion.settings.* (system settings)
# com.transsion.tele.settings
# com.transsion.net.wifi
# com.transsion.resolver
# com.transsion.XOSLauncher
# com.transsion.necessity (system utility)
# com.transsion.overlaysuw (OOBE/setup wizard)
# com.transsion.ossettingsext
# com.infinix (launcher resources)
# com.transsion (framework resources)
# com.transsion.thub.res (theme hub resources)
# com.transsion.trproductframeworkresoverlay
# com.transsion.trproduct.overlaysuw.resoverlay

echo "[1/1] Removing ${#SAFE[@]} safe bloat packages..."
REMOVED=0
FAILED=0
for pkg in "${SAFE[@]}"; do
    if $ADB shell "pm uninstall --user 0 $pkg" 2>/dev/null | grep -q "Success"; then
        echo "  ✓ $pkg"
        ((REMOVED++))
    else
        echo "  ✗ $pkg (not found or protected)"
        ((FAILED++))
    fi
done

echo ""
echo "=== Summary ==="
echo "Removed: $REMOVED"
echo "Failed/skipped: $FAILED"
echo "Remaining: $($ADB shell 'pm list packages -s | wc -l')"
echo ""
echo "=== KEEP list (verify these are present) ==="
for pkg in \
    "com.google.android.gms" \
    "com.google.android.vending" \
    "com.google.android.webview" \
    "com.google.android.modulemetadata" \
    "com.mediatek.ims" \
    "com.mediatek.telephony" \
    "com.transsion.camera" \
    "com.transsion.XOSLauncher"; do
    $ADB shell "pm list packages $pkg" 2>/dev/null | grep -q "$pkg" && echo "  ✓ $pkg" || echo "  ✗ $pkg MISSING!"
done
