CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL DEFAULT '',
    role ENUM('user', 'moderator') NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Dietary preference tags (issue #9). Normalized the same way recipes'
-- tags/recipe_tag pair works (backend/recipes/schema.sql) rather than a
-- JSON column on users, so the mealplan prompt-building consumer (issue #1)
-- can join/filter per-tag directly instead of parsing a blob. Tag names are
-- stored lowercase/trimmed by the API layer (backend/auth/app.py), not
-- enforced here.
CREATE TABLE IF NOT EXISTS dietary_tag (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_dietary_tag (
    user_id INT NOT NULL,
    dietary_tag_id INT NOT NULL,
    PRIMARY KEY (user_id, dietary_tag_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (dietary_tag_id) REFERENCES dietary_tag(id) ON DELETE CASCADE
);
