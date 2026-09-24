"""Uptime check for the Mason Ark sites, run by GitHub Actions every 10 minutes.

Each check is tried up to 3 times (20 s apart) before it counts as down, so a
single slow response does not wake anyone. Certificates expiring within 14
days are reported too. Writes results.json and exits 1 if anything is down.
"""
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

TIMEOUT = 20
CERT_WARN_DAYS = 14


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mason-ark-uptime/1.0"})
    t0 = time.monotonic()
    try:
        with OPENER.open(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(200_000), time.monotonic() - t0
    except urllib.error.HTTPError as err:
        return err.code, err.read(200_000) if err.fp else b"", time.monotonic() - t0


def judge(check):
    status, body, secs = fetch(check["url"])
    if status != check["expect"]:
        return f"HTTP {status}, expected {check['expect']}", secs
    if "contains" in check and check["contains"].encode() not in body:
        return f"page does not contain {check['contains']!r}", secs
    if "json_ok" in check or "json_field" in check:
        try:
            data = json.loads(body)
        except ValueError:
            return "response is not JSON", secs
        if "json_ok" in check and data.get(check["json_ok"]) is not True:
            return f"{check['json_ok']} is not true: degraded={data.get('degraded')}", secs
        if "json_field" in check:
            key, want = check["json_field"]
            if data.get(key) != want:
                return f"{key} is {data.get(key)!r}, expected {want!r}", secs
    return "", secs


def cert_days(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            not_after = tls.getpeercert()["notAfter"]
    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return (expires - datetime.now(timezone.utc)).days


def main():
    checks = json.load(open("checks.json"))
    results, down = [], []
    for check in checks:
        problem, secs = "", 0.0
        for attempt in range(3):
            try:
                problem, secs = judge(check)
            except Exception as exc:  # noqa: BLE001 - any failure to answer is "down"
                problem = f"{type(exc).__name__}: {exc}"[:200]
            if not problem:
                break
            if attempt < 2:
                time.sleep(20)
        results.append({"name": check["name"], "url": check["url"], "ok": not problem,
                        "problem": problem, "seconds": round(secs, 2)})
        if problem:
            down.append(check["name"])
    hosts = sorted({urlparse(c["url"]).hostname for c in checks})
    for host in hosts:
        try:
            days = cert_days(host)
            if days < CERT_WARN_DAYS:
                results.append({"name": f"TLS certificate {host}", "url": f"https://{host}/", "ok": False,
                                "problem": f"certificate expires in {days} days", "seconds": 0})
                down.append(f"TLS certificate {host}")
        except Exception as exc:  # noqa: BLE001
            results.append({"name": f"TLS certificate {host}", "url": f"https://{host}/", "ok": False,
                            "problem": f"TLS check failed: {exc}"[:200], "seconds": 0})
            down.append(f"TLS certificate {host}")
    json.dump(results, open("results.json", "w"), indent=2)
    for r in results:
        print(("OK   " if r["ok"] else "DOWN ") + f"{r['name']:<28} {r['seconds']:>5}s {r['problem']}")
    sys.exit(1 if down else 0)


if __name__ == "__main__":
    main()
