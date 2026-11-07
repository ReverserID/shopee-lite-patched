#!/bin/bash
# Infinix XOS Debloat MINIMAL — ONLY clearly-safe packages
# NO system framework components. NO Transsion system utilities.
# Tested: Infinix X6873 (Android 15, XOS 15)

D="${1:-143382554V104575}"
ADB="adb -s $D"

echo "=== Infinix Debloat MINIMAL (ultra-safe) ==="

# ONLY these are 100% safe to remove:
# - AI junk (no system dependency)
# - Live wallpapers (cosmetic)
# - Theme/fonts (cosmetic)
# - Google apps (not GMS core)
# - MediaTek debug tools
# - Third-party bloat

SAFE=(
    # AI junk
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

    # Live wallpapers
    "com.transsion.livewallpaper.colorart"
    "com.transsion.livewallpaper.fantasy"
    "com.transsion.livewallpaper.gt30"
    "com.transsion.livewallpaper.magictouch"
    "com.transsion.livewallpaper.mondrian"
    "com.transsion.livewallpaper.page"
    "com.transsion.livewallpaper.pictorial"
    "com.transsion.livewallpaper.theme"

    # Theme/fonts (cosmetic only)
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

    # XOS cosmetic bloat
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
    "com.transsion.compass"
    "com.transsion.batterylab"
    "com.transsion.dualapp"
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
    "com.transsion.aftersalecalibrationtool"
    "com.transsion.easypic"
    "com.transsion.fmradio"
    "com.transsion.irremote"
    "com.transsion.iotcard"
    "com.transsion.iotservice"
    "com.transsion.letswitch"
    "com.transsion.mobilecloner"
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

    # Google apps (NOT GMS core)
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

    # MediaTek debug tools only
    "com.mediatek.engineermode"
    "com.mediatek.ygps"
    "com.mediatek.voiceunlock"
    "com.mediatek.mdmlsample"
    "com.mediatek.omacp"
    "com.mediatek.batterywarning"

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
)

# DO NOT REMOVE (system framework):
# - com.transsion.* (all remaining — system utilities, settings, etc.)
# - com.mediatek.* (all remaining — telephony, IMS, framework)
# - com.google.android.gms, vending, gsf, webview, modulemetadata
# - com.android.* (all)
# - com.infinix (launcher resources)
# - com.transsion (framework resources)

echo "Removing ${#SAFE[@]} packages..."
R=0; F=0
for pkg in "${SAFE[@]}"; do
    if $ADB shell "pm uninstall --user 0 $pkg" 2>/dev/null | grep -q "Success"; then
        ((R++))
    else
        ((F++))
    fi
done
echo "Removed: $R | Skipped: $F"
echo "Remaining: $($ADB shell 'pm list packages -s | wc -l')"
echo ""
echo "=== Verify essentials ==="
for pkg in "com.android.vending" "com.google.android.gms" "com.google.android.modulemetadata" "com.mediatek.ims" "com.transsion.camera" "com.transsion.XOSLauncher" "com.android.settings" "com.android.systemui"; do
    $ADB shell "pm list packages $pkg" 2>/dev/null | grep -q "$pkg" && echo "  ✓ $pkg" || echo "  ✗ $pkg MISSING!"
done
