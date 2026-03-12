CREATE TABLE IF NOT EXISTS food_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    meal TEXT,
    food TEXT,
    qty REAL,
    calories REAL,
    protein REAL,
    fat REAL,
    sugar REAL
);

CREATE TABLE IF NOT EXISTS sleep_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE,
    hours REAL,
    quality INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS wellbeing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    activity TEXT,
    minutes INTEGER
);
