import sqlite3

def create_dbs():
    """
    Create or update the database schema to ensure it matches the application's requirements.
    """
    connection = sqlite3.connect("synth.db")
    cursor = connection.cursor()

    # Create initial tables if they don't exist
    create_tables = """
    CREATE TABLE IF NOT EXISTS Users (
        Uid INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS AdditivePresets (
        Aid INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT UNIQUE NOT NULL,
        base_frequency REAL,
        sample_rate REAL,
        duration REAL,
        volume REAL,
        tone REAL,
        num_harmonics INTEGER,
        attack REAL,
        decay REAL,
        sustain REAL,
        release REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(Uid)
    );

    CREATE TABLE IF NOT EXISTS SubtractivePresets (
        Sid INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT UNIQUE NOT NULL,
        volume REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(Uid)
    );

    -- New table to store community presets
    CREATE TABLE IF NOT EXISTS CommunityPresets (
        Cid INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,  -- The user who uploaded the preset
        name TEXT NOT NULL,
        preset_type TEXT NOT NULL,  -- 'Additive' or 'Subtractive'
        preset_data TEXT NOT NULL,  -- JSON-encoded preset data
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(Uid)
    );

    --  New table to store multiple filters per preset
    CREATE TABLE IF NOT EXISTS SubtractivePresetFilters (
        Fid INTEGER PRIMARY KEY AUTOINCREMENT,
        preset_id INTEGER NOT NULL,
        filter_type TEXT NOT NULL,
        cutoff_frequency REAL NOT NULL,
        resonance REAL NOT NULL,
        FOREIGN KEY (preset_id) REFERENCES SubtractivePresets(Sid) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS Effects (
        Eid INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS SubtractivePresetEffects (
        SpeId INTEGER PRIMARY KEY AUTOINCREMENT,
        preset_id INTEGER NOT NULL,
        effect_id INTEGER NOT NULL,
        parameters TEXT NOT NULL,
        FOREIGN KEY (preset_id) REFERENCES SubtractivePresets(Sid) ON DELETE CASCADE,
        FOREIGN KEY (effect_id) REFERENCES Effects(Eid) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS SubtractivePresetOscillators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        preset_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        frequency REAL NOT NULL,
        amplitude REAL NOT NULL,
        FOREIGN KEY (preset_id) REFERENCES SubtractivePresets(Sid) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS SubtractivePresetLFOs (
    LfoId INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id INTEGER NOT NULL,
    shape TEXT NOT NULL,
    frequency REAL NOT NULL,
    depth REAL NOT NULL,
    target TEXT NOT NULL,
    FOREIGN KEY (preset_id) REFERENCES SubtractivePresets(Sid) ON DELETE CASCADE
    );

    """
    cursor.executescript(create_tables)

    # Prepopulate the Effects table with predefined effects
    predefined_effects = [
        ("Chorus", "Adds depth and richness to the sound"),
        ("Flanger", "Creates a sweeping, jet-like sound"),
        ("Bitcrusher", "Reduces the bit depth and sample rate for distortion"),
        ("Ring Modulation", "Multiplies the waveform with a modulating frequency"),
        ("Phaser", "Creates a sweeping phase effect"),
        ("Wavefolder", "Adds harmonic complexity through wavefolding")
    ]
    cursor.executemany("INSERT OR IGNORE INTO Effects (name, description) VALUES (?, ?)", predefined_effects)

    connection.commit()
    connection.close()
    print("Database setup completed successfully.")

if __name__ == "__main__":
    create_dbs()