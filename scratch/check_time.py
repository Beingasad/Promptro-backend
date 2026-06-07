import urllib.request
import datetime
import email.utils

try:
    response = urllib.request.urlopen("https://www.google.com")
    date_str = response.headers.get("Date")
    print("Google Server Time (UTC):", date_str)
    
    # Parse RFC 2822 date
    google_time = datetime.datetime(*email.utils.parsedate(date_str)[:6])
    local_time = datetime.datetime.utcnow()
    
    print("Local Machine Time (UTC):", local_time)
    diff = abs((google_time - local_time).total_seconds())
    print(f"Time Difference: {diff} seconds ({diff / 3600:.2f} hours)")
except Exception as e:
    print("Error checking time:", e)
