# claude-week

我學 Claude API 時的練習：用 Anthropic Messages API 從零寫一個會呼叫工具的 agent，沒有用 framework，再把同一個任務改寫成 pipeline，比較兩種寫法。

## 實驗目的：agent or pipeline？

測試什麼情況該讓模型決定下一步（agent），什麼情況該把流程寫死（pipeline）。

同一個任務做兩個版本：查五個城市的天氣，判斷哪裡最適合出遊。

| | `day7.py`（agent） | `day7_pipeline.py`（pipeline） |
|---|---|---|
| 誰決定查哪個城市 | 模型 | 程式裡寫死的 `cities` 清單 |
| API 呼叫次數 | 6 | 1 |
| 累計 input tokens | 4,444 | 127 |
| 工具定義 | 每一輪都送 | 不送 |
| 工具出錯時 | 包成 `tool_result` 回傳，程式繼續跑 | `for` 迴圈拋出例外，整批停止 |

兩個檔案用同一份 `weather_table`，五個城市的天氣都不一樣，數字可以直接比。agent 的 6 次呼叫是 5 次查天氣加 1 次總結，input tokens 是每一輪的實測值加起來：498、639、725、817、907、858。

每次跑出來的數字會差一點。模型每次回覆的長度不同，會算進下一輪的 input，例如第 2 輪兩次送出的 messages 結構相同，input_tokens 一次是 694，一次是 639。表上是其中一次的值。

城市清單是固定的，這個任務用不到 agent 的彈性，卻多付了 35 倍的 input tokens。我之後的選法：執行前就知道步驟，寫成 pipeline；要看到中間結果才能決定下一步，才用 agent。後來做 B2B 詢價信自動化系統（[n8n-auto-quote](https://github.com/ilkido-dot/n8n-auto-quote)）時，我就照這個選了 pipeline。

## 遇到的問題

### 截斷太多，agent 忘了查過哪些城市

`day6.py` 為了省 context，只留最初的指令和最近兩組工具往返：

```python
messages = [messages[0]] + messages[-4:]
```

這行不會讓 API 回錯誤。每一輪加兩則（模型的 `tool_use` 和工具的 `tool_result`），`-4` 是偶數，留下的是完整的兩組，所以程式照樣跑完，要看結果才看得出問題。

第三輪之後，`messages` 停在 5 則。模型只記得最後兩個城市，一直重查查過的，5 個城市查了 8 次：

```
turn 1  台北           turn 5  台南
turn 2  台中           turn 6  花蓮
turn 3  高雄           turn 7  台中  ← 重複
turn 4  台北 ← 重複   turn 8  高雄  ← 重複
```

`day6.py` 沒有 `weather_table`，`get_weather` 對每個城市都回「晴天,28度」。模型最後的總結：

| 城市 | 模型寫的 | 工具回傳的 | |
|---|---|---|---|
| 台北 | 多雲 26°C | 晴天 28度 | 編的 |
| 台中 | 晴天 28°C | 晴天 28度 | 對 |
| 高雄 | 晴天 28°C | 晴天 28度 | 對 |
| 台南 | 晴天 29°C | 晴天 28度 | 編的 |
| 花蓮 | 多雲 24°C | 晴天 28度 | 編的 |

寫對的兩個城市是最後兩輪查的，還留在 context 裡。另外三個城市的結果已經截掉了，模型沒有說不知道，自己編了天氣。

兩個版本放在一起比：

| | `day6.py`（留最近 2 組往返） | `day7.py`（留最近 4 組） |
|---|---|---|
| API 呼叫 | 9 次 | 6 次 |
| 累計 input tokens | 6,607 | 4,444 |
| 工具呼叫 | 8 次（5 個城市） | 5 次 |
| 答案 | 5 個城市編了 3 個 | 全對 |

重查用掉的 tokens 比截斷省下的多，`day6.py` 的總成本是 `day7.py` 的 1.5 倍。我把 `day6.py` 留著不修，當對照組。

### 印 len(tools) 檢查不到工具有沒有送出去

想確認工具定義有沒有送出去，我一開始寫：

```python
print(len(tools))   # 印出 1
```

把 `tools=tools` 註解掉，它還是印 1。這行只看得到 `tools` 這個 list 存在，看不到這一輪有沒有把它送出去。我改看 `response.usage.input_tokens`：有送是 488，沒送是 60。

### try/except 把 NameError 藏起來了

重構時，我把 `weather_table` 從 `day7.py` 搬到 `day7_pipeline.py`，但 `day7.py` 的 `get_weather()` 還在用它。

`python -m py_compile day7.py` 會通過，因為函式裡用到的名字，要等函式被呼叫時才會去找。一呼叫就是 NameError，錯誤指著 `get_weather` 裡的那一行，少掉的定義卻在另一個檔案：

```
  File "day7.py", line 2, in get_weather
    return f"{city}現在是{weather_table[city]}"
                          ^^^^^^^^^^^^^
NameError: name 'weather_table' is not defined
```

`try/except` 又把這個 NameError 接住了：

```python
try:
    output = get_weather(block.input["city"])
except Exception as e:
    output = f"工具執行失敗:{e}"
```

程式沒有中斷。模型收到「工具執行失敗:name 'weather_table' is not defined」，照樣寫出一段看起來正常的回覆。唯一看得出問題的是 `查到的天氣` 這個變數，它是空的 `{}`。修正在 commit `5f1a7d6`。

### 每輪的則數對不上：截斷的 off-by-one

我每一輪印出 `len(messages)`：

```
1 → 3 → 5 → 8 → 9 → 9
```

每輪加兩則，5 的下一個應該是 7。原因在修正前 `day7.py` 的這兩行：

```python
if len(messages) > 5:
    messages = [messages[0]] + messages[-8:]
```

`len` 是 7 的時候，`messages[-8:]` 湊不到 8 則，會回傳全部 7 則，前面再加上 `messages[0]`，第一則就重複了。門檻設 5、切片切 8，兩個數字對不上，門檻要設成 `> 8` 才不會重疊。

影響不大，只有第 4 輪多送了一份重複的指令，下一輪截斷時就清掉了。修好之後是 `1 → 3 → 5 → 7 → 9 → 9`。

## 工具結果另外存一份

`day7.py` 執行工具時，同時把結果存進程式自己的變數：

```python
output = get_weather(block.input["city"])
查到的天氣[block.input["city"]] = output
```

結果只放在 `messages` 裡的話，一截斷就沒了，程式自己也拿不到。後面要拿來算的資料，我會在模型之外另外存一份。上面那次 NameError，也是看到這個變數是空的才發現。

<details>
<summary>檔案地圖</summary>

| 檔案 | 內容 |
|---|---|
| `day1.py`–`day5_thinking.py` | 基礎練習：第一次呼叫 API、多輪對話、工具定義、agent loop、adaptive thinking |
| `day6.py` | 每輪印出 `stop_reason`、`messages` 長度、tokens；刻意保留截斷的錯誤 |
| `day7.py` | agent 版：五個城市，工具結果同時存進程式變數 `查到的天氣` |
| `day7_pipeline.py` | pipeline 版：同一個任務，流程寫死，1 次呼叫 |

</details>

<details>
<summary>怎麼跑</summary>

```cmd
pip install anthropic
set ANTHROPIC_API_KEY=你的key
py day7.py
py day7_pipeline.py
```

PowerShell 用 `$env:ANTHROPIC_API_KEY="你的key"`；macOS、Linux 用 `export ANTHROPIC_API_KEY=你的key`，執行時用 `python3`。

`.env` 和 `__pycache__` 已經寫在 `.gitignore`，repo 裡沒有任何金鑰。

</details>
