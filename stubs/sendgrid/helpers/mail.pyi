from typing import Any, List, Union

class Mail:
    def __init__(
        self,
        from_email: str,
        to_emails: list,
        subject: str,
        plain_text_content: str,
    ) -> None: ...
    def add_attachment(self, attachment: Attachment) -> None: ...

class Attachment:
    def __init__(
        self,
        file_content: "FileContent",
        file_name: "FileName",
        file_type: "FileType",
        disposition: "Disposition",
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
    def send(self, message: Mail) -> Any: ...
