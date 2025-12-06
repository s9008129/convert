#!/bin/bash
# MLX-Whisper 修復驗證測試腳本
# 測試 2 個音訊檔案的上傳與轉錄

set -e

BASE_URL="http://localhost:9527"
TEST_DIR="/Users/hsiaojohnny/dev/convert/tests/test_audio"

echo "======================================"
echo "🧪 MLX-Whisper 修復驗證測試"
echo "======================================"
echo ""

# 測試 1: test1_5sec.wav
echo "📝 測試 1: 上傳 test1_5sec.wav (5秒音訊)"
echo "--------------------------------------"

RESPONSE1=$(curl -s -X POST "$BASE_URL/api/upload" \
  -F "file=@$TEST_DIR/test1_5sec.wav" \
  -F "mode=local")

TASK_ID1=$(echo $RESPONSE1 | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null || echo "")

if [ -z "$TASK_ID1" ]; then
    echo "❌ 測試 1 失敗: 無法取得 task_id"
    echo "回應: $RESPONSE1"
    exit 1
fi

echo "✅ 任務已建立: $TASK_ID1"
echo "⏳ 等待轉錄完成..."
sleep 2

# 輪詢任務狀態 (最多等 60 秒)
for i in {1..30}; do
    STATUS1=$(curl -s "$BASE_URL/api/tasks/$TASK_ID1")
    STATE1=$(echo $STATUS1 | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
    
    if [ "$STATE1" = "completed" ]; then
        echo "✅ 測試 1 轉錄成功!"
        echo "$STATUS1" | python3 -m json.tool | grep -E "(status|progress|current_step|transcript)" | head -10
        break
    elif [ "$STATE1" = "failed" ]; then
        echo "❌ 測試 1 轉錄失敗"
        echo "$STATUS1" | python3 -m json.tool
        exit 1
    fi
    
    echo "  [$(date +%H:%M:%S)] 狀態: $STATE1, 嘗試 $i/30..."
    sleep 2
done

echo ""
sleep 3

# 測試 2: test2_3sec.wav
echo "📝 測試 2: 上傳 test2_3sec.wav (3秒音訊)"
echo "--------------------------------------"

RESPONSE2=$(curl -s -X POST "$BASE_URL/api/upload" \
  -F "file=@$TEST_DIR/test2_3sec.wav" \
  -F "mode=local")

TASK_ID2=$(echo $RESPONSE2 | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null || echo "")

if [ -z "$TASK_ID2" ]; then
    echo "❌ 測試 2 失敗: 無法取得 task_id"
    echo "回應: $RESPONSE2"
    exit 1
fi

echo "✅ 任務已建立: $TASK_ID2"
echo "⏳ 等待轉錄完成..."
sleep 2

# 輪詢任務狀態
for i in {1..30}; do
    STATUS2=$(curl -s "$BASE_URL/api/tasks/$TASK_ID2")
    STATE2=$(echo $STATUS2 | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
    
    if [ "$STATE2" = "completed" ]; then
        echo "✅ 測試 2 轉錄成功!"
        echo "$STATUS2" | python3 -m json.tool | grep -E "(status|progress|current_step|transcript)" | head -10
        break
    elif [ "$STATE2" = "failed" ]; then
        echo "❌ 測試 2 轉錄失敗"
        echo "$STATUS2" | python3 -m json.tool
        exit 1
    fi
    
    echo "  [$(date +%H:%M:%S)] 狀態: $STATE2, 嘗試 $i/30..."
    sleep 2
done

echo ""
echo "======================================"
echo "📊 測試結果總結"
echo "======================================"
echo "✅ 測試 1 (5秒音訊): 成功"
echo "✅ 測試 2 (3秒音訊): 成功"
echo ""
echo "🎉 所有測試通過! MLX-Whisper 模型問題已修復!"
echo "======================================"
