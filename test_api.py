"""
Quick verification script for the FastAPI backend endpoints.
Tests:
  1. GET  /api/health
  2. POST /api/generate  (local project path)
  3. POST /api/generate  (public GitHub repo URL)
  4. POST /api/generate  (missing input → structured 400 error)
"""

import urllib.request
import urllib.error
import json
import time

BASE = "http://127.0.0.1:8050"

def get(path):
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    r = urllib.request.urlopen(req, timeout=30)
    return r.status, json.loads(r.read())

def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        r = urllib.request.urlopen(req, timeout=300)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("=" * 60)
print("TEST 1: GET /api/health")
print("=" * 60)
status, body = get("/api/health")
print(f"HTTP Status : {status}")
print(f"Response    : {json.dumps(body, indent=2)}")
assert status == 200, "FAIL: expected 200"
assert body.get("status") == "healthy", "FAIL: status != healthy"
assert "model" in body, "FAIL: 'model' key missing"
print("PASS\n")

print("=" * 60)
print("TEST 2: POST /api/generate — missing input (expect 400)")
print("=" * 60)
status, body = post("/api/generate", {})
print(f"HTTP Status : {status}")
print(f"Response    : {json.dumps(body, indent=2)}")
assert status == 400, f"FAIL: expected 400, got {status}"
assert "detail" in body, "FAIL: 'detail' key missing from error"
print("PASS\n")

print("=" * 60)
print("TEST 3: POST /api/generate — local project path")
print("=" * 60)
print("Sending request (may take 60-120s for agent pipeline)...")
t0 = time.time()
status, body = post("/api/generate", {"project_path": "C:/Users/gadam/Smart ReadME"})
elapsed = round(time.time() - t0, 2)
print(f"HTTP Status    : {status}")
if status == 200:
    print(f"Success        : {body['success']}")
    print(f"Project Name   : {body['project_name']}")
    print(f"Execution Time : {body['execution_time']}s")
    print(f"Saved Path     : {body['saved_path']}")
    print(f"Tech Profile   : {json.dumps(body['tech_profile'], indent=2)}")
    print(f"README preview : {body['readme_content'][:300]}")
    print("PASS\n")
else:
    print(f"ERROR response : {json.dumps(body, indent=2)}")
    print("FAIL\n")

print("=" * 60)
print("TEST 4: POST /api/generate — GitHub URL")
print("=" * 60)
print("Cloning & running agents (may take 90-180s)...")
t0 = time.time()
status, body = post("/api/generate", {"github_url": "https://github.com/tiangolo/fastapi"})
elapsed = round(time.time() - t0, 2)
print(f"HTTP Status    : {status}")
if status == 200:
    print(f"Success        : {body['success']}")
    print(f"Project Name   : {body['project_name']}")
    print(f"Execution Time : {body['execution_time']}s")
    print(f"Tech Profile   : {json.dumps(body['tech_profile'], indent=2)}")
    print(f"README preview : {body['readme_content'][:300]}")
    print("PASS\n")
else:
    print(f"ERROR response : {json.dumps(body, indent=2)}")
    print("FAIL\n")

print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
