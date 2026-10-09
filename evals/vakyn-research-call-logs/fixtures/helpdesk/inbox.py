"""Thin wrapper around the mail server and the ticket database (no chat-model calls here)."""

from dataclasses import dataclass


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str


def fetch_new() -> list[Email]:
    raise NotImplementedError("connect to IMAP")


def mark_spam(email: Email) -> None:
    raise NotImplementedError


def save_ticket(email: Email, *, team: str, urgency: int, draft: str) -> None:
    raise NotImplementedError


def page_on_call(team: str, email: Email) -> None:
    raise NotImplementedError
