#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GPU 轉錄測試腳本
測試 MeetingScribe 是否正確使用 GPU 進行轉錄
"""

import requests
import time
import sys

def main():
    print('='*60)
    print('GPU 轉錄測試開始')
    print('='*60)
    
    # 上傳測試音頻
    print('\n[1] 上傳測試音頻...')
    try:
        with open('D:/dev/convert/test_audio.wav', 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            data = {'mode': 'local'}
            response = requests.post('http://localhost:9527/api/upload', files=files, data=data)
            result = response.json()
            print(f'    狀態: {result.get("status", "unknown")}')
            task_id = result.get('task_id')
            print(f'    任務 ID: {task_id}')
    except Exception as e:
        print(f'    錯誤: {e}')
        return 1
    
    if not task_id:
        print('    錯誤: 未取得任務 ID')
        return 1
    
    # 等待處理完成
    print('\n[2] 等待轉錄處理...')
    max_wait = 120
    waited = 0
    current_status = 'unknown'
    status = {}
    
    while waited < max_wait:
        time.sleep(3)
        waited += 3
        try:
            status_response = requests.get(f'http://localhost:9527/api/task/{task_id}')
            status = status_response.json()
            current_status = status.get('status', 'unknown')
            progress = status.get('progress', 0)
            print(f'    {waited}秒: {current_status} ({progress}%)')
            if current_status in ['completed', 'error', 'failed']:
                break
        except Exception as e:
            print(f'    {waited}秒: 查詢錯誤 - {e}')
    
    print('\n[3] 測試結果:')
    print(f'    最終狀態: {current_status}')
    
    if current_status == 'completed':
        print('    ✅ GPU 轉錄測試成功!')
        if 'transcript' in status:
            print(f'    轉錄內容: {status.get("transcript", "")[:200]}...')
    else:
        print(f'    ❌ 測試未成功')
        print(f'    詳細: {status}')
    
    print('\n' + '='*60)
    return 0 if current_status == 'completed' else 1

if __name__ == '__main__':
    sys.exit(main())
