# Domain-Wise Browser Behavior

This implementation ensures that each domain runs in its own dedicated browser instance, providing complete isolation between domains and preventing any state interference.

## 🎯 **Behavior Overview**

### **For Each Domain:**
1. **Open Fresh Browser** → Run all features → **Close Browser** → Move to next domain
2. **No Session Reuse** between domains
3. **Complete Isolation** - each domain starts with a clean state
4. **Automatic Cleanup** - browser is properly closed after each domain

## 🔧 **Implementation Details**

### **1. Browser Lifecycle Management**

#### **Before Each Domain (`before_all`):**
```python
# Ensure we start with a clean state - no existing driver
if hasattr(context, 'driver') and context.driver:
    print(f"[INFO] Closing existing browser for domain: {context.domain}")
    context.driver.quit()
    context.driver = None

print(f"[INFO] Starting fresh browser instance for domain: {context.domain}")
```

#### **During Feature Execution (`before_feature`):**
```python
# Always perform fresh login for each domain (no session reuse)
print(f"[INFO] Performing fresh login for domain: {domain}")
if not perform_login(context):
    # Handle login failure
```

#### **After Each Domain (`after_all`):**
```python
# Cleanup after all tests for this domain
if hasattr(context, 'driver') and context.driver:
    print(f"[INFO] Closing browser for domain: {context.domain}")
    try:
        context.driver.quit()
        print(f"[INFO] Browser closed successfully for domain: {context.domain}")
    except Exception as e:
        print(f"[WARN] Error closing browser for domain {context.domain}: {e}")
    finally:
        context.driver = None
```

### **2. Fresh Driver Creation (`perform_login`):**
```python
# Always create a fresh driver for each domain
if hasattr(context, 'driver') and context.driver:
    print(f"[INFO] Closing existing driver for fresh session...")
    context.driver.quit()
    context.driver = None

print(f"[INFO] Creating fresh browser instance for domain: {context.domain}")
```

### **3. Domain Separation in Main Loop:**
```python
for entry in domains:
    print(f"[INFO] Opening fresh browser instance for domain: {entry['domain']}")
    
    # Run all features for this domain
    result, timing_data = run_behave_on_domain(...)
    
    print(f"[INFO] Browser instance closed for domain: {entry['domain']}")
    
    # Wait before next domain
    print(f"[INFO] Waiting 3 seconds before next domain...")
    time.sleep(3)
```

## 📊 **Execution Flow**

### **Example Execution:**
```
============================================================
STARTING DOMAIN: anamta.primeerp.top (Server: s12)
============================================================
[INFO] Opening fresh browser instance for domain: anamta.primeerp.top
[INFO] Domain = anamta.primeerp.top
[INFO] Starting fresh browser instance for domain: anamta.primeerp.top
[INFO] Creating fresh browser instance for domain: anamta.primeerp.top
[INFO] Performing fresh login for domain: anamta.primeerp.top
[INFO] Starting test execution for domain: anamta.primeerp.top
[INFO] Completed test execution for domain: anamta.primeerp.top
[INFO] Closing browser for domain: anamta.primeerp.top
[INFO] Browser closed successfully for domain: anamta.primeerp.top
[INFO] Browser instance cleared for domain: anamta.primeerp.top

============================================================
COMPLETED DOMAIN: anamta.primeerp.top
[INFO] Browser instance closed for domain: anamta.primeerp.top
============================================================
[INFO] Waiting 3 seconds before next domain...

============================================================
STARTING DOMAIN: mhp.itserver.biz (Server: MHP)
============================================================
[INFO] Opening fresh browser instance for domain: mhp.itserver.biz
...
```

## ✅ **Benefits**

### **1. Complete Isolation**
- Each domain runs in its own browser instance
- No shared state between domains
- No session conflicts or interference

### **2. Clean State**
- Fresh login for each domain
- No cached data or cookies from previous domains
- Predictable behavior

### **3. Resource Management**
- Proper browser cleanup after each domain
- Memory leaks prevented
- System resources properly released

### **4. Error Isolation**
- Issues in one domain don't affect others
- Each domain can fail independently
- Better error tracking and debugging

### **5. Performance Monitoring**
- Accurate timing per domain
- No interference from previous test runs
- Clean performance metrics

## 🔍 **Verification**

### **Check Browser Behavior:**
```bash
# Run the test script to verify domain-wise browser behavior
python test_domain_browser.py
```

### **Monitor Browser Instances:**
- Each domain should show "Opening fresh browser instance"
- Each domain should show "Browser closed successfully"
- No browser instances should persist between domains

## 🛠️ **Troubleshooting**

### **Browser Not Closing:**
- Check `after_all` function execution
- Verify exception handling in cleanup
- Monitor for browser process leaks

### **Session Persistence:**
- Ensure `before_feature` always performs fresh login
- Check that no session reuse logic remains
- Verify driver is properly nullified

### **Performance Issues:**
- Adjust sleep time between domains (currently 3 seconds)
- Monitor system resources during execution
- Check for memory leaks in browser processes

## 📈 **Expected Output**

### **Console Log:**
```
[INFO] Opening fresh browser instance for domain: domain1.com
[INFO] Domain = domain1.com
[INFO] Starting fresh browser instance for domain: domain1.com
[INFO] Creating fresh browser instance for domain: domain1.com
[INFO] Performing fresh login for domain: domain1.com
[INFO] Starting test execution for domain: domain1.com
[INFO] Completed test execution for domain: domain1.com
[INFO] Closing browser for domain: domain1.com
[INFO] Browser closed successfully for domain: domain1.com
[INFO] Browser instance cleared for domain: domain1.com
[INFO] Waiting 3 seconds before next domain...
```

This implementation ensures that your test suite runs each domain in complete isolation with fresh browser instances, providing reliable and predictable test execution. 