from datetime import date, datetime, timedelta
from urllib.parse import urlparse, urljoin
from flask import request

def parse_optional_int(value):
    value = (value or "").strip()
    return int(value) if value else None

def parse_optional_float(value):
    value = (value or "").strip()
    return float(value) if value else None

def is_safe_redirect_target(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc

def normalize_selected_date(raw_date):
    today_iso = date.today().isoformat()
    if not raw_date:
        return today_iso

    try:
        parsed = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return today_iso

    return min(parsed, date.today()).isoformat()

def get_week_dates(selected_date):
    d = datetime.strptime(selected_date, "%Y-%m-%d")
    start = d - timedelta(days=6)
    return [(start + timedelta(days=i)).date().isoformat() for i in range(7)]
