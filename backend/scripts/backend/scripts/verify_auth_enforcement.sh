#!/usr/bin/env bash
# Live server-side auth verification against the deployed stack — issues #40 and #41.
#
# Run this from a machine that can reach the deployed API Gateway (this repo's
# sandbox network allowlist does not include *.execute-api.*.amazonaws.com,
# so it could not be run from there — this is meant to be run by a human,
# or from CI with network access).
#
# Usage:
#   API_BASE=https://yat192qddb.execute-api.us-east-2.amazonaws.com/dev \
#   MOD_EMAIL=mod@example.com MOD_PASSWORD=mod-test-password \
#   USER_EMAIL=alice@example.com USER_PASSWORD=alice-test-password \
#   ./verify_auth_enforcement.sh
#
# Exits non-zero if any check fails. Prints a pass/fail line per route,
# suitable for pasting into the issue as the DoD's documented results.

set -uo pipefail

API_BASE="${API_BASE:?set API_BASE, e.g. https://yat192qddb.execute-api.us-east-2.amazonaws.com/dev}"
USER_EMAIL="${USER_EMAIL:?set USER_EMAIL (a non-moderator test account)}"
USER_PASSWORD="${USER_PASSWORD:?set USER_PASSWORD}"
MOD_EMAIL="${MOD_EMAIL:-}"
MOD_PASSWORD="${MOD_PASSWORD:-}"

PASS=0
FAIL=0

# --- get tokens ------------------------------------------------------------

user_login=$(curl -s -X POST "$API_BASE/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$USER_EMAIL\",\"password\":\"$USER_PASSWORD\"}")
USER_TOKEN=$(echo "$user_login" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
if [ -z "$USER_TOKEN" ]; then
    echo "FATAL: could not log in as USER_EMAIL ($user_login)"; exit 1
fi

MOD_TOKEN=""
if [ -n "$MOD_EMAIL" ]; then
    mod_login=$(curl -s -X POST "$API_BASE/auth/login" \
        -H 'Content-Type: application/json' \
        -d "{\"email\":\"$MOD_EMAIL\",\"password\":\"$MOD_PASSWORD\"}")
    MOD_TOKEN=$(echo "$mod_login" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
fi

# --- helpers -----------------------------------------------------------------

check_401_unauthenticated() {
    local method="$1" path="$2" body="${3:-}"
    local args=(-s -o /dev/null -w '%{http_code}' -X "$method" "$API_BASE$path" -H 'Content-Type: application/json')
    [ -n "$body" ] && args+=(-d "$body")
    local code
    code=$(curl "${args[@]}")
    if [ "$code" = "401" ]; then
        echo "PASS  $method $path -> 401 unauthenticated"
        PASS=$((PASS+1))
    else
        echo "FAIL  $method $path -> expected 401, got $code"
        FAIL=$((FAIL+1))
    fi
}

check_status() {
    local expect="$1" desc="$2" method="$3" path="$4" token="$5" body="${6:-}"
    local args=(-s -o /dev/null -w '%{http_code}' -X "$method" "$API_BASE$path" \
        -H 'Content-Type: application/json' -H "Authorization: Bearer $token")
    [ -n "$body" ] && args+=(-d "$body")
    local code
    code=$(curl "${args[@]}")
    if [ "$code" = "$expect" ]; then
        echo "PASS  $desc -> $code"
        PASS=$((PASS+1))
    else
        echo "FAIL  $desc -> expected $expect, got $code"
        FAIL=$((FAIL+1))
    fi
}

# --- #40: every protected route rejects an unauthenticated request ---------
#
# Enumerated from infra/template.yaml's actual API Gateway Events (not from
# docs/API_CONTRACT.md, which documents GET /mealplan/status/{jobId} — a
# route that has no handler and isn't wired in infra/template.yaml at all;
# it's excluded here because it doesn't exist to test yet, not because it
# passed. Public routes (GET /health, POST /auth/login, GET /recipes,
# GET /recipes/{id}) are correctly excluded, not skipped by oversight.

echo "== #40: unauthenticated requests -> 401 on every protected route =="
check_401_unauthenticated GET  "/users/me/preferences"
check_401_unauthenticated PUT  "/users/me/preferences" '{"dietaryTags":["vegetarian"]}'
check_401_unauthenticated POST "/recipes" '{"title":"x","ingredients":[{"name":"a","amount":"1"}],"steps":["s"],"tags":[]}'
check_401_unauthenticated PUT  "/recipes/1" '{"title":"x","ingredients":[{"name":"a","amount":"1"}],"steps":["s"],"tags":[]}'
check_401_unauthenticated DELETE "/recipes/1"
check_401_unauthenticated POST "/recipes/1/ratings" '{"score":5}'
check_401_unauthenticated POST "/recipes/1/save"
check_401_unauthenticated POST "/recipes/1/photo"
check_401_unauthenticated POST "/mealplan/generate" '{"preferences":{"days":3,"mealsPerDay":2}}'

# --- #41: non-moderator hitting the actual moderator-gated logic -----------
#
# IMPORTANT: as of this write-up there is no route in this codebase gated
# "moderator-only" (i.e. rejecting a non-moderator regardless of ownership).
# The only moderator-aware logic that exists is require_owner_or_moderator
# on PUT/DELETE /recipes/{id}, which is an *inclusive* check (owner OR
# moderator) — a non-moderator author still succeeds. What #41 can actually
# verify today is: a non-owner, non-moderator is 403'd (not merely UI-hidden)
# on the write routes that use that check, and a moderator succeeds against
# someone else's resource. If the actual report/moderation-queue feature
# (Project_Proposal.docx section 2, "Moderator review queue") ships later,
# add its endpoints below the same way.

echo
echo "== #41: owner-or-moderator enforcement (the only moderator-gated logic that currently exists) =="
if [ -n "$MOD_TOKEN" ]; then
    check_status 403 "PUT /recipes/1 as non-owner non-moderator" PUT "/recipes/1" "$USER_TOKEN" \
        '{"title":"hostile edit","ingredients":[{"name":"a","amount":"1"}],"steps":["s"],"tags":[]}'
    check_status 403 "DELETE /recipes/1 as non-owner non-moderator" DELETE "/recipes/1" "$USER_TOKEN"
    echo "NOTE: moderator-succeeds-on-others'-resource checks need a recipe ID owned by someone other than MOD_EMAIL — set one manually and adapt above."
else
    echo "SKIP  MOD_EMAIL/MOD_PASSWORD not set — cannot test moderator-vs-non-moderator behavior"
fi

echo
echo "---"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
