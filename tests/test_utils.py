"""Unit tests for utils.py helper functions."""
from datetime import date, timedelta
import pytest


# ---------------------------------------------------------------------------
# parse_optional_int
# ---------------------------------------------------------------------------

def test_parse_optional_int_valid():
    from utils import parse_optional_int
    assert parse_optional_int("42") == 42


def test_parse_optional_int_empty():
    from utils import parse_optional_int
    assert parse_optional_int("") is None
    assert parse_optional_int(None) is None
    assert parse_optional_int("   ") is None


def test_parse_optional_int_invalid():
    from utils import parse_optional_int
    with pytest.raises(ValueError):
        parse_optional_int("abc")


# ---------------------------------------------------------------------------
# parse_optional_float
# ---------------------------------------------------------------------------

def test_parse_optional_float_valid():
    from utils import parse_optional_float
    assert parse_optional_float("3.14") == pytest.approx(3.14)


def test_parse_optional_float_empty():
    from utils import parse_optional_float
    assert parse_optional_float("") is None
    assert parse_optional_float(None) is None


# ---------------------------------------------------------------------------
# normalize_selected_date
# ---------------------------------------------------------------------------

def test_normalize_selected_date_today(app):
    with app.app_context():
        from utils import normalize_selected_date
        today = date.today().isoformat()
        assert normalize_selected_date(today) == today


def test_normalize_selected_date_future_clamps_to_today(app):
    with app.app_context():
        from utils import normalize_selected_date
        future = (date.today() + timedelta(days=5)).isoformat()
        assert normalize_selected_date(future) == date.today().isoformat()


def test_normalize_selected_date_past_returns_as_is(app):
    with app.app_context():
        from utils import normalize_selected_date
        past = "2024-01-01"
        assert normalize_selected_date(past) == past


def test_normalize_selected_date_empty_returns_today(app):
    with app.app_context():
        from utils import normalize_selected_date
        assert normalize_selected_date("") == date.today().isoformat()
        assert normalize_selected_date(None) == date.today().isoformat()


def test_normalize_selected_date_invalid_returns_today(app):
    with app.app_context():
        from utils import normalize_selected_date
        assert normalize_selected_date("not-a-date") == date.today().isoformat()


# ---------------------------------------------------------------------------
# get_week_dates
# ---------------------------------------------------------------------------

def test_get_week_dates_length(app):
    with app.app_context():
        from utils import get_week_dates
        dates = get_week_dates("2024-06-10")
        assert len(dates) == 7


def test_get_week_dates_ends_on_selected(app):
    with app.app_context():
        from utils import get_week_dates
        selected = "2024-06-10"
        dates = get_week_dates(selected)
        assert dates[-1] == selected


def test_get_week_dates_spans_seven_days(app):
    with app.app_context():
        from utils import get_week_dates
        dates = get_week_dates("2024-06-10")
        start = date.fromisoformat(dates[0])
        end = date.fromisoformat(dates[-1])
        assert (end - start).days == 6
