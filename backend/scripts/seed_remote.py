"""Seed the demo patients into a running deployment over its public API.

    python scripts/seed_remote.py https://healthsync-api.onrender.com

app/seed.py needs database access, which a deployment does not hand out. This
does the same thing through the API instead, so it needs only the public URL.
Accounts that already exist are left alone rather than duplicated.
"""
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.seed import DEMO_PASSWORD, DOCTORS, PATIENTS

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def call(method, path, payload=None, token=None, timeout=180):
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


print(f"seeding {BASE}")
status, health = call("GET", "/api/health")
if status != 200:
    print(f"  cannot reach the API: {health.get('detail')}")
    raise SystemExit(1)
print(f"  database={health.get('database')} demo_mode={health.get('demo_mode')}\n")

for spec in PATIENTS:
    username = spec["username"]

    status, body = call("POST", "/api/auth/register", {
        "username": username,
        "password": DEMO_PASSWORD,
        "full_name": spec["full_name"],
        "dob": spec["dob"],
        "sex": spec["sex"],
        "blood_group": spec["blood_group"],
        "phone": spec["phone"],
        "emergency_contact_name": spec["emergency_contact_name"],
        "emergency_contact_phone": spec["emergency_contact_phone"],
        "hospital_phone": spec["hospital_phone"],
    })

    if status == 409:
        print(f"{username}: already exists, signing in to refresh the record")
        status, body = call("POST", "/api/auth/login",
                            {"username": username, "password": DEMO_PASSWORD})
        if status != 200:
            print(f"  cannot sign in ({status}); the password may differ. skipping.")
            continue
    elif status != 200:
        print(f"{username}: register failed ({status}) {body}")
        continue
    else:
        print(f"{username}: created")

    token = body["token"]

    status, saved = call("PUT", "/api/portfolio/conditions", spec["conditions"], token=token)
    print(f"  conditions   {status}: {[c['name'] for c in saved] if status == 200 else saved}")

    status, saved = call("PUT", "/api/portfolio/allergies", spec["allergies"], token=token)
    print(f"  allergies    {status}: {[a['substance'] for a in saved] if status == 200 else saved}")

    appointments = []
    for appt in spec["appointments"]:
        doctor = DOCTORS[appt["doctor"]]
        appointments.append({
            "scheduled_for": appt["scheduled_for"],
            "reason": appt["reason"],
            "status": appt["status"],
            "doctor_name": doctor["name"],
            "doctor_specialty": doctor["specialty"],
            "doctor_hospital": doctor["hospital"],
            "doctor_phone": doctor["phone"],
        })

    status, saved = call("PUT", "/api/portfolio/appointments", appointments, token=token)
    print(f"  appointments {status}: {len(saved) if status == 200 else saved}")

    # give each patient a processed consultation so the demo has something to show
    status, enc = call("POST", "/api/audio/sample", token=token)
    if status == 200:
        status, enc = call("POST", f"/api/encounters/{enc['id']}/transcribe", token=token, timeout=600)
        if status == 200:
            status, enc = call("POST", f"/api/encounters/{enc['id']}/note", token=token, timeout=600)
    if status == 200:
        meds = [m["name"] for m in enc["note"]["entities"]["medications"]]
        print(f"  consultation 200: note ready, medications {meds}, fhir valid={enc['fhir_valid']}")
    else:
        print(f"  consultation {status}: {enc}")

    call("POST", "/api/auth/logout", token=token)
    print()

print("done. sign in with any of:", ", ".join(p["username"] for p in PATIENTS),
      f"/ {DEMO_PASSWORD}")
