/**
 * MeetingScribe 前端應用程式
 * v2.1
 */

// 全域狀態
const state = {
    currentMode: 'local',
    taskId: null,
    websocket: null,
    config: null
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
    footerMode: document.getElementById('footerMode')
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
        const health = await response.json();
        
        // 更新系統狀態
        if (elements.systemStatus) {
            elements.systemStatus.textContent = health.status === 'healthy' ? '正常' : '異常';
            elements.systemStatus.className = `status-value ${health.status === 'healthy' ? 'online' : 'offline'}`;
        }
        
        // 更新 GPU 狀態
        if (elements.gpuStatus) {
            if (health.gpu_available) {
                elements.gpuStatus.textContent = health.gpu_name || 'GPU';
                elements.gpuStatus.className = 'status-value online';
            } else {
                elements.gpuStatus.textContent = 'CPU 模式';
                elements.gpuStatus.className = 'status-value';
            }
        }
        
        // 更新排隊狀態
        if (elements.queueCount) {
            elements.queueCount.textContent = health.queue_status.total_queued;
        }
        
        // 更新雲端模式可用性
        if (!health.gemini_available) {
            if (elements.cloudWarning) {
                elements.cloudWarning.style.display = 'block';
            }
            if (elements.modeCloud) {
                elements.modeCloud.classList.add('disabled');
            }
        } else {
            if (elements.cloudWarning) {
                elements.cloudWarning.style.display = 'none';
            }
            if (elements.modeCloud) {
                elements.modeCloud.classList.remove('disabled');
            }
        }
        
    } catch (error) {
        console.error('健康檢查失敗:', error);
        if (elements.systemStatus) {
            elements.systemStatus.textContent = '無法連接';
            elements.systemStatus.className = 'status-value offline';
        }
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_mode', state.currentMode);
    
    const userPrompt = elements.userPrompt.value.trim();
    if (userPrompt) {
        formData.append('user_prompt', userPrompt);
    }
    
    try {
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
        showError(error.message);
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
    }, 25000);
}

function handleProgressUpdate(message) {
    console.log('進度更新:', message);
    
    // 更新排隊資訊
    if (message.queue_position) {
        if (elements.queuePosition) {
            elements.queuePosition.textContent = `第 ${message.queue_position} 位`;
        }
        if (elements.queueTotal) {
            elements.queueTotal.textContent = message.queue_total || 0;
        }
        
        // 更新狀態文字
        if (elements.queueStatus) {
            if (message.queue_position === 1) {
                elements.queueStatus.textContent = '即將處理';
            } else {
                elements.queueStatus.textContent = '排隊中';
            }
        }
    }
    
    // 根據狀態更新 UI
    switch (message.status) {
        case 'queued':
            showQueueSection();
            break;
            
        case 'pending':
        case 'transcribing':
        case 'summarizing':
            hideQueueSection();
            showProgress(message);
            break;
            
        case 'completed':
            showCompleted();
            break;
            
        case 'failed':
            showError(message.message || '處理失敗');
            break;
    }
}

// ===== UI 更新函數 =====
function showQueueStatus(result) {
    if (elements.queueSection) {
        elements.queueSection.style.display = 'block';
    }
    if (elements.queuePosition) {
        elements.queuePosition.textContent = `第 ${result.queue_position} 位`;
    }
    if (elements.queueTotal) {
        elements.queueTotal.textContent = result.queue_position;
    }
    
    // 更新狀態文字
    if (elements.queueStatus) {
        if (result.queue_position === 1) {
            elements.queueStatus.textContent = '即將處理';
        } else {
            elements.queueStatus.textContent = '排隊中';
        }
    }
    
    // 隱藏其他區塊
    if (elements.uploadArea && elements.uploadArea.parentElement) {
        elements.uploadArea.parentElement.style.display = 'none';
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
}

function showQueueSection() {
    if (elements.queueSection) {
        elements.queueSection.style.display = 'block';
    }
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
}

function hideQueueSection() {
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
}

function showProgress(message) {
    if (elements.progressSection) {
        elements.progressSection.style.display = 'block';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    
    // 更新進度條
    const progress = message.progress || 0;
    if (elements.progressBar) {
        elements.progressBar.style.width = `${progress}%`;
    }
    if (elements.progressPercent) {
        elements.progressPercent.textContent = `${Math.round(progress)}%`;
    }
    if (elements.progressText) {
        elements.progressText.textContent = message.stage || message.message || '處理中...';
    }
    
    // 更新階段指示器
    updateStages(message.status);
}

function updateStages(status) {
    const stages = document.querySelectorAll('.stage');
    const statusMap = {
        'pending': 0,
        'uploading': 0,
        'transcribing': 1,
        'summarizing': 2,
        'completed': 3
    };
    
    const currentStage = statusMap[status] || 0;
    
    stages.forEach((stage, index) => {
        stage.classList.remove('active', 'completed');
        if (index < currentStage) {
            stage.classList.add('completed');
        } else if (index === currentStage) {
            stage.classList.add('active');
        }
    });
}

async function showCompleted() {
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.resultSection) {
        elements.resultSection.style.display = 'block';
    }
    
    // 載入結果
    try {
        const response = await fetch(`/api/tasks/${state.taskId}/result`);
        if (!response.ok) {
            throw new Error('載入結果失敗');
        }
        const text = await response.text();
        
        // 使用 textContent 來防止 XSS
        // 創建 pre 元素以保留格式
        if (elements.resultPreview) {
            const preElement = document.createElement('pre');
            preElement.style.whiteSpace = 'pre-wrap';
            preElement.style.wordWrap = 'break-word';
            preElement.textContent = text;
            elements.resultPreview.innerHTML = '';
            elements.resultPreview.appendChild(preElement);
        }
        
    } catch (error) {
        console.error('載入結果失敗:', error);
        if (elements.resultPreview) {
            elements.resultPreview.textContent = '載入結果失敗';
        }
    }
}

function showError(message) {
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    if (elements.errorSection) {
        elements.errorSection.style.display = 'block';
    }
    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
    }
}

function resetUI() {
    state.taskId = null;
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
        elements.uploadArea.addEventListener('click', () => {
            if (elements.fileInput) elements.fileInput.click();
        });
        elements.uploadArea.addEventListener('dragover', handleDragOver);
        elements.uploadArea.addEventListener('dragleave', handleDragLeave);
        elements.uploadArea.addEventListener('drop', handleDrop);
    }
    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', handleFileSelect);
    }
    
    // 按鈕
    if (elements.copyBtn) {
        elements.copyBtn.addEventListener('click', copyResult);
    }
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadResult);
    }
    if (elements.resetBtn) {
        elements.resetBtn.addEventListener('click', resetUI);
    }
    if (elements.retryBtn) {
        elements.retryBtn.addEventListener('click', resetUI);
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
        alert(`檔案大小超過限制（最大 ${state.config?.max_file_size_mb || 100}MB）`);
        return;
    }
    
    // 驗證檔案類型
    const allowedExtensions = state.config?.allowed_extensions || ['.mp3', '.mp4', '.wav', '.m4a', '.mkv'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(ext)) {
        alert(`不支援的檔案格式：${ext}`);
        return;
    }
    
    uploadFile(file);
}

function copyResult() {
    if (!elements.resultPreview) return;
    
    const text = elements.resultPreview.innerText;
    navigator.clipboard.writeText(text).then(() => {
        if (elements.copyBtn) {
            elements.copyBtn.textContent = '✓ 已複製';
            setTimeout(() => {
                elements.copyBtn.textContent = '📋 複製文字';
            }, 2000);
        }
    }).catch(err => {
        console.error('複製失敗:', err);
        alert('複製失敗');
    });
}

// ===== 工具函數 =====
function simpleMarkdownToHtml(markdown) {
    return markdown
        // 標題
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        // 粗體
        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
        // 斜體
        .replace(/\*(.*)\*/gim, '<em>$1</em>')
        // 列表
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        // 換行
        .replace(/\n/gim, '<br>')
        // 引用區塊
        .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
        // 分隔線
        .replace(/^---$/gim, '<hr>')
        // details 標籤（保留原樣）
        .replace(/<details>/g, '<details>')
        .replace(/<\/details>/g, '</details>')
        .replace(/<summary>(.*)<\/summary>/g, '<summary>$1</summary>');
}
