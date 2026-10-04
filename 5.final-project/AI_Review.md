# AIASE 2026 期末專案 — AI 評閱回饋

**GitHub ID:** `MelanieShih`

## 成績摘要

| 軌道 | 分數 |
|---|---|
| Basic Track(text2sql) | 28.0 / 30 |
| Pairwise Track(角色:Code Author) | 7.5 / 10 |
| Open Track(設計 40% + 執行 60%) | 52.6 / 100 |
| 基礎加分(nano 第二參考) | 6.0 / 30 |
| Pairwise 加分(nano CA) | 3.75 / 10 |
| **Project 總分** | **66.48** |

- 額外榮譽 / 加分:—
- 評分重試次數:Basic **0 次**(一次到位);Pairwise 採統一重試政策(no-result 重試 1 次、flaky 受害者重評取最佳),未逐人記錄次數。

## Open Track 計分明細(透明拆解)

Open 總分 = **設計審查 × 40% + 實跑驗證(60 分制)** = **52.6 / 100**

**① 設計審查(占 40 分)= 32.6 分**(LLM 閱讀你的 skill 評分:81.5/100)

- **可驗證性:9/10** — evaluate_repair.py 直接對 buggy_code 與 repaired_code 執行相同測試集，以 exec() 呼叫並比對回傳值，結果完全由 deterministic script 計算；AIASE_RESULT_PATH 合約清楚，無需人工判讀。唯一小缺點是 exec() 在無沙盒環境下執行學生程式碼存在安全疑慮（雖有 forbidden import 檢查），略降可信度。
- **完整與清晰:9/10** — OPEN_TRACK.md、SKILL.md、scripts/run.py、scripts/evaluate_repair.py 均完整提交，涵蓋 payload schema、metric 定義、pass condition、失敗模式及三組 dev scenario；dev_set JSON 檔案本體未見於素材中但已在 OPEN_TRACK.md 明確列路徑，略扣 1 分。
- **方法正確性:8/10** — binary_search 的 buggy/repaired 對（`while left < right` → `while left <= right`）確實反映真實 off-by-one bug，測試案例覆蓋空陣列、首尾與找不到目標，邏輯上正確；evaluate_payload 中 `fully_fixed` 在 total_tests==0 時返回 False 亦屬合理保護。小問題：compute_sloc 優先呼叫外部 radon，若 radon 未安裝 fallback 計算空白行+註解行方式仍正確但與 radon SLOC 定義可能有輕微差異。
- **失敗模式/穩健:7/10** — 設計了 bug-family level 的 fallback sample（_samples_for_known_task），對已知 task 型別有硬編碼備用測試集，且明確說明 staff perturbation 情境；然而若 staff 換用完全不在已知五種 family 內的題目，sample_source 將為 'none'，total_tests=0，導致 improved 永遠為 False，robustness 有明確邊界限制。
- **工程嚴謹度:8/10** — metric 定義（repair_delta、improved、fully_fixed、pass_rate）清晰且數學上無歧義；import 檢查用 AST walk 而非字串比對，LoC 有 radon/fallback 雙層；SKILL.md 中 procedure 步驟、最多 2 次 repair loop 限制及 pitfalls 均有明確說明，整體設計嚴謹。
- **難度與原創:7/10** — Code repair with deterministic execution-based evaluation 在 AIASE 課程脈絡中屬於具體且有實務意義的選題，設計了 bug-family 分類與 fast repair patterns 概念；相較於一般 code generation skill，多了 buggy vs repaired 的 delta 比較機制，具一定獨特性，但整體技術深度屬中等，未涉及更複雜的語意等價驗證或 mutation testing。

**② 實跑驗證(占 60 分)= 20 分**
- 可實際執行、輸出合法:✓ +20(滿 20)
- **確定性**(同輸入跑兩次結果一致):✗ +0(滿 25)
- 對自宣告 gold 正確:✗ +0(滿 15)

**執行診斷:** **確定性未通過**:同一輸入連跑兩次,輸出在 `repair_summary` 欄位不同——多因 skill 讓 LLM 直接生成答案(如 regex/測試案例),建議改由確定性腳本計算最終答案,讓輸出可逐字重現。 **對 gold 未通過**:輸出與你在 scenario 宣告的預期 gold 不一致(可檢查輸出格式/欄位是否與宣告一致)。

> 為何採「設計 + 實跑」雙軌:對齊公告「open in design, strict in verification」——設計分肯定你的構想,實跑分檢驗它**真的可重現、可驗證**(確定性 / 對得上自己的 gold)。

## 評語

你的 Basic Track 表現相當亮眼，gemini 模型拿到 **28/30**（93.3 分），整體 SQL 品質扎實。Pairwise 身為 Code Author 也通過 6/8 題（7.5/10），大多數題目的測試設計有效。Open Track 設計審查拿到 **81.5/100**，核心概念——用 `evaluate_repair.py` 確定性執行取代模型自評——十分到位，`repair_delta` 等 metric 數學定義清晰，工程結構完整，選題也具實務意義，這些都是值得肯定的地方。

1. **Open Track 確定性與可重現性**：兩次執行結果不一致，且 `dev_set JSON` 未隨素材提交。建議固定隨機種子並將 dev_set 一併納入 repo，讓評估流程可完整重現。

2. **Fallback 覆蓋範圍**：目前五種已知 bug family 以外的題目會因 fallback sample 為空而評估失效。建議加入通用型 fallback 邏輯，避免未知類型題目直接造成空結果。

3. **exec() 安全機制**：裸露的 `exec()` 執行有安全風險（已觸發靜態掃描標記）。建議導入 subprocess 沙盒或資源限制，這也能同步提升穩健性分項的分數。

---
> 本評閱由 AIASE 2026 自動化評分系統產生,供學習回饋參考。
> 方法對齊課程公告精神「**open in design, strict in verification**」:
> Open Track 以 **LLM 設計審查(40%)+ 確定性實跑驗證(60%)** 評分;Basic 對齊權威 `run_dev.py`;Pairwise 以 sandbox 跑題與 bug 偵測 F1 計分。
> 各軌分數與權重以課程最終公告為準;加分項獨立計算。
