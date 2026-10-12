"""Ask every branch's question in one request; read only the branch the code takes. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

TEAMS = {
    "billing": "Charges, invoices, refunds and failed payments",
    "access": "Sign-in, passwords, 2FA and who can use the account",
    "product": "Bugs and how-to questions about the product",
    "other": "Anything that is not a support request for these teams",
}
BILLING_TOPICS = {
    "refund": "Wants money back for a charge already made",
    "invoice_fix": "An invoice or receipt has wrong details or a wrong amount",
    "payment_failed": "A card or payment was declined or expired",
    "plan_change": "Wants to upgrade, downgrade or cancel",
    "not_billing": "The message is not about billing",
}
BUG_LEVELS = [
    "No bug, or a cosmetic one: work goes on as normal",
    "Slows work down, with a workaround",
    "Blocks one task, no workaround",
    "Blocks the whole team's work",
]
QUESTIONS = {
    "team": Choice(instructions="Which team should handle the customer's message?", criteria=TEAMS),
    # Branch questions: each states its premise, because no question sees another's answer.
    "billing_topic": Choice(
        instructions="Suppose the customer's message is about billing. Which billing topic is it about? "
                     "If it is not about billing at all, pick not_billing.",
        criteria=BILLING_TOPICS),
    "locked_out_everyone": Noul(
        instructions="Suppose the customer's message is about signing in. Does it say that nobody on the "
                     "customer's team can sign in, rather than one person?"),
    "bug_blocks_work": Score(
        instructions="Suppose the customer's message reports a bug. How much does the bug stop the customer's work?",
        criteria=BUG_LEVELS),
}
MIN_CONFIDENCE = 0.6  # starting value; set yours with check

client = TypeSafeClient(timeout=30.0)


def handle(message: str, plan: str) -> str:
    r = client.system_one(state={"plan": plan, "message": message}, questions=QUESTIONS)
    team = r.choices["team"]
    if team.choice not in TEAMS or team.choice == "other" or team.confidence < MIN_CONFIDENCE:
        return "triage_queue"
    # Read only the answer for the branch taken. The others answered a premise that is false here.
    if team.choice == "billing":
        topic = r.choices["billing_topic"]
        if topic.choice not in BILLING_TOPICS or topic.choice == "not_billing" or topic.confidence < MIN_CONFIDENCE:
            return "billing_queue"
        return f"billing/{topic.choice}"
    if team.choice == "access":
        return "access/urgent" if r.nouls["locked_out_everyone"].noul >= 0.8 else "access_queue"
    level = r.scores["bug_blocks_work"].score  # probability-weighted level, 0 to 3
    return "product/urgent" if level >= 2.5 else "product_queue"


for msg in [
    "Our company card expired last week and the renewal payment failed. How do I add a new card before we lose access?",
    "Since this morning nobody on our team can sign in, the login page just reloads. We have a client demo at 3pm.",
    "Exporting a report to PDF crashes the app every time, so none of us can send the monthly reports to clients.",
]:
    print(f"{handle(msg, 'team, 12 seats'):24} | {msg[:60]}")
