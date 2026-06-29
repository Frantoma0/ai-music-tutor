from app.db.database import (
    DEFAULT_DB_PATH,
    create_pipeline_run,
    create_session,
    create_transcription_record,
    create_metric_record,
    initialize_database,
    list_tables,
    list_pipeline_runs,
    get_pipeline_run,
    list_metrics,
    get_metrics_for_run,
    delete_pipeline_run_by_job_id,
    ensure_pipeline_runs_thumbnail_column,
    set_pipeline_run_thumbnail_url,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "create_pipeline_run",
    "create_session",
    "create_transcription_record",
    "create_metric_record",
    "initialize_database",
    "list_tables",
    "list_pipeline_runs",
    "get_pipeline_run",
    "list_metrics",
    "get_metrics_for_run",
    "delete_pipeline_run_by_job_id",
    "ensure_pipeline_runs_thumbnail_column",
    "set_pipeline_run_thumbnail_url",
]

from app.db.correction_persistence import (
    get_correction_run,
    init_correction_schema,
    list_correction_runs,
    persist_correction_artifacts,
)
