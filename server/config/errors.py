"""Errores de la aplicación, con mensaje en español."""


class DomainError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
