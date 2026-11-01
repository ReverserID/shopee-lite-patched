# Shopee Mod Menu — Roadmap

Status: **v1.6.7 shipped** (fix no-internet + emu_mask Magisk module).

## Shipping queue (urutan prioritas user)

| # | Fitur | Status | Blocker / effort |
|---|---|---|---|
| 1 | Fix "no internet" bug | ✅ v1.6.7 | — |
| 2 | Google login via microG | 📝 Dokumentasi | Guide-only (microG install prosedur) |
| 3 | Flash Sale Auto-Buy | 🔬 R&D | Capture race-checkout endpoint + sign header pattern |
| 4 | Auto-Claim Coin 11.11 | 🔬 R&D | Capture `/claim/coin/{campaign_id}` endpoint |
| 5 | Auto-Claim Coin Drama Cina | 🔬 R&D | Sama shape dgn #4, campaign_id beda |
| 6 | Checkout voucher Memru auto-apply | 🔬 R&D + 💪 fingerprint | Needs real-device-grade fingerprint untuk tembus risk engine |
| 7 | Checkout voucher Kompensasi telat | 🔬 R&D + 💪 fingerprint | Idem, risk engine tier tinggi |
| 8 | Bagi-Bagi Hadiah auto-collect | 🔬 R&D + 💪 fingerprint | Idem |
| 9 | Voucher VIP auto-apply | 🔬 R&D + 💪 fingerprint | Idem (tier paling ketat) |
| 10 | Mission ShopeePay Transfer bypass | 🔬 R&D | Reverse mission-completion endpoint; historical bypass pernah pakai forged state POST |

🔬 R&D = butuh traffic capture dari user yang punya akses fitur live
💪 fingerprint = butuh device profile real + sign token asli + behavioral timing

## Per-feature: apa yang harus di-capture

### Flash Sale Auto-Buy

Setup HTTP Toolkit (atau Reqable) sebelum flash sale buka:

1. Buka Shopee → masuk halaman flash sale yg mau diincer
2. **Tepat jam** sale start, tap "Beli Sekarang" → "Checkout" → "Buat Pesanan"
3. Export semua request yang hit domain `*.shopee.co.id` dari antara waktu tap "Beli Sekarang" sampai pesanan sukses
4. Yang penting:
   - `POST /api/v4/cart/add_to_cart_batch` (tambah ke keranjang)
   - `POST /api/v4/checkout/get` (preview checkout, dapet sign challenge)
   - `POST /api/v4/checkout/place_order` (konfirmasi order — target auto-buy)
5. Catat full header (termasuk `X-API-SOURCE`, `X-Shopee-Client-Timezone`, `X-Sap-Access-T`, `X-Sz-Sap-Session-Id` + sign-related) & body JSON

Setelah template ada → modmenu hook `AutoBuyHooks` fire `place_order` di T=0 (saat timer sale 00:00:00) tanpa nunggu Shopee's UI load.

### Auto-Claim Coin (11.11 / Drama Cina)

Capture tap "Klaim Koin":

1. Buka campaign page (misal shopee.co.id/m/11-11, atau h5 Drama Cina)
2. Tap tombol klaim → capture request yang hit → biasanya `POST /api/v4/pfb/coin_claim` atau `/api/v4/campaign/coin/claim`
3. Catat endpoint + body (`campaign_id`, `promotion_id`, `nonce`)
4. Replay dengan sign token real (dari libshpssdk - v1.6.7 udah normal)

Setelah template ada → `AutoClaimHooks` fire tiap jam target (00:00 WIB).

### Checkout voucher auto-apply (Memru / Kompensasi / Bagi-Bagi / VIP)

Shopee **risk engine** scoring per request. Faktor:
- Device fingerprint (model, brand, Build.*, sensors, android_id) → ✅ sudah di-handle `EmuHooks`
- Sign token real (bukan empty) → ✅ v1.6.7 unblock libshpssdk
- Account age + behavior history (nilai Shopee's)
- IP residensial (bukan DC/VPN)
- Request timing (human-like, bukan burst)

**Yang bisa modmenu lakuin:**
- Hook `GET /api/v4/voucher_wallet/get_voucher_list` → inject voucher ID target
- Hook `POST /api/v4/voucher_wallet/claim_voucher` → auto-fire dengan delay random 500-2000ms
- Rotasi device fingerprint via `DEVICE → rotate identity` biar beda per claim session

**Yang gak bisa:**
- Nambah account age/history
- Server-side scoring final (kalau akun di-flag, voucher pasti ditolak server)

Realistik: success rate 30-60% depending akun. Kalau akun baru/level rendah → mostly rejected.

### Mission ShopeePay Transfer bypass

Historical bypass (per laporan user):
- Fire `POST /api/v4/pfb/mission/complete` dengan state forged (misi `pending` → `completed`)
- Server previously trust client-side state submission
- Now Shopee validate server-side action trace — bypass closed since mid-2024

Realistik: kalau Shopee udah close server-side, bypass client gak jalan. Tetap try sebagai feature + log kalau endpoint masih accept forged state.

## Alternative Google login — microG

Untuk emulator tanpa Google Play Services (clean AOSP, non-GApps AVD, LineageOS emu):

### Setup

1. **Download microG** (unofficial build):
   - [GmsCore.apk](https://github.com/microg/GmsCore/releases/latest) (~15MB, replaces Google Play Services)
   - [GsfProxy.apk](https://github.com/microg/GsfProxy/releases/latest) (gTalk/GCM proxy, ~100KB)
   - [FakeStore.apk](https://github.com/microg/FakeStore/releases/latest) (Play Store stub signature)

2. **Signature spoofing** support — microG butuh ini. Dua pilihan:
   - **Magisk module**: install [NanoDroid-microG](https://nanolx.org/nanolx/nanodroid/-/releases) atau standalone [Shelter-SignSpoof](https://github.com/ale5000-git/signature-spoofing-helper/releases) module
   - **ROM dengan built-in sig spoof** (LineageOS forks, iodéOS, /e/OS)

3. **Install order** (penting):
   ```
   adb install FakeStore.apk        # dulu, biar menang signature atas Play Store
   adb install GmsCore.apk
   adb install GsfProxy.apk
   # reboot
   # buka microG Settings → Self-Check (semua harus hijau)
   # login akun Google di microG Settings → Google Account
   ```

4. **Shopee**: install modmenu v1.6.7 → launch → tombol Google Sign-In sekarang pakai microG backend → login jalan.

### Catatan

- MicroG = reimplementation sebagian Google Services API. Fitur yg jalan: Google Sign-In, GCM push, ~90% Firebase. **Tidak** cover: ARCore, Play Protect, SafetyNet (tapi ada DroidGuard helper).
- Kalau emu kamu udah pakai `google_apis_playstore` system image (Pixel AVD default), skip microG — pakai `shopee-gmsfix-1.0.0.apk` module aja (already shipped).
- MicroG di LDPlayer/MuMu: supported, tapi harus flash sig-spoof patch dulu (LDPlayer tidak expose signature spoofing API by default).

## Fingerprint quality (device identity)

Current `DeviceGen` profile pool (dari `shopee-modmenu/app/src/main/java/id/reverser/modmenu/DeviceGen.java`):

| Field | Spoof |
|---|---|
| MANUFACTURER / BRAND / MODEL / DEVICE / PRODUCT | Real-device roster (Pixel, Samsung, Xiaomi, Oppo, Vivo) |
| android_id | 16-char hex, stable per identity |
| IMEI | Luhn-valid 15-digit |
| Sensors | List dari real-device sensor profile (accelerometer + gyroscope + proximity + light + magnetic) |

Yang bisa di-tingkatkan di v1.7:
- Fingerprint pool size dari ~15 → 200+ (full Pixel + Samsung + Xiaomi dari past 3 years)
- Sync GSM operator (Telkomsel/Indosat/XL) ke profile region (ID-only accounts)
- NFC + fingerprint sensor presence match (Shopee cek untuk ShopeePay)
- `Build.FINGERPRINT` match persis sama OTA fingerprint real (bukan assembled)

## Timeline estimate

| Milestone | Target | Pre-req |
|---|---|---|
| v1.6.7 | ✅ Done | — |
| v1.7 — fingerprint pool v2 + microG guide | 1 minggu | — |
| v1.8 — auto-claim coin (11.11 + drama) | 2 minggu | Capture 2 endpoint |
| v1.9 — flash sale auto-buy | 3 minggu | Capture checkout flow + stress test |
| v2.0 — voucher auto-apply tier rendah | 4 minggu | Capture 4 voucher endpoint + risk engine tuning |
| v2.1 — mission bypass + voucher tier tinggi | +4 minggu | Risk engine tier tinggi butuh account aging + behavioral model |

## Contributing captures

Kalau punya akses fitur live + mau bantu capture:

1. Setup [HTTP Toolkit](https://httptoolkit.com/) atau [Reqable](https://reqable.com/) di device/emu
2. Install Shopee patched v1.6.7 → login → aktifkan proxy ke HTTP Toolkit
3. Exercise fitur target (e.g. tap klaim coin 11.11)
4. Export HAR file atau screenshot full request/response
5. Buka issue di [GitHub](https://github.com/ReverserID/shopee-lite-patched/issues) atau post ke [forum thread](https://reverser.id/d/54)

## FAQ

**Q: Kenapa fitur ga langsung jadi?**
A: Karena Shopee API berubah tiap release, dan risk engine evaluate ribuan signal. Scaffold hook tanpa capture = hook kosong = useless. Mesti capture dulu per-fitur, baru implement.

**Q: Ada ETA pasti?**
A: Nope. Capture + reverse per fitur bisa 1-5 hari tergantung complexity. Risk engine evaluation per fitur (fingerprint tier) bisa butuh berminggu-minggu tuning.

**Q: Akun gue bakal kena banned ga?**
A: Bisa. Shopee risk engine detects abnormal pattern. Pakai akun throwaway kalau mau test voucher auto-apply. Account trading / jual beli = resiko ditanggung sendiri.
