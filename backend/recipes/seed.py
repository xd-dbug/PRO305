"""
Seeds a real, isolatable batch of recipes for pagination sanity-checking
(issue #39) — past-page-1 behavior can't be exercised with the ~3 recipes
used in Week 2 testing.

Follows backend/auth/seed.py's pattern: direct DB writes via
shared.db.get_connection, not the API. Bypassing the API means seeding 60
recipes takes one script run instead of 60 authenticated POSTs, and (more
importantly) keeps this independent of whatever create_recipe's auth path
is doing — this script's only job is to put known rows in the DB.

Requires backend/auth/seed.py to have been run already — every seeded
recipe needs a real author_id, and this looks up alice@example.com's user
id rather than inventing one, to avoid an FK violation against `users`.

Every seeded recipe is tagged with SEED_TAG so verify_pagination.py (and
cleanup, via --cleanup) can operate on an isolated slice of the data
instead of whatever else is in the table from real usage or other
people's testing.

Usage:
    python seed.py                 # seed 60 recipes (3 full pages @ default limit 20, if using limit=20)
    python seed.py --count 45      # seed a specific number
    python seed.py --cleanup       # delete every recipe tagged SEED_TAG (cascades to children)
"""
import argparse

from shared.db import get_connection

SEED_TAG = "paginationtest-w3"
SEED_USER_EMAIL = "alice@example.com"


def _get_seed_author_id(cur) -> int:
    cur.execute("SELECT id FROM users WHERE email = %s", (SEED_USER_EMAIL,))
    row = cur.fetchone()
    if not row:
        raise SystemExit(
            f"No user found for {SEED_USER_EMAIL}. Run backend/auth/seed.py first — "
            "this script seeds recipes against an existing user, it doesn't create one."
        )
    return row["id"]


def seed(count: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            author_id = _get_seed_author_id(cur)

            cur.execute("INSERT IGNORE INTO tags (name) VALUES (%s)", (SEED_TAG,))
            cur.execute("SELECT id FROM tags WHERE name = %s", (SEED_TAG,))
            tag_id = cur.fetchone()["id"]

            for i in range(count):
                # Zero-padded index in the title makes it easy to eyeball
                # ordering by hand if something looks wrong; verify_pagination.py
                # checks it programmatically via recipeId, not this string.
                title = f"Pagination Seed {i:04d}"
                cur.execute(
                    "INSERT INTO recipes (title, author_id) VALUES (%s, %s)",
                    (title, author_id),
                )
                recipe_id = cur.lastrowid

                cur.execute(
                    "INSERT INTO recipe_ingredient (recipe_id, name, amount, sort_order) VALUES (%s, %s, %s, %s)",
                    (recipe_id, "filler ingredient", "1", 0),
                )
                cur.execute(
                    "INSERT INTO recipe_step (recipe_id, step_number, body) VALUES (%s, %s, %s)",
                    (recipe_id, 1, "Seed step — no real content."),
                )
                cur.execute(
                    "INSERT IGNORE INTO recipe_tag (recipe_id, tag_id) VALUES (%s, %s)",
                    (recipe_id, tag_id),
                )
        conn.commit()
        print(f"Seeded {count} recipes tagged '{SEED_TAG}' (author: {SEED_USER_EMAIL}).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cleanup():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tags WHERE name = %s", (SEED_TAG,))
            tag_row = cur.fetchone()
            if not tag_row:
                print(f"No '{SEED_TAG}' tag found — nothing to clean up.")
                return

            cur.execute(
                "SELECT recipe_id FROM recipe_tag WHERE tag_id = %s", (tag_row["id"],)
            )
            recipe_ids = [r["recipe_id"] for r in cur.fetchall()]

            for rid in recipe_ids:
                # Cascades to recipe_ingredient/recipe_step/recipe_tag/rating
                # per schema.sql's ON DELETE CASCADE.
                cur.execute("DELETE FROM recipes WHERE id = %s", (rid,))
        conn.commit()
        print(f"Deleted {len(recipe_ids)} seeded recipes tagged '{SEED_TAG}'.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=60, help="How many recipes to seed (default 60)")
    parser.add_argument("--cleanup", action="store_true", help="Delete all previously seeded recipes instead")
    args = parser.parse_args()

    if args.cleanup:
        cleanup()
    else:
        seed(args.count)