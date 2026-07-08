#!/bin/bash
# 政府智慧會議紀錄生成系統 Docker 容器清理腳本
# 安全地移除 Docker 中的 政府智慧會議紀錄生成系統 容器，避免與 Native 服務衝突
# 此腳本僅移除 macOS 版本的 Docker 容器，不影響 Windows 版本
# 使用者導覽（給非技術同仁）：
# - 環境檢查：先確認是 macOS，且 Docker 服務可正常回應。
# - 啟停流程：會先停止目標容器，再執行移除，避免殘留衝突。
# - 清理步驟：可選擇是否連映像檔一起刪除以回收空間。
# - 安全注意：僅清理名稱含 meetingscribe 的容器，降低誤刪風險。

set -e

echo "=========================================="
echo "🧹 政府智慧會議紀錄生成系統 Docker 容器清理"
echo "=========================================="
echo ""

# 步驟 1：先確認系統是 macOS，避免誤清理其他環境
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  此腳本僅適用於 macOS 系統"
    echo "❌ 當前系統: $OSTYPE"
    exit 1
fi

# 步驟 2：確認 Docker 可用，若沒啟動就直接結束
if ! docker info &>/dev/null; then
    echo "⚠️  Docker 未運行或未安裝"
    exit 0
fi

# 步驟 3：搜尋與 政府智慧會議紀錄生成系統 相關的容器
echo "🔍 搜尋 政府智慧會議紀錄生成系統 Docker 容器..."
CONTAINERS=$(docker ps -a --filter "name=meetingscribe" --format "{{.ID}} {{.Names}} {{.Status}}" 2>/dev/null || echo "")

if [ -z "$CONTAINERS" ]; then
    echo "✅ 未發現 政府智慧會議紀錄生成系統 Docker 容器"
    exit 0
fi

echo "發現以下容器："
echo "$CONTAINERS"
echo ""

# 步驟 4：逐一強制停止並移除容器
echo "🛑 停止並移除容器..."
docker ps -a --filter "name=meetingscribe" --format "{{.ID}}" | while read -r container_id; do
    container_name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/\///')
    echo "  - 處理: $container_name ($container_id)"
    docker rm -f "$container_id" &>/dev/null
    echo "    ✅ 已移除"
done

# 步驟 5（可選）：詢問是否連映像檔一起清理
echo ""
# 安全提醒：映像檔刪除後需重新下載，預設 N 可避免誤操作。
read -p "是否同時移除 政府智慧會議紀錄生成系統 Docker 映像檔？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  移除 Docker 映像檔..."
    docker images --filter "reference=meetingscribe*" --format "{{.ID}} {{.Repository}}:{{.Tag}}" | while read -r image_id image_name; do
        echo "  - 移除: $image_name ($image_id)"
        docker rmi -f "$image_id" &>/dev/null
        echo "    ✅ 已移除"
    done
fi

echo ""
echo "=========================================="
echo "✅ Docker 容器清理完成"
echo "=========================================="
echo ""
echo "📝 提示："
echo "   - Native 服務可繼續正常運行"
echo "   - Windows Docker 版本不受影響"
echo "   - 如需重新使用 Docker 版本，請執行 docker-compose up"
