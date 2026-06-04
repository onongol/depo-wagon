def run_processing(document_id: int) -> None:
    """Thread target: run process_document with Django DB connection handling."""
    from django.db import connection

    try:
        from apps.ai_service.processing import process_document

        process_document(document_id)
    except Exception:
        pass
    finally:
        connection.close()
