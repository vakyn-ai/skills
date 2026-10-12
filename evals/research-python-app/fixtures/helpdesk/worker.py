"""Poll the inbox and process each new email."""

import time

from .config import INBOX_POLL_SECONDS, URGENT_AT
from .inbox import fetch_new, mark_spam, page_on_call, save_ticket
from .replies import draft_reply
from .triage import is_spam, rate_urgency, route_ticket


def handle(email) -> None:
    if is_spam(email.body):
        mark_spam(email)
        return
    team = route_ticket(email.body)
    urgency = rate_urgency(email.body)
    reply = draft_reply(email.body, team)
    save_ticket(email, team=team, urgency=urgency, draft=reply)
    if urgency >= URGENT_AT:
        page_on_call(team, email)


def main() -> None:
    while True:
        for email in fetch_new():
            handle(email)
        time.sleep(INBOX_POLL_SECONDS)


if __name__ == "__main__":
    main()
