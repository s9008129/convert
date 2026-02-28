#!/bin/bash
# 使用真實音檔做端到端驗證，確認修復在實務情境也有效
# 測試目的：驗證真實會議音檔在雲端轉錄模式下可成功完成，避免僅在小樣本測試通過卻在真實情境失敗。
# Given：API 服務可連線，且 TEST_FILES 內音檔存在且可讀取。
# When：逐一上傳音檔、取得 task_id，並輪詢任務進度與最終狀態。
# Then：每個檔案都應回報 completed 並產生轉錄片段；若出現 failed 或上傳失敗，最終 exit code 需為 1。
# 關鍵 mock/assertion 意義：此腳本為真實整合流程，不使用 mock；以 success_count、失敗統計與 exit code 驗證品質風險。

# 任一步驟失敗就停止，避免後續測試混淆結果
set -e

BASE_URL="http://localhost:9527"
TEST_FILES=(
    "/Users/hsiaojohnny/dev/convert/input/test_meeting_1.wav"
    "/Users/hsiaojohnny/dev/convert/input/test_meeting_2.wav"
)

echo "=========================================="
echo "🎯 MLX-Whisper 真實音檔驗證測試"
echo "=========================================="
echo ""

test_count=0
success_count=0

# 逐一測試每個真實音檔
for TEST_FILE in "${TEST_FILES[@]}"; do
    test_count=$((test_count + 1))
    TEST_NAME=$(basename "$TEST_FILE")
    FILE_SIZE=$(ls -lh "$TEST_FILE" | awk '{print $5}')
    
    echo "📝 測試 $test_count: $TEST_NAME ($FILE_SIZE)"
    echo "--------------------------------------"
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/upload" \
      -F "file=@$TEST_FILE" \
      -F "mode=cloud")
    
    TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null || echo "")
    
    if [ -z "$TASK_ID" ]; then
        echo "❌ 上傳失敗"
        echo "回應: $RESPONSE"
        continue
    fi
    
    echo "✅ 任務已建立: $TASK_ID"
    echo "⏳ 等待處理..."
    
    # 每 2 秒查一次任務狀態，最多等待 120 秒
    for i in {1..60}; do
        sleep 2
        STATUS=$(curl -s "$BASE_URL/api/tasks/$TASK_ID")
        STATE=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
        PROGRESS=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['progress'])" 2>/dev/null || echo "0")
        
        echo -ne "\r  處理中... ${PROGRESS}%"
        
        if [ "$STATE" = "completed" ]; then
            TRANSCRIPT=$(echo $STATUS | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('transcript', '')[:100])" 2>/dev/null || echo "")
            echo ""
            echo "✅ 測試 $test_count 成功!"
            echo "📄 轉錄片段: $TRANSCRIPT..."
            success_count=$((success_count + 1))
            break
        elif [ "$STATE" = "failed" ]; then
            ERROR=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', 'Unknown')[:150])" 2>/dev/null || echo "Unknown")
            echo ""
            echo "❌ 測試 $test_count 失敗"
            echo "錯誤: $ERROR"
            break
        fi
    done
    
    echo ""
    sleep 2
done

echo "=========================================="
echo "📊 測試結果總結"
echo "=========================================="
echo "總測試數: $test_count"
echo "成功數: $success_count"
echo "失敗數: $((test_count - success_count))"
echo ""

if [ $success_count -eq $test_count ]; then
    echo "🎉 所有測試通過! MLX-Whisper 模型問題已完全修復!"
    echo "=========================================="
    exit 0
else
    echo "⚠️  部分測試失敗"
    exit 1
fi
