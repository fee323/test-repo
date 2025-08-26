# 7-Day Average Tracking System

This enhancement adds comprehensive 7-day average tracking to your Behave test summary, providing historical performance insights for page load, login, feature, and scenario timings.

## Features

### 📊 7-Day Average Tracking
- **Page Load Times**: Tracks daily page load performance
- **Login Times**: Monitors login performance trends
- **Feature Times**: Averages all feature execution times
- **Scenario Times**: Averages all scenario execution times

### 📈 Performance Indicators
- **Historical Data**: Shows last 7 days of timing data
- **Average Calculation**: Computes rolling 7-day averages
- **Performance Alerts**: Highlights when today's time exceeds 7-day average
- **Visual Indicators**: Uses color coding for high times

### 🗂️ Data Management
- **Automatic Cleanup**: Removes data older than 7 days
- **JSON Storage**: Maintains data in `timing_history/timing_history.json`
- **Daily Tracking**: Stores one entry per domain per day

## How It Works

### 1. Data Collection
- Each test run stores timing data for the current day
- Data is organized by domain and date
- Automatic cleanup removes old data

### 2. Average Calculation
- Calculates 7-day rolling averages for each metric
- Handles missing days gracefully
- Provides both individual values and averages

### 3. Performance Monitoring
- Compares today's times against 7-day averages
- Highlights performance degradation
- Shows trend information

## Output Format

### Console Output
```
[PASS] Page Load (2.63s)  Above 7-Day Avg
Times (Last 7 Days): 2.1, 2.3, 2.0, 2.2, 2.1, 2.4, 2.6
7-Day Avg: 2.2
Today: 2.6  Above 7-Day Avg
```

### Email Output
- HTML formatted with color coding
- Orange highlighting for high times
- Detailed 7-day history in collapsible sections

## File Structure

```
timing_history/
└── timing_history.json    # Main data storage
```

### JSON Structure
```json
{
  "2024-01-15": {
    "domain.com": {
      "Server": "Server Name",
      "Page Load": 2.5,
      "Login": 15.2,
      "Features": {
        "Feature Name": {
          "Feature": 45.8,
          "Scenario Timings": [...]
        }
      }
    }
  }
}
```

## Usage

### Running Tests with Tracking
```bash
python run_behave.py
```

The system automatically:
1. Initializes the timing tracker
2. Cleans up old data (>7 days)
3. Stores today's results
4. Generates enhanced summaries

### Manual Data Management
```python
from timing_tracker import TimingTracker

# Initialize tracker
tracker = TimingTracker()

# Add data manually
tracker.add_timing_data("domain.com", timing_data)

# Get 7-day summary
summary = tracker.format_timing_summary("domain.com", current_data)

# Clean up old data
tracker.cleanup_old_data()
```

## Configuration

### Data Directory
Change the data storage location:
```python
tracker = TimingTracker("custom_data_dir")
```

### Retention Period
Modify the cleanup function to change retention:
```python
# In timing_tracker.py, modify cleanup_old_data()
if (today - date_obj).days > 7:  # Change 7 to desired days
```

## Benefits

1. **Performance Monitoring**: Track performance trends over time
2. **Issue Detection**: Identify when performance degrades
3. **Historical Analysis**: Compare current vs historical performance
4. **Proactive Alerts**: Get notified of performance issues
5. **Data-Driven Decisions**: Make informed decisions based on trends

## Troubleshooting

### No Historical Data
- First few runs will show limited data
- After 7 days, full historical context will be available

### Missing Metrics
- Some metrics may not appear if no data is available
- Check that timing data is being properly collected

### Data Corruption
- Delete `timing_history.json` to reset
- System will recreate from scratch

## Future Enhancements

- **Trend Analysis**: Add trend indicators (improving/declining)
- **Alert Thresholds**: Configurable performance thresholds
- **Export Features**: Export data for external analysis
- **Dashboard**: Web-based performance dashboard 