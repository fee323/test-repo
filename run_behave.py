import sys
import io
import os
from behave.configuration import Configuration
from selenium.webdriver import Chrome, ChromeOptions
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from behave.runner import Runner
from behave.model_core import Status
import smtplib
from email.message import EmailMessage
from features.environment import errors_summary, timing_summary
import json
import glob
from email.mime.text import MIMEText
from timing_tracker import TimingTracker
import re
import html

#def safe_str(obj):
    # Remove non-ASCII characters
    #return ''.join(c if ord(c) < 128 else '?' for c in str(obj))

# UTF-8 fix for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

test_summary = []

# Sanitization helpers to avoid unintended formatting like strikethrough
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
STRIKE_COMBINING_RE = re.compile(r"[\u0335\u0336\u0337\u0338]")  # Short/long stroke overlays and slashes


def strip_ansi(s: str) -> str:
    return ANSI_ESCAPE_RE.sub("", s)


def sanitize_text(s) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    # Remove ANSI codes
    s = strip_ansi(s)
    # Remove markdown strikethrough markers
    s = s.replace("~~", "")
    # Remove unicode combining strikethrough overlays
    s = STRIKE_COMBINING_RE.sub("", s)
    return s


def sanitize_html_text(s) -> str:
    return html.escape(sanitize_text(s))


def format_7_day_summary(metric_data, metric_name):
    """Format 7-day average summary for display"""
    if not metric_data or metric_data.get("average") is None:
        return ""
    
    current = metric_data["current"]
    average = metric_data["average"]
    values = metric_data["values"]
    is_high = metric_data.get("is_high", False)
    
    # Format values as comma-separated list
    values_str = ", ".join([f"{v:.1f}" for v in values])
    
    # Create summary text with actual number of days
    num_days = len(values)
    if num_days == 1:
        summary = f"\nTimes (Today): {values_str}\n"
        summary += f"Today: {current:.1f}"
    else:
        summary = f"\nTimes (Last {num_days} Days): {values_str}\n"
        summary += f"{num_days}-Day Avg: {average:.1f}\n"
        summary += f"Today: {current:.1f}"
    
    # Add warning if today's time is high
    if is_high:
        summary += f"  Above {num_days}-Day Avg"
    
    return summary

def run_behave_on_domain(domain_name, server_name, password, base_features_path, timing_dir):
    domain_feature_path = os.path.join(base_features_path, domain_name)
    fallback_path = os.path.join(base_features_path, "global")
    feature_path = domain_feature_path if os.path.isdir(domain_feature_path) else fallback_path

    # List all .feature files in the feature_path
    feature_files = glob.glob(os.path.join(feature_path, '**', '*.feature'), recursive=True)
    print(f"[INFO] Running {len(feature_files)} feature files for domain '{domain_name}':")
    for f in feature_files:
        print(f"    {f}")

    config = Configuration()
    config.userdata.update({"domain": domain_name, "password": password, "server": server_name})
    config.format = ['pretty']
    config.reporters = []
    config.paths = [feature_path]

    os.environ["BEHAVE_TIMING_DIR"] = timing_dir

    runner = Runner(config)
    try:
        runner.run()
    except Exception as e:
        # msg = f"[WARN] Server error on {server_name} | Domain: {domain_name} -- {safe_str(e)}"
        msg = f"[WARN] Server error on {server_name} | Domain: {domain_name} -- {e}"
        print(msg)
        errors_summary.append({"domain": domain_name, "feature": "Server Error", "result": msg})
        return msg, {}

    output = [f"\n[INFO] Server: {server_name} | Domain: {domain_name}", "=" * 50]
    #output = []

    for feature in runner.features:
        feature_status = "[PASS]" if all(s.status == Status.passed for s in feature.scenarios) else "[FAIL]"
        output.append(f"{feature_status} {feature.name}")
        for scenario in feature.scenarios:
            result = "[PASS] Pass" if scenario.status == Status.passed else "[FAIL] Fail"
            test_summary.append({
                "domain": domain_name, "server": server_name,
                "feature": feature.name, "scenario": scenario.name,
                "result": result
            })

    test_summary.extend(errors_summary)
    errors_summary.clear()

    # Read timing summary from file
    timing_file = os.path.join(timing_dir, f"{domain_name}_timing.json")
    timing_data = {}
    if os.path.exists(timing_file):
        with open(timing_file, "r", encoding="utf-8") as f:
            timing_data = json.load(f)
    return "\n".join(output), timing_data

def print_final_summary(timing_summary, timing_tracker=None):
    print("\n" + "=" * 50)
    print("[SUMMARY] FINAL TEST SUMMARY")
    print("=" * 50)
    
    # Collect all failures and performance issues for summary at the top
    all_failures = []
    all_slow_tests = []
    
    for domain, domain_summary in timing_summary.items():
        server = domain_summary.get("Server", "Unknown")
        features = domain_summary.get("Features", {})
        page_load = domain_summary.get("Page Load")
        login = domain_summary.get("Login")
        
        # Check page load failures and performance
        if not isinstance(page_load, float) or page_load == "Failed":
            all_failures.append({
                "type": "Page Load",
                "domain": domain,
                "server": server,
                "details": "Failed to load page"
            })
        elif timing_tracker:
            page_load_data = timing_tracker.format_timing_summary(domain, domain_summary).get("page_load")
            if page_load_data and page_load_data.get("is_high"):
                all_slow_tests.append({
                    "type": "Page Load",
                    "domain": domain,
                    "server": server,
                    "time": page_load,
                    "avg_time": page_load_data.get("average", 0),
                    "details": f"Above 7-day average ({page_load_data.get('average', 0):.1f}s)"
                })
        
        # Check login failures and performance
        if not isinstance(login, float) or login == "Failed":
            all_failures.append({
                "type": "Login",
                "domain": domain,
                "server": server,
                "details": "Failed to login"
            })
        elif timing_tracker:
            login_data = timing_tracker.format_timing_summary(domain, domain_summary).get("login")
            if login_data and login_data.get("is_high"):
                all_slow_tests.append({
                    "type": "Login",
                    "domain": domain,
                    "server": server,
                    "time": login,
                    "avg_time": login_data.get("average", 0),
                    "details": f"Above 7-day average ({login_data.get('average', 0):.1f}s)"
                })
        
        # Check feature failures and performance
        for fname, summary in features.items():
            feature_time = summary.get("Feature")
            if not isinstance(feature_time, float):
                all_failures.append({
                    "type": "Feature",
                    "domain": domain,
                    "server": server,
                    "feature": fname,
                    "details": "Feature execution failed"
                })
            elif timing_tracker:
                features_data = timing_tracker.format_timing_summary(domain, domain_summary).get("features", {})
                feature_data = features_data.get(fname) if features_data else None
                if feature_data and feature_data.get("is_high"):
                    all_slow_tests.append({
                        "type": "Feature",
                        "domain": domain,
                        "server": server,
                        "feature": fname,
                        "time": feature_time,
                        "avg_time": feature_data.get("average", 0),
                        "details": f"Above 7-day average ({feature_data.get('average', 0):.1f}s)"
                    })
            
            # Check scenario failures and performance
            scenario_timings = summary.get("Scenario Timings", [])
            for scenario in scenario_timings:
                if scenario["status"] == "failed":
                    all_failures.append({
                        "type": "Scenario",
                        "domain": domain,
                        "server": server,
                        "feature": fname,
                        "scenario": scenario["name"],
                        "details": f"Scenario failed in {scenario['duration']:.2f}s"
                    })

    
    # Print failures and performance issues summary at the top
    if all_failures or all_slow_tests:
        print("\n" + "=" * 80)
        print("[CRITICAL] FAILURES AND PERFORMANCE ISSUES SUMMARY")
        print("=" * 80)
        
        if all_failures:
            print(f"\nFAILURES ({len(all_failures)} total):")
            print("-" * 50)
            for failure in all_failures:
                if failure["type"] == "Page Load":
                    print(f"[FAIL] {failure['type']} FAILED | {failure['server']} | {failure['domain']}")
                    print(f"   Details: {failure['details']}")
                elif failure["type"] == "Login":
                    print(f"[FAIL] {failure['type']} FAILED | {failure['server']} | {failure['domain']}")
                    print(f"   Details: {failure['details']}")
                elif failure["type"] == "Feature":
                    print(f"[FAIL] {failure['type']} FAILED | {failure['server']} | {failure['domain']}")
                    print(f"   Feature: {failure['feature']}")
                    print(f"   Details: {failure['details']}")
                elif failure["type"] == "Scenario":
                    print(f"[FAIL] {failure['type']} FAILED | {failure['server']} | {failure['domain']}")
                    print(f"   Feature: {failure['feature']}")
                    print(f"   Scenario: {failure['scenario']}")
                    print(f"   Details: {failure['details']}")
                print()
        
        if all_slow_tests:
            print(f"\nSLOW TESTS ({len(all_slow_tests)} total):")
            print("-" * 50)
            for slow_test in all_slow_tests:
                if slow_test["type"] == "Page Load":
                    print(f"[SLOW] {slow_test['type']} SLOW | {slow_test['server']} | {slow_test['domain']}")
                    print(f"   Time: {slow_test['time']:.2f}s | {slow_test['details']}")
                elif slow_test["type"] == "Login":
                    print(f"[SLOW] {slow_test['type']} SLOW | {slow_test['server']} | {slow_test['domain']}")
                    print(f"   Time: {slow_test['time']:.2f}s | {slow_test['details']}")
                elif slow_test["type"] == "Feature":
                    print(f"[SLOW] {slow_test['type']} SLOW | {slow_test['server']} | {slow_test['domain']}")
                    print(f"   Feature: {slow_test['feature']}")
                    print(f"   Time: {slow_test['time']:.2f}s | {slow_test['details']}")
                # Scenarios removed from slow tests
        
        print("=" * 80)
        print()
    
    # Generate HTML content for email
    html_lines = []
    html_lines.append("<html><body>")
    html_lines.append("<h2>FINAL TEST SUMMARY</h2>")
    
    # Add failures and performance issues to HTML
    if all_failures or all_slow_tests:
        html_lines.append("<h3 style='color: #d32f2f;'>FAILURES AND PERFORMANCE ISSUES SUMMARY</h3>")
        
        if all_failures:
            html_lines.append(f"<h4 style='color: #d32f2f;'>FAILURES ({len(all_failures)} total):</h4>")
            html_lines.append("<ul>")
            for failure in all_failures:
                if failure["type"] == "Page Load":
                    html_lines.append(f"<li style='color: #d32f2f;'><strong>{failure['type']} FAILED</strong> | {failure['server']} | {failure['domain']}<br>Details: {failure['details']}</li>")
                elif failure["type"] == "Login":
                    html_lines.append(f"<li style='color: #d32f2f;'><strong>{failure['type']} FAILED</strong> | {failure['server']} | {failure['domain']}<br>Details: {failure['details']}</li>")
                elif failure["type"] == "Feature":
                    html_lines.append(f"<li style='color: #d32f2f;'><strong>{failure['type']} FAILED</strong> | {failure['server']} | {failure['domain']}<br>Feature: {failure['feature']}<br>Details: {failure['details']}</li>")
                elif failure["type"] == "Scenario":
                    html_lines.append(f"<li style='color: #d32f2f;'><strong>{failure['type']} FAILED</strong> | {failure['server']} | {failure['domain']}<br>Feature: {failure['feature']}<br>Scenario: {failure['scenario']}<br>Details: {failure['details']}</li>")
            html_lines.append("</ul>")
        
        if all_slow_tests:
            html_lines.append(f"<h4 style='color: #f57c00;'>SLOW TESTS ({len(all_slow_tests)} total):</h4>")
            html_lines.append("<ul>")
            for slow_test in all_slow_tests:
                if slow_test["type"] == "Page Load":
                    html_lines.append(f"<li style='color: #f57c00;'><strong>{slow_test['type']} SLOW</strong> | {slow_test['server']} | {slow_test['domain']}<br>Time: {slow_test['time']:.2f}s | {slow_test['details']}</li>")
                elif slow_test["type"] == "Login":
                    html_lines.append(f"<li style='color: #f57c00;'><strong>{slow_test['type']} SLOW</strong> | {slow_test['server']} | {slow_test['domain']}<br>Time: {slow_test['time']:.2f}s | {slow_test['details']}</li>")
                elif slow_test["type"] == "Feature":
                    html_lines.append(f"<li style='color: #f57c00;'><strong>{slow_test['type']} SLOW</strong> | {slow_test['server']} | {slow_test['domain']}<br>Feature: {slow_test['feature']}<br>Time: {slow_test['time']:.2f}s | {slow_test['details']}</li>")
                # Scenarios removed from slow tests
            html_lines.append("</ul>")
        
        html_lines.append("<hr>")
    
    for domain, domain_summary in timing_summary.items():
        server = domain_summary.get("Server", "Unknown")
        features = domain_summary.get("Features", {})
        page_load = domain_summary.get("Page Load")
        login = domain_summary.get("Login")
        
        safe_server = sanitize_html_text(server)
        safe_domain = sanitize_html_text(domain)
        html_lines.append(f"<h3>Server: {safe_server} | Domain: {safe_domain}</h3>")
        html_lines.append("<h4>Features executed:</h4>")
        html_lines.append("<ul>")
        for fname in features:
            html_lines.append(f"<li>{sanitize_html_text(fname)}</li>")
        html_lines.append("</ul>")
        html_lines.append("<hr>")
        
        # Page Load and Login status (domain level)
        if isinstance(page_load, float):
            # Get 7-day average data if tracker is available
            page_load_summary = ""
            if timing_tracker:
                page_load_data = timing_tracker.format_timing_summary(domain, domain_summary).get("page_load")
                if page_load_data:
                    page_load_summary = format_7_day_summary(page_load_data, "page_load")
                    if page_load_data.get("is_high"):
                        html_lines.append(f"<span style='color:red; font-weight:bold;'>PASS Page Load ({page_load:.2f}s)  Above 7-Day Avg</span><br>")
                    else:
                        html_lines.append(f"<span style='color:green;'>PASS Page Load ({page_load:.2f}s)</span><br>")
                else:
                    html_lines.append(f"<span style='color:green;'>PASS Page Load ({page_load:.2f}s)</span><br>")
            
            # Add 7-day summary to HTML
            if page_load_summary:
                html_lines.append(f"<div style='margin-left: 20px; font-size: 0.9em; color: #666;'>{sanitize_html_text(page_load_summary).replace(chr(10), '<br>')}</div>")
        else:
            html_lines.append("<span style='color:red;'>FAIL Page Load: Failed</span><br>")
        
        if isinstance(login, float):
            # Get 7-day average data if tracker is available
            login_summary = ""
            if timing_tracker:
                login_data = timing_tracker.format_timing_summary(domain, domain_summary).get("login")
                if login_data:
                    login_summary = format_7_day_summary(login_data, "login")
                    if login_data.get("is_high"):
                        html_lines.append(f"<span style='color:red; font-weight:bold;'>PASS Login ({login:.2f}s)  Above 7-Day Avg</span><br>")
                    else:
                        html_lines.append(f"<span style='color:green;'>PASS Login ({login:.2f}s)</span><br>")
                else:
                    html_lines.append(f"<span style='color:green;'>PASS Login ({login:.2f}s)</span><br>")
            
            # Add 7-day summary to HTML
            if login_summary:
                html_lines.append(f"<div style='margin-left: 20px; font-size: 0.9em; color: #666;'>{sanitize_html_text(login_summary).replace(chr(10), '<br>')}</div>")
        else:
            html_lines.append("<span style='color:red;'>FAIL Login: Failed</span><br>")
        
        html_lines.append("<br>")
        
        for fname, summary in features.items():
            safe_fname = sanitize_html_text(fname)
            html_lines.append(f"<h4>Feature: {safe_fname}</h4>")
            
            feature_time = summary.get("Feature")
            scenario_timings = summary.get("Scenario Timings", [])
            
            # Feature status
            if isinstance(feature_time, float):
                # Get 7-day average data if tracker is available
                feature_summary = ""
                if timing_tracker:
                    features_data = timing_tracker.format_timing_summary(domain, domain_summary).get("features", {})
                    feature_data = features_data.get(fname) if features_data else None
                    if feature_data:
                        feature_summary = format_7_day_summary(feature_data, "feature")
                        if feature_data.get("is_high"):
                            html_lines.append(f"<span style='color:red; font-weight:bold;'>PASS Feature: {safe_fname} ({feature_time:.2f}s)  Above 7-Day Avg</span><br>")
                        else:
                            html_lines.append(f"<span style='color:green;'>PASS Feature: {safe_fname} ({feature_time:.2f}s)</span><br>")
                    else:
                        html_lines.append(f"<span style='color:green;'>PASS Feature: {safe_fname} ({feature_time:.2f}s)</span><br>")
                else:
                    html_lines.append(f"<span style='color:green;'>PASS Feature: {safe_fname} ({feature_time:.2f}s)</span><br>")
                
                # Add 7-day summary to HTML
                if feature_summary:
                    html_lines.append(f"<div style='margin-left: 20px; font-size: 0.9em; color: #666;'>{sanitize_html_text(feature_summary).replace(chr(10), '<br>')}</div>")
            else:
                html_lines.append(f"<span style='color:red;'>FAIL Feature: {safe_fname} Failed</span><br>")
            
            # Separate failed and passed scenarios
            failed_scenarios = []
            passed_scenarios = []
            
            for scenario in scenario_timings:
                if scenario["status"] == "failed":
                    failed_scenarios.append(scenario)
                else:
                    passed_scenarios.append(scenario)
            
            # Show failed scenarios first
            if failed_scenarios:
                html_lines.append("<h5>FAILED Scenarios:</h5>")
                for scenario in failed_scenarios:
                    html_lines.append(f"<span style='color:red;'>FAILED: {sanitize_html_text(scenario['name'])} ({scenario['duration']:.2f}s)</span><br>")
                    
                    # Show failed steps for this scenario
                    for step in scenario.get("failed_steps", []):
                        html_lines.append(f"<span style='color:red;'>Step: {sanitize_html_text(step['Step'])}<br>")
                        html_lines.append(f"Error: {sanitize_html_text(step['Error'])}<br>")
                        html_lines.append(f"Time: {step['Duration']:.2f}s</span><br>")
                    html_lines.append("<br>")
            
            # Show passed scenarios
            if passed_scenarios:
                html_lines.append("<h5>PASSED Scenarios:</h5>")
                for scenario in passed_scenarios:
                    html_lines.append(f"<span style='color:green;'>PASSED: {sanitize_html_text(scenario['name'])} ({scenario['duration']:.2f}s)</span><br>")
            
            html_lines.append("<br>")
    
    html_lines.append("</body></html>")
    
    # Also print plain text version to console
    final_lines = []
    for domain, domain_summary in timing_summary.items():
        server = domain_summary.get("Server", "Unknown")
        features = domain_summary.get("Features", {})
        page_load = domain_summary.get("Page Load")
        login = domain_summary.get("Login")
        
        final_lines.append(f"\n[INFO] Server: {server} | Domain: {domain}")
        final_lines.append(f"[INFO] Features executed:")
        for fname in features:
            final_lines.append(f"    {fname}")
        final_lines.append("=" * 50)
        
        # Page Load and Login status (domain level)
        if isinstance(page_load, float):
            # Get 7-day average data if tracker is available
            if timing_tracker:
                print(f"[DEBUG] Getting 7-day data for domain: {domain}")
                page_load_data = timing_tracker.format_timing_summary(domain, domain_summary).get("page_load")
                print(f"[DEBUG] Page load data: {page_load_data}")
                
                if page_load_data and page_load_data.get("is_high"):
                    final_lines.append(f"[PASS] Page Load ({page_load:.2f}s)  Above 7-Day Avg")
                else:
                    final_lines.append(f"[PASS] Page Load ({page_load:.2f}s)")
                
                # Add 7-day summary to console
                if page_load_data:
                    summary = format_7_day_summary(page_load_data, "page_load")
                    print(f"[DEBUG] Formatted summary: {summary}")
                    if summary:
                        final_lines.append(summary)
            else:
                final_lines.append(f"[PASS] Page Load ({page_load:.2f}s)")
        else:
            final_lines.append("[FAIL] Page Load: Failed")
        
        if isinstance(login, float):
            # Get 7-day average data if tracker is available
            if timing_tracker:
                print(f"[DEBUG] Getting 7-day login data for domain: {domain}")
                login_data = timing_tracker.format_timing_summary(domain, domain_summary).get("login")
                print(f"[DEBUG] Login data: {login_data}")
                
                if login_data and login_data.get("is_high"):
                    final_lines.append(f"[PASS] Login ({login:.2f}s)  Above 7-Day Avg")
                else:
                    final_lines.append(f"[PASS] Login ({login:.2f}s)")
                
                # Add 7-day summary to console
                if login_data:
                    summary = format_7_day_summary(login_data, "login")
                    print(f"[DEBUG] Formatted login summary: {summary}")
                    if summary:
                        final_lines.append(summary)
            else:
                final_lines.append(f"[PASS] Login ({login:.2f}s)")
        else:
            final_lines.append("[FAIL] Login: Failed")
        
        final_lines.append("")
        
        for fname, summary in features.items():
            final_lines.append(f"[INFO] Feature: {fname}")
            feature_time = summary.get("Feature")
            scenario_timings = summary.get("Scenario Timings", [])
            
            if isinstance(feature_time, float):
                # Get 7-day average data if tracker is available
                if timing_tracker:
                    features_data = timing_tracker.format_timing_summary(domain, domain_summary).get("features", {})
                    feature_data = features_data.get(fname) if features_data else None
                    if feature_data and feature_data.get("is_high"):
                        final_lines.append(f"[PASS] Feature: {fname} ({feature_time:.2f}s)  Above 7-Day Avg")
                    else:
                        final_lines.append(f"[PASS] Feature: {fname} ({feature_time:.2f}s)")
                    
                    # Add 7-day summary to console
                    if feature_data:
                        summary = format_7_day_summary(feature_data, "feature")
                        if summary:
                            final_lines.append(summary)
                else:
                    final_lines.append(f"[PASS] Feature: {fname} ({feature_time:.2f}s)")
            else:
                final_lines.append(f"[FAIL] Feature: {fname} Failed")
            
            for scenario in scenario_timings:
                status_icon = "[PASS]" if scenario["status"] == "passed" else "[FAIL]"
                final_lines.append(f"{status_icon} Scenario: {scenario['name']} ({scenario['duration']:.2f}s)")
                for step in scenario.get("failed_steps", []):
                    final_lines.append(f"    [FAIL] Step: {step['Step']} -- {step['Duration']:.2f}s")
                    final_lines.append(f"        Error: {step['Error']}")
    
    final_output = "\n".join(final_lines)
    print(final_output)
    
    # Return HTML content for email
    html_content = "".join(html_lines)
    return html_content

def send_test_summary_email(summary_text):
    try:
        msg = EmailMessage()
        msg["Subject"] = "[SUMMARY] Automated Test Summary Report"
        msg["From"] = "CLAutomation_Alert@inayaat.com"
        msg["To"] = "shafi@cartzlink.com"#, Devleads@cartzlink.com"
        
        # Set HTML content properly
        msg.set_content(summary_text, subtype='html')

        with smtplib.SMTP_SSL("s7.itserver.biz", 465) as server:
            server.login("CLAutomation_Alert@inayaat.com", "x6!493Crz")
            server.send_message(msg)
        print("[PASS] Test summary email sent successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to send email: {e}")

def main():
    base_dir = os.path.dirname(os.path.realpath(__file__))
    features_dir = os.path.join(base_dir, "features")
    timing_dir = os.path.join(base_dir, "timing_results")
    all_timing = {}
    
    # Initialize timing tracker for 7-day averages
    timing_tracker = TimingTracker()
    timing_tracker.cleanup_old_data()  # Remove data older than 7 days

    domains = [
#        {"domain": "anamta.primeerp.top", "server": "s12", "password": "fdgd"},
#        {"domain": "anamta.primeerp.top", "server": "s12", "password": "czxVYO,30y8{2w"},
#        {"domain": "mhp.itserver.biz", "server": "MHP", "password": "czxVYO,30y8{2w"},
        {"domain": "mt2.itserver.biz", "server": "metro crm", "password": "c3q)1k10(Yv!"},
#        {"domain": "mt.itserver.biz", "server": "metro crm", "password": "vI$97cK59+E2"},
#        {"domain": "gta.cartzlink.com", "server": "s13", "password": "czxVYO,30y8{2w"},
#        {"domain": "fst.itserver.biz", "server": "FST", "password": "8}rZ`bB8?68"},
#        {"domain": "cam.itserver.biz", "server": "metro cam", "password": "dXT2316?.m_5"},
#        {"domain": "nb.newagedistributions.com", "server": "newage", "password": "GkD4e7o[0?>T"},
#        {"domain": "bmkenya.itserver.biz", "server": "bmkenya", "password": "7!WrCiO1£>3T"},
#        {"domain": "scentnsecret.itserver.biz", "server": "scentnsecret", "password": "x%11<Zc8;J^!"},
#        {"domain": "crm.cartzlink.com", "server": "s15", "password": "£8~pYxF~i40&"},
#        {"domain": "crm.tabrospharma.com", "server": "TP", "password": "3M8Fg&Sn,18>"},

#        {"domain": "crm.cqsignal.com ", "server": "cqsignal", "password": "1"},        
#        {"domain": "aone.cartzlink.com", "server": "s", "password": "d87-2w1Qh:9d"},
#        {"domain": "gtalhr.cartzlink.com", "server": "s12", "password": ",#>7r5Q5Q%&S"},

    ]

    for entry in domains:
        print(f"\n{'='*60}")
        print(f"STARTING DOMAIN: {entry['domain']} (Server: {entry['server']})")
        print(f"{'='*60}")
        
        result, timing_data = run_behave_on_domain(entry["domain"], entry["server"], entry["password"], features_dir, timing_dir)
        print(result)
        all_timing.update(timing_data)
        
        # Store timing data for 7-day tracking
        if timing_data:
            timing_tracker.add_timing_data(entry["domain"], timing_data)
        
        print(f"\n{'='*60}")
        print(f"COMPLETED DOMAIN: {entry['domain']}")
        print(f"{'='*60}")
        
        # Small delay between domains to ensure clean separation
        import time
        time.sleep(2)

    summary_text = print_final_summary(all_timing, timing_tracker)
    send_test_summary_email(summary_text)

if __name__ == "__main__":
    main()





