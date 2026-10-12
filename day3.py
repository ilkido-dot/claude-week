import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather", "description": "查詢某個城市現在的天氣",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名稱"}
            },
            "required": ["city"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1000,
    tools=tools,
    messages=[{"role": "user", "content": "台北天氣如何"}],
)

print("stop_reason:", response.stop_reason)

for block in response.content:
    if block.type == "text":
        print("模型說:", block.text)
    elif block.type == "tool_use":
        print("要用工具:", block.name)
        print("參數:", block.input)
        
print(response)        