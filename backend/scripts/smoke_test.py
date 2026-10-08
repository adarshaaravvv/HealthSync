"""End-to-end check against a running HealthSync deployment.

    python scripts/smoke_test.py https://healthsync-api.onrender.com

Needs only the public URL. Creates a throwaway account, exercises every route,
and deletes what it made.
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
PASSWORD = "smoke-test-" + str(int(time.time()))
USERNAME = "smoketest" + str(int(time.time()))

passed, failed = [], []


def call(method, path, payload=None, token=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"detail": str(e)}


def check(name, got, want):
    ok = got == want
    (passed if ok else failed).append(name)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: {got}" + ("" if ok else f" (expected {want})"))
    return ok


print(f"checking {BASE}")

print("\nhealth")
status, health = call("GET", "/api/health", timeout=180)  # a sleeping free host is slow to wake
check("reachable", status, 200)
if status != 200:
    print(f"\ncannot reach the API: {health.get('detail')}")
    raise SystemExit(1)
print(f"       demo_mode={health.get('demo_mode')} ffmpeg={health.get('ffmpeg')} "
      f"asr={health.get('asr_model')}/{health.get('asr_device')}")

print("\naccounts")
status, body = call("POST", "/api/auth/register",
                    {"username": USERNAME, "password": PASSWORD, "full_name": "Smoke Test",
                     "blood_group": "O+", "emergency_contact_name": "Nobody"})
check("register", status, 200)
token = body.get("token")
patient_id = body.get("patient", {}).get("id")
check("duplicate rejected", call("POST", "/api/auth/register",
      {"username": USERNAME, "password": PASSWORD, "full_name": "x"})[0], 409)
check("weak password rejected", call("POST", "/api/auth/register",
      {"username": USERNAME + "b", "password": "short", "full_name": "x"})[0], 422)
check("login", call("POST", "/api/auth/login",
      {"username": USERNAME, "password": PASSWORD})[0], 200)
check("wrong password rejected", call("POST", "/api/auth/login",
      {"username": USERNAME, "password": "nope"})[0], 401)

print("\naccess control")
check("portfolio needs a token", call("GET", "/api/portfolio")[0], 401)
check("encounters need a token", call("GET", "/api/encounters")[0], 401)
check("portfolio with token", call("GET", "/api/portfolio", token=token)[0], 200)

print("\nediting the record")
check("save conditions", call("PUT", "/api/portfolio/conditions",
      [{"name": "Asthma", "since": "2015", "status": "active", "notes": None}], token=token)[0], 200)
check("save allergies", call("PUT", "/api/portfolio/allergies",
      [{"substance": "Penicillin", "reaction": "Rash", "severity": "severe"}], token=token)[0], 200)
check("empty name rejected", call("PUT", "/api/portfolio/conditions",
      [{"name": ""}], token=token)[0], 422)

print("\nemergency card (no token on purpose)")
status, card = call("GET", f"/api/emergency/{patient_id}")
check("readable without signing in", status, 200)
check("carries the allergy", [a["substance"] for a in card.get("allergies", [])], ["Penicillin"])
check("leaks no transcript", any(k in card for k in ("segments", "note", "encounters")), False)

print("\nconsultation pipeline")
status, enc = call("POST", "/api/audio/sample", token=token)
check("load sample", status, 200)
enc_id = enc.get("id")
status, enc = call("POST", f"/api/encounters/{enc_id}/transcribe", token=token, timeout=600)
check("transcribe", status, 200)
if status == 200:
    print(f"       {len(enc['segments'])} segments in {enc['asr_ms']} ms via {enc['asr_model']}")
status, enc = call("POST", f"/api/encounters/{enc_id}/note", token=token, timeout=600)
check("generate note", status, 200)
if status == 200:
    meds = [m["name"] for m in enc["note"]["entities"]["medications"]]
    print(f"       {enc['llm_ms']} ms via {enc['llm_model']}, medications: {meds}")
    check("fhir bundle valid", enc["fhir_valid"], True)

print("\ncleanup")
check("delete encounter", call("DELETE", f"/api/encounters/{enc_id}", token=token)[0], 200)
check("logout", call("POST", "/api/auth/logout", token=token)[0], 200)
check("token dead after logout", call("GET", "/api/portfolio", token=token)[0], 401)

print("\n" + "=" * 60)
print(f"{len(passed)} passed, {len(failed)} failed")
if failed:
    for name in failed:
        print(f"  failed: {name}")
    raise SystemExit(1)
print("deployment looks healthy")
print(f"\nnote: the account '{USERNAME}' is left behind; remove it from the database if you care.")
