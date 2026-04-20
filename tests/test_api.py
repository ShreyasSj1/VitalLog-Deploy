"""Integration tests for /api/food-items and /api/exercises lookup endpoints."""
import pytest
from tests.conftest import make_user, login


class TestFoodItemsAPI:
    def test_requires_login(self, client):
        resp = client.get("/api/food-items", follow_redirects=False)
        assert resp.status_code == 302

    def test_returns_all_categories_when_no_param(self, client, db):
        make_user(db, email="api_food_all@example.com")
        login(client, email="api_food_all@example.com")
        resp = client.get("/api/food-items")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert "Breakfast" in data
        assert "Lunch" in data
        assert "Dinner" in data

    def test_returns_items_for_specific_category(self, client, db):
        make_user(db, email="api_food_cat@example.com")
        login(client, email="api_food_cat@example.com")
        resp = client.get("/api/food-items?category=Breakfast")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        names = [item["name"] for item in data]
        assert "Idli" in names

    def test_food_item_has_required_fields(self, client, db):
        make_user(db, email="api_food_fields@example.com")
        login(client, email="api_food_fields@example.com")
        resp = client.get("/api/food-items?category=Snacks")
        data = resp.get_json()
        item = data[0]
        for field in ("id", "meal_category", "name", "calories", "protein", "fat", "sugar", "is_custom"):
            assert field in item, f"Missing field: {field}"

    def test_empty_category_returns_empty_list(self, client, db):
        make_user(db, email="api_food_empty@example.com")
        login(client, email="api_food_empty@example.com")
        resp = client.get("/api/food-items?category=NonExistentCategory")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == []


class TestExercisesAPI:
    def test_requires_login(self, client):
        resp = client.get("/api/exercises", follow_redirects=False)
        assert resp.status_code == 302

    def test_returns_all_groups_when_no_param(self, client, db):
        make_user(db, email="api_ex_all@example.com")
        login(client, email="api_ex_all@example.com")
        resp = client.get("/api/exercises")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert "Chest" in data
        assert "Legs" in data
        assert "Cardio" in data

    def test_returns_exercises_for_specific_muscle(self, client, db):
        make_user(db, email="api_ex_muscle@example.com")
        login(client, email="api_ex_muscle@example.com")
        resp = client.get("/api/exercises?muscle=Chest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        names = [ex["name"] for ex in data]
        assert "Bench Press" in names

    def test_exercise_entry_has_required_fields(self, client, db):
        make_user(db, email="api_ex_fields@example.com")
        login(client, email="api_ex_fields@example.com")
        resp = client.get("/api/exercises?muscle=Arms")
        data = resp.get_json()
        ex = data[0]
        for field in ("id", "muscle_group", "name", "is_cardio", "is_custom"):
            assert field in ex, f"Missing field: {field}"

    def test_cardio_exercises_flagged_correctly(self, client, db):
        make_user(db, email="api_cardio_flag@example.com")
        login(client, email="api_cardio_flag@example.com")
        resp = client.get("/api/exercises?muscle=Cardio")
        data = resp.get_json()
        assert all(ex["is_cardio"] is True for ex in data)

    def test_empty_muscle_returns_empty_list(self, client, db):
        make_user(db, email="api_ex_empty@example.com")
        login(client, email="api_ex_empty@example.com")
        resp = client.get("/api/exercises?muscle=NonExistentMuscle")
        data = resp.get_json()
        assert data == []
