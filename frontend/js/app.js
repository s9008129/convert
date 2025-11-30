/**
 * MeetingScribe 前端應用程式
 * v2.3.2 - 模式鎖定與 UI 優化
 */

// 全域狀態
const state = {
    currentMode: 'local',
    taskId: null,
    websocket: null,
    config: null,
    lastFile: null,          // 保存最後上傳的檔案
    retryAttempts: 0,        // 重試計數
    maxRetryAttempts: 3,     // 最大重試次數
    modeLocked: false        // 模式是否已鎖定
};

// DOM 元素
const elements = {
    // 狀態欄
    systemStatus: document.getElementById('systemStatus'),
    gpuStatus: document.getElementById('gpuStatus'),
    queueCount: document.getElementById('queueCount'),
    
    // 模式選擇
    modeLocal: document.getElementById('modeLocal'),
    modeCloud: document.getElementById('modeCloud'),
    cloudWarning: document.getElementById('cloudWarning'),
    
    // 自訂 Prompt
    userPrompt: document.getElementById('userPrompt'),
    
    // 上傳
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    maxFileSize: document.getElementById('maxFileSize'),
    
    // 排隊
    queueSection: document.getElementById('queueSection'),
    queueTotal: document.getElementById('queueTotal'),
    queuePosition: document.getElementById('queuePosition'),
    queueStatus: document.getElementById('queueStatus'),
    
    // 進度
    progressSection: document.getElementById('progressSection'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    progressPercent: document.getElementById('progressPercent'),
    deviceInfo: document.getElementById('deviceInfo'),
    
    // 結果
    resultSection: document.getElementById('resultSection'),
    resultPreview: document.getElementById('resultPreview'),
    copyBtn: document.getElementById('copyBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    resetBtn: document.getElementById('resetBtn'),
    
    // 錯誤
    errorSection: document.getElementById('errorSection'),
    errorMessage: document.getElementById('errorMessage'),
    retryBtn: document.getElementById('retryBtn'),
    
    // 頁尾
    footerMode: document.getElementById('footerMode'),
    
    // 本地模式資訊
    localModelInfo: document.getElementById('localModelInfo'),
    
    // 雲端模式資訊
    cloudModelInfo: document.getElementById('cloudModelInfo'),
    
    // 模式鎖定提示
    modeLockHint: document.getElementById('modeLockHint')
};

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await checkHealth();
    setupEventListeners();
    
    // 定期檢查健康狀態
    setInterval(checkHealth, 30000);
});

// ===== API 函數 =====
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        state.config = await response.json();
        
        // 更新 UI
        if (elements.maxFileSize) {
            elements.maxFileSize.textContent = state.config.max_file_size_mb;
        }
        
        // 檢查雲端模式是否可用
        if (!state.config.gemini_available) {
            if (elements.cloudWarning) {
                elements.cloudWarning.style.display = 'block';
            }
            if (elements.modeCloud) {
                elements.modeCloud.classList.add('disabled');
            }
        }
    } catch (error) {
        console.error('載入配置失敗:', error);
    }
}

async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            throw new Error('健康檢查失敗');
        }
        
        const data = await response.json();
        
        // 更新系統狀態
        if (elements.systemStatus) {
            elements.systemStatus.className = data.status === 'healthy' ? 'status-ok' : 'status-error';
            elements.systemStatus.textContent = data.status === 'healthy' ? '系統正常' : '系統異常';
        }
        
        // 更新 GPU 狀態
        if (elements.gpuStatus) {
            elements.gpuStatus.className = data.gpu_available ? 'status-ok' : 'status-warning';
            elements.gpuStatus.textContent = data.gpu_name ? `GPU: ${data.gpu_name}` : 'GPU 未偵測';
        }
        
        // 更新排隊狀態
        if (elements.queueCount && data.queue_status) {
            elements.queueCount.textContent = `排隊: ${data.queue_status.total_queued}`;
        }
        
        // 更新本地模式資訊（自動偵測 Ollama 或 LM Studio）
        if (elements.localModelInfo) {
            const localAvailable = data.ollama_available || data.lmstudio_available;
            if (localAvailable) {
                elements.localModelInfo.textContent = '使用：本地 LLM（已就緒）';
                elements.localModelInfo.style.color = '#34C759';
            } else {
                elements.localModelInfo.textContent = '使用：本地 LLM（未偵測）';
                elements.localModelInfo.style.color = '#FF9500';
            }
        }
        
        // 更新雲端模式資訊（檢查 Gemini API 可用性）
        if (elements.cloudModelInfo) {
            if (data.gemini_available) {
                elements.cloudModelInfo.textContent = '使用：Gemini API（已就緒）';
                elements.cloudModelInfo.style.color = '#34C759';
            } else {
                elements.cloudModelInfo.textContent = '使用：Gemini API（連線失敗）';
                elements.cloudModelInfo.style.color = '#FF3B30';
            }
        }
        
        // 更新本地模式可用性
        if (elements.modeLocal) {
            const localAvailable = data.ollama_available || data.lmstudio_available;
            if (!localAvailable) {
                elements.modeLocal.classList.add('disabled');
            } else {
                elements.modeLocal.classList.remove('disabled');
            }
        }
        
        // 更新雲端模式可用性
        if (elements.modeCloud) {
            if (!data.gemini_available) {
                elements.modeCloud.classList.add('disabled');
            } else {
                elements.modeCloud.classList.remove('disabled');
            }
        }
    } catch (error) {
        console.error('健康檢查失敗:', error);
        if (elements.systemStatus) {
            elements.systemStatus.className = 'status-error';
            elements.systemStatus.textContent = '無法連接';
        }
    }
}

// 上傳檔案（支援重試）
async function uploadFile(file, isRetry = false) {
    // 保存檔案以便重試
    if (!isRetry) {
        state.lastFile = file;
        state.retryAttempts = 0;
    } else {
        state.retryAttempts++;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_mode', state.currentMode);
    
    const userPrompt = elements.userPrompt.value.trim();
    if (userPrompt) {
        formData.append('user_prompt', userPrompt);
    }
    
    try {
        // 隱藏錯誤訊息
        if (elements.errorSection) {
            elements.errorSection.style.display = 'none';
        }
        
        // 🔒 鎖定模式選擇
        lockModeSelection(true);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '上傳失敗');
        }
        
        const result = await response.json();
        state.taskId = result.task_id;
        
        // 顯示排隊狀態
        showQueueStatus(result);
        
        // 連接 WebSocket
        connectWebSocket(result.task_id);
        
    } catch (error) {
        // 解鎖模式選擇（失敗時）
        lockModeSelection(false);
        showError(error.message, true);
    }
}

// 🔒 鎖定/解鎖模式選擇
function lockModeSelection(locked) {
    state.modeLocked = locked;
    
    if (elements.modeLocal) {
        if (locked) {
            elements.modeLocal.classList.add('locked');
            elements.modeLocal.style.pointerEvents = 'none';
            elements.modeLocal.style.opacity = '0.6';
        } else {
            elements.modeLocal.classList.remove('locked');
            elements.modeLocal.style.pointerEvents = 'auto';
            elements.modeLocal.style.opacity = '1';
        }
    }
    
    if (elements.modeCloud) {
        if (locked) {
            elements.modeCloud.classList.add('locked');
            elements.modeCloud.style.pointerEvents = 'none';
            elements.modeCloud.style.opacity = '0.6';
        } else {
            elements.modeCloud.classList.remove('locked');
            elements.modeCloud.style.pointerEvents = 'auto';
            elements.modeCloud.style.opacity = '1';
        }
    }
    
    // 顯示/隱藏鎖定提示
    if (elements.modeLockHint) {
        elements.modeLockHint.style.display = locked ? 'block' : 'none';
    }
}

// 顯示錯誤訊息（支援重試）
function showError(message, allowRetry = false) {
    if (elements.errorSection) {
        elements.errorSection.style.display = 'block';
    }
    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
    }
    
    // 隱藏進度和排隊區塊
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    if (elements.resultSection) {
        elements.resultSection.style.display = 'none';
    }
    
    // 隱藏上傳區域
    if (elements.uploadArea && elements.uploadArea.parentElement) {
        elements.uploadArea.parentElement.style.display = 'none';
    }
    
    // 更新重試按鈕
    if (elements.retryBtn) {
        if (allowRetry && state.lastFile && state.retryAttempts < state.maxRetryAttempts) {
            elements.retryBtn.style.display = 'block';
            elements.retryBtn.textContent = `重試 (${state.retryAttempts}/${state.maxRetryAttempts})`;
        } else {
            elements.retryBtn.style.display = 'none';
        }
    }
}

async function downloadResult() {
    if (!state.taskId) return;
    
    try {
        const response = await fetch(`/api/tasks/${state.taskId}/result`);
        if (!response.ok) {
            throw new Error('下載失敗');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `會議記錄_${state.taskId}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('下載失敗:', error);
        alert('下載失敗，請重試');
    }
}

// WebSocket 心跳 - 使用獨立的 interval ID 以便清理
let heartbeatIntervalId = null;

// ===== WebSocket =====
function connectWebSocket(taskId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`;
    
    state.websocket = new WebSocket(wsUrl);
    
    state.websocket.onopen = () => {
        console.log('WebSocket 已連接');
    };
    
    state.websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleProgressUpdate(message);
    };
    
    state.websocket.onclose = () => {
        console.log('WebSocket 已斷開');
        // 清理心跳 interval
        if (heartbeatIntervalId) {
            clearInterval(heartbeatIntervalId);
            heartbeatIntervalId = null;
        }
    };
    
    state.websocket.onerror = (error) => {
        console.error('WebSocket 錯誤:', error);
    };
    
    // 心跳 - 清理之前的 interval（如果存在）
    if (heartbeatIntervalId) {
        clearInterval(heartbeatIntervalId);
    }
    heartbeatIntervalId = setInterval(() => {
        if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
            state.websocket.send('ping');
        }
    }, 30000);
}

function handleProgressUpdate(message) {
    const progress = message.progress || 0;
    
    // 更新進度條
    if (elements.progressBar) {
        elements.progressBar.style.width = `${progress}%`;
    }
    if (elements.progressPercent) {
        elements.progressPercent.textContent = `${Math.round(progress)}%`;
    }
    if (elements.progressText) {
        elements.progressText.textContent = message.message || '處理中...';
    }
    
    // 顯示進度區塊
    if (elements.progressSection) {
        elements.progressSection.style.display = 'block';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    
    // 更新階段
    const stages = document.querySelectorAll('.stage');
    stages.forEach(stage => {
        stage.classList.remove('active', 'completed');
    });
    
    // 根據進度決定當前階段
    let currentStage = 0;
    if (progress < 30) {
        currentStage = 0;
    } else if (progress < 70) {
        currentStage = 1;
    } else {
        currentStage = 2;
    }
    
    stages.forEach((stage, index) => {
        if (index < currentStage) {
            stage.classList.add('completed');
        } else if (index === currentStage) {
            stage.classList.add('active');
        }
    });
    
    // 如果完成，顯示結果
    if (message.status === 'completed') {
        showResult(message);
    }
    
    // 如果失敗，顯示錯誤
    if (message.status === 'failed') {
        showError(message.message || '處理失敗，請重試', true);
    }
}

function showQueueStatus(result) {
    if (elements.queueSection) {
        elements.queueSection.style.display = 'block';
    }
    
    if (elements.uploadArea && elements.uploadArea.parentElement) {
        elements.uploadArea.parentElement.style.display = 'none';
    }
    
    if (elements.queuePosition) {
        elements.queuePosition.textContent = result.queue_position || 'N/A';
    }
    
    if (elements.queueStatus) {
        const minutes = Math.ceil((result.estimated_wait_seconds || 0) / 60);
        elements.queueStatus.textContent = `預計等待: ${minutes} 分鐘`;
    }
}

async function showResult(message) {
    if (elements.resultSection) {
        elements.resultSection.style.display = 'block';
    }
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    
    if (elements.resultPreview) {
        // 如果有預覽內容，顯示前 1000 字
        if (message.preview) {
            elements.resultPreview.textContent = message.preview;
        } else {
            elements.resultPreview.textContent = '已完成，請下載檔案查看詳細內容。';
        }
    }
}

function resetUI() {
    state.taskId = null;
    state.lastFile = null;
    state.retryAttempts = 0;
    
    if (state.websocket) {
        state.websocket.close();
        state.websocket = null;
    }
    
    // 清理心跳 interval
    if (heartbeatIntervalId) {
        clearInterval(heartbeatIntervalId);
        heartbeatIntervalId = null;
    }
    
    // 重置所有區塊
    if (elements.uploadArea && elements.uploadArea.parentElement) {
        elements.uploadArea.parentElement.style.display = 'block';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.resultSection) {
        elements.resultSection.style.display = 'none';
    }
    if (elements.errorSection) {
        elements.errorSection.style.display = 'none';
    }
    
    // 重置進度
    if (elements.progressBar) {
        elements.progressBar.style.width = '0%';
    }
    if (elements.progressPercent) {
        elements.progressPercent.textContent = '0%';
    }
    if (elements.progressText) {
        elements.progressText.textContent = '準備中...';
    }
    
    // 重置階段
    document.querySelectorAll('.stage').forEach(stage => {
        stage.classList.remove('active', 'completed');
    });
    
    // 清空自訂 Prompt
    if (elements.userPrompt) {
        elements.userPrompt.value = '';
    }
    
    // 重置文件輸入
    if (elements.fileInput) {
        elements.fileInput.value = '';
    }
    
    // 🔓 解鎖模式選擇
    lockModeSelection(false);
    
    // 更新健康狀態
    checkHealth();
}

// ===== 事件處理 =====
function setupEventListeners() {
    // 模式選擇
    if (elements.modeLocal) {
        elements.modeLocal.addEventListener('click', () => selectMode('local'));
    }
    if (elements.modeCloud) {
        elements.modeCloud.addEventListener('click', () => {
            if (!elements.modeCloud.classList.contains('disabled')) {
                selectMode('cloud');
            }
        });
    }
    
    // 上傳區域
    if (elements.uploadArea) {
        elements.uploadArea.addEventListener('dragover', handleDragOver);
        elements.uploadArea.addEventListener('dragleave', handleDragLeave);
        elements.uploadArea.addEventListener('drop', handleDrop);
        elements.uploadArea.addEventListener('click', () => {
            elements.fileInput.click();
        });
    }
    
    // 檔案輸入
    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', handleFileSelect);
    }
    
    // 操作按鈕
    if (elements.copyBtn) {
        elements.copyBtn.addEventListener('click', copyResult);
    }
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadResult);
    }
    if (elements.resetBtn) {
        elements.resetBtn.addEventListener('click', resetUI);
    }
    // 重試按鈕 - 重新上傳相同檔案
    if (elements.retryBtn) {
        elements.retryBtn.addEventListener('click', () => {
            if (state.lastFile) {
                uploadFile(state.lastFile, true);
            }
        });
    }
}

function selectMode(mode) {
    state.currentMode = mode;
    
    // 更新 UI
    if (elements.modeLocal) {
        elements.modeLocal.classList.toggle('selected', mode === 'local');
    }
    if (elements.modeCloud) {
        elements.modeCloud.classList.toggle('selected', mode === 'cloud');
    }
    
    // 更新頁尾
    if (elements.footerMode) {
        if (mode === 'local') {
            elements.footerMode.textContent = '🔒 本地模式：完全離線，資料不外傳';
            elements.footerMode.className = 'footer-mode local';
        } else {
            elements.footerMode.textContent = '☁️ 雲端模式：使用 Gemini API';
            elements.footerMode.className = 'footer-mode cloud';
        }
    }
}

function handleDragOver(e) {
    e.preventDefault();
    elements.uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    elements.uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    elements.uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    // 驗證檔案大小
    const maxSize = (state.config?.max_file_size_mb || 100) * 1024 * 1024;
    if (file.size > maxSize) {
        showError(`檔案過大，上限: ${state.config?.max_file_size_mb || 100}MB`);
        return;
    }
    
    // 驗證檔案類型
    const allowedExtensions = state.config?.allowed_extensions || [];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
        showError(`不支援的檔案格式: ${fileExt}`);
        return;
    }
    
    // 上傳檔案
    uploadFile(file);
}

function copyResult() {
    if (elements.resultPreview) {
        const text = elements.resultPreview.textContent;
        navigator.clipboard.writeText(text).then(() => {
            alert('已複製到剪貼板');
        }).catch(err => {
            console.error('複製失敗:', err);
        });
    }
}
