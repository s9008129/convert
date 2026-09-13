#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 政府智慧會議紀錄生成系統 文件健康檢查腳本 v1.0
# 檢查文件版本號一致性、連結有效性、命名規範
# ═══════════════════════════════════════════════════════════════
# 使用者導覽（給非技術同仁）：
# - 環境檢查：先切到專案根目錄，避免在錯誤路徑檢查。
# - 啟停流程：本腳本只做文件掃描，不會啟動或停止任何服務。
# - 清理步驟：不會刪除檔案，只統計錯誤與警告數量。
# - 安全注意：屬於唯讀檢查，適合在部署前先行確認文件健康度。

# 只要任何一步出錯就立刻停止，避免錯誤被忽略
set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 先定位專案根目錄，確保後續檢查都在同一個基準點
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

CURRENT_VERSION="$(cat VERSION 2>/dev/null || echo unknown)"
ERRORS=0
WARNINGS=0

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}║         📋 政府智慧會議紀錄生成系統 文件健康檢查工具 v1.0              ║${NC}"
echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}目標版本: v${CURRENT_VERSION}${NC}"
echo -e "${BLUE}檢查時間: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# 檢查 1：版本號一致性
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}【檢查 1】版本號一致性${NC}"
echo "─────────────────────────────────────────"

# 檢查 VERSION 檔案
if [ -f "VERSION" ]; then
    FILE_VERSION=$(cat VERSION | tr -d '\n')
    if [ "$FILE_VERSION" = "$CURRENT_VERSION" ]; then
        echo -e "  ${GREEN}✅ VERSION 檔案: v${FILE_VERSION}${NC}"
    else
        echo -e "  ${RED}❌ VERSION 檔案: v${FILE_VERSION} (預期: v${CURRENT_VERSION})${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${YELLOW}⚠️ VERSION 檔案不存在${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 檢查 README.md
if grep -q "version-${CURRENT_VERSION}" README.md 2>/dev/null; then
    echo -e "  ${GREEN}✅ README.md 版本號正確${NC}"
else
    echo -e "  ${YELLOW}⚠️ README.md 版本號可能不一致${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 檢查 doc/README.md
if grep -q "v${CURRENT_VERSION}" doc/README.md 2>/dev/null; then
    echo -e "  ${GREEN}✅ doc/README.md 版本號正確${NC}"
else
    echo -e "  ${YELLOW}⚠️ doc/README.md 版本號可能不一致${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 搜尋舊版本號
OLD_VERSIONS=("3.5.4" "3.5.3" "3.5.2")
for old_ver in "${OLD_VERSIONS[@]}"; do
    COUNT=$(grep -r "v${old_ver}" . --include="*.md" --exclude-dir={node_modules,.git,old,歷史封存,venv,.venv,archive,venv.backup.*} 2>/dev/null | grep -v "歷史" | grep -v "版本" | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️ 發現 v${old_ver} 引用: ${COUNT} 處${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

echo ""

# ═══════════════════════════════════════════════════════════════
# 檢查 2：文件命名規範
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}【檢查 2】文件命名規範${NC}"
echo "─────────────────────────────────────────"

# 檢查是否有大寫字母（除中文檔案外）
BAD_NAMES=$(find doc/ -name "*.md" -type f | grep -E '[A-Z]' | grep -v "README" | grep -v "old\|歷史封存" | wc -l | tr -d ' ')
if [ "$BAD_NAMES" -eq 0 ]; then
    echo -e "  ${GREEN}✅ 所有檔案名稱符合小寫規範${NC}"
else
    echo -e "  ${YELLOW}⚠️ 發現 ${BAD_NAMES} 個檔案包含大寫字母${NC}"
    find doc/ -name "*.md" -type f | grep -E '[A-Z]' | grep -v "README" | grep -v "old\|歷史封存" | head -5 | while read file; do
        echo -e "      - ${file}"
    done
    WARNINGS=$((WARNINGS + 1))
fi

# 檢查是否有空格（應使用底線）
SPACE_NAMES=$(find doc/ -name "*.md" -type f | grep " " | grep -v "old\|歷史封存" | wc -l | tr -d ' ')
if [ "$SPACE_NAMES" -eq 0 ]; then
    echo -e "  ${GREEN}✅ 所有檔案名稱使用底線分隔${NC}"
else
    echo -e "  ${RED}❌ 發現 ${SPACE_NAMES} 個檔案名稱包含空格${NC}"
    find doc/ -name "*.md" -type f | grep " " | grep -v "old\|歷史封存" | head -5 | while read file; do
        echo -e "      - ${file}"
    done
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ═══════════════════════════════════════════════════════════════
# 檢查 3：文件結構完整性
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}【檢查 3】文件結構完整性${NC}"
echo "─────────────────────────────────────────"

# 檢查必要目錄
# 依 doc/README.md 的維護規則：實際只有「操作手冊」「規格與設計」兩個分類子資料夾
REQUIRED_DIRS=("doc/操作手冊" "doc/規格與設計")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✅ ${dir}/ 存在${NC}"
    else
        echo -e "  ${RED}❌ ${dir}/ 不存在${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# 檢查必要文件
# 注意大小寫：實際檔名為 .github/instructions.md（Linux 等大小寫敏感檔案系統會區分）
REQUIRED_FILES=("README.md" "CHANGELOG.md" "VERSION" "doc/README.md" ".github/instructions.md")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✅ ${file} 存在${NC}"
    else
        echo -e "  ${RED}❌ ${file} 不存在${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# ═══════════════════════════════════════════════════════════════
# 檢查 4：連結有效性（基本檢查）
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}【檢查 4】連結有效性（本地連結）${NC}"
echo "─────────────────────────────────────────"

# 檢查 doc/README.md 中的連結（簡化版）
if [ -f "doc/README.md" ]; then
    echo -e "  ${GREEN}✅ doc/README.md 存在（連結檢查已跳過）${NC}"
else
    echo -e "  ${RED}❌ doc/README.md 不存在${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ═══════════════════════════════════════════════════════════════
# 總結（給維護者快速判斷是否需要立刻修正文件）
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════════"
echo -e "${BLUE}📊 檢查總結${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ "$ERRORS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}🎉 所有檢查通過！文件狀態良好。${NC}"
    exit 0
elif [ "$ERRORS" -eq 0 ]; then
    echo -e "${YELLOW}⚠️ 發現 ${WARNINGS} 個警告，建議修復。${NC}"
    exit 0
else
    echo -e "${RED}❌ 發現 ${ERRORS} 個錯誤和 ${WARNINGS} 個警告，請立即修復。${NC}"
    exit 1
fi
