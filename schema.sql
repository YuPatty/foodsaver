-- database: app.db
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS specials;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS favorites;

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    avatar_url TEXT
);


CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    image_url TEXT,
    price REAL NOT NULL,
    remaining_qty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE specials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    discount_rate REAL NOT NULL DEFAULT 1.0,
    end_date DATE NOT NULL
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (user_id, category),
    FOREIGN KEY (user_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_url TEXT NOT NULL,
    link_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

INSERT INTO ads(image_url, link_url, is_active) VALUES
('https://picsum.photos/seed/ad1/1200/300','https://example.com/a',1),
('https://picsum.photos/seed/ad2/1200/300','https://example.com/b',1),
('https://picsum.photos/seed/ad3/1200/300','https://example.com/c',1);


-- 沒類別的先補成「其他」
UPDATE products SET category='其他' WHERE category IS NULL OR TRIM(category)='';

-- 依名稱粗分（可選）
UPDATE products SET category='飲料' WHERE category='其他' AND name LIKE '%飲%';
UPDATE products SET category='便當' WHERE category='其他' AND name LIKE '%便當%';
UPDATE products SET category='麵包' WHERE category='其他' AND name LIKE '%麵包%';
UPDATE products SET category='甜點' WHERE category='其他' AND name LIKE '%蛋糕%' OR name LIKE '%甜%';
