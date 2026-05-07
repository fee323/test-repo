#!/usr/bin/env python3
"""
Test script to verify timeout fixes for problematic domains
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'features'))

from environment import is_problematic_domain, get_domain_specific_timeouts, create_driver_with_retry

def test_domain_detection():
    """Test if problematic domains are correctly identified"""
    print("Testing domain detection...")
    
    test_domains = [
        'scentnsecret.itserver.biz',
        'mt2.itserver.biz', 
        'mt.itserver.biz',
        'anamta.primeerp.top',  # Should be normal
        'cam.itserver.biz'      # Should be normal
    ]
    
    for domain in test_domains:
        is_problematic = is_problematic_domain(domain)
        print(f"  {domain}: {'PROBLEMATIC' if is_problematic else 'NORMAL'}")
    
    print()

def test_timeout_settings():
    """Test if timeout settings are correctly applied"""
    print("Testing timeout settings...")
    
    problematic_domain = 'scentnsecret.itserver.biz'
    normal_domain = 'anamta.primeerp.top'
    
    problematic_timeouts = get_domain_specific_timeouts(problematic_domain)
    normal_timeouts = get_domain_specific_timeouts(normal_domain)
    
    print(f"Problematic domain ({problematic_domain}) timeouts:")
    for key, value in problematic_timeouts.items():
        print(f"  {key}: {value}")
    
    print(f"\nNormal domain ({normal_domain}) timeouts:")
    for key, value in normal_timeouts.items():
        print(f"  {key}: {value}")
    
    print()

def test_driver_creation():
    """Test driver creation with retry logic"""
    print("Testing driver creation...")
    
    # Test with problematic domain
    print("Testing driver creation for problematic domain...")
    try:
        driver = create_driver_with_retry(domain='scentnsecret.itserver.biz')
        if driver:
            print("  ✓ Driver created successfully")
            driver.quit()
        else:
            print("  ✗ Driver creation failed")
    except Exception as e:
        print(f"  ✗ Driver creation error: {e}")
    
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING TIMEOUT FIXES")
    print("=" * 60)
    
    test_domain_detection()
    test_timeout_settings()
    test_driver_creation()
    
    print("=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
