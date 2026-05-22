PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    job_id TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT,
    final_audio_path TEXT,
    midi_path TEXT,
    detected_key TEXT,
    hvs_score REAL,
    error TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS transcriptions (
    id TEXT PRIMARY KEY,
    pipeline_run_id TEXT,
    job_id TEXT NOT NULL,
    input_audio TEXT NOT NULL,
    midi_path TEXT,
    transcription_method TEXT NOT NULL,
    note_count INTEGER NOT NULL DEFAULT 0,
    notes_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS corrections (
    id TEXT PRIMARY KEY,
    pipeline_run_id TEXT,
    raw_midi_path TEXT,
    corrected_midi_path TEXT,
    correction_mask_json TEXT NOT NULL DEFAULT '[]',
    proposals_json TEXT NOT NULL DEFAULT '[]',
    accepted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    car REAL,
    status TEXT NOT NULL,
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY,
    pipeline_run_id TEXT,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS practice_results (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    piece_id TEXT,
    pitch_accuracy REAL,
    tempo_accuracy REAL,
    velocity_score REAL,
    overall_score REAL,
    weak_spots_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS practice_plans (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    plan_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_job_id
ON pipeline_runs(job_id);

CREATE INDEX IF NOT EXISTS idx_transcriptions_job_id
ON transcriptions(job_id);

CREATE INDEX IF NOT EXISTS idx_metrics_name
ON metrics(metric_name);

CREATE INDEX IF NOT EXISTS idx_practice_results_session_id
ON practice_results(session_id);
