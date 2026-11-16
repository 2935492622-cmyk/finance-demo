-- finance_demo initial schema; MySQL 8.0.16+.
-- Not executed during planning. Contains no credentials or seed records.
-- Existing tables are preserved; IF NOT EXISTS does not migrate their schema.
SET NAMES utf8mb4;
SET SESSION time_zone = '+00:00';

CREATE DATABASE IF NOT EXISTS finance_demo
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE finance_demo;

CREATE TABLE IF NOT EXISTS transactions (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    amount DECIMAL(10,2) NOT NULL,
    type VARCHAR(7) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    category VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs NOT NULL,
    note VARCHAR(500) NOT NULL DEFAULT '',
    transaction_date DATE NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT chk_transactions_amount CHECK (amount > 0),
    CONSTRAINT chk_transactions_type CHECK (
        (type = 'income' AND CHAR_LENGTH(type) = 6)
        OR (type = 'expense' AND CHAR_LENGTH(type) = 7)
    ),
    CONSTRAINT chk_transactions_category CHECK (
        CHAR_LENGTH(TRIM(category)) BETWEEN 1 AND 50
        AND CHAR_LENGTH(category) = CHAR_LENGTH(TRIM(category))
    ),
    INDEX idx_transactions_date_id (transaction_date, id),
    INDEX idx_transactions_type_date (type, transaction_date),
    INDEX idx_transactions_category_date (category, transaction_date)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
