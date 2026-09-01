# Pre-registration（事前登記）

> 判準來源：docs/spec/statistical-decision-tree.md
> 不可改寫由 `scripts/check_append_only.py` + pre-commit hook 強制

## 為什麼

統計檢定的效力建立在「假說先於資料」之上。事後看著結果補假說，p 值就失去意義——
不是因為算錯，而是因為那個 p 值回答的問題已經變成「在我看過的所有可能假說裡，
這一個看起來多好」，而它不是那樣算出來的。

這個目錄存在的唯一理由，是讓「假說先於資料」變成一件**可以被第三者查證**的事，
而不是一句自我聲明。

## 規則

1. **一個假說一份檔案**，檔名 `NNN-<slug>.yaml`，NNN 遞增不重用。
2. **一旦 commit 就凍結。** 不可修改、不可刪除、不可改名。pre-commit hook 會擋。
3. 判準真的要改，**開一份新的**，在 `supersedes` 欄寫明它取代了哪一份、為什麼。
   那樣讀者看得到判準變過；就地編輯會讓「事前」這兩個字失去意義。
4. 每一筆 `purpose: selection` 的 trial 都要能指回一份登記檔
   （trial 記錄的 `stat_decision.preregistration_id`）。
5. **沒有事前登記不是無效，是降級。** 依規範 §一 關卡零，事後發現的顯著結果
   一律標「探索性發現」、門檻升到 |t| ≥ 3，且需以新資料重新驗證才能升回正式假說。
   在 resolver 裡就是 `Facts(preregistered=False)`。

## 存證

`git commit` 之後打一個 GPG 簽章的 annotated tag 並 push：

```bash
git tag -s prereg/001 -m "pre-registration 001 凍結"
git push origin prereg/001
git tag -v prereg/001          # 驗章
```

推到遠端即形成第三方時間戳。對外舉證需求真的出現時再考慮 OpenTimestamps
（把 commit hash 錨定到 Bitcoin）——在那之前不值得那個複雜度。

## 怎麼寫

複製 `TEMPLATE.yaml`，逐欄填完。欄位不是裝飾：`hypothesis` 到 `falsification`
這七項對應 Arnott, Harvey & Markowitz (2019) 的 backtesting protocol；
`stat_plan` 那一段直接餵給 `validation.decision.resolve()`，所以**填完就等於
把檢定選定了**——那正是重點，你在看到任何結果之前就把檢定綁死了。

寫不出 `economic_mechanism`（誰在另一邊持續虧錢）通常代表這個訊號是從資料裡
挖出來的而不是想出來的。那不是自動否決，但它應該讓你把 `family` 誠實填成
`open_mining`。

## 檢查

```bash
python scripts/check_preregistration.py                 # 驗所有登記檔
python scripts/check_append_only.py                     # 驗沒有改寫（pre-commit 也會跑）
./scripts/install_hooks.sh                              # 安裝 hook
```
