"""Domain exceptions raised by services.

Routes catch these and map them to the appropriate HTTP status — services
themselves don't know about HTTP. New exception classes should be added
here so they're discoverable in one place (CLAUDE.md §2).
"""


class ResultsValidationError(Exception):
    """Raised by result_service.import_results when an uploaded results
    file has structural or content issues that prevent saving.

    The `errors` attribute carries a list of {"row": int, "issue": str}
    dicts so the route can pass the whole batch straight back to the
    frontend in one response — teachers fix all the bad cells at once
    instead of upload-edit-upload looping per error.
    """

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s) in results file")


class AIGenerationFailed(Exception):
    """Raised by ai_service when an AI provider call fails (HTTP error,
    timeout, network drop, or unparseable response). The message is already
    user-facing and sanitized — it never contains the request URL or API key,
    so the route can surface it straight to the teacher (CLAUDE.md §2, §6)."""


class DuplicateSyllabusTopic(Exception):
    """Raised by syllabus_repository.insert when a topic with the same
    (subject, grade, unit_no, subtopic_title, page_no) key already exists.
    Importers catch this to skip duplicates on re-import — the repository
    translates the underlying UNIQUE-constraint violation so callers never
    touch sqlite3 directly (CLAUDE.md §2)."""


class PdfConversionFailed(Exception):
    """Raised by export_service when the docx->PDF step fails — typically
    because LibreOffice (soffice) isn't installed/found on the server, or the
    conversion subprocess errored or timed out. The route maps this to 502
    (upstream tool failure) with the message surfaced to the admin."""
