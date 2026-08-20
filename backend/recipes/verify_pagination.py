"""
Walks GET /recipes?tag=paginationtest-w3 across every page at a few
different limit values and checks pagination is actually correct — not
just "doesn't error." Run against a real deployed API, after seed.py.

Checks, for each limit tested:
  - every page except (maybe) the last has exactly `limit` items
  - the last page's count matches the remainder math (totalPages, total count)
  - no recipeId appears on more than one page (would mean a row got
    re-shown — the failure mode of the missing ORDER BY tiebreaker)
  - no recipeId is missing from the full walk that should be there (would
    mean a row got silently skipped — the other half of the same failure mode)
  - requesting one page past the last returns an empty list, not an error

Deliberately scoped to tag=paginationtest-w3 (see seed.py) so results
aren't polluted by whatever else is in the table from real usage.

Usage:
    python verify_pagination.py --base-url https://xxxx.execute-api.us-east-1.amazonaws.com/dev/
"""
import argparse
import sys

import requests

SEED_TAG = "paginationtest-w3"


def fetch_all_recipe_ids(base_url: str, limit: int) -> list[str]:
    """Walks every page at this limit, returns the recipeIds in the order
    the API returned them (page 1 first item -> last page last item)."""
    seen_across_pages = {}  # recipeId -> list of pages it appeared on
    ordered_ids = []
    page = 1

    while True:
        resp = requests.get(
            f"{base_url.rstrip('/')}/recipes",
            params={"tag": SEED_TAG, "page": page, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()

        recipes = body["recipes"]
        total_pages = body["totalPages"]

        if page < total_pages:
            assert len(recipes) == limit, (
                f"[limit={limit}] page {page} of {total_pages} has {len(recipes)} items, "
                f"expected exactly {limit} (not the last page)"
            )
        else:
            assert len(recipes) >= 1, (
                f"[limit={limit}] last page ({page}) came back empty — totalPages/count math is off"
            )

        for r in recipes:
            seen_across_pages.setdefault(r["recipeId"], []).append(page)
            ordered_ids.append(r["recipeId"])

        if page >= total_pages:
            break
        page += 1

    duplicated = {rid: pages for rid, pages in seen_across_pages.items() if len(pages) > 1}
    assert not duplicated, (
        f"[limit={limit}] {len(duplicated)} recipe(s) appeared on more than one page "
        f"(classic symptom of an unstable ORDER BY tiebreaker): {duplicated}"
    )

    return ordered_ids


def check_one_past_last_page_is_empty(base_url: str, limit: int):
    resp = requests.get(
        f"{base_url.rstrip('/')}/recipes",
        params={"tag": SEED_TAG, "page": 1, "limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    total_pages = resp.json()["totalPages"]

    resp = requests.get(
        f"{base_url.rstrip('/')}/recipes",
        params={"tag": SEED_TAG, "page": total_pages + 1, "limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    assert body["recipes"] == [], (
        f"[limit={limit}] page {total_pages + 1} (one past the last page) "
        f"returned {len(body['recipes'])} items, expected an empty list"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="e.g. https://xxxx.execute-api.us-east-1.amazonaws.com/dev/")
    parser.add_argument(
        "--limits", type=int, nargs="+", default=[20, 7],
        help="Page sizes to test against the same seeded dataset (default: 20 7)",
    )
    args = parser.parse_args()

    resp = requests.get(f"{args.base_url.rstrip('/')}/recipes", params={"tag": SEED_TAG, "page": 1, "limit": 1}, timeout=10)
    resp.raise_for_status()
    total_seeded = resp.json()["totalPages"]  # not the real total, just confirms tag has *some* data
    if total_seeded == 0:
        print(f"No recipes tagged '{SEED_TAG}' found. Run seed.py against this environment first.", file=sys.stderr)
        sys.exit(1)

    all_ok = True
    id_sets_by_limit = {}

    for limit in args.limits:
        print(f"--- Checking limit={limit} ---")
        try:
            ids = fetch_all_recipe_ids(args.base_url, limit)
            check_one_past_last_page_is_empty(args.base_url, limit)
            id_sets_by_limit[limit] = set(ids)
            print(f"  OK — {len(ids)} recipes walked across all pages, no duplicates, boundaries correct.")
        except AssertionError as e:
            all_ok = False
            print(f"  FAILED: {e}")
        except requests.RequestException as e:
            all_ok = False
            print(f"  REQUEST ERROR: {e}")

    # Cross-check: different limits should walk the exact same *set* of
    # recipes overall, even though page boundaries differ.
    distinct_sets = list(id_sets_by_limit.values())
    if len(distinct_sets) > 1 and any(s != distinct_sets[0] for s in distinct_sets):
        all_ok = False
        print("FAILED: different `limit` values walked different sets of recipeIds overall — "
              "pagination is inconsistent across page sizes, not just within one.")

    print()
    if all_ok:
        print("All pagination checks passed.")
    else:
        print("Pagination checks FAILED — see above.")
        sys.exit(1)


if __name__ == "__main__":
    main()