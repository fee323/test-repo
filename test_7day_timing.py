#!/usr/bin/env python3
"""
Test script to verify 7-day timing functionality
"""

import json
import os
from datetime import datetime, timedelta
from timing_tracker import TimingTracker

def test_7day_timing():
    """Test the 7-day timing functionality"""
    
    print("=== Testing 7-Day Timing Functionality ===")
    
    # Initialize timing tracker
    timing_tracker = TimingTracker()
    
    # Test data for the last 7 days
    test_domains = ["test.domain.com", "another.domain.com"]
    test_metrics = ["page_load", "login", "feature", "scenario"]
    
    # Generate test data for the last 7 days
    today = datetime.now()
    for i in range(7):
        date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        
        for domain in test_domains:
            # Create test timing data
            test_data = {
                "Server": f"test-server-{i}",
                "Page Load": 2.0 + (i * 0.1),  # Varying page load times
                "Login": 15.0 + (i * 0.5),      # Varying login times
                "Features": {
                    "Test Feature": {
                        "Feature": 50.0 + (i * 2.0),  # Varying feature times
                        "Scenario Timings": [
                            {
                                "name": f"Test Scenario {i}",
                                "duration": 10.0 + (i * 1.0),
                                "status": "passed",
                                "failed_steps": []
                            }
                        ],
                        "Failed Steps": []
                    }
                }
            }
            
            # Add to timing tracker
            timing_tracker.add_timing_data(domain, {domain: test_data})
            print(f"Added test data for {domain} on {date_key}")
    
    print(f"\n--- Testing 7-Day Calculations ---")
    
    # Test each domain and metric
    for domain in test_domains:
        print(f"\nDomain: {domain}")
        
        for metric in test_metrics:
            # Get 7-day values
            values = timing_tracker.get_7_day_values(domain, metric)
            average = timing_tracker.get_7_day_average(domain, metric)
            summary = timing_tracker.get_7_day_summary(domain, metric)
            
            print(f"  {metric.upper()}:")
            print(f"    Values: {values}")
            print(f"    Average: {average:.2f}")
            print(f"    Count: {summary['count']}/{summary['total_days']}")
            print(f"    Min: {summary['min']:.2f}, Max: {summary['max']:.2f}")
    
    print(f"\n--- Testing Timing Summary Format ---")
    
    # Test the full timing summary
    test_current_data = {
        "Server": "current-server",
        "Page Load": 3.5,
        "Login": 18.0,
        "Features": {
            "Current Feature": {
                "Feature": 55.0,
                "Scenario Timings": [
                    {
                        "name": "Current Scenario",
                        "duration": 12.0,
                        "status": "passed",
                        "failed_steps": []
                    }
                ],
                "Failed Steps": []
            }
        }
    }
    
    summary = timing_tracker.format_timing_summary(test_domains[0], test_current_data)
    
    print(f"Timing Summary for {test_domains[0]}:")
    print(json.dumps(summary, indent=2))
    
    # Test cleanup functionality
    print(f"\n--- Testing Data Cleanup ---")
    print(f"Before cleanup: {len(timing_tracker.history)} date entries")
    timing_tracker.cleanup_old_data()
    print(f"After cleanup: {len(timing_tracker.history)} date entries")
    
    print(f"\n=== Test Complete ===")
    print(f"Timing data saved to: {timing_tracker.history_file}")
    
    # Show final data structure
    if os.path.exists(timing_tracker.history_file):
        with open(timing_tracker.history_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        
        print(f"\nFinal data structure:")
        for date_key in sorted(final_data.keys()):
            domains = list(final_data[date_key].keys())
            print(f"  {date_key}: {len(domains)} domains")

if __name__ == "__main__":
    test_7day_timing()
