"""School settings (singleton row id=1)."""
from app.models.requests import SchoolSettings
from app.repositories import settings_repository


def get_settings() -> dict:
    """Returns the saved settings, or model defaults if nothing has been
    saved yet (frontend always gets a populated shape)."""
    saved = settings_repository.get()
    if not saved:
        return SchoolSettings().model_dump()
    return saved


def save_settings(settings: SchoolSettings) -> None:
    settings_repository.upsert(
        school_name=settings.school_name,
        school_name_ur=settings.school_name_ur,
        address=settings.address,
        address_ur=settings.address_ur,
        logo_base64=settings.logo_base64,
        accent_color=settings.accent_color,
    )
