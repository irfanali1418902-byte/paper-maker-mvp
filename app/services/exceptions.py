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


class PdfConversionFailed(Exception):
    """Raised by export_service when the docx->PDF step fails — typically
    because LibreOffice (soffice) isn't installed/found on the server, or the
    conversion subprocess errored or timed out. The route maps this to 502
    (upstream tool failure) with the message surfaced to the admin."""
