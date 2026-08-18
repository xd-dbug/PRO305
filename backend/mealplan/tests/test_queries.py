import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

MEALPLAN_DIR = Path(__file__).parent.parent
MODULE_PATH = MEALPLAN_DIR / "queries.py"

def _load():
      spec = importlib.util.spec_from_file_location("mealplan_queries", MODULE_PATH)
      module = importlib.util.module_from_spec(spec)
      sys.modules["mealplan_queries"] = module
      spec.loader.exec_module(module)
      return module

queries = _load()

def test_get_saved_recipes_queries_and_returns_rows():
    rows = [{"title": "Oat Bowl", "ratings_avg": "4.50"}]

    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor

    result = queries.get_saved_recipes(conn, 42)

    sql, params = cursor.execute.call_args.args
    assert "saved_recipe" in sql
    assert "recipes" in sql
    assert "sr.user_id = %s" in sql
    assert params == (42,)

    assert result == rows

def test_get_dietary_tags_queries_and_returns_names():
    rows = [{"name": "vegetarian"}, {"name": "gluten-free"}]
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor

    result = queries.get_dietary_tags(conn, 42)

    sql, params = cursor.execute.call_args.args
    assert "user_dietary_tag" in sql
    assert "dietary_tag" in sql
    assert "udt.user_id = %s" in sql
    assert params == (42,)

    assert result == ["vegetarian", "gluten-free"]