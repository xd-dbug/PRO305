"""Minimal in-memory stand-in for pymysql's DictCursor connection.

app.py's routes are all DB-backed (real MySQL/RDS via shared.db.get_connection —
see backend/layer/shared/db.py), and per the repo's testing convention DB-dependent
code is normally only smoke-tested manually after a real `sam deploy` (sam local
can't reach the VPC-bound RDS instance).

This fake exists purely to make the *auth/ownership wiring* in update_recipe and
delete_recipe unit-testable — it is not a general-purpose SQL engine and only
understands the exact statements app.py currently issues. If app.py's SQL changes,
this needs to change with it. It is not a substitute for the manual post-deploy
smoke test of the actual DB-dependent behavior.
"""


class FakeDB:
    def __init__(self):
        self.recipes = {}
        self.ingredients = []
        self.steps = []
        self.tags = {}
        self.recipe_tags = []
        self.ratings = {}
        self.saved = []  # ordered list of (user_id, recipe_id) tuples, save order
        self._next_id = 1
        self._next_tag_id = 1

    def seed_recipe(self, recipe_id, author_id, title="Original Title"):
        self.recipes[int(recipe_id)] = {
            "id": int(recipe_id),
            "title": title,
            "author_id": str(author_id),
            "rating_avg": None,
            "photo_url": None,
            "servings": None,
            "prep_time": None,
            "cook_time": None,
            "notes": None,
        }
        self._next_id = max(self._next_id, int(recipe_id) + 1)


class FakeCursor:
    def __init__(self, db: FakeDB):
        self.db = db
        self._rows = []
        self.lastrowid = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split())
        db = self.db
        self._rows = []

        if normalized.startswith("SELECT * FROM recipes WHERE id"):
            row = db.recipes.get(int(params[0]))
            self._rows = [dict(row)] if row else []

        elif normalized.startswith("INSERT INTO recipes (title, author_id, servings, prep_time, cook_time, notes)"):
            new_id = db._next_id
            db._next_id += 1
            title, author_id, servings, prep_time, cook_time, notes = params
            db.recipes[new_id] = {
                "id": new_id,
                "title": title,
                "author_id": str(author_id),
                "rating_avg": None,
                "photo_url": None,
                "servings": servings,
                "prep_time": prep_time,
                "cook_time": cook_time,
                "notes": notes,
            }
            self.lastrowid = new_id

        elif normalized.startswith("UPDATE recipes SET title"):
            title, servings, prep_time, cook_time, notes, recipe_id = params
            row = db.recipes[int(recipe_id)]
            row["title"] = title
            row["servings"] = servings
            row["prep_time"] = prep_time
            row["cook_time"] = cook_time
            row["notes"] = notes

        elif normalized.startswith("UPDATE recipes SET rating_avg"):
            avg_score, recipe_id = params
            db.recipes[int(recipe_id)]["rating_avg"] = avg_score

        elif normalized.startswith("UPDATE recipes SET photo_url"):
            photo_key, recipe_id = params
            db.recipes[int(recipe_id)]["photo_url"] = photo_key

        elif normalized.startswith("DELETE FROM recipes WHERE id"):
            db.recipes.pop(int(params[0]), None)

        elif normalized.startswith("DELETE FROM recipe_ingredient"):
            db.ingredients = [i for i in db.ingredients if i["recipe_id"] != int(params[0])]

        elif normalized.startswith("DELETE FROM recipe_step"):
            db.steps = [s for s in db.steps if s["recipe_id"] != int(params[0])]

        elif normalized.startswith("DELETE FROM recipe_tag"):
            db.recipe_tags = [t for t in db.recipe_tags if t["recipe_id"] != int(params[0])]

        elif normalized.startswith("INSERT INTO recipe_ingredient"):
            recipe_id, name, amount, sort_order = params
            db.ingredients.append(
                {"recipe_id": int(recipe_id), "name": name, "amount": amount, "sort_order": sort_order}
            )

        elif normalized.startswith("INSERT INTO recipe_step"):
            recipe_id, step_number, body = params
            db.steps.append({"recipe_id": int(recipe_id), "step_number": step_number, "body": body})

        elif normalized.startswith("INSERT IGNORE INTO tags"):
            name = params[0]
            if name not in db.tags:
                db.tags[name] = db._next_tag_id
                db._next_tag_id += 1

        elif normalized.startswith("SELECT id FROM tags WHERE name"):
            name = params[0]
            self._rows = [{"id": db.tags[name]}] if name in db.tags else []

        elif normalized.startswith("INSERT IGNORE INTO recipe_tag"):
            recipe_id, tag_id = params
            db.recipe_tags.append({"recipe_id": int(recipe_id), "tag_id": tag_id})

        elif normalized.startswith("SELECT name, amount FROM recipe_ingredient"):
            recipe_id = int(params[0])
            self._rows = [
                {"name": i["name"], "amount": i["amount"]}
                for i in db.ingredients
                if i["recipe_id"] == recipe_id
            ]

        elif normalized.startswith("SELECT body FROM recipe_step"):
            recipe_id = int(params[0])
            self._rows = [{"body": s["body"]} for s in db.steps if s["recipe_id"] == recipe_id]

        elif normalized.startswith("SELECT t.name FROM tags"):
            self._rows = []

        elif normalized.startswith("INSERT INTO rating"):
            recipe_id, user_id, score = params
            db.ratings[(int(recipe_id), str(user_id))] = score

        elif normalized.startswith("SELECT ROUND(AVG(score)"):
            recipe_id = int(params[0])
            scores = [s for (rid, _uid), s in db.ratings.items() if rid == recipe_id]
            avg = round(sum(scores) / len(scores), 2) if scores else None
            self._rows = [{"avg_score": avg}]

        elif normalized.startswith("SELECT COUNT(*) AS total FROM recipes"):
            self._rows = [{"total": len(db.recipes)}]

        elif normalized.startswith("SELECT COUNT(*) AS total FROM saved_recipe"):
            user_id = str(params[0])
            self._rows = [{"total": sum(1 for uid, _rid in db.saved if uid == user_id)}]

        elif "JOIN saved_recipe sr" in normalized:
            user_id = str(params[0])
            saved_ids = [rid for uid, rid in reversed(db.saved) if uid == user_id]
            self._rows = [dict(db.recipes[rid]) for rid in saved_ids if rid in db.recipes]

        elif normalized.startswith("INSERT IGNORE INTO saved_recipe"):
            user_id, recipe_id = str(params[0]), int(params[1])
            if (user_id, recipe_id) not in db.saved:
                db.saved.append((user_id, recipe_id))

        elif normalized.startswith("DELETE FROM saved_recipe"):
            user_id, recipe_id = str(params[0]), int(params[1])
            db.saved = [(uid, rid) for uid, rid in db.saved if (uid, rid) != (user_id, recipe_id)]

        else:
            raise AssertionError(f"FakeCursor got an unexpected statement: {normalized!r}")

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConnection:
    def __init__(self, db: FakeDB):
        self.db = db
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True
