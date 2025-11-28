# 部署 / 移轉檢查表

以下清單協助您將會議轉錄工具從開發機移轉到新的工作站。建議依序勾選並保留執行紀錄。

## 1. 作業環境與硬體
- [ ] 安裝最新 NVIDIA 顯示卡驅動，確認 `nvidia-smi` 可正常顯示 GPU
- [ ] 確認目標機具備足夠儲存空間（建議 >20GB）及網路可存取內部鏡像/封包

## 2. 必要軟體
- [ ] 安裝 Ollama，啟動一次 `ollama serve` 確認無誤
- [ ] 下載並 `ollama pull` 需要的模型（例如 `qwen2.5:7b` 或 `gemma3:270m`），使用 `ollama list` 驗證
- [ ] 建立虛擬環境或可攜式 Python：
  - `python -m venv .venv` 或複製現有 `.venv`
  - `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

## 3. 專案檔案
- [ ] 將整個專案資料夾（含 `config.yaml`, `input/`, `output/`, `temp/`, `logs/`）複製到新主機
- [ ] 確認 `requirements.txt`, `install_deps.py`, `docs/` 等輔助檔案皆在
- [ ] 若使用自訂模型或批次腳本，檢查相依檔案是否同步（例如自訂 prompt, 工作流程）

## 4. 系統設定
- [ ] 依需求將專案資料夾或 `.venv\Scripts\python.exe` 加入 Windows Defender 例外
- [ ] 若檔案來自網路，執行 `Unblock-File` 移除封鎖標記
- [ ] 更新 `config.yaml` 的路徑設定（若新機資料夾位置不同）

## 5. 驗證流程
- [ ] 在 PowerShell 執行：`curl http://localhost:11434/api/tags` 確認 Ollama 回應
- [ ] 執行 `.\.venv\Scripts\python.exe -c "import yaml, httpx, faster_whisper"`
- [ ] 將一個測試音訊放入 `input/`，雙擊 `開始轉錄.bat`，確認可生成輸出
- [ ] 檢查 `logs/` 內是否產生日誌且無錯誤，`output/` 產生 Markdown

## 6. 文件與支援
- [ ] 更新 README/INSTALL 連結或內部 Wiki，指向新主機位置與流程
- [ ] 保留本檢查表與執行情況，方便下次移轉與稽核
