import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather", "description": "查詢某個城市現在的天氣",
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
    {"role": "user", "content": "請依序查詢台北、台中、高雄、台南、花蓮的天氣,一次只查一個城市,最後告訴我哪裡最適合出遊。"}
]

turns= 0


while True:
    turns = turns + 1
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
    print("input_tokens:", response.usage.input_tokens, "output_tokens:", response.usage.output_tokens)

    if response.stop_reason != "tool_use":
        break

    messages.append({"role": "assistant", "content": response.content})

    results = []
    for block in response.content:
        if block.type == "tool_use":
            print("申請單:", block.id, block.name, block.input)
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
    # 刻意保留的對照組：只留最近兩組往返,agent 會忘記自己查過哪些城市,
    # 重複查詢,並在最後捏造沒查到的資料。不會報錯。詳見 README。
    if len(messages) > 5:
        messages = [messages[0]] + messages[-4:]
    用了工具 = False
    for block in response.content:
        if block.type == "tool_use":
           用了工具 = True
    print(f"這輪有沒有用工具:{用了工具}")

for block in response.content:
    if block.type == "text":
        print("最終回答:", block.text)
for block in response.content:
    if block.type == "thinking":
        print("推理過程")
        print(block.thinking)
