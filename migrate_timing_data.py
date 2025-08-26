#!/usr/bin/env python3
"""
Data migration script to consolidate timing data from multiple locations
into the main timing_history directory for proper 7-day tracking.
"""

import json
import os
import shutil
from datetime import datetime
from timing_tracker import TimingTracker

def migrate_timing_data():
    """Migrate timing data from multiple locations to main timing_history"""
    
    print("=== Timing Data Migration Script ===")
    
    # Initialize timing tracker
    timing_tracker = TimingTracker()
    
    # Source directories to migrate from
    source_dirs = [
        "timing_results",
        "timing_history",  # The old timing_history directory
        "."  # Root directory for timing_history.json
    ]
    
    migrated_count = 0
    
    for source_dir in source_dirs:
        print(f"\n--- Processing {source_dir} ---")
        
        if source_dir == ".":
            # Check for timing_history.json in root
            root_file = "timing_history.json"
            if os.path.exists(root_file):
                try:
                    with open(root_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    print(f"Found root {root_file} with {len(data)} date entries")
                    
                    # Migrate each date entry
                    for date_key, domains_data in data.items():
                        for domain, domain_data in domains_data.items():
                            print(f"  Migrating {domain} from {date_key}")
                            timing_tracker.add_timing_data(domain, {domain: domain_data})
                            migrated_count += 1
                    
                    # Backup and remove the root file
                    backup_file = f"{root_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(root_file, backup_file)
                    print(f"  Backed up to {backup_file}")
                    
                except Exception as e:
                    print(f"  Error processing {root_file}: {e}")
        
        elif source_dir == "timing_results":
            # Process individual domain timing files
            if os.path.exists(source_dir):
                for filename in os.listdir(source_dir):
                    if filename.endswith("_timing.json"):
                        file_path = os.path.join(source_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            # Extract domain name from filename
                            domain = filename.replace("_timing.json", "")
                            print(f"  Migrating {domain} from {filename}")
                            
                            # Add to timing tracker
                            timing_tracker.add_timing_data(domain, data)
                            migrated_count += 1
                            
                            # Backup the file
                            backup_file = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            shutil.move(file_path, backup_file)
                            print(f"    Backed up to {backup_file}")
                            
                        except Exception as e:
                            print(f"    Error processing {filename}: {e}")
        
        elif source_dir == "timing_history":
            # Process the old timing_history directory
            if os.path.exists(source_dir):
                history_file = os.path.join(source_dir, "timing_history.json")
                if os.path.exists(history_file):
                    try:
                        with open(history_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        print(f"Found {history_file} with {len(data)} date entries")
                        
                        # Migrate each date entry
                        for date_key, domains_data in data.items():
                            for domain, domain_data in domains_data.items():
                                print(f"  Migrating {domain} from {date_key}")
                                timing_tracker.add_timing_data(domain, {domain: domain_data})
                                migrated_count += 1
                        
                        # Backup the old file
                        backup_file = f"{history_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.move(history_file, backup_file)
                        print(f"  Backed up to {backup_file}")
                        
                    except Exception as e:
                        print(f"  Error processing {history_file}: {e}")
    
    print(f"\n=== Migration Complete ===")
    print(f"Total entries migrated: {migrated_count}")
    
    # Show final data structure
    print(f"\nFinal timing history structure:")
    print(f"Main file: {timing_tracker.history_file}")
    
    if os.path.exists(timing_tracker.history_file):
        with open(timing_tracker.history_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        
        print(f"Total dates: {len(final_data)}")
        for date_key in sorted(final_data.keys()):
            domains = list(final_data[date_key].keys())
            print(f"  {date_key}: {len(domains)} domains - {', '.join(domains[:3])}{'...' if len(domains) > 3 else ''}")
    
    # Clean up old data
    print(f"\nCleaning up data older than 7 days...")
    timing_tracker.cleanup_old_data()
    
    print(f"\nMigration script completed successfully!")
    print(f"All timing data is now consolidated in: {timing_tracker.history_file}")

if __name__ == "__main__":
    migrate_timing_data()
