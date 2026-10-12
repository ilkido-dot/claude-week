

import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": "你好 ,請告訴我台北市明天的天氣。"}
    ],
)
print(response.content[0].text
)
