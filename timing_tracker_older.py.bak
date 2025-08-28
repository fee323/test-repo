import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TimingTracker:
    def __init__(self, data_dir: str = "timing_history"):
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "timing_history.json")
        self.ensure_data_dir()
        self.history = self.load_history()
    
    def ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_history(self) -> Dict:
        """Load timing history from JSON file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_history(self):
        """Save timing history to JSON file"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def get_today_key(self) -> str:
        """Get today's date as string key"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def add_timing_data(self, domain: str, timing_data: Dict):
        """Add today's timing data for a domain"""
        today = self.get_today_key()
        
        if today not in self.history:
            self.history[today] = {}
        
        # Extract the actual timing data from the nested structure
        # The timing_data comes in format: {"domain": {"Server": ..., "Page Load": ..., ...}}
        if domain in timing_data:
            actual_data = timing_data[domain]
        else:
            actual_data = timing_data
        
        self.history[today][domain] = actual_data
        self.save_history()
    
    def get_metric_value(self, domain_data: Dict, metric: str, feature_name: str = None) -> Optional[float]:
        """Extract metric value from domain data"""
        if metric == "page_load":
            value = domain_data.get("Page Load")
            return value if isinstance(value, (int, float)) else None
        elif metric == "login":
            value = domain_data.get("Login")
            return value if isinstance(value, (int, float)) else None
        elif metric == "feature":
            # For features, return the specific feature's duration if feature_name is provided
            features = domain_data.get("Features", {})
            if feature_name and feature_name in features:
                value = features[feature_name].get("Feature")
                return value if isinstance(value, (int, float)) else None
            # Fallback: return average of all features (for backward compatibility)
            if features:
                feature_times = [f.get("Feature") for f in features.values() if isinstance(f.get("Feature"), (int, float))]
                if feature_times:
                    return sum(feature_times) / len(feature_times)
        elif metric == "scenario":
            # For scenarios, we'll use the average of all scenario times
            features = domain_data.get("Features", {})
            scenario_times = []
            for feature_data in features.values():
                # Ensure feature_data is a dictionary
                if not isinstance(feature_data, dict):
                    continue
                scenarios = feature_data.get("Scenario Timings", [])
                for scenario in scenarios:
                    # Ensure scenario is a dictionary
                    if isinstance(scenario, dict) and isinstance(scenario.get("duration"), (int, float)):
                        scenario_times.append(scenario["duration"])
            if scenario_times:
                return sum(scenario_times) / len(scenario_times)
        return None
    
    def get_7_day_values(self, domain: str, metric: str, feature_name: str = None) -> List[float]:
        """Get all available historical values for a metric (up to 7 days)"""
        today = datetime.now()
        values = []
        dates_with_data = []
        
        # Look for data in the last 7 days
        for i in range(7):
            date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date_key in self.history and domain in self.history[date_key]:
                value = self.get_metric_value(self.history[date_key][domain], metric, feature_name)
                if value is not None and isinstance(value, (int, float)):
                    values.append(value)
                    dates_with_data.append(date_key)
        
        # If we have less than 7 days of data, also check for any other available data
        if len(values) < 7:
            for date_key in sorted(self.history.keys(), reverse=True):
                if date_key not in dates_with_data and domain in self.history[date_key]:
                    value = self.get_metric_value(self.history[date_key][domain], metric, feature_name)
                    if value is not None and isinstance(value, (int, float)):
                        values.append(value)
                        dates_with_data.append(date_key)
                        if len(values) >= 7:  # Limit to 7 most recent values
                            break
        
        return values
    
    def get_7_day_average(self, domain: str, metric: str, feature_name: str = None) -> Optional[float]:
        """Calculate average for all available historical data (up to 7 days)"""
        values = self.get_7_day_values(domain, metric, feature_name)
        if values:
            return sum(values) / len(values)
        return None
    
    def cleanup_old_data(self):
        """Remove data older than 7 days"""
        today = datetime.now()
        keys_to_remove = []
        
        for date_key in self.history.keys():
            try:
                date_obj = datetime.strptime(date_key, "%Y-%m-%d")
                if (today - date_obj).days > 7:
                    keys_to_remove.append(date_key)
            except ValueError:
                # Invalid date format, remove it
                keys_to_remove.append(date_key)
        
        for key in keys_to_remove:
            del self.history[key]
        
        if keys_to_remove:
            self.save_history()
    
    def format_timing_summary(self, domain: str, current_data: Dict) -> Dict:
        """Format timing summary with 7-day averages"""
        try:
            summary = {}
            
            # Page Load
            current_page_load = current_data.get("Page Load")
            if current_page_load is not None:
                page_load_avg = self.get_7_day_average(domain, "page_load")
                page_load_values = self.get_7_day_values(domain, "page_load")
                summary["page_load"] = {
                    "current": current_page_load,
                    "average": page_load_avg,
                    "values": page_load_values,
                    "is_high": page_load_avg and current_page_load > page_load_avg
                }
            
            # Login
            current_login = current_data.get("Login")
            if current_login is not None:
                login_avg = self.get_7_day_average(domain, "login")
                login_values = self.get_7_day_values(domain, "login")
                summary["login"] = {
                    "current": current_login,
                    "average": login_avg,
                    "values": login_values,
                    "is_high": login_avg and current_login > login_avg
                }
            
            # Features (track each feature separately)
            features = current_data.get("Features", {})
            if features:
                summary["features"] = {}
                for feature_name, feature_data in features.items():
                    current_feature_time = feature_data.get("Feature")
                    if isinstance(current_feature_time, (int, float)):
                        feature_avg = self.get_7_day_average(domain, "feature", feature_name)
                        feature_values = self.get_7_day_values(domain, "feature", feature_name)
                        summary["features"][feature_name] = {
                            "current": current_feature_time,
                            "average": feature_avg,
                            "values": feature_values,
                            "is_high": feature_avg and current_feature_time > feature_avg
                        }
            
            # Scenario (average of all scenarios)
            scenario_times = []
            for feature_data in features.values():
                scenarios = feature_data.get("Scenario Timings", [])
                for scenario in scenarios:
                    if isinstance(scenario.get("duration"), (int, float)):
                        scenario_times.append(scenario["duration"])
            
            if scenario_times:
                current_scenario_avg = sum(scenario_times) / len(scenario_times)
                scenario_avg = self.get_7_day_average(domain, "scenario")
                scenario_values = self.get_7_day_values(domain, "scenario")
                summary["scenario"] = {
                    "current": current_scenario_avg,
                    "average": scenario_avg,
                    "values": scenario_values,
                    "is_high": scenario_avg and current_scenario_avg > scenario_avg
                }
            
            return summary
        except Exception as e:
            print(f"[ERROR] Error in format_timing_summary for domain '{domain}': {e}")
            # Return minimal summary to prevent crash
            return {
                "error": f"Failed to format timing summary: {e}",
                "domain": domain
            } 