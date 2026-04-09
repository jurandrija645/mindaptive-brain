from dataclasses import dataclass, field


@dataclass
class EmailMessage:
    """Normalized email message passed between Gmail client and tools."""
    id: str
    thread_id: str
    subject: str
    from_email: str
    from_name: str
    to: str
    date: str
    body_text: str
    body_html: str
    labels: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"EmailMessage(id={self.id}, from={self.from_email}, subject={self.subject!r})"
