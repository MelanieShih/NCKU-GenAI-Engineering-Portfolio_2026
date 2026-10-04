# Demo

本資料夾提供本作業的 demo 影片與截圖說明，目的是讓助教快速確認本專案已完成的功能、實際執行情況，以及這些結果與 `README.md`、`REPORT.md` 之間的對應關係。

本 demo 主要展示以下內容：

- 任務一核心功能與 `pytest -q` 測試通過
- pure BM25 benchmark
- hybrid retrieval benchmark
- `/recall`、`/forget`
- Privacy Filter
- Time Decay
- Pi bridge 與 Python memory system 的整合
- 跨 session 的記憶注入效果

---

## 影片觀看方式

本次 demo 影片已上傳至 Google Drive。  
**建議直接點擊以下連結觀看影片**，而不是依賴 repo 內的本地影片檔。

### Google Drive 資料夾

- [Demo folder（Google Drive）](https://drive.google.com/drive/folders/1NopwaYQc4ziT43JtvNp395Vge7pvT9NC?usp=drive_link)

### 個別影片連結

- `01_task1_core.mp4`  
  [點此觀看](https://drive.google.com/file/d/1Wbws7ET938-zb0vlPeQOIMmwrUsHawGm/view?usp=sharing)

- `02_benchmark_bm25.mp4`  
  [點此觀看](https://drive.google.com/file/d/1mWrlS_AwySk1H8fiwHkXVDgGQk1muDx2/view?usp=drive_link)

- `02_benchmark_hybrid.mp4`  
  [點此觀看](https://drive.google.com/file/d/1YUcIa-Z-LWbE0QNXSts0KlXpf1-NEnW5/view?usp=drive_link)

- `04_privacy_filter.mp4`  
  [點此觀看](https://drive.google.com/file/d/1Hv2AlPk8KjX-kVn6wGVNPDkJF2m46Bjr/view?usp=drive_link)

- `Pi_test.mp4`  
  [點此觀看](https://drive.google.com/file/d/1kbwc2_eMC0Jp4K3VyhoFAIq3YGyPxh-B/view?usp=drive_link)

---

## 影片內容說明

### `01_task1_core.mp4`

- 本影片展示任務一核心功能已完成，包含 `memory/store.py` 的 JSON 持久化、去重，以及 `memory/bm25.py` 的 pure BM25 retrieval。
- 影片中可看到 `pytest tests/test_memory.py -q` 與 `pytest -q` 的執行結果，證明公開測試皆通過。
- 此影片的重點是讓助教快速確認：任務一的核心函式確實已完成，且程式行為符合測試要求。

### `02_benchmark_bm25.mp4`

- 本影片展示 pure BM25 baseline 的 benchmark 執行流程與結果。
- 影片中會執行 benchmark 指令，並顯示小資料集或大資料集的 `Recall@5`、`MRR`、`nDCG@5`。
- 此影片用來證明本作業的 pure BM25 baseline 已正確實作，並可對照 `README.md` 與 `REPORT.md` 中的 baseline 分數。

### `02_benchmark_hybrid.mp4`

- 本影片展示 hybrid retrieval 的 benchmark 結果。
- 影片中可看到在 hybrid 模式下的評估指標，並可與 pure BM25 baseline 做比較。
- 此影片的主要目的，是展示任務二中 hybrid retrieval 的實作不只是概念說明，而是有經過實際執行與評估。

### `04_privacy_filter.mp4`

- 本影片展示 Privacy Filter 的實際效果。
- 影片中會將包含敏感資訊的 observation 寫入記憶，再檢查儲存後的結果。
- 助教可在畫面中看到如 API key、`password=...` 等字串在存入前已被替換成 `[REDACTED_...]`，並可看到 `sanitized`、`redaction_count`、`redaction_types` 等欄位。
- 這段影片用來證明任務二中的隱私保護機制確實有作用。

### `Pi_test.mp4`

- 本影片展示 Pi bridge 與 Python memory system 的整合流程。
- 內容包含：
  - 使用 `remember` 將資訊寫入記憶
  - 使用 `/recall` 列出或查詢記憶
  - 使用 `/forget` 刪除指定記憶
  - 重新開啟 Pi session 後，透過 `before_agent_start -> inject` 自動注入相關記憶
- 這段影片最重要的意義是：它證明本作業不只是實作 CLI 工具，而是真正把記憶系統整合到 Pi agent lifecycle 中。

---

## 截圖內容說明

### `screenshots/01_task1_core/`

- 本資料夾收錄任務一核心功能的截圖。
- 內容包含 `pytest tests/test_memory.py -q` 與 `pytest -q` 的成功畫面。
- 這些截圖可作為單元測試全數通過的靜態證據，對應 `README.md` 的安裝與測試章節，以及 `REPORT.md` 的任務一驗證結果。

### `screenshots/02_benchmark/02-1Pure_BM25/`

- 本資料夾收錄 pure BM25 benchmark 的執行截圖。
- 截圖中可看到 benchmark 指令與最終評估指標。
- 這些畫面可對照 `README.md` 與 `REPORT.md` 中所列的 pure BM25 baseline 分數，作為 benchmark 可重現性的證據。

### `screenshots/02_benchmark/02-2 Hybrid/`

- 本資料夾收錄 hybrid retrieval benchmark 的執行截圖。
- 截圖中展示 hybrid 模式的 benchmark 分數，並可與 pure BM25 baseline 做比較。
- 這些畫面對應 `README.md` 與 `REPORT.md` 中的任務二 benchmark 結果，用來證明 hybrid retrieval 確實有被執行與評估。

### `screenshots/03_recall_forget/`

- 本資料夾收錄 `recall` 與 `forget` 功能的截圖。
- 內容包含：
  - 建立測試記憶後的列表畫面
  - BM25 recall 結果
  - hybrid recall 結果
  - 刪除前後的對照畫面
- 這些截圖用來展示：記憶不只能被存入，還能被檢索、比對，以及手動刪除。

### `screenshots/04_privacy_filter/`

- 本資料夾收錄 Privacy Filter 的截圖。
- 截圖中可看到敏感資訊已被遮蔽後的 `summary` 欄位，以及 `sanitized`、`redaction_count`、`redaction_types` 等資訊。
- 這些畫面可用來驗證 observation 在進入記憶系統前已先做隱私保護。

### `screenshots/05_time_decay/`

- 本資料夾收錄 Time Decay 功能的截圖。
- 內容比較 `Decay OFF`、`Decay ON（24hr）`、`Decay ON（168hr）` 三種情況下的排序差異。
- 助教可透過這些畫面觀察：當查詢內容相近時，較新的記憶在啟用 decay 後會有更高優先度。

### `screenshots/06 Pi_test/`

- 本資料夾收錄 Pi bridge 整合測試的截圖。
- 內容包含 Pi 中的 `remember`、`/recall`、`/forget` 操作，以及重開 session 後的記憶注入效果。
- 這些截圖是本作業「將 Python 記憶系統接入 Pi agent lifecycle」的直接證據。

---

## 文件對照與閱讀方式

本資料夾中的影片與截圖，不只是附加素材，而是用來對照本作業其餘文件中的結果與說明。建議閱讀方式如下：

- 若想了解**如何重現系統功能、安裝環境、執行測試與 benchmark**，請先閱讀 `README.md`。
- 若想了解**設計理由、benchmark 分析、錯誤類型、反思與取捨**，請閱讀 `REPORT.md`。
- 若想直接確認**功能是否真的執行成功**，則可優先查看本資料夾中的影片與截圖。

具體來說：

- `01_task1_core.mp4` 與 `screenshots/01_task1_core/`  
  對應任務一的正確性驗證與 `pytest` 結果。

- `02_benchmark_bm25.mp4`、`02_benchmark_hybrid.mp4` 與 benchmark 截圖  
  對應 `README.md` 中的 benchmark 重現步驟，以及 `REPORT.md` 中的 benchmark 分析結果。

- `04_privacy_filter.mp4` 與 `screenshots/04_privacy_filter/`  
  對應任務二中 Privacy Filter 的設計與驗證。

- `screenshots/05_time_decay/`  
  對應任務二中 Time Decay 的設計與效果說明。

- `Pi_test.mp4` 與 `screenshots/06 Pi_test/`  
  對應 Pi bridge 整合、`remember`、`/recall`、`/forget`，以及跨 session 記憶注入的實際展示。

換言之：

- `README.md` 負責說明如何執行
- `REPORT.md` 負責說明為何這樣設計、效果如何
- `demo/` 負責提供實際執行過程的證據

---

## 備註

- Demo 影片建議以 demo/ README 中 Google Drive 連結觀看。
- Pi bridge 透過 subprocess 呼叫：
  - `python -m memory.cli capture`
  - `python -m memory.cli recall`
  - `python -m memory.cli forget`
  - `python -m memory.cli inject`
