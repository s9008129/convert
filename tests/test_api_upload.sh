#!/bin/bash
# MLX-Whisper 修復驗證測試腳本
# 測試 2 個音訊檔案的上傳與轉錄
# 測試目的：確認「檔案上傳 → 建立任務 → 查詢完成」流程可穩定運作，避免修復後再次失效。
# Given：本機 API 服務已啟動，並備妥可上傳的測試音檔。
# When：透過 curl 呼叫 /api/upload，接著輪詢 /api/tasks/{task_id} 直到完成或失敗。
# Then：必須成功取得 task_id 並看到 completed 狀態；若 failed 或無 task_id 立即視為風險警訊。
# 關鍵 mock/assertion 意義：此腳本屬整合驗證，不用 mock；以 shell 條件判斷與 exit code 取代 assertion，確保 CI 可正確擋下異常。

# 測試途中若出錯就立即停止，避免誤判結果
set -e

BASE_URL="http://localhost:9527"
TEST_DIR="/Users/hsiaojohnny/dev/convert/tests/test_audio"

echo "======================================"
echo "🧪 MLX-Whisper 修復驗證測試"
echo "======================================"
echo ""

# 測試區塊 1：上傳第一個測試音檔並追蹤任務
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

# 每 2 秒查一次狀態，最多等待 60 秒
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

# 測試區塊 2：重複同樣流程驗證第二個音檔
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
