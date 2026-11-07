# Shopee + microG Google Sign-In Unlock

Shopee ID v3.83.36 hides Google Sign-In button + blocks OAuth when GMS cert mismatch.

## Patches (4 smali files)

### 1. `smali_classes2/com/google/android/gms/common/GoogleSignatureVerifier.smali`
4 methods → return true always:
- `isGooglePublicSignedPackage(PackageInfo)`
- `isPackageGoogleSigned(String)`
- `isUidGoogleSigned(I)`
- `zzb(PackageInfo, Z)` static

Replace method body with:
```smali
.locals 1
const/4 v0, 0x1
return v0
```

### 2. `smali_classes4/com/shopee/app/ui/auth2/signuplogin/connect3rd/b.smali`
Method `d()Z` → force return true (shows Google button):
```smali
.locals 3
const/4 v0, 0x1
return v0
```

### 3. `smali_classes4/com/shopee/app/helper/c0.smali`
Method `a()Z` → GMS available always true:
```smali
.locals 2
const/4 v0, 0x1
return v0
```

### 4. `smali_classes2/com/google/android/gms/auth/api/signin/GoogleSignInClient.smali`
Method `zba()I` → return 4 (APPAUTH flow via browser, bypass GMS IPC):
```smali
.locals 4
const/4 v0, 0x4
return v0
```

## Install microG (replace stock GMS)

```bash
# 1. Disable + remove stock GMS
adb shell "pm disable-user --user 0 com.google.android.gms"
adb shell "pm uninstall -k --user 0 com.google.android.gms"
adb shell "rm -rf /data/app/com.google.android.gms-*"

# 2. Replace system priv-app (requires root + remount rw)
adb root && adb remount
adb push microg-upstream.apk /system/priv-app/PrebuiltGmsCore/PrebuiltGmsCore.apk
adb shell "chmod 644 /system/priv-app/PrebuiltGmsCore/PrebuiltGmsCore.apk"
adb shell "chcon u:object_r:system_file:s0 /system/priv-app/PrebuiltGmsCore/PrebuiltGmsCore.apk"
adb reboot
```

## Status

- ✅ Google button muncul di Shopee login
- ⚠️ APPAUTH flow triggered, "Gagal menghubungkan ke server Google" (microG sig spoof butuh Xposed FakeGApps atau ROM-level signature spoofing)

## microG upstream
https://github.com/microg/GmsCore/releases → `com.google.android.gms-*-hw.apk`
