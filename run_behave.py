import sys
import io
import os
import glob
import json
import re
import html
import time
import smtplib
from datetime import datetime

import requests
from behave.configuration import Configuration
from behave.runner import Runner
from behave.model_core import Status
from email.message import EmailMessage

from features.environment import errors_summary, timing_summary
from timing_tracker import TimingTracker


# =========================
# Console UTF-8 fix (Windows)
# =========================
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

test_summary = []

# Sanitization helpers to avoid unintended formatting like strikethrough
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
STRIKE_COMBINING_RE = re.compile(r"[\u0335\u0336\u0337\u0338]")  # stroke overlays


def strip_ansi(s: str) -> str:
    return ANSI_ESCAPE_RE.sub("", s)


def sanitize_text(s) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = strip_ansi(s)
    s = s.replace("~~", "")
    s = STRIKE_COMBINING_RE.sub("", s)
    return s


def sanitize_html_text(s) -> str:
    return html.escape(sanitize_text(s))


# =========================
# ✅ OTP Fetch (API) Helper
# =========================
def fetch_otp(domain: str, user: str, api_base: str, api_key: str, endpoint: str, timeout: int = 30) -> str:
    if not api_key:
        raise RuntimeError("Missing CL_OTP_API_KEY env var")

    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    payload = {"domain": domain, "user": user, "key": api_key}

    # ✅ IMPORTANT: do NOT follow redirects
    r = requests.post(url, data=payload, timeout=timeout, allow_redirects=False)

    ct = (r.headers.get("Content-Type") or "").lower()

    # ✅ If redirect => RequireLogin / auth is still blocking
    if r.status_code in (301, 302, 303, 307, 308):
        loc = r.headers.get("Location", "")
        raise RuntimeError(
            f"OTP API redirected (status={r.status_code}) to: {loc}  "
            f"=> RequireLogin/auth still blocking this endpoint."
        )

    # ✅ Non-200
    if r.status_code != 200:
        raise RuntimeError(
            f"OTP API HTTP {r.status_code}. content-type={ct}. First 300 chars: {r.text[:300]}"
        )

    # ✅ Must be JSON
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(
            f"OTP API returned non-JSON (status=200, content-type={ct}). First 500 chars: {r.text[:500]}"
        )

    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"OTP API failed: {data}")

    otp = str(data.get("otp", "")).strip()
    if not otp:
        raise RuntimeError(f"OTP missing in response: {data}")

    return otp


# =========================
# Behave Runner (per-domain)
# =========================
def run_behave_on_domain(domain_name, server_name, username, password, base_features_path, timing_dir):
    domain_feature_path = os.path.join(base_features_path, domain_name)
    fallback_path = os.path.join(base_features_path, "global")
    feature_path = domain_feature_path if os.path.isdir(domain_feature_path) else fallback_path

    feature_files = glob.glob(os.path.join(feature_path, "**", "*.feature"), recursive=True)
    print(f"[INFO] Running {len(feature_files)} feature files for domain '{domain_name}':")
    for f in feature_files:
        print(f"    {f}")

    config = Configuration()
    config.userdata.update(
        {
            "domain": domain_name,
            "server": server_name,
            "username": username,  # ✅ NEW
            "password": password,  # ✅ OTP
        }
    )
    config.format = ["pretty"]
    config.reporters = []
    config.paths = [feature_path]

    os.environ["BEHAVE_TIMING_DIR"] = timing_dir

    runner = Runner(config)
    try:
        runner.run()
    except Exception as e:
        msg = f"[WARN] Server error on {server_name} | Domain: {domain_name} -- {e}"
        print(msg)
        errors_summary.append({"domain": domain_name, "feature": "Server Error", "result": msg})
        return msg, {}

    output = [f"\n[INFO] Server: {server_name} | Domain: {domain_name}", "=" * 50]

    for feature in runner.features:
        feature_status = "[PASS]" if all(s.status == Status.passed for s in feature.scenarios) else "[FAIL]"
        output.append(f"{feature_status} {feature.name}")
        for scenario in feature.scenarios:
            result = "[PASS] Pass" if scenario.status == Status.passed else "[FAIL] Fail"
            test_summary.append(
                {
                    "domain": domain_name,
                    "server": server_name,
                    "feature": feature.name,
                    "scenario": scenario.name,
                    "result": result,
                }
            )

    test_summary.extend(errors_summary)
    errors_summary.clear()

    timing_file = os.path.join(timing_dir, f"{domain_name}_timing.json")
    timing_data = {}
    if os.path.exists(timing_file):
        with open(timing_file, "r", encoding="utf-8") as f:
            timing_data = json.load(f)

    return "\n".join(output), timing_data


# =========================
# HTML Summary (your existing)
# =========================

def print_final_summary(timing_summary, timing_tracker=None):


    def key_domain(d, s):
        return f"{s} | {d}"

    # ---------- collect failures + slow tests ----------
    all_failures = []
    all_slow = []

    for domain, domain_summary in timing_summary.items():
        server = domain_summary.get("Server", "Unknown")
        features = domain_summary.get("Features", {})
        page_load = domain_summary.get("Page Load")
        login = domain_summary.get("Login")

        # Page Load
        if not isinstance(page_load, float) or page_load == "Failed":
            all_failures.append({
                "type": "Page Load",
                "domain": domain,
                "server": server,
                "feature": "",
                "scenario": "",
                "details": "Failed to load page"
            })
        elif timing_tracker:
            pd = timing_tracker.format_timing_summary(domain, domain_summary).get("page_load")
            if pd and pd.get("is_high"):
                all_slow.append({
                    "type": "Page Load",
                    "domain": domain,
                    "server": server,
                    "feature": "",
                    "time": page_load,
                    "details": f"Above 7-day avg ({pd.get('average', 0):.1f}s)"
                })

        # Login
        if not isinstance(login, float) or login == "Failed":
            all_failures.append({
                "type": "Login",
                "domain": domain,
                "server": server,
                "feature": "",
                "scenario": "",
                "details": "Failed to login"
            })
        elif timing_tracker:
            ld = timing_tracker.format_timing_summary(domain, domain_summary).get("login")
            if ld and ld.get("is_high"):
                all_slow.append({
                    "type": "Login",
                    "domain": domain,
                    "server": server,
                    "feature": "",
                    "time": login,
                    "details": f"Above 7-day avg ({ld.get('average', 0):.1f}s)"
                })

        # Features + scenarios
        for fname, summary in features.items():
            feature_time = summary.get("Feature")

            if not isinstance(feature_time, float):
                all_failures.append({
                    "type": "Feature",
                    "domain": domain,
                    "server": server,
                    "feature": fname,
                    "scenario": "",
                    "details": "Feature execution failed"
                })
            elif timing_tracker:
                fdata_map = timing_tracker.format_timing_summary(domain, domain_summary).get("features", {}) or {}
                fdata = fdata_map.get(fname)
                if fdata and fdata.get("is_high"):
                    all_slow.append({
                        "type": "Feature",
                        "domain": domain,
                        "server": server,
                        "feature": fname,
                        "time": feature_time,
                        "details": f"Above 7-day avg ({fdata.get('average', 0):.1f}s)"
                    })

            # scenario failures
            for sc in summary.get("Scenario Timings", []) or []:
                if sc.get("status") == "failed":
                    all_failures.append({
                        "type": "Scenario",
                        "domain": domain,
                        "server": server,
                        "feature": fname,
                        "scenario": sc.get("name", ""),
                        "details": f"Scenario failed in {float(sc.get('duration', 0)):.2f}s"
                    })

    total_domains = len(timing_summary)
    total_fail = len(all_failures)
    total_slow = len(all_slow)

    # group slow by domain
    slow_group = {}
    for s in all_slow:
        k = key_domain(s["domain"], s["server"])
        slow_group.setdefault(k, []).append(s)

    # group failures by domain
    fail_group = {}
    for f in all_failures:
        k = key_domain(f["domain"], f["server"])
        fail_group.setdefault(k, []).append(f)

    # ---------- HTML helpers ----------
    def badge(text, bg, fg):
        return (
            "<span style='display:inline-block;padding:3px 10px;border-radius:999px;"
            f"background:{bg};color:{fg};font-size:12px;font-weight:800;line-height:18px;'>"
            f"{sanitize_html_text(text)}</span>"
        )

    def h(txt):
        return sanitize_html_text(txt)

    def row_kv(k, v, vcolor="#111827"):
        return (
            "<tr>"
            f"<td style='padding:8px 10px;color:#6b7280;font-size:13px;border-top:1px solid #eef2f7;width:42%;'>{h(k)}</td>"
            f"<td style='padding:8px 10px;color:{vcolor};font-size:13px;font-weight:800;border-top:1px solid #eef2f7;'>{h(v)}</td>"
            "</tr>"
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---------- build HTML ----------
    html_lines = []
    html_lines.append("<html><body style='margin:0;padding:0;background:#f6f7fb;'>")
    html_lines.append(f"""
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:980px;margin:0 auto;padding:18px;">

  <div style="background:#111827;color:#fff;border-radius:12px;padding:16px 18px;">
    <div style="font-size:18px;font-weight:900;letter-spacing:.2px;">Automated Test Summary Report</div>
    <div style="font-size:12px;color:#cbd5e1;margin-top:6px;">Generated: {h(now_str)}</div>
  </div>

  <!-- executive cards -->
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:12px;">
    <div style="flex:1;min-width:200px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:12px;">
      <div style="font-size:12px;color:#6b7280;">Domains Tested</div>
      <div style="font-size:26px;font-weight:900;color:#111827;margin-top:6px;">{total_domains}</div>
    </div>
    <div style="flex:1;min-width:200px;background:#ffffff;border:1px solid #fee2e2;border-radius:12px;padding:12px;">
      <div style="font-size:12px;color:#b91c1c;">Failures</div>
      <div style="font-size:26px;font-weight:900;color:#b91c1c;margin-top:6px;">{total_fail}</div>
    </div>
    <div style="flex:1;min-width:200px;background:#ffffff;border:1px solid #ffedd5;border-radius:12px;padding:12px;">
      <div style="font-size:12px;color:#c2410c;">Performance Regressions</div>
      <div style="font-size:26px;font-weight:900;color:#c2410c;margin-top:6px;">{total_slow}</div>
    </div>
  </div>

  <!-- boss note -->
  <div style="margin-top:10px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:12px;">
    <div style="font-size:13px;color:#111827;font-weight:900;">What needs attention</div>
    <div style="font-size:12px;color:#6b7280;margin-top:6px;line-height:18px;">
      This report highlights only <b>Failures</b> and <b>Performance regressions</b> (above 7-day average).
      Passed checks are intentionally minimized to keep this email actionable.
    </div>
  </div>
""")

    # ---------- FAILURES section ----------
    if total_fail:
        html_lines.append("""
  <div style="margin-top:12px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
    <div style="padding:12px 14px;background:#7f1d1d;color:#ffffff;font-weight:900;font-size:14px;">
      FAILURES (Action Required)
    </div>
    <table style="width:100%;border-collapse:collapse;">
""")
        # show domain-wise
        for k, items in fail_group.items():
            html_lines.append(f"""
      <tr><td style="padding:10px 14px;background:#fff7f7;border-top:1px solid #fee2e2;">
        {badge("FAIL", "#fee2e2", "#b91c1c")}
        <span style="margin-left:8px;font-weight:900;color:#111827;">{h(k)}</span>
      </td></tr>
""")
            # list items
            for f in items:
                t = h(f.get("type",""))
                feat = h(f.get("feature",""))
                scen = h(f.get("scenario",""))
                details = h(f.get("details",""))

                extra = ""
                if feat:
                    extra += f"<div style='color:#6b7280;font-size:12px;margin-top:4px;'>Feature: <b>{feat}</b></div>"
                if scen:
                    extra += f"<div style='color:#6b7280;font-size:12px;'>Scenario: <b>{scen}</b></div>"

                html_lines.append(f"""
      <tr>
        <td style="padding:12px 14px;border-top:1px solid #eef2f7;">
          <div style="font-weight:900;color:#111827;">{t}</div>
          {extra}
          <div style="color:#111827;font-size:13px;margin-top:8px;">{details}</div>
        </td>
      </tr>
""")

        html_lines.append("""
    </table>
  </div>
""")
    else:
        html_lines.append("""
  <div style="margin-top:12px;background:#ffffff;border:1px solid #dcfce7;border-radius:12px;padding:12px;">
    <div style="font-weight:900;color:#166534;">No Failures detected ✅</div>
  </div>
""")

    # ---------- PERFORMANCE section ----------
    if total_slow:
        html_lines.append("""
  <div style="margin-top:12px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
    <div style="padding:12px 14px;background:#7c2d12;color:#ffffff;font-weight:900;font-size:14px;">
      PERFORMANCE REGRESSIONS (Above 7-day average)
    </div>
    <table style="width:100%;border-collapse:collapse;">
""")
        for k, items in slow_group.items():
            html_lines.append(f"""
      <tr><td style="padding:10px 14px;background:#fff7ed;border-top:1px solid #fed7aa;">
        {badge("SLOW", "#ffedd5", "#c2410c")}
        <span style="margin-left:8px;font-weight:900;color:#111827;">{h(k)}</span>
      </td></tr>
""")
            # sort slow items by time desc
            items_sorted = sorted(items, key=lambda x: float(x.get("time", 0) or 0), reverse=True)
            for s in items_sorted:
                t = h(s.get("type",""))
                feat = h(s.get("feature",""))
                tm = s.get("time", None)
                details = h(s.get("details",""))

                line = f"{t}"
                if isinstance(tm, (int,float)):
                    line += f" • {tm:.2f}s"
                if feat:
                    line += f" • Feature: {feat}"

                html_lines.append(f"""
      <tr>
        <td style="padding:12px 14px;border-top:1px solid #eef2f7;">
          <div style="font-weight:900;color:#111827;">{h(line)}</div>
          <div style="color:#6b7280;font-size:12px;margin-top:6px;">{details}</div>
        </td>
      </tr>
""")

        html_lines.append("""
    </table>
  </div>
""")
    else:
        html_lines.append("""
  <div style="margin-top:12px;background:#ffffff;border:1px solid #dcfce7;border-radius:12px;padding:12px;">
    <div style="font-weight:900;color:#166534;">No Performance regressions ✅</div>
  </div>
""")

    # ---------- NEXT ACTIONS (template) ----------
    html_lines.append("""
  <div style="margin-top:12px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:12px;">
    <div style="font-size:14px;font-weight:900;color:#111827;">Next Actions</div>
    <ul style="margin:8px 0 0 18px;color:#374151;font-size:13px;line-height:20px;">
      <li>Investigate failures first (scenario-level). Confirm if regression is data-related or UI change.</li>
      <li>For slow tests: review server load, DB locks, and recent deploy changes. Compare against 7-day baseline.</li>
      <li>Re-run only affected domains after fixes for quick confirmation.</li>
    </ul>
  </div>
""")

    # ---------- DOMAIN SNAPSHOT (high-level, boss readable) ----------
    html_lines.append("""
  <div style="margin-top:12px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
    <div style="padding:12px 14px;background:#0f172a;color:#ffffff;font-weight:900;font-size:14px;">
      Domain Snapshot
    </div>
""")

    for domain, domain_summary in timing_summary.items():
        server = domain_summary.get("Server", "Unknown")
        features = domain_summary.get("Features", {})
        page_load = domain_summary.get("Page Load")
        login = domain_summary.get("Login")

        safe_server = h(server)
        safe_domain = h(domain)

        # quick status
        domain_fail_count = len(fail_group.get(key_domain(domain, server), []))
        domain_slow_count = len(slow_group.get(key_domain(domain, server), []))

        html_lines.append(f"""
    <div style="padding:12px 14px;border-top:1px solid #eef2f7;">
      <div style="font-weight:900;color:#111827;">{safe_domain}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px;">Server: <b>{safe_server}</b></div>

      <div style="margin-top:8px;">
        {badge(f"Failures: {domain_fail_count}", "#fee2e2" if domain_fail_count else "#dcfce7", "#b91c1c" if domain_fail_count else "#166534")}
        <span style="display:inline-block;width:8px;"></span>
        {badge(f"Slow: {domain_slow_count}", "#ffedd5" if domain_slow_count else "#dcfce7", "#c2410c" if domain_slow_count else "#166534")}
      </div>

      <table style="width:100%;border-collapse:collapse;margin-top:10px;border:1px solid #eef2f7;border-radius:10px;overflow:hidden;">
""")

        if isinstance(page_load, float):
            html_lines.append(row_kv("Page Load", f"{page_load:.2f}s", "#16a34a"))
        else:
            html_lines.append(row_kv("Page Load", "FAILED", "#b91c1c"))

        if isinstance(login, float):
            html_lines.append(row_kv("Login", f"{login:.2f}s", "#16a34a"))
        else:
            html_lines.append(row_kv("Login", "FAILED", "#b91c1c"))

        html_lines.append(row_kv("Features Executed", str(len(features)), "#111827"))
        html_lines.append("</table></div>")

    html_lines.append("</div>")  # close snapshot card
    html_lines.append("</div></body></html>")

    return "".join(html_lines)

# =========================
# Email Sender
# =========================
def send_test_summary_email(summary_html, summary_text_fallback=None):
    try:
        msg = EmailMessage()
        msg["Subject"] = "[SUMMARY] Automated Test Summary Report"
        msg["From"] = "CLAutomation_Alert@inayaat.com"
        msg["To"] = "devleads@cartzlink.com"

        if not summary_text_fallback:
            summary_text_fallback = "Automated Test Summary Report (HTML). Please view in an HTML-capable email client."
        msg.set_content(summary_text_fallback)

        msg.add_alternative(summary_html, subtype="html")

        # ✅ Move SMTP password to env (recommended)
        SMTP_PASS = 'x6!493Crz'
        if not SMTP_PASS:
            raise RuntimeError("Missing CL_SMTP_PASS env var for SMTP login")

        with smtplib.SMTP_SSL("s7.itserver.biz", 465) as server:
            server.login("CLAutomation_Alert@inayaat.com", SMTP_PASS)
            server.send_message(msg)

        print("[PASS] Test summary email sent successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to send email: {e}")


# =========================
# Main
# =========================
# def main():
#     base_dir = os.path.dirname(os.path.realpath(__file__))
#     features_dir = os.path.join(base_dir, "features")
#     timing_dir = os.path.join(base_dir, "timing_results")

#     all_timing = {}
#     timing_tracker = TimingTracker()
#     timing_tracker.cleanup_old_data()  # Remove data older than 7 days

#     # ✅ OTP configuration
#     OTP_USER = "cl_tester"
#     OTP_API_BASE = "https://crm.cartzlink.com"
#     OTP_ENDPOINT = "admin/indexyii.php?r=api/GetOTPApi"  # ✅ Adjust if your route differs
#     OTP_API_KEY = os.environ.get("CL_OTP_API_KEY", "")

#     # Fetch domains
#     try:
#     url = "https://crm.cartzlink.com/admin/indexyii.php?r=api/FetchDomainList"

#     # ✅ same key as OTP (recommended: reuse CL_OTP_API_KEY)
#     payload = {"key": OTP_API_KEY}  # OTP_API_KEY = os.environ.get("CL_OTP_API_KEY","")

#     response = requests.post(url, data=payload, timeout=30)
#     response.raise_for_status()

#     data = response.json()

#     # ✅ new response format: { ok: 1, data: [...] }
#     if not isinstance(data, dict) or not data.get("ok"):
#         raise ValueError(f"FetchDomainList failed: {data}")

#     domains = data.get("data", [])
#     if not isinstance(domains, list):
#         raise ValueError(f"Unexpected domains type: {type(domains)}")

#     if not domains:
#         raise ValueError("Domain list is empty")

# except Exception as e:
#     print(f"Error fetching domain list: {e}")
#     return

# # Run tests per domain
# for entry in domains:
#     domain = entry["domain"]
#     server = entry["server"]

#     print(f"\n{'='*60}")
#     print(f"STARTING DOMAIN: {domain} (Server: {server})")
#     print(f"{'='*60}")

#     # ✅ Generate OTP per-domain immediately before login/tests
#     try:
#         otp = fetch_otp(domain, OTP_USER, OTP_API_BASE, OTP_API_KEY, OTP_ENDPOINT)
#     except Exception as e:
#         msg = f"[FAIL] OTP fetch failed | Domain: {domain} | Server: {server} | {e}"
#         print(msg)
#         errors_summary.append({"domain": domain, "feature": "OTP Error", "result": msg})
#         continue


#         result, timing_data = run_behave_on_domain(
#             domain,
#             server,
#             OTP_USER,
#             otp, 
#             features_dir,
#             timing_dir,
#         )

#         print(result)
#         all_timing.update(timing_data)

#         if timing_data:
#             timing_tracker.add_timing_data(domain, timing_data)

#         print(f"\n{'='*60}")
#         print(f"COMPLETED DOMAIN: {domain}")
#         print(f"{'='*60}")

#         time.sleep(2)

#     # Final summary + email
#     summary_html = print_final_summary(all_timing, timing_tracker)
#     send_test_summary_email(summary_html, "Automated Test Summary Report (HTML).")


def main():
    base_dir = os.path.dirname(os.path.realpath(__file__))
    features_dir = os.path.join(base_dir, "features")
    timing_dir = os.path.join(base_dir, "timing_results")

    all_timing = {}
    timing_tracker = TimingTracker()
    timing_tracker.cleanup_old_data()  # Remove data older than 7 days

    # ✅ OTP configuration
    OTP_USER = "cl_tester"
    OTP_API_BASE = "https://crm.cartzlink.com"
    OTP_ENDPOINT = "admin/indexyii.php?r=api/GetOTPApi"
    OTP_API_KEY = os.environ.get("CL_OTP_API_KEY", "")

    # -------------------------
    # Fetch domains (SECURED)
    # -------------------------
    try:
        url = "https://crm.cartzlink.com/admin/indexyii.php?r=api/FetchDomainList"
        payload = {"key": OTP_API_KEY}

        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Expected: { ok: 1, data: [...] }
        if not isinstance(data, dict) or not data.get("ok"):
            raise ValueError(f"FetchDomainList failed: {data}")

        domains = data.get("data", [])
        if not isinstance(domains, list):
            raise ValueError(f"Unexpected domains type: {type(domains)}")

        if not domains:
            raise ValueError("Domain list is empty")

    except Exception as e:
        print(f"Error fetching domain list: {e}")
        return

    # -------------------------
    # Run tests per domain
    # -------------------------
    for entry in domains:
        domain = entry["domain"]
        server = entry["server"]

        print(f"\n{'='*60}")
        print(f"STARTING DOMAIN: {domain} (Server: {server})")
        print(f"{'='*60}")

        # ✅ Generate OTP per-domain immediately before login/tests
        try:
            otp = fetch_otp(domain, OTP_USER, OTP_API_BASE, OTP_API_KEY, OTP_ENDPOINT)
        except Exception as e:
            msg = f"[FAIL] OTP fetch failed | Domain: {domain} | Server: {server} | {e}"
            print(msg)
            errors_summary.append({"domain": domain, "feature": "OTP Error", "result": msg})
            continue

        result, timing_data = run_behave_on_domain(
            domain,
            server,
            OTP_USER,
            otp,
            features_dir,
            timing_dir,
        )

        print(result)
        all_timing.update(timing_data)

        if timing_data:
            timing_tracker.add_timing_data(domain, timing_data)

        print(f"\n{'='*60}")
        print(f"COMPLETED DOMAIN: {domain}")
        print(f"{'='*60}")

        time.sleep(2)

    # Final summary + email
    summary_html = print_final_summary(all_timing, timing_tracker)
    send_test_summary_email(summary_html, "Automated Test Summary Report (HTML).")


if __name__ == "__main__":
    main()
