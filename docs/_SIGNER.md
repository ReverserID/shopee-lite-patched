# Shopee SPSSDK Signer (unidbg)

## Overview

`unidbg-sign/` = Java-based SPSSDK emulator (unidbg ARM64 backend) yang bisa generate valid
`af-ac-enc-sz-token` + obfuscated signature headers untuk semua Shopee API endpoint.

**Status**: ✅ Produces valid signatures — passes WAF (no 418/90309999).

## Architecture

```
unidbg-sign/
├── src/main/java/id/rev/shopeesign/
│   ├── Server.java       # HTTP server (port 28882) + unidbg emulator init
│   ├── ShopeeJni.java    # JNI bridge (mock Android framework calls)
│   └── PrefStore.java    # SharedPreferences mock
├── src/main/resources/libs/
│   ├── libshpssdk.so     # SPSSDK native library (6.3MB)
│   └── libshpssdk_lite.so
└── target/
    └── shopeesign-1.0-shaded.jar  # Fat jar (all deps bundled)
```

## How It Works

1. **Unidbg** emulates ARM64 execution of `libshpssdk.so`
2. **ShopeeJni** intercepts JNI calls (SharedPreferences, JCE, Context, etc.)
3. **patchAntiEmu** patches two anti-emu checks in native code
4. **`/sign`** endpoint calls `vuwuuwvw([B[B)Ljava/lang/String;` (the sign method)
5. Returns JSON with obfuscated header names + signature values

## Critical Patches (patchAntiEmu)

Two patches required in `Server.java → patchAntiEmu()`:

| Offset | Instruction | Purpose |
|--------|-------------|---------|
| `libshpssdk+0xd7184` | `mov x0, #0; ret` | Stack-trace anti-emu check (returns 0 = no emu) |
| `libshpssdk+0x19446c` | `mov x0, #0` | CallObjectMethodV anti-emu (skip JNI call) |

**⚠️ DO NOT patch `0x194400`** — that breaks the entire signing logic (returns null).
The correct surgical patch is at `0x19446c` (the `blr x8` instruction = CallObjectMethodV).

### Anti-emu details

- **`0xd7184`**: Stack-trace checker. Calls `Throwable.getStackTrace()` → `StackTraceElement.toString()`.
  Under unidbg, StackTraceElement isn't registered → crash. Patch entry to `mov x0,#0; ret`.
  Result: stack-trace-dependent field in signature is zeroed.

- **`0x19446c`**: Another anti-emu path. Calls `CallObjectMethodV` with `dvmObject=null`
  (StackTraceElement instance). Patch the `blr x8` instruction to `mov x0,#0` (skip JNI call).

## API Usage

### Start server
```bash
cd unidbg-sign
java --enable-native-access=ALL-UNNAMED -jar target/shopeesign-1.0-shaded.jar 28882
```

### Status check
```bash
curl http://127.0.0.1:28882/status
# → {"ready":true}
```

### Sign request
```bash
curl -X POST http://127.0.0.1:28882/sign \
  -H "Content-Type: application/json" \
  -d '{"url":"https://games-dailycheckin.shopee.co.id/mkt/coins/api/v2/task/claim","body_b64":""}'
```

Response:
```json
{
  "ok": true,
  "raw": "{\"361e3ca2\":\"dN37CsdtjTM7IVmkZ0kXyeVtBkb=\",\"b32ca616\":\"...\",\"c31cf57\":\"...\",\"x-sap-ri\":\"0fc6ec6a...\"}"
}
```

The `raw` JSON keys are **obfuscated header names** — add them directly as HTTP headers.

## Build (no Maven installed)

```bash
# Compile
CP=""
for j in $(find ~/.m2/repository/com/github/zhkl0228/unidbg/ -name "*.jar"); do
  CP="$CP;$j"
done
CP="$CP;~/.m2/repository/org/json/json/20240303/json-20240303.jar"
javac -cp "$CP;target/shopeesign-1.0-shaded.jar" -d target/classes src/main/java/id/rev/shopeesign/*.java

# Update fat jar
jar -uf target/shopeesign-1.0-shaded.jar -C target/classes id/rev/shopeesign/Server.class \
    -C target/classes 'id/rev/shopeesign/Server$1.class' \
    -C target/classes id/rev/shopeesign/ShopeeJni.class
```

## Backend: Unicorn2 vs Dynarmic

Both work. Unicorn2 used as default (better compatibility).

```java
// Server.java line 43
.addBackendFactory(new Unicorn2Factory(true))  // was DynarmicFactory
```

Unicorn2 native libs included in fat jar (`natives/windows_64/unicorn_java.dll`).

## Task Claim Flow (from HTTP Toolkit capture)

Full sequence to claim Shopee coins (e.g. "Lihat Serial Shopee Drama" = 25 coins):

```
1. GET  games.shopee.co.id/gameplatform/api/v3/task/browse/{task_code}?module_id=233
   → report_token (server-generated, encrypted)

2. POST sv.shopee.co.id/api/v2/drama/view/report  (×N heartbeat, every 15s)
   body: {series_user_id, short_drama_key, episode_no, watch_position, encoded_post_id}
   → code:0 (success)

3. POST games.shopee.co.id/gameplatform/api/v3/task/component/report
   body: {report_token}
   → can_reward:true, task_finish_status:2

4. POST games-dailycheckin.shopee.co.id/mkt/coins/api/v2/task/claim
   body: {task_id, request_id, module_id}
   → {"code":0,"data":{"coin_amount":25}}
```

### report_token

- **Server-generated** di `task/browse` response (NOT client-generated)
- **Encrypted** — `code:150004 "decrypt token failed"` kalau token invalid/expired
- Per-session, per-task — must call `task/browse` fresh
- Format: base64 string

### Task IDs (from capture)

| Task | task_code (hex) | task_id (int) | coins | action_key |
|------|-----------------|---------------|-------|------------|
| Lihat Serial Shopee Drama | `73cc5d2f418a6482` | 34220 | 25 | `act_browse_shortdrama` |
| Nonton Shopee Live | `e2e998fc5606d1bf` | 23334 | 15 | `act_browse_livestream` |
| Lihat Produk Rekomendasi | — | 11200 | 25 | `act_browse_product_ads` |

### request_id format

```
{userid}:{module_id}:{task_id}_{timestamp_ms}
```

Example: `1177416568:233:34220_1793898219773`

## Replay Test Results

Direct replay (without signer) → all 418 `error:90309999`:
- Exact clone: 418
- Fresh request_id: 418
- Different task_id: 418
- No request_id: 418
- Random task_id: 418

**With signer** → passes WAF, gets application-level response:
- `code:1006 "cheat request"` = task not complete (missing component/report)
- `code:150004 "decrypt token failed"` = invalid report_token

## Key Headers (from capture)

| Header | Value | Notes |
|--------|-------|-------|
| `af-ac-enc-sz-token` | `M3cZbIoCFly0HZueQJ/GnA==\|...` | SPSSDK device fingerprint |
| `afinfo` | `{"lang":"id","avn":"38336",...}` | App info + dfp |
| `x-csrftoken` | `OcbDngNsM52eWV5OlVlniGozuPTWohwM` | CSRF token |
| `x-sap-ri` | `ebb6ec6a...` | SAP request ID (from signer) |
| `c31cf57` | `...` | Obfuscated (from signer) |
| `b32ca616` | `...` | Obfuscated (from signer) |
| `x-shopee-client-timezone` | `Asia/Jakarta` | Required |
| `af-ac-enc-sz-token` | device fingerprint | SPSSDK signed |

## Known Issues

1. **`report_token` encryption**: Token from `task/browse` is encrypted per-session.
   `task/component/report` with stale token → `150004 "decrypt token failed"`.
   Need to use token immediately after `task/browse`.

2. **`af-ac-enc-sz-token` staleness**: Token has timestamp component. Old tokens may
   fail. Regenerate via signer or capture fresh from device.

3. **Session cookies**: `SPC_T_ID`, `SPC_R_T_ID`, `SPC_ST` are time-sensitive.
   Refresh from HTTP Toolkit capture before batch claims.

4. **Task refresh time**: `refresh_time` field in task info — tasks reset daily.
   `cycle_type: "per_day"` = can claim once per day.

## Next Steps

1. Fix `report_token` freshness — call `task/browse` then immediately `task/component/report`
2. Add cookie auto-refresh from device
3. Batch claim all daily tasks
4. Handle `af-ac-enc-sz-token` regeneration
