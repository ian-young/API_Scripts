from sendgrid.helpers.mail import Mail
from typing import Any

class Attachment:
    def __init__(
        self,
        file_content: FileContent,
        file_name: str,
        file_type: str,
        disposition: str,
    ) -> None: ...

class FileContent:
    def __init__(self, data: bytes) -> None: ...

class FileName:
    def __init__(self, name: str) -> None: ...

class FileType:
    def __init__(self, file_type: str) -> None: ...

class Disposition:
    def __init__(self, disposition: str) -> None: ...

class SendGridAPIClient:
    def __init__(self, api_key: str) -> None: ...
    def send(self, message: Mail) -> Response: ...

class Response:
    @property
    def status_code(self) -> int: ...
