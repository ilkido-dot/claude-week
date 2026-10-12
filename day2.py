
import anthropic

client = anthropic.Anthropic()

messages = []

while True:
    user_input = input("你: ")
    if user_input == "bye":
        break

    messages.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1000,
        messages=messages,
    )

    reply = response.content[0].text
    print("Claude:", reply)
    print(response)
    messages.append({"role": "assistant", "content": reply})
