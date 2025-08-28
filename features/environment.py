from selenium.webdriver import Chrome, ChromeOptions
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

timing_summary = {}
errors_summary = []

def wait_for_element_with_auto_refresh(driver, by, value, timeout=10, refresh_timeout=10):
    """
    Wait for an element with auto-refresh on slow page loads
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        print(f"[WARN] Page load taking longer than {timeout}s, refreshing...")
        driver.refresh()
        time.sleep(2)  # Wait for refresh to complete
        element = WebDriverWait(driver, refresh_timeout).until(
            EC.presence_of_element_located((by, value))
        )
        print(f"[PASS] Element found after refresh: {value}")
        return element

def navigate_to_page_with_retry(driver, url, expected_element_id='title', timeout=10):
    """
    Navigate to a page with auto-refresh retry logic
    """
    try:
        driver.get(url)
        print(f"[PASS] Navigated to: {url}")
        # Wait for page to load with auto-refresh
        wait_for_element_with_auto_refresh(driver, By.ID, expected_element_id, timeout)
        return True
    except Exception as e:
        print(f"[FAIL] Navigation failed: {e}")
        return False

def perform_login(context):
    """
    Perform login for the current domain with proper error handling
    """
    # Always create a fresh driver for each domain
    if hasattr(context, 'driver') and context.driver:
        try:
            print(f"[INFO] Closing existing driver for fresh session...")
            context.driver.quit()
        except:
            pass
        context.driver = None
    
    print(f"[INFO] Creating fresh browser instance for domain: {context.domain}")
    domain = context.domain
    password = context.password
    
    if not password:
        context.login_failed = True
        raise ValueError("[FAIL] Password not provided. Use -D password=yourpass")
    
    # Create new driver
    options = ChromeOptions()
    driver = Chrome(options=options)
    driver.implicitly_wait(8)
    driver.maximize_window()
    
    # Page Load Timing
    t1 = time.time()
    login_url = f'https://{domain}/admin/?r=user/user/login&_lang=en'
    
    try:
        driver.get(login_url)
        print(f"[PASS] Opened URL: {login_url}")
    except WebDriverException as e:
        msg = f"[FAIL] Page Load Failed: {e}"
        print(msg)
        driver.quit()
        context.page_load_failed = True
        context.login_failed = True
        return False
    
    t2 = time.time()
    page_load_time = _round_time(t2 - t1)
    
    # Login Timing
    t3 = time.time()
    try:
        if driver.find_elements(By.ID, 'title'):
            print("[PASS] Already logged in")
        elif driver.find_elements(By.ID, 'YumUserLogin_username'):
            driver.find_element(By.ID, 'YumUserLogin_username').send_keys('tester')
            driver.find_element(By.ID, 'YumUserLogin_password').send_keys(password)
            driver.find_element(By.ID, 'wp-submit').click()
            
            # Wait for login success - look for dashboard elements instead of login wrapper
            try:
                # Wait for either dashboard title or any common dashboard element
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, 'title')),
                        EC.presence_of_element_located((By.CLASS_NAME, 'dashboard')),
                        EC.presence_of_element_located((By.CLASS_NAME, 'main-content')),
                        EC.presence_of_element_located((By.TAG_NAME, 'body'))
                    )
                )
                print("[PASS] Login successful - dashboard loaded")
            except TimeoutException:
                # If timeout, just check if we're not on login page anymore
                if not driver.find_elements(By.ID, 'YumUserLogin_username'):
                    print("[PASS] Login successful - no longer on login page")
                else:
                    raise Exception("Login failed - still on login page after timeout")
        else:
            raise Exception("Login page not found.")
    except Exception as e:
        msg = f"[FAIL] Login Failed: {e}"
        print(msg)
        driver.quit()
        context.login_failed = True
        return False
    
    t4 = time.time()
    login_time = _round_time(t4 - t3)
    
    # Store timing data at domain level
    if domain not in timing_summary:
        timing_summary[domain] = {
            "Server": context.config.userdata.get("server", "Unknown"),
            "Page Load": page_load_time,
            "Login": login_time,
            "Features": {}
        }
    else:
        # Update existing domain timing
        timing_summary[domain]["Page Load"] = page_load_time
        timing_summary[domain]["Login"] = login_time
    
    # Store driver in context
    context.driver = driver
    
    print(f"[INFO] Login completed. Page Load: {page_load_time}s, Login: {login_time}s")
    return True

def before_all(context):
    """Initialize domain, open browser, and perform login ONCE per domain."""
    import sys
    from timing_tracker import TimingTracker
    context.domain = context.config.userdata.get("domain")
    context.password = context.config.userdata.get("password")
    context.timing_tracker = TimingTracker()
    print(f"[INFO] Domain = {context.domain}")
    if not context.domain:
        raise ValueError("[FAIL] Domain not provided. Use -D domain=yourdomain.com")
    if not context.password:
        raise ValueError("[FAIL] Password not provided. Use -D password=yourpass")
    # Ensure no existing driver
    if hasattr(context, 'driver') and context.driver:
        try:
            print(f"[INFO] Closing existing browser for domain: {context.domain}")
            context.driver.quit()
        except:
            pass
        context.driver = None
    # Open browser and login ONCE
    print(f"[INFO] Starting browser and logging in for domain: {context.domain}")
    context.page_load_failed = False
    context.login_failed = False
    if not perform_login(context):
        print(f"[FAIL] Login failed for domain {context.domain}. Aborting all features.")
        context.page_load_failed = True
        context.login_failed = True
        # Abort all features by raising exception
        sys.exit(1)
    print(f"[INFO] Login successful for domain: {context.domain}")

# --- Timing Helpers ---
def _round_time(val):
    return round(val, 1) if isinstance(val, (int, float)) else val

def record_feature_duration(context, domain, feature_name, start_time):
    """Calculate and store feature duration, rounded, and return it."""
    t_end = time.time()
    duration = _round_time(t_end - start_time)
    timing_summary[domain]["Features"][feature_name]["Feature"] = duration
    return duration

def record_scenario_timing(context, domain, feature_name, scenario, start_time, status):
    duration = _round_time(time.time() - start_time)
    timing_summary[domain]["Features"][feature_name]["Scenario Timings"].append({
        "name": scenario.name,
        "duration": duration,
        "status": status,
        "failed_steps": context.failed_steps[:]
    })
    context.failed_steps = []

def before_feature(context, feature):
    """Setup for each feature - just set up timing and feature context."""
    context.feature_start = time.time()
    domain = context.domain
    feature_name = feature.name
    print(f"[INFO] Starting feature: {feature_name}")
    # Initialize domain structure if not exists
    if domain not in timing_summary:
        timing_summary[domain] = {
            "Server": context.config.userdata.get("server", "Unknown"),
            "Page Load": None,
            "Login": None,
            "Features": {}
        }
    # Initialize feature timing structure
    timing_summary[domain]["Features"][feature_name] = {
        "Feature": None,
        "Scenario Timings": [],
        "Failed Steps": []
    }
    context.current_feature_name = feature_name
    # Do NOT perform login here anymore

def before_scenario(context, scenario):
    """Setup for each scenario"""
    context.scenario_start = time.time()
    context.failed_steps = []

def after_scenario(context, scenario):
    """Record scenario timing"""
    domain = context.domain
    feature_name = getattr(context, "current_feature_name", None)
    # Check if page load or login failed
    if getattr(context, "page_load_failed", False) or getattr(context, "login_failed", False):
        status = "failed"
    else:
        status = "passed" if scenario.status.name == "passed" else "failed"
    record_scenario_timing(context, domain, feature_name, scenario, context.scenario_start, status)

def after_step(context, step):
    """Record failed steps"""
    if step.status.name == "failed":
        domain = context.domain
        feature_name = getattr(context, "current_feature_name", None)
        duration = round(step.duration, 2)
        fail_detail = {
            "Step": step.name,
            "Error": str(step.exception),
            "Duration": duration
        }
        context.failed_steps.append(fail_detail)

def after_feature(context, feature):
    """Record feature timing and write to file"""
    domain = context.domain
    feature_name = getattr(context, "current_feature_name", None)
    print(f"[INFO] Completed feature: {feature_name}")
    print("DEBUG: context.domain =", getattr(context, "domain", None))
    print("DEBUG: timing_summary =", timing_summary)
    # Check if page load or login failed
    if getattr(context, "page_load_failed", False) or getattr(context, "login_failed", False):
        timing_summary[domain]["Features"][feature_name]["Feature"] = "Failed"
        # Mark all scenarios as failed
        for scenario in timing_summary[domain]["Features"][feature_name]["Scenario Timings"]:
            scenario["status"] = "failed"
        # If no scenarios were executed, add a dummy failed scenario
        if not timing_summary[domain]["Features"][feature_name]["Scenario Timings"]:
            timing_summary[domain]["Features"][feature_name]["Scenario Timings"].append({
                "name": "No scenario executed (page load or login failed)",
                "duration": 0,
                "status": "failed",
                "failed_steps": []
            })
    else:
        # Use helper to calculate and store feature duration
        duration = record_feature_duration(context, domain, feature_name, context.feature_start)
        print(f"PASS Feature: {feature_name} ({duration}s)")
    # Write timing summary to file
    output_dir = os.environ.get("BEHAVE_TIMING_DIR", ".")
    timing_file_path = os.path.join(output_dir, f"{domain}_timing.json")
    print(f"[DEBUG] Writing timing summary for {domain} to {timing_file_path}")
    os.makedirs(output_dir, exist_ok=True)
    with open(timing_file_path, "w", encoding="utf-8") as f:
        json.dump({domain: timing_summary[domain]}, f)

def after_all(context):
    """Cleanup after all tests for this domain. Close browser and print/save timing summary."""
    if hasattr(context, 'driver') and context.driver:
        print(f"[INFO] Closing browser for domain: {context.domain}")
        try:
            context.driver.quit()
            print(f"[INFO] Browser closed successfully for domain: {context.domain}")
        except Exception as e:
            print(f"[WARN] Error closing browser for domain {context.domain}: {e}")
        finally:
            context.driver = None
            print(f"[INFO] Browser instance cleared for domain: {context.domain}")
    else:
        print(f"[INFO] No browser instance to close for domain: {context.domain}")
    # Save timing summary using TimingTracker
    domain = getattr(context, 'domain', None)
    if domain and domain in timing_summary:
        context.timing_tracker.add_timing_data(domain, timing_summary[domain])
        summary = context.timing_tracker.format_timing_summary(domain, timing_summary[domain])
        print(f"[SUMMARY] Timing for {domain}:\n{json.dumps(summary, indent=2)}")
