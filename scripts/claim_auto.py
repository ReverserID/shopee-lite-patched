"""Auto-claim Shopee coins via unidbg signer.

Full flow (from HTTP Toolkit capture):
1. GET task/browse/{task_code} → report_token
2. POST drama/view/report (heartbeat, optional)
3. POST task/component/report {report_token} → marks task complete
4. POST task/claim {task_id} → coins
"""
import requests, json, time, sys, urllib3
urllib3.disable_warnings()

SIGNER_URL = "http://127.0.0.1:28882/sign"
BASE_GAMES = "https://games.shopee.co.id/gameplatform/api/v3"
BASE_CHECKIN = "https://games-dailycheckin.shopee.co.id/mkt/coins/api"
BASE_SV = "https://sv.shopee.co.id/api/v2"

COOKIE = "SPC_F=c283f5467121a446_unknown; SPC_CLIENTID=XfCBY6o0U95jq6nminnarezbcmaueqwo; SPC_AFTID=b2955ba6-e305-4178-8e34-ffbbe55a37d2; language=id; shopee_app_version=38336; SPC_EC=-; REC_T_ID=5a0a937b-d5ca-11f1-9026-9ef00a6eadc4; userid=1177416568; shopid=1177067894; username=abdulmuttaqin394; shopee_token=EPJjDkMIfF9o6f/f8i0vuhyCW+mTpvPvh1yAzg0zBG11bYeTlaj2l5xSkNlJoQ6Y3tJ5LS+nqJBATGQ=; SPC_U=1177416568; SPC_T_IV=bW5VYzBGRzd6R1RmaU5yYw==; SPC_R_T_ID=ZqtBagWXBmu8VGv3BkXbtXJWtagcB2wwPIsk0ajgXYLLokKjLnBIc57tyk2OLLQSc1Aya3olA6+gVxGJTXCWe6C65R7FGGKXI3TqR6AyoS8Xrp/phfZ6uxeD+Eso+QcpTeJYPgwRdB9ckBc5apbLcXzDE+XBDcJMMzZ2qlCqock=; SPC_R_T_IV=bW5VYzBGRzd6R1RmaU5yYw==; SPC_T_ID=ZqtBagWXBmu8VGv3BkXbtXJWtagcB2wwPIsk0ajgXYLLokKjLnBIc57tyk2OLLQSc1Aya3olA6+gVxGJTXCWe6C65R7FGGKXI3TqR6AyoS8Xrp/phfZ6uxeD+Eso+QcpTeJYPgwRdB9ckBc5apbLcXzDE+XBDcJMMzZ2qlCqock=; SPC_B_SI=dKvEagAAAAB5VEpwVDA3ViBqKgMAAAAAYlU2ZDYzOVg=; SPC_SI=Z6vEagAAAABma0JYOEVpZByJKQMAAAAAZ1hYRWdqdnM=; csrftoken=FSOv2hTtrhd3CDmwLo82xRo7VwMiefj7"

USERID = "1177416568"
AF_TOKEN = "M3cZbIoCFly0HZueQJ/GnA==|XsZNfLUHaPdAXhaJaE5VQ60zNYo+iq/pNeX+5RrS2r65hAEJWFip6LlLRWsmmf4mz6IH7QxyXudPpHZrbxc9ZHkWwroTVNT143srwwYh9g==|18yfWJ/pPsQV3hmq|08|1"
AFINFO = '{"lang":"id","avn":"38336","uat":2,"pf":4,"at":1,"dfp":"' + AF_TOKEN + '"}'


def get_sign(url: str, body: dict) -> dict:
    import base64
    body_b64 = base64.b64encode(json.dumps(body).encode()).decode() if body else ""
    r = requests.post(SIGNER_URL, json={"url": url, "body_b64": body_b64}, timeout=30)
    data = r.json()
    if not data.get("ok"):
        raise Exception(f"sign error: {data.get('err')}")
    return json.loads(data["raw"])


def make_headers(url: str, body: dict, extra: dict = None) -> dict:
    sig = get_sign(url, body)
    headers = {
        "x-api-source": "rn",
        "accept": "application/json",
        "x-csrftoken": "OcbDngNsM52eWV5OlVlniGozuPTWohwM",
        "afinfo": AFINFO,
        "content-type": "application/json",
        "cookie": COOKIE,
        "user-agent": "Android app Shopee appver=38336 app_type=1 platform=native_android os_ver=35",
        "af-ac-enc-sz-token": AF_TOKEN,
        "x-shopee-client-timezone": "Asia/Jakarta",
        "shopee_http_dns_mode": "1",
        "cache-control": "no-cache, no-store",
    }
    if extra:
        headers.update(extra)
    for k, v in sig.items():
        headers[k] = v
    return headers


def step1_browse(task_code: str, module_id: str = "233") -> dict:
    """GET task/browse → returns report_token + task info."""
    url = f"{BASE_GAMES}/task/browse/{task_code}?module_id={module_id}"
    headers = make_headers(url, {})
    r = requests.get(url, headers=headers, verify=False, timeout=15)
    data = r.json()
    if data.get("code") != 0:
        raise Exception(f"browse failed: {data}")
    report_token = data["data"]["report_token"]
    task_info = data["data"]["user_task"]
    print(f"  task: {task_info['task']['task_name']}")
    print(f"  can_reward: {task_info.get('can_reward')}")
    print(f"  report_token: {report_token[:60]}...")
    return {"report_token": report_token, "task_info": task_info}


def step2_view_report(series_user_id: int, short_drama_key: str, episode_no: int = 1,
                       watch_position: int = 60000, encoded_post_id: str = "DYPBkFSjCQBtaaGCAgAAAA==") -> dict:
    """POST drama/view/report (heartbeat)."""
    url = f"{BASE_SV}/drama/view/report"
    body = {
        "series_user_id": series_user_id,
        "short_drama_key": short_drama_key,
        "episode_no": episode_no,
        "watch_position": watch_position,
        "encoded_post_id": encoded_post_id,
    }
    headers = make_headers(url, body, {
        "sv-referer": "browse_short_drama_landing_page",
        "sv-from-source": "browse_short_drama",
        "sv-source-page": "browse_short_drama",
        "os-type": "2",
        "model": "Infinix Infinix X6873",
        "sdk-version": "1.101.0",
    })
    r = requests.post(url, headers=headers, json=body, verify=False, timeout=15)
    return r.json()


def step3_component_report(report_token: str) -> dict:
    """POST task/component/report → marks task complete, can_reward=true."""
    url = f"{BASE_GAMES}/task/component/report"
    body = {"report_token": report_token}
    headers = make_headers(url, body, {
        "referer": "https://games.shopee.co.id/gameplatform/api/v3/task/",
    })
    r = requests.post(url, headers=headers, json=body, verify=False, timeout=15)
    data = r.json()
    if data.get("code") != 0:
        raise Exception(f"component/report failed: {data}")
    ut = data["data"]["user_task"]
    print(f"  can_reward: {ut.get('can_reward')}")
    print(f"  task_finish_status: {ut.get('task_finish_status')}")
    return data


def step4_claim(task_id: int, module_id: str = "233") -> dict:
    """POST task/claim → get coins."""
    url = f"{BASE_CHECKIN}/v2/task/claim"
    ts = int(time.time() * 1000)
    body = {
        "task_id": task_id,
        "request_id": f"{USERID}:{module_id}:{task_id}_{ts}",
        "module_id": module_id,
    }
    headers = make_headers(url, body, {
        "referer": "https://games.shopee.co.id/gameplatform/api/v3/task/",
    })
    r = requests.post(url, headers=headers, json=body, verify=False, timeout=15)
    return r.json()


def get_task_list() -> dict:
    """GET task list to check current state."""
    url = f"{BASE_CHECKIN}/v3/tasks?device_id=XfCBY6o0U95jq6nm4%2Fdr3GVg%2Fw3dJlGVBthLtEkbcwo%3D&is_supported_widget=true&s=AAAAAAAAAAAAAAAAAAAAAASZ7H9qmZAxEADidvXb%2BVi1q4Jso%2Fv%2F23GbenNYyQmZ112345678901212&view_all_task=true"
    headers = make_headers(url, {})
    r = requests.get(url, headers=headers, verify=False, timeout=15)
    return r.json()


def main():
    print("=== Shopee Auto-Claim (unidbg signer) ===\n")

    # Use captured token from HTTP Toolkit (known working)
    report_token = "TC8wdTRUaDd4S1J1UGZIbHNha3FOVlNGblNyZkptRGhhWUlUWU4zRVY4UUk5eG1SYkovUExLMWJEY2ZFbTVIeUoyT3FVNkZRMFJ4M1p5ZER5alk2bDJQVGp5SzVkMU5jOUlRZytxUnE3Q1k9"
    task_id = 34220

    print("[1/2] Component report (captured token)...")
    try:
        comp = step3_component_report(report_token)
    except Exception as e:
        print(f"  component/report failed: {e}")
        print("  Trying fresh browse...")
        browse = step1_browse("73cc5d2f418a6482")
        report_token = browse["report_token"]
        comp = step3_component_report(report_token)

    print("\n[2/2] Claim...")
    result = step4_claim(task_id)
    print(f"  result: {result}")

    if result.get("code") == 0:
        coins = result.get("data", {}).get("coin_amount", 0)
        print(f"\n✓ SUCCESS: +{coins} coins!")
    else:
        print(f"\n✗ FAILED: {result.get('msg')}")


if __name__ == "__main__":
    main()
