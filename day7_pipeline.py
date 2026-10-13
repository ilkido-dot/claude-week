import anthropic

client = anthropic.Anthropic()

weather_table = {
    "台北": "陰天,22度",
    "台中": "晴天,30度",
    "高雄": "雷陣雨,27度",
    "台南": "晴天,31度",
    "花蓮": "大雨,19度",
}


def get_weather(city):
    return f"{city}現在是{weather_table[city]}"


cities = ["台北", "台中", "高雄", "台南", "花蓮"]

weather_data = {}
for city in cities:
    weather_data[city] = get_weather(city)

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=16000,
    messages=[{"role": "user",
               "content": f"根據以下天氣資料,告訴我哪裡最適合出遊:{weather_data}"}]
)
print("input_tokens:", response.usage.input_tokens, "output_tokens:", response.usage.output_tokens)

for block in response.content:
    if block.type == "text":
        print("最終回答:", block.text)
