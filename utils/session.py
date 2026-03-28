class Session:
    """Simple in-memory session. Holds the currently logged-in user."""
    _user: dict | None = None

    @classmethod
    def set(cls, user: dict) -> None:
        cls._user = user

    @classmethod
    def get(cls) -> dict | None:
        return cls._user

    @classmethod
    def clear(cls) -> None:
        cls._user = None

    @classmethod
    def is_admin(cls) -> bool:
        return cls._user is not None and cls._user.get("role") == "admin"

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls._user is not None
