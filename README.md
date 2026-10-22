# claude-week

不用任何 framework，用 Anthropic Messages API 從零手刻一個會呼叫工具的 agent，
並把同一個任務改寫成 pipeline，實測兩種架構的成本差異。

---

## 這個 repo 在回答什麼問題

> 什麼時候該讓模型自己決定下一步（agent），什麼時候該把流程寫死（pipeline）？

同一個任務 —— **查五個城市的天氣，判斷哪裡最適合出遊** —— 用兩種架構各實作一次：

| | `day7.py`（agent） | `day7_pipeline.py`（pipeline） |
|---|---|---|
| 誰決定查哪個城市 | 模型 | 程式寫死 `cities` 清單 |
| API 呼叫次數 | **6 次** | **1 次** |
| 累計 input tokens | **4,444** | **127** |
| 工具 schema 送出 | 每一輪都送 | 不送 |
| 工具出錯時 | 包成 `tool_result` 回傳，程式不中斷 | `for` 迴圈直接拋例外，整批中止 |

兩個檔案用的是**同一份 `weather_table`**（五個城市各不同天氣），所以這組數字是對等比較。
agent 的 6 次＝5 次工具查詢 + 1 次總結；input tokens 是每一輪實測值的總和（498 / 639 / 725 / 817 / 907 / 858）。

這組數字每次跑都會差一點 —— 模型每次回應的長度不同，會累加到下一輪的 input。
實測例子：第 2 輪兩次送出的 messages 結構完全相同，input_tokens 卻分別是 694 和 639。
所以這裡列的是單次實測值，不是定值。

**結論（也是我的判斷標準）：**
路徑在執行前不確定 —— 有分支，或次數／對象不確定 —— 才用 agent；
否則寫死，就算中間有用到 LLM。

上面這個任務的城市清單是**固定的**，所以它根本不該是 agent。
多付的 35 倍 token 買的是「我不需要的彈性」。

---

## 四個真的撞到的失敗

這些不是讀來的，是跑出來的。

**1. 截斷得太兇 → agent 失憶 → 重複查詢 + 捏造答案**

`day6.py` 為了省 context 做了截斷，只留「最初的指令 + 最近兩組工具往返」：

```python
messages = [messages[0]] + messages[-4:]
```

我一開始以為這會把 `tool_use` 跟它的 `tool_result` 切開、導致 API 退 400。
**實測後發現不是** —— `-4` 是偶數，切片永遠從 `tool_use` 開始，配對是完整的。

真正發生的事更難發現。`messages 則數` 從第三輪之後永遠卡在 5，
模型只記得最後兩個城市，所以不斷重查已經查過的：

```
turn 1  台北           turn 5  台南
turn 2  台中           turn 6  花蓮
turn 3  高雄           turn 7  台中  ← 重複
turn 4  台北 ← 重複   turn 8  高雄  ← 重複
```

5 個城市，它查了 8 次。

**但最嚴重的是最終答案。** `day6.py` 的 `get_weather` 對每個城市都回傳同一句
「晴天,28度」（它沒有 `weather_table`）。它的總結卻是：

| 城市 | 它報告的 | 工具實際回傳 | |
|---|---|---|---|
| 台北 | 多雲 26°C | 晴天 28度 | ❌ 捏造 |
| 台中 | 晴天 28°C | 晴天 28度 | ✅ |
| 高雄 | 晴天 28°C | 晴天 28度 | ✅ |
| 台南 | 晴天 29°C | 晴天 28度 | ❌ 捏造 |
| 花蓮 | 多雲 24°C | 晴天 28度 | ❌ 捏造 |

對的那兩個，正好是最後兩輪查的、還留在 context 裡的。
被截斷丟掉的三個，**模型沒有說「我不知道」，它編了一個看起來很合理的答案**。

而且截斷得更兇反而更貴：

| | `day6.py`（只留最近 2 組往返） | `day7.py`（留最近 4 組） |
|---|---|---|
| API 呼叫 | 9 次 | 6 次 |
| 累計 input tokens | 6,607 | 4,444 |
| 工具呼叫 | 8 次（5 個城市） | 5 次 |
| 答案正確性 | 5 個裡 3 個是假的 | 全對 |

省 context 是為了省錢，結果 agent 重做了工作，總成本反而高 1.5 倍。

`day6.py` 刻意保留這個錯誤作為對照組。學到的是：
**沒有錯誤訊息不代表沒有錯。** 400 你一定會發現；這種不會。

**2. 用錯的方式檢查，會得到假的安心**

想確認工具有沒有送出去，一開始寫：

```python
print(len(tools))   # 印出 1
```

但把 `tools=tools` 註解掉之後，它**還是印 1** —— 因為它量的是「這個 list 存不存在」，
不是「這一輪有沒有把它送出去」。

改成看 `response.usage.input_tokens`（有送 488 / 沒送 60），
或在迴圈裡用旗標記錄實際有沒有出現 `tool_use` block。

**3. 爆炸的位置不是真正的原因，而且它還被藏起來了**

重構時我把 `weather_table` 從 `day7.py` 搬到 `day7_pipeline.py`，
但 `day7.py` 的 `get_weather()` 還在用它。這個 bug 有三層偽裝。

**第一層：語法檢查說沒問題。**

```
python -m py_compile day7.py   →  OK
```

`def` 只是把函式存起來，不檢查裡面用到的名字 —— 要等真的呼叫才去找。

**第二層：真的呼叫了，錯誤卻指向函式內部。**

```
  File "day7.py", line 2, in get_weather
    return f"{city}現在是{weather_table[city]}"
                          ^^^^^^^^^^^^^
NameError: name 'weather_table' is not defined
```

它指著用到名字的那一行，真正的原因卻是**另一個檔案少了一個定義**。

**第三層：這個 NameError 被 `try/except` 吞掉了。**

```python
try:
    output = get_weather(block.input["city"])
except Exception as e:
    output = f"工具執行失敗:{e}"
```

程式不會中斷。模型收到的是「工具執行失敗:name 'weather_table' is not defined」，
然後它會照樣生出一段看起來正常的回覆。

唯一會露餡的地方是 `查到的天氣` 這個變數 —— 它會是空的 `{}`。
這就是下面「資料落地」那段的用處。

修正紀錄在 commit `5f1a7d6`。

**4. 觀測數字對不上 → 找出截斷邏輯的 off-by-one**

每一輪印 `len(messages)`，實測出來是：

```
1 → 3 → 5 → 8 → 9 → 9
```

每輪會 append 兩則（assistant 的回應 + tool_result），所以 5 的下一個應該是 7，不是 8。

原因在這行（修正前的 `day7.py`）：

```python
if len(messages) > 5:
    messages = [messages[0]] + messages[-8:]
```

當 `len` 是 7，`messages[-8:]` 取不到 8 則，會把**全部 7 則都回傳**，
再加上前面手動補的 `messages[0]` → 第一則被複製成兩份。

門檻設 5、切片切 8，兩個數字不匹配。門檻要 `> 8` 以上才不會重疊。

實際代價很小：只有第 4 輪多送了一份重複的指令，下一輪截斷時它剛好被清掉。
修好前後軌跡從 `1, 3, 5, 8, 9, 9` 變成 `1, 3, 5, 7, 9, 9`。

重點不在省了多少 —— **在追出根因之前，我不可能知道它只有這麼小。**
沒把 `len(messages)` 印出來，就永遠不會發現它存在。

---

## 檔案地圖

| 檔案 | 在示範什麼 |
|---|---|
| `day1.py` | 最小可運行的 API 呼叫 |
| `day2.py` | 多輪對話 —— 自己維護 `messages`，模型本身沒有記憶 |
| `day3.py` | 送出工具定義，觀察 `stop_reason` 變成 `tool_use` |
| `day4.py` | 完整 agent loop：執行工具 → 包成 `tool_result` → 送回去 |
| `day5_thinking.py` | 開 adaptive thinking，讀 `thinking` block |
| `day6.py` | 可觀測性（每輪印 `stop_reason` / `messages` 長度 / tokens）＋ 刻意保留的 truncation 錯誤 |
| `day7.py` | agent 版本：五城市、工具結果同時落地到程式變數 `查到的天氣` |
| `day7_pipeline.py` | pipeline 版本：同一個任務，流程寫死，1 次呼叫 |

---

## 一個容易被忽略的設計：資料落地

`day7.py` 在執行工具的同時，把結果存進自己的變數：

```python
output = get_weather(block.input["city"])
查到的天氣[block.input["city"]] = output
```

如果只把結果丟回 `messages`，資料就只活在對話歷史裡 ——
一旦做 truncation 就被砍掉了，程式自己拿不到。
要後續運算的資料，必須在經過模型之外**自己留一份**。

---

## 怎麼跑

```cmd
pip install anthropic
set ANTHROPIC_API_KEY=你的key
py day7.py
py day7_pipeline.py
```

PowerShell 用 `$env:ANTHROPIC_API_KEY="你的key"`；
macOS / Linux 用 `export ANTHROPIC_API_KEY=你的key`，執行用 `python3`。

`.env` 與 `__pycache__` 已在 `.gitignore`，repo 內無任何金鑰。
