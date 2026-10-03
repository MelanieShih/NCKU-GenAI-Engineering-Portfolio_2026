# Markdown 渲染作業：個人履歷

## 1. 專案簡介
本作業的 `content.md` 為「個人履歷」格式文件，內容包含：
- 個人基本資料（姓名、系所）
- 聯絡資訊（Email / Phone / GitHub / Location，搭配小圖示）
- 自我簡介（Profile）
- 教育背景（表格）
- 專業技能（清單）
- 專案經歷與學術研究（段落 + 清單）
- 附錄：Python 程式碼範例

### 選用渲染工具與理由
本作業輸出兩種成果：
- **HTML：使用 Pandoc**
  - Pandoc 對 Markdown + 表格 + fenced code block 支援完整，且可使用 `--embed-resources` 產出單一 HTML 檔，方便助教檢視與重現。
  - 本作業的 `content.md` 混用少量 raw HTML（例如 `<div class="contact">`），因此 Pandoc 轉換需開啟 `raw_html` 支援。
- **PDF：使用 md-to-pdf（npx md-to-pdf）**
  - 基於 Chromium 渲染，對 CSS（`<style>`）支援較佳，能保留版面設計（字體、卡片 blockquote、表格、程式碼區塊樣式）。

> 備註：Pandoc 的 Lua filter 只影響 Pandoc 輸出（HTML），不會影響 `md-to-pdf` 輸出（PDF）。

---

## 2. 環境需求

**作業系統**
* Windows 10 / Windows 11

**Runtime**
* **Node.js**: 建議 18+ (用於執行 `npx md-to-pdf`)
* **npm**: 隨 Node.js 附帶安裝
* **Pandoc**: 建議 3.x (系統安裝)

**系統層套件安裝 (Windows)**

建議直接至官方網站下載 Windows 安裝檔 (`.msi` 或 `.exe`) 進行安裝，或是透過 Windows 內建的 `winget` 指令於終端機快速安裝：

```bash
# 使用 winget 安裝 Node.js
winget install OpenJS.NodeJS

# 使用 winget 安裝 Pandoc
winget install JohnMacFarlane.Pandoc

# 驗證安裝是否成功
node -v
npm -v
pandoc --version
```
---

## 3. 安裝步驟

本作業不需要 Python 套件，只需確保：

- 已安裝 pandoc
- 已安裝 node/npm（用於 md-to-pdf）
- 確認 npx 可用：npx --version

---

## 4. 執行渲染（Windows / PowerShell）

4.1 產生 HTML（Pandoc）

請在專案根目錄（與 `content.md` 同一層）執行：

```powershell
# 建立 output 資料夾（若已存在則略過）
if (!(Test-Path "output")) { New-Item -ItemType Directory -Path "output" | Out-Null }

# 產生 HTML（含內嵌資源）
pandoc content.md `
  -f gfm+raw_html `
  -s --embed-resources `
  -o output/output.html `
  --metadata title="施孟伶 - 個人履歷" `
  --metadata charset="utf-8"

重要注意事項:
- content.md 內含 raw HTML（例如 <div class="contact"> ...），請確保：
- Pandoc 指令包含 -f gfm+raw_html
- HTML 區塊每一行不要縮排（前面不要有 4 個空白或 tab），否則 Markdown 會把該段判成 code block，導致 <img ...> 等 HTML 標籤被原樣印出。
```
4.2 產生 PDF（md-to-pdf）

請在專案根目錄執行：

```powershell
# 建立 output 資料夾（若已存在則略過）
if (!(Test-Path "output")) { New-Item -ItemType Directory -Path "output" | Out-Null }

# 使用 md-to-pdf 產生 PDF（此版本不支援 --output，預設輸出為 content.pdf）
npx md-to-pdf content.md

# 將輸出移至 output/ 並統一命名為 output.pdf
Move-Item -Force .\content.pdf .\output\output.pdf

說明：本作業使用的 md-to-pdf CLI 不支援 --output 參數，因此先產生預設檔名 content.pdf，再移動並重新命名為 output/output.pdf，以符合作業繳交規範。
```
---

## 5. 預期輸出

執行完上述指令後，output/ 內應包含：

output/output.html：單一 HTML 檔（已 embed 圖片與資源）

output/output.pdf：PDF 履歷

[輸出樣貌]

- 首頁包含照片（右上角），姓名與學校系所資訊

- 聯絡資訊列包含 icon + 文字（Email/Phone/GitHub/Location）

- 聯絡資訊 "GitHub有超連結"，可連結至個人帳號

- "個人簡介" 使用 blockquote 卡片風格

- 教育背景以表格呈現

- 附錄程式碼區塊使用 fenced code block，保留縮排與樣式

---

## 6. 參考資料
* [Pandoc 官方文件 (User Guide)](https://pandoc.org/MANUAL.html)
* [Pandoc Markdown (GFM / raw HTML) 相關說明](https://pandoc.org/MANUAL.html#markdown-variants)
* [md-to-pdf (npm 套件) 文件](https://www.npmjs.com/package/md-to-pdf)
* [Iconify SVG API (小圖示來源)](https://iconify.design/docs/api/)




