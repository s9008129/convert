#!/bin/bash
# MeetingScribe Docker 容器清理腳本
# 安全地移除 Docker 中的 MeetingScribe 容器，避免與 Native 服務衝突
# 此腳本僅移除 macOS 版本的 Docker 容器，不影響 Windows 版本

set -e

echo "=========================================="
echo "🧹 MeetingScribe Docker 容器清理"
echo "=========================================="
echo ""

# 檢查是否為 macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  此腳本僅適用於 macOS 系統"
    echo "❌ 當前系統: $OSTYPE"
    exit 1
fi

# 檢查 Docker 是否運行
if ! docker info &>/dev/null; then
    echo "⚠️  Docker 未運行或未安裝"
    exit 0
fi

# 查找 MeetingScribe 相關容器
echo "🔍 搜尋 MeetingScribe Docker 容器..."
CONTAINERS=$(docker ps -a --filter "name=meetingscribe" --format "{{.ID}} {{.Names}} {{.Status}}" 2>/dev/null || echo "")

if [ -z "$CONTAINERS" ]; then
    echo "✅ 未發現 MeetingScribe Docker 容器"
    exit 0
fi

echo "發現以下容器："
echo "$CONTAINERS"
echo ""

# 停止並移除容器
echo "🛑 停止並移除容器..."
docker ps -a --filter "name=meetingscribe" --format "{{.ID}}" | while read -r container_id; do
    container_name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/\///')
    echo "  - 處理: $container_name ($container_id)"
    docker rm -f "$container_id" &>/dev/null
    echo "    ✅ 已移除"
done

# 清理相關映像檔（可選）
echo ""
read -p "是否同時移除 MeetingScribe Docker 映像檔？(y/N): " -n 1 -r
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
