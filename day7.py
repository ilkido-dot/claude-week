import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather", "description": "查詢某個城市現在的天氣",
        "input_schema":  {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description":"工具"}
                },
                "required": ["city"]
            }
        }
]



weather_table = {
    "台北": "陰天,22度",
    "台中": "晴天,30度",
    "高雄": "雷陣雨,27度",
    "台南": "晴天,31度",
    "花蓮": "大雨,19度",
}


def get_weather(city):
    return f"{city}現在是{weather_table[city]}"
    

messages = [
    {"role": "user", "content": "請依序查詢台北、台中、高雄、台南、花蓮的天氣,一次只查一個城市,最後告訴我哪裡最適合出遊"}
]

turns= 0

查到的天氣 = {}

while True:
    turns = turns + 1
    print("turns =", turns)
    if turns > 10:
        print("超過10倫,強制停止")
        break

    
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=16000,
        tools=tools,
        messages=messages,
    )

    print("--- stop_reason:", response.stop_reason, "---")
    print("messages 則數:", len(messages))
    print("input_tokens:", response.usage.input_tokens)

    if response.stop_reason != "tool_use":
        break

    messages.append({"role": "assistant", "content": response.content})

    results = []
    用了工具 = False

    for block in response.content:
        if block.type == "tool_use":
            用了工具 = True
            try:
                output = get_weather(block.input["city"])
                查到的天氣[block.input["city"]] = output
            except Exception as e:
                output = f"工具執行失敗:{e}"    
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output
            })
    print("這倫有沒有用工具:",用了工具)
    messages.append({"role": "user", "content": results})
    
    if len(messages) > 5:
        messages = [messages[0]] + messages[-8:]

for block in response.content:
    if block.type == "text":
        print("最終回答:", block.text)
for block in response.content:
    if block.type == "thinking":
        print("推理過程")
        print(block.thinking)
print("我自己存的資料:", 查到的天氣)
        