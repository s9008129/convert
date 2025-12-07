# 🌿 Git 分支管理最佳實踐 - Vibe Coder 友善版

> **文件版本**：v1.0  
> **建立日期**：2025-12-07  
> **適用對象**：非技術人員、Vibe Coder、專案管理者

---

## 📖 前言：為什麼需要分支管理？

想像一下，您正在寫一份重要報告：
- **主文件**（main）：已經審核通過、可以提交的版本
- **草稿**（develop）：正在撰寫、修改中的版本
- **嘗試新想法**（feature）：想試試看的新段落，不確定會不會保留

Git 分支就像這樣，幫助您：
- 🔒 保護已經可用的版本不被破壞
- 🧪 安全地嘗試新功能
- 📜 追蹤每次修改的歷史

---

## 🗺️ 分支結構圖

```
main（穩定版本）
│
└── develop（開發整合）
    │
    ├── feature/新功能A
    ├── feature/新功能B
    └── fix/修復問題C
```

### 分支說明

| 分支 | 用途 | 誰可以修改 | 比喻 |
|------|------|----------|------|
| `main` | 穩定、可用的版本 | 只接受經過測試的 PR | 正式報告 |
| `develop` | 開發整合 | 開發者、Copilot | 草稿區 |
| `feature/*` | 新功能開發 | 開發者、Copilot | 嘗試新想法 |
| `fix/*` | 修復問題 | 開發者、Copilot | 修正錯誤 |
| `release/*` | 準備發布 | 專案管理者 | 最終審核 |

---

## 🚀 日常操作指南

### 情境 1：我想新增一個功能

**步驟**：
1. 確保在最新的 develop 分支上
   ```bash
   git checkout develop
   git pull origin develop
   ```

2. 建立新的功能分支
   ```bash
   git checkout -b feature/我的新功能
   ```

3. 進行開發和修改

4. 完成後提交
   ```bash
   git add .
   git commit -m "[新增] 功能說明"
   ```

5. 推送到遠端
   ```bash
   git push origin feature/我的新功能
   ```

6. 在 GitHub 上建立 Pull Request 合併到 develop

### 情境 2：我想修復一個問題

**步驟**：
1. 建立修復分支
   ```bash
   git checkout develop
   git checkout -b fix/問題描述
   ```

2. 修復問題

3. 提交並推送
   ```bash
   git add .
   git commit -m "[修復] 問題描述"
   git push origin fix/問題描述
   ```

### 情境 3：我想發布新版本

**步驟**：
1. 確認 develop 分支穩定
2. 建立 release 分支
   ```bash
   git checkout develop
   git checkout -b release/v3.6.0
   ```

3. 進行最終測試
4. 更新版本號和 CHANGELOG
5. 合併到 main
   ```bash
   git checkout main
   git merge --no-ff release/v3.6.0 -m "[Stable] 發布 v3.6.0"
   ```

6. 打標籤
   ```bash
   git tag -a v3.6.0 -m "版本 v3.6.0"
   ```

---

## ⚠️ 重要守則

### ✅ 該做的事

1. **每次修改前先拉取最新版本**
   ```bash
   git pull origin <分支名>
   ```

2. **寫清楚的 commit message**
   - ✅ 好：`[新增] 自訂格式範本上傳功能`
   - ❌ 壞：`update`

3. **小步提交，頻繁提交**
   - 完成一個小功能就提交
   - 不要累積太多修改

4. **發布前完整測試**
   - 在 Windows 和 macOS 上都測試
   - 確認所有功能正常

### ❌ 不該做的事

1. **不要直接修改 main 分支**
   - main 是穩定版本，只接受合併

2. **不要強制推送（force push）到共享分支**
   ```bash
   # 危險！不要這樣做
   git push --force origin main
   ```

3. **不要提交敏感資訊**
   - API Key、密碼不要寫進程式碼
   - 使用 `.env` 檔案存放

---

## 🛡️ 安全機制

### Pre-Push Hook

專案已設定 pre-push hook，當您嘗試 push 到 main 分支時：

1. 會顯示警告訊息
2. 會提示檢查清單
3. 需要輸入確認才能繼續

### 如何安裝（已預設安裝）

```bash
cp scripts/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

---

## 📋 常用指令速查表

| 目的 | 指令 |
|------|------|
| 查看目前分支 | `git branch` |
| 切換分支 | `git checkout <分支名>` |
| 建立新分支 | `git checkout -b <新分支名>` |
| 查看修改狀態 | `git status` |
| 提交修改 | `git add . && git commit -m "說明"` |
| 推送到遠端 | `git push origin <分支名>` |
| 拉取最新版本 | `git pull origin <分支名>` |
| 查看提交歷史 | `git log --oneline` |

---

## 🆘 遇到問題怎麼辦？

### 問題 1：我改壞了，想回到之前的狀態

```bash
# 放棄所有未提交的修改
git checkout -- .

# 或者回到特定的 commit
git reset --hard <commit-id>
```

### 問題 2：我提交錯了訊息

```bash
# 修改最後一次的 commit 訊息
git commit --amend -m "正確的訊息"
```

### 問題 3：我不小心在錯誤的分支上修改

```bash
# 先暫存修改
git stash

# 切換到正確的分支
git checkout <正確的分支>

# 恢復修改
git stash pop
```

### 問題 4：合併時發生衝突

1. 打開有衝突的檔案
2. 找到 `<<<<<<< HEAD` 標記
3. 手動決定要保留哪些內容
4. 刪除衝突標記
5. 提交解決後的結果

---

## 📚 進階資源

- [Git 官方文件](https://git-scm.com/doc)
- [GitHub Flow 說明](https://guides.github.com/introduction/flow/)
- [本專案 INSTRUCTIONS.md](/.github/INSTRUCTIONS.md)

---

> **💡 記住**：分支管理的核心目標是「保護穩定版本」和「安全嘗試新功能」。  
> 如果不確定，先建立新分支再修改，總是比較安全的選擇。
