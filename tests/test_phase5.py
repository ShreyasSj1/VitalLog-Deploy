"""Tests for Phase 5 features: custom user goals and CSV export."""
import pytest
from datetime import date
from tests.conftest import make_user, login

TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# Custom goals — model property
# ---------------------------------------------------------------------------

class TestUserGoalsProperty:
    def test_goals_use_app_defaults_when_null(self, db):
        user = make_user(db, email="goals_default@example.com")
        from constants import GOALS
        assert user.goals["calories"] == GOALS["calories"]
        assert user.goals["protein"]  == GOALS["protein"]
        assert user.goals["fat"]      == GOALS["fat"]
        assert user.goals["sugar"]    == GOALS["sugar"]

    def test_goals_use_custom_values_when_set(self, db):
        user = make_user(db, email="goals_custom@example.com")
        user.goal_calories = 2000
        user.goal_protein  = 150
        user.goal_fat      = 60
        user.goal_sugar    = 30
        db.session.commit()

        assert user.goals["calories"] == pytest.approx(2000)
        assert user.goals["protein"]  == pytest.approx(150)
        assert user.goals["fat"]      == pytest.approx(60)
        assert user.goals["sugar"]    == pytest.approx(30)

    def test_goals_partial_override(self, db):
        """Only calories set — others should fall back to defaults."""
        user = make_user(db, email="goals_partial@example.com")
        user.goal_calories = 1800
        db.session.commit()

        from constants import GOALS
        assert user.goals["calories"] == pytest.approx(1800)
        assert user.goals["protein"]  == GOALS["protein"]


# ---------------------------------------------------------------------------
# Custom goals — profile POST route
# ---------------------------------------------------------------------------

class TestProfileGoals:
    def test_save_custom_goals(self, client, db):
        make_user(db, email="save_goals@example.com")
        login(client, email="save_goals@example.com")
        resp = client.post(
            "/profile",
            data={
                "name": "Goals User",
                "age": "", "height": "", "weight": "",
                "goal_calories": "2200",
                "goal_protein": "160",
                "goal_fat": "70",
                "goal_sugar": "35",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        from models import User
        user = User.query.filter_by(email="save_goals@example.com").first()
        assert user.goal_calories == pytest.approx(2200)
        assert user.goal_protein  == pytest.approx(160)
        assert user.goal_fat      == pytest.approx(70)
        assert user.goal_sugar    == pytest.approx(35)

    def test_clear_goals_resets_to_none(self, client, db):
        """Submitting empty goal fields should set columns back to NULL."""
        make_user(db, email="clear_goals@example.com")
        login(client, email="clear_goals@example.com")
        # First set some goals
        client.post("/profile", data={
            "name": "User", "goal_calories": "1800",
            "goal_protein": "", "goal_fat": "", "goal_sugar": "",
        })
        # Then clear them
        client.post("/profile", data={
            "name": "User", "goal_calories": "",
            "goal_protein": "", "goal_fat": "", "goal_sugar": "",
        })
        from models import User
        user = User.query.filter_by(email="clear_goals@example.com").first()
        assert user.goal_calories is None

    def test_dashboard_reflects_custom_goal(self, client, db):
        """The dashboard index should receive the user's custom goals."""
        make_user(db, email="dash_goal@example.com")
        login(client, email="dash_goal@example.com")
        client.post("/profile", data={
            "name": "User", "goal_calories": "3000",
            "goal_protein": "", "goal_fat": "", "goal_sugar": "",
        })
        resp = client.get("/")
        assert resp.status_code == 200
        # 3000 kcal should appear somewhere in the rendered HTML
        assert b"3000" in resp.data


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

class TestCSVExport:
    def test_export_requires_login(self, client):
        resp = client.get("/export/csv", follow_redirects=False)
        assert resp.status_code == 302

    def test_export_returns_csv_content_type(self, client, db):
        make_user(db, email="export_ct@example.com")
        login(client, email="export_ct@example.com")
        resp = client.get("/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_export_has_attachment_header(self, client, db):
        make_user(db, email="export_hdr@example.com")
        login(client, email="export_hdr@example.com")
        resp = client.get("/export/csv")
        assert "attachment" in resp.headers.get("Content-Disposition", "")

    def test_export_contains_section_headers(self, client, db):
        make_user(db, email="export_sec@example.com")
        login(client, email="export_sec@example.com")
        resp = client.get("/export/csv")
        body = resp.data.decode("utf-8")
        assert "Food Log" in body
        assert "Sleep Log" in body
        assert "Gym Log" in body
        assert "Wellbeing Log" in body

    def test_export_includes_logged_data(self, client, db):
        """Food log entries should appear in the exported CSV."""
        make_user(db, email="export_data@example.com")
        login(client, email="export_data@example.com")
        # Log a food item
        client.post(
            f"/food?date={TODAY}",
            data={"meal": "Breakfast", "food": "Idli", "qty": "3", "date": TODAY},
        )
        resp = client.get("/export/csv")
        body = resp.data.decode("utf-8")
        assert "Idli" in body

    def test_export_custom_date_range(self, client, db):
        make_user(db, email="export_range@example.com")
        login(client, email="export_range@example.com")
        resp = client.get("/export/csv?from=2024-01-01&to=2024-01-31")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_export_invalid_dates_falls_back(self, client, db):
        make_user(db, email="export_bad_date@example.com")
        login(client, email="export_bad_date@example.com")
        resp = client.get("/export/csv?from=not-a-date&to=also-bad")
        # Should not 500 — falls back to 30-day default
        assert resp.status_code == 200

    def test_export_swapped_dates_clamped(self, client, db):
        """If from > to, the route should swap them gracefully."""
        make_user(db, email="export_swap@example.com")
        login(client, email="export_swap@example.com")
        resp = client.get("/export/csv?from=2024-12-31&to=2024-01-01")
        assert resp.status_code == 200
