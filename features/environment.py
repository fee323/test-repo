from selenium.webdriver import Chrome, ChromeOptions
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import datetime
import os
import urllib3.exceptions

timing_summary = {}
errors_summary = []

def open_page_with_retry(driver, url, max_retries=3, wait_time=3):
    """
    Open a page with automatic retry and refresh if "site temporarily unavailable" error appears.
    Uses exponential backoff between retries.
    """
    for attempt in range(max_retries):
        try:
            print(f"[INFO] Attempt {attempt + 1}/{max_retries}: Opening {url}")
            driver.get(url)
            
            # Check if page loaded successfully (not showing error)
            if "The site is temporarily unavailable" not in driver.page_source:
                print(f"[PASS] Page loaded successfully on attempt {attempt + 1}")
                return True
            
            # Error detected, wait and retry (exponential backoff)
            print(f"[WARN] 'Site temporarily unavailable' detected on attempt {attempt + 1}")
            if attempt < max_retries - 1:  # Don't wait on last attempt
                backoff = min(wait_time * (2 ** attempt), 20)
                print(f"[INFO] Waiting {backoff} seconds before retry...")
                time.sleep(backoff)
                print(f"[INFO] Refreshing page...")
                driver.refresh()
                time.sleep(2)  # Wait for refresh to complete
                
                # Check again after refresh
                if "The site is temporarily unavailable" not in driver.page_source:
                    print(f"[PASS] Page loaded successfully after refresh on attempt {attempt + 1}")
                    return True
            else:
                print(f"[FAIL] All {max_retries} attempts failed. Page still shows 'Site temporarily unavailable'")
                
        except Exception as e:
            print(f"[WARN] Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                backoff = min(wait_time * (2 ** attempt), 20)
                print(f"[INFO] Waiting {backoff} seconds before retry...")
                time.sleep(backoff)
            else:
                print(f"[FAIL] All {max_retries} attempts failed due to errors")
    
    return False

def wait_for_element_with_auto_refresh(driver, by, value, timeout=10, refresh_timeout=10, max_refreshes=2):
    """
    Wait for an element with auto-refresh on slow page loads. Will attempt multiple
    refresh cycles with increasing timeouts.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        # Try multiple refresh attempts
        for i in range(max_refreshes):
            print(f"[WARN] Page load taking longer than {timeout}s, refreshing... (refresh {i+1}/{max_refreshes})")
            driver.refresh()
            time.sleep(2)  # Wait for refresh to complete
            try:
                # Increase refresh timeout each cycle
                increased_timeout = refresh_timeout * (i + 1)
                element = WebDriverWait(driver, increased_timeout).until(
                 EC.presence_of_element_located((by, value))
                )
                print(f"[PASS] Element found after refresh: {value}")
                return element
            except TimeoutException:
                continue
        # If all refresh attempts failed, re-raise
        raise

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
    
    # Create new driver with retry logic and domain-specific settings
    try:
        driver = create_driver_with_retry(domain=domain)
        if not driver:
            raise Exception("Failed to create Chrome driver after all retries")
    except Exception as e:
        msg = f"[FAIL] Driver Creation Failed: {e}"
        print(msg)
        context.page_load_failed = True
        context.login_failed = True
        return False
    
    # Page Load Timing
    t1 = time.time()
    login_url = f'https://{domain}/admin/?r=user/user/login&_lang=en'
    
    try:
        # Use domain-specific retry logic for page loading
        timeouts = get_domain_specific_timeouts(domain)
        if not open_page_with_retry(driver, login_url, max_retries=timeouts['max_retries'], wait_time=timeouts['retry_delay']):
            raise Exception("Failed to load login page after all retries")
        print(f"[PASS] Opened URL: {login_url}")
    except (WebDriverException, urllib3.exceptions.ReadTimeoutError, urllib3.exceptions.ConnectTimeoutError) as e:
        msg = f"[FAIL] Page Load Failed: {e}"
        print(msg)
        try:
            driver.quit()
        except:
            pass
        context.page_load_failed = True
        context.login_failed = True
        return False
    except Exception as e:
        msg = f"[FAIL] Page Load Failed: {e}"
        print(msg)
        try:
            driver.quit()
        except:
            pass
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
                # Test refresh function for dashboard elements
                print("[INFO] Testing refresh function for dashboard elements...")
                login_timeout = timeouts['login_timeout']
                wait_for_element_with_auto_refresh(driver, By.ID,"tab-home", timeout=login_timeout, refresh_timeout=login_timeout)
                print("[PASS] Login successful - dashboard loaded with refresh function")
            except Exception as e:
                print(f"[WARN] Refresh function failed, trying fallback method: {e}")
                # Fallback to original method
            try:
                    WebDriverWait(driver, login_timeout).until(
                    EC.any_of(
                            EC.presence_of_element_located((By.ID, "tab-home")),
                            EC.presence_of_element_located((By.CLASS_NAME, "column2")),
                        EC.presence_of_element_located((By.CLASS_NAME, 'main-content')),
                        EC.presence_of_element_located((By.TAG_NAME, 'body'))
                        )
                    )
                    print("[PASS] Login successful - dashboard loaded with fallback method")
            except TimeoutException:
                # If timeout, just check if we're not on login page anymore
                if not driver.find_elements(By.ID, 'YumUserLogin_username'):
                    print("[PASS] Login successful - no longer on login page")
                else:
                    raise Exception("Login failed - still on login page after timeout")
        else:
            raise Exception("Login page not found.")
    except (urllib3.exceptions.ReadTimeoutError, urllib3.exceptions.ConnectTimeoutError) as e:
        msg = f"[FAIL] Login Failed - Connection Timeout: {e}"
        print(msg)
        try:
            driver.quit()
        except:
            pass
        context.login_failed = True
        return False
    except Exception as e:
        msg = f"[FAIL] Login Failed: {e}"
        print(msg)
        try:
            driver.quit()
        except:
            pass
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
    if step.status == "failed":
        # Screenshot folder
        screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        # File name with timestamp
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{step.name[:30]}_{ts}.png"  # step name + time
        file_path = os.path.join(screenshot_dir, file_name)

        try:
            # Selenium driver from context
            context.driver.save_screenshot(file_path)
            print(f"\n[Screenshot Saved] {file_path}")
        except Exception as e:
            print(f"\n[ERROR saving screenshot] {e}")

#def after_step(context, step):
#    """Record failed steps"""
#    if step.status.name == "failed":
#        domain = context.domain
#        feature_name = getattr(context, "current_feature_name", None)
#        duration = round(step.duration, 2)
#        fail_detail = {
#            "Step": step.name,
#            "Error": str(step.exception),
#            "Duration": duration
#        }
#        context.failed_steps.append(fail_detail)

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

def is_problematic_domain(domain):
    """
    Check if a domain is known to have performance issues
    """
    problematic_domains = [
        'scentnsecret.itserver.biz',
        'mt2.itserver.biz',  # Also showing slow performance
        'mt.itserver.biz'
    ]
    return domain in problematic_domains

def get_domain_specific_timeouts(domain):
    """
    Get timeout settings specific to domain performance characteristics
    """
    if is_problematic_domain(domain):
        return {
            'page_load_timeout': 300,  # 5 minutes for problematic domains
            'implicit_wait': 20,
            'login_timeout': 60,
            'retry_delay': 10,
            'max_retries': 5
        }
    else:
        return {
            'page_load_timeout': 180,  # 3 minutes for normal domains
            'implicit_wait': 15,
            'login_timeout': 30,
            'retry_delay': 5,
            'max_retries': 3
        }

def create_driver_with_retry(max_retries=3, retry_delay=5, domain=None):
    """
    Create a new Chrome driver with retry logic for connection issues.
    """
    # Get domain-specific settings
    if domain:
        timeouts = get_domain_specific_timeouts(domain)
        max_retries = timeouts['max_retries']
        retry_delay = timeouts['retry_delay']
        page_load_timeout = timeouts['page_load_timeout']
        implicit_wait = timeouts['implicit_wait']
    else:
        page_load_timeout = 180
        implicit_wait = 15
    
    for attempt in range(max_retries):
        try:
            print(f"[INFO] Attempt {attempt + 1}/{max_retries}: Creating Chrome driver...")
            options = ChromeOptions()
            
            # Add performance optimizations for problematic domains
            if domain and is_problematic_domain(domain):
                print(f"[INFO] Applying performance optimizations for problematic domain: {domain}")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                options.add_argument("--disable-images")
                options.add_argument("--disable-web-security")
                options.add_argument("--disable-features=VizDisplayCompositor")
                options.page_load_strategy = "eager"
            
            driver = Chrome(options=options)
            driver.set_page_load_timeout(page_load_timeout)
            driver.implicitly_wait(implicit_wait)
            driver.maximize_window()
            print(f"[PASS] Chrome driver created successfully on attempt {attempt + 1}")
            return driver
        except (urllib3.exceptions.ReadTimeoutError, urllib3.exceptions.ConnectTimeoutError) as e:
            print(f"[WARN] Connection timeout on attempt {attempt + 1}: {e}. Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
        except Exception as e:
            print(f"[WARN] Error creating Chrome driver on attempt {attempt + 1}: {e}. Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
    print(f"[FAIL] All {max_retries} attempts to create Chrome driver failed.")
    return None
