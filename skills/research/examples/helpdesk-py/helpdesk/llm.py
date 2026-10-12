from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY


def ask(model: str, system: str, user: str, **kwargs) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return resp.choices[0].message.content.strip()
