#!/usr/bin/env python3
"""Test Rhythmverse API — shows actual JSON structure returned."""
import urllib.request, json, sys, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test(endpoint, body):
    req = urllib.request.Request(
        f"https://rhythmverse.co/api/all/songfiles/{endpoint}",
        data=body.encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://rhythmverse.co/songfiles/game",
            "Origin": "https://rhythmverse.co",
        }
    )
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    return json.loads(resp.read())

print("=== SEARCH: metallica ===")
r = test("search/live", "data_type=full&text=metallica&page=1&records=2")
print(f"status: {r.get('status')}")
d = r.get("data", {})
print(f"records: {d.get('records')}")
print(f"pagination: {d.get('pagination')}")
songs = d.get("songs", [])
print(f"songs count: {len(songs)}")
if songs:
    print("\nFirst song FULL structure:")
    print(json.dumps(songs[0], indent=2))
else:
    print("No songs returned")
    print(json.dumps(r, indent=2)[:2000])
