-- Depends on backend/auth/schema.sql (users) being applied first.

CREATE TABLE IF NOT EXISTS mealplan_job (
    id CHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    status ENUM('pending', 'complete', 'failed') NOT NULL DEFAULT 'pending',
    request_preferences JSON NOT NULL,
    generated_plan JSON,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);