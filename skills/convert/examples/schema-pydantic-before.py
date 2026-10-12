"""BEFORE: ticket triage with OpenAI structured outputs and a Pydantic model.

The chat model fills the whole object: three decisions (category, urgent, sentiment) and one
piece of text (summary). schema_pydantic_after.py is the same app after the conversion.

pip install openai pydantic
"""

from enum import Enum

from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI()


class Category(str, Enum):
    billing = "billing"
    shipping_label = "shipping_label"
    tracking = "tracking"
    account = "account"


class TicketTriage(BaseModel):
    category: Category = Field(
        description="billing: charges, invoices, plan changes and refunds. "
        "shipping_label: buying, printing or voiding a label. "
        "tracking: where a parcel is, late or lost parcels. "
        "account: sign-in, users and shop connections."
    )
    urgent: bool = Field(
        description="True when parcels cannot ship today because of the problem, "
        "or money is being taken by mistake right now."
    )
    sentiment: int = Field(ge=1, le=5, description="How the customer feels: 1 = angry, 3 = neutral, 5 = delighted.")
    summary: str = Field(description="One sentence for the support agent: the problem and what the customer wants.")


def triage(ticket_text: str) -> TicketTriage:
    resp = client.chat.completions.parse(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Triage this support ticket for Parcelo, a shipping-label app."},
            {"role": "user", "content": ticket_text},
        ],
        response_format=TicketTriage,
    )
    return resp.choices[0].message.parsed
