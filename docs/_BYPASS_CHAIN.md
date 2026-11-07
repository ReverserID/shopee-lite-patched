# Shopee Lite — Frida bypass + MITM chain (2026-10-27, verified live)

## What works NOW (evidence-backed)
- Frida 17.24.3 server (user module `frida-ksu`), client 17.24.3 matched.
  Link 14ms, `enumerate_processes` 256 procs / 124ms.
- Race-attach beats AppDome init: attach ≤0.5s after launch succeeds
  (276ms attach, scripts execute, clean detach). Late attach stalls
  (`TimedOutError` waiting for stop) — AppDome anti-ptrace armed <1s.
- Native exec fully works in-process: module enum (409 mods),
  export resolution, Interceptor hooks, NativeFunction calls.
- SSL unpin `_unpin_native.js` (Frida 16+17 API): `SSL_set_custom_verify`
  replaced (43 handshakes neutered / 30s), `SSL_CTX_set_custom_verify`,
  `X509_verify_cert` forced 1, `SSL_get_verify_result` forced 0.
  Conscrypt-only stack (no Cronet/TrustKit in Lite maps). Java TrustManager
  (incl. custom pins) never runs for the handshake.
- MITM chain, all plaintext verified: Reqable system CA (module) +
  HTTPToolkit user CA (`/data/misc/user/0/cacerts-added/867c4082.0`,
  live-installed, no reboot). Login-required + auth + WebView captcha
  endpoints all captured with bodies.
- LSPosed module shipped: `fdciabdul/shopee-unpin` (source + v1.0.0 APK,
  Xposed API stubbed from on-device framework.dex signatures).
- Signer: VM (sign.reverser.id) structurally valid; `is_login:true` on cart
  with fresh HP session. Header shape matches app (3 shorts + envelope +
  `x-sap-ri` + SAP). SAP is session-stable (identical across requests).
  Names randomized per call except stable `4418a1ac`.

## Hard blocks (evidence, not guesses)
1. Java bridge dead on 16 AND 17: 16 hangs `Java.perform`; 17 loads but
   `typeof Java === 'undefined'` permanently (12s poll). AppDome ART hooks
   block bridge init. Kills: OkHttp/Conscrypt Java hooks, Gadget-as-JS path.
2. Dispatcher hook unreachable: `shpssdk`+`aegis` load at startup (<0.5s,
   race lost); `RegisterNatives` not exported (JNIEnv-table only);
   `dlsym("JNI_OnLoad")` hits are probes, never called; spawn blocked
   (zygote SELinux denial on agent memfd); no-Java ⇒ no GetMethodID path.
3. cart/search 90309999 with `is_login:true`: risk-wall on strict endpoints.
   Prime suspect = short VM envelope (872 vs ~1800 chars, ~half fields).
   Needs server-side session fields (repo is private).

## Unblock conditions (owner-side)
- Hide frida-server (neutral name + custom port) in `frida-ksu` →
  attach likely works outside race windows; reboots stop.
- Grant `imtaqin/shopee-sign` access (or paste Unidbg key/pref list) →
  envelope parity closable by adding missing session fields.
- `permissive zygote` (or spawn path) → spawn-capture of JNI table.

## 2026-10-27 addendum (Frida 17.24.3, user module `frida-ksu`)
- Link healthy (14ms); enumerate 256 procs/124ms. Settings attach OK.
- Race-attach beats AppDome (<0.5s): 276ms attach, native exec, clean detach.
  Late attach always stalls (ptrace refused) — AppDome arms <1s.
- Unpin rewritten for Frida 17 (`Module.enumerateExports` removed; use
  per-module `getExportByName`): 4/4 hooks live, 43 handshakes neutered/30s.
- Java bridge dead on 17 too: `typeof Java === 'undefined'` for 12s straight
  (16 hung instead). AppDome blocks bridge ART init. No Java hooks possible.
- Dispatcher: `dlsym("JNI_OnLoad")` hits are probes (resolved, never called);
  `shpssdk`/`aegis` load pre-race (<0.5s). Spawn blocked (zygote SELinux).
  Static: lib strings encrypted (only dotted SHPSSDK ref); web enhance_sap
  bundle is a module-federation shell (crypto in unknown chunks).
- MITM chain unchanged and green (Reqable system CA + HTTPToolkit user CA).
- SAP is session-stable across requests; `is_login:true` achieved on cart
  with fresh cookies — remaining 90309999 is endpoint risk policy.

## 2026-10-27 dispatcher verdict (static RE, zero-device)
- Lite `libshpssdk.so` (6.3MB): exports ONLY JNI_OnLoad + VERS_1.0;
  zero JNI imports; JNI_OnLoad (0xb90) makes NO JNIEnv-table calls
  (no LDR #1720 in 740 insns); its 4 callees only SCAN table slots
  (t1/t2 read idx 171-234 incl. 215/216 = hook-detection, no calls).
  Whole .text (928K insns): ZERO (ldr #1720 -> blr). Conclusion: Lite's
  signer lib performs NO standard JNI registration at all.
- `libshopeeaegis.so` (248KB): same pattern (tiny JNI_OnLoad, no imports).
- No lib in Lite ships `RegisterNatives` (sweep: only media SDKs hit).
- Implication: Lite sign path != main-app path the VM replicates
  (VM OPCALL `vuwuuuvv` belongs to main-app lib). VM-vs-Lite envelope
  comparison is cross-implementation; cart/search 90309999 likely
  endpoint risk policy, not provably envelope.
- Web SAP bundle is a module-federation shell only (crypto in unknown chunks).
- Main-app APK absent locally; jadx MCP disconnected — static Java side pending tool return.

## 2026-10-27 late session: JNI chain breakthrough + device thrashing
- Pure-native JNI works WITHOUT Java bridge: `JNI_GetCreatedJavaVMs` via
  `getExportByName("libart.so")` returns rc=0 (JavaVM* acquired), clean
  detach, 2s. Proves native-to-JVM path exists.
- `GetEnv`/later JNI calls hang at script load (3 consecutive sessions).
  Distinguishing test pending.
- DEVICE HEALTH is the likely cause of escalation: mem 11040/11476MB (96%),
  loadavg ~20, sustained all day. Attach timeouts, load hangs, IPC delays
  all consistent with thrashing — not only AppDome hardening.
  Recommendation: user-initiated reboot when convenient (frees memory AND
  resets AppDome threat state), then resume with proven playbooks
  (race-attach <0.5s, unpin 17, GetVMs-first JNI chain).
- Java bridge still undefined on 17 (12s poll). Dispatcher table still
  unmapped (startup race lost; dlsym hits are probes).

## 2026-10-27 local-VM field audit (definitive inputs per sign)
Traced with PREFTRACE=1 on upstream replica + real base.apk dex:
ONLY inputs per sign: PREF SPHelper_sp_main/E1YA + mini-uuid,
OPCALL key74 (AF UID env) + key78 (null), JCE MD5(4B). Zero MISS, zero
JNI-UNRESOLVED. VM serves everything the native requests.
Prefs synced live (141 files, AF/env/ANDROID_ID live). Envelope stayed
~904 vs app ~1200-1800 (endpoint-variable). Conclusion: gap is NOT missing
inputs — VM is input-complete. Remaining suspects: silent Build-field
values (getStaticObjectField has no logging) or request-bound envelope
structure. Cart 90309999 with is_login:true = endpoint risk policy,
not sign/auth failure.
Local fix found: ShopeeJni catch-all never swallowed the entry
(no class prefix on entry sig) — the `!vuwuuwvw` guard added 10-27 is a
harmless no-op; entry failure on fresh builds was missing base.apk dex
(AppDome-packed stub classes.dex on device lacks SHPSSDK; prod uses the
real 9.5MB classes.dex).

## 2026-10-27 cart/search verdict: SIGNER EXONERATED (app-parity proof)
App's OWN cart/get (native sign, HP IP, real session) -> HTTP 418 +
error 90309999 + is_login:true, 5x in capture (Android-app source).
Identical verdict to VM-signed replay (same code, is_login:true).
App response even carries a Cart captcha challenge (challenge_type=1,
action_type=3, business mfrcaptcha "Cart"). Conclusion: cart/search
gating is endpoint/account-risk policy (+captcha), NOT signature quality,
headers, IP, envelope, or SAP freshness. Offline VM sign stands valid
for all endpoints the account/session is entitled to.
