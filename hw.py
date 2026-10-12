import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather", "description": "工具",
        "input_schema":  {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description":"城市名稱"}
                },
                "required": ["city"]
            }
        }
]



def get_weather(city):
    return f"{city}現在是晴天,28度"
    

messages = [
    {"role": "user", "content": "台北現在天氣如何"}
]



while True:
    turns= 0
    turns = turns + 1
    print("turns =", turns)
    if turns > 10:
        print("超過10倫,強制停止")
        break

    
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1000,
        tools=tools,
        messages=messages,
    )

    print("--- stop_reason:", response.stop_reason, "---")

    if response.stop_reason != "tool_use":
        break

    messages.append({"role": "assistant", "content": response.content})

    results = []
    for block in response.content:
        if block.type == "tool_use":
            try:
                output = get_weather(block.input["city"])
            except Exception as e:
                output = f"工具執行失敗:{e}"    
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output
            })

    messages.append({"role": "user", "content": results})

for block in response.content:
    if block.type == "text":
        print("最終回答:", block.text)
for block in response.content:
    if block.type == "thinking":
        print("推理過程")
        print(block.thinking)
    
        