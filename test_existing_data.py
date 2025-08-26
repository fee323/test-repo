#!/usr/bin/env python3
"""
Test script to verify that the timing tracker can handle existing mixed data structures
"""

import json
import os
from timing_tracker import TimingTracker

def test_existing_data():
    """Test the timing tracker with existing data structures"""
    
    print("=== Testing Timing Tracker with Existing Data ===")
    
    # Initialize timing tracker
    timing_tracker = TimingTracker()
    
    # Test with a domain that has mixed data structures
    test_domain = "crm.tabrospharma.com"
    
    print(f"\nTesting domain: {test_domain}")
    
    # Check if we have data for this domain
    today = timing_tracker.get_today_key()
    if today in timing_tracker.history and test_domain in timing_tracker.history[today]:
        domain_data = timing_tracker.history[today][test_domain]
        print(f"Found data for {test_domain} on {today}")
        
        # Test each metric
        metrics = ["page_load", "login", "feature", "scenario"]
        
        for metric in metrics:
            try:
                value = timing_tracker.get_metric_value(domain_data, metric)
                print(f"  {metric}: {value}")
                
                # Test 7-day calculations
                values = timing_tracker.get_7_day_values(test_domain, metric)
                average = timing_tracker.get_7_day_average(test_domain, metric)
                summary = timing_tracker.get_7_day_summary(test_domain, metric)
                
                print(f"    7-day values: {values}")
                print(f"    7-day average: {average}")
                print(f"    7-day summary: {summary}")
                
            except Exception as e:
                print(f"  {metric}: ERROR - {e}")
        
        # Test the full timing summary
        print(f"\nTesting full timing summary...")
        try:
            summary = timing_tracker.format_timing_summary(test_domain, domain_data)
            print(f"Summary generated successfully:")
            print(json.dumps(summary, indent=2))
        except Exception as e:
            print(f"Error generating summary: {e}")
    
    else:
        print(f"No data found for {test_domain} on {today}")
        print("Available dates:")
        for date_key in sorted(timing_tracker.history.keys()):
            domains = list(timing_tracker.history[date_key].keys())
            print(f"  {date_key}: {', '.join(domains[:3])}{'...' if len(domains) > 3 else ''}")
    
    print(f"\n=== Test Complete ===")

if __name__ == "__main__":
    test_existing_data()
