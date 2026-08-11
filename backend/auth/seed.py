from auth_service import hash_password
from shared.db import get_connection

SEED_USERS = [
    ("alice@example.com", "alice-test-password", "user"),
    ("mod@example.com", "mod-test-password", "moderator"),
]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for email, password, role in SEED_USERS:
                cursor.execute(
                    "INSERT IGNORE INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
                    (email, hash_password(password), role),
                )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
