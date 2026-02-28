# MeetingScribe 文件中心

> **版本**：v4.0  
> **最後更新**：2026-02-28  
> **維護者**：MeetingScribe 開發團隊

---

## 📚 文件導航

### 📖 核心文件

| 文件 | 說明 |
|------|------|
| [spec.md](spec.md) | 功能規格（需求、驗收標準） |
| [使用者手冊.md](使用者手冊.md) | 使用者操作指南（非技術人員友善） |
| [../README.md](../README.md) | 專案總覽與快速開始 |
| [../CHANGELOG.md](../CHANGELOG.md) | 版本變更紀錄 |

### 🔬 研究資料

| 目錄 | 說明 |
|------|------|
| [research/](research/) | 技術研究報告 |
| [research/breeze-asr-25/](research/breeze-asr-25/) | 聯發科 Breeze-ASR-25 語音辨識研究 |

### 🗄️ 歷史文件

| 目錄 | 說明 |
|------|------|
| [old/](old/) | 已封存的舊版本文件（系統分析、修復報告等） |

---

## 📁 目錄結構

```
doc/
├── README.md                  # 📄 文件導航中心（本文件）
├── spec.md                    # 🎯 功能規格書
├── 使用者手冊.md              # 📖 使用者操作指南
│
├── research/                  # 🔬 技術研究
│   ├── research.md            # 技術研究總覽
│   ├── mediatek-research-breeze-3-ai-must.md
│   └── breeze-asr-25/         # 聯發科 Breeze-ASR-25 研究
│       ├── 聯發科 Breeze-ASR-25 台灣中英混用辨識技術.md
│       ├── VAD 技術解決語音辨識模型幻覺問題實務指南.md
│       ├── Breeze-ASR-25：台灣中英混用語音辨識新標竿.md
│       └── Breeze-ASR 與 Whisper 台灣在地化效能評測.md
│
└── old/                       # 🗄️ 歷史文件（封存）
    ├── 系統改善計劃.md
    ├── implement_and_tasks.md
    ├── 語音轉台灣繁體中文語意逐字稿升級計劃.md
    ├── v3.5.5_系統修復驗證報告.md
    └── ... (舊版本分析報告)
```

---

## 📋 文件維護規則

1. **新增文件**：放入對應目錄，更新本 README.md
2. **更新文件**：在頂部標註更新日期，同步更新 CHANGELOG.md
3. **封存文件**：移至 `old/` 目錄，更新本 README.md
4. **命名規範**：使用有意義的名稱，版本文件含版號

---

**維護者**：MeetingScribe 開發團隊  
**最後更新**：2026-02-28  
**版本**：v4.0
