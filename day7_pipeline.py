import anthropic

client = anthropic.Anthropic()




def get_weather(city):
    return f"{city}現在是晴天,28度"
    

messages = [
    {"role": "user", "content": "請依序查詢台北、台中、高雄、台南、花蓮的天氣,一次只查一個城市,最後告訴我哪裡最適合出遊。"}
]

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

                
