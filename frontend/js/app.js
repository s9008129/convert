/**
 * 政府智慧會議紀錄生成系統 前端應用程式
 * v4.3.1 - 介面改版（政府藍設計系統、三步驟流程列、動態模型資訊顯示）
 *
 * 介面流程（給非技術同仁）：
 * 1) 載入頁面時先檢查系統可用性（API /api/config、/api/health）
 * 2) 使用者選模式並上傳檔案（API /api/upload）
 * 3) 以 WebSocket 接收排隊與進度更新（/ws/tasks/{taskId}）
 * 4) 完成後顯示結果；若失敗則統一顯示錯誤區塊
 */

// 全域狀態（集中管理目前模式、任務編號、WebSocket 與鎖定狀態）
const state = {
    currentMode: 'local',
    currentTemplate: 'general',   // v4.4.0：目前選擇的會議類型模板
    templateLocalOnly: false,     // 目前模板是否強制本地（機敏會議）
    taskId: null,
    websocket: null,
    config: null,
    health: null,            // 最近一次健康檢查結果（供模型資訊顯示）
    modeLocked: false        // 模式是否已鎖定
};

const DEFAULT_MAX_FILE_SIZE_MB = 100;

// 畫面元件對照表（先抓好元件，後續更新畫面會更容易）
const elements = {
    // 狀態欄
    systemStatus: document.getElementById('systemStatus'),
    gpuStatus: document.getElementById('gpuStatus'),
    queueCount: document.getElementById('queueCount'),
    
    // 模式選擇
    modeLocal: document.getElementById('modeLocal'),
    modeCloud: document.getElementById('modeCloud'),
    cloudWarning: document.getElementById('cloudWarning'),

    // 會議類型（v4.4.0；卡片由 /api/config 動態渲染）
    templateSelector: document.getElementById('templateSelector'),
    templateHint: document.getElementById('templateHint'),
    
    // 上傳（v4.3.0：setupSection 為「模式＋上傳」整區，任務開始後一併隱藏）
    setupSection: document.getElementById('setupSection'),
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    maxFileSize: document.getElementById('maxFileSize'),

    // 處理卡（排隊＋進度合併的外層卡片，v4.3.0）
    processCard: document.getElementById('processCard'),
    
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
    downloadBtn: document.getElementById('downloadBtn'),
    downloadDocxBtn: document.getElementById('downloadDocxBtn'),
    downloadTranscriptBtn: document.getElementById('downloadTranscriptBtn'),
    resetBtn: document.getElementById('resetBtn'),
    
    // 錯誤
    errorSection: document.getElementById('errorSection'),
    errorMessage: document.getElementById('errorMessage'),
    resetFromErrorBtn: document.getElementById('resetFromErrorBtn'),
    
    // 頁尾
    footerMode: document.getElementById('footerMode'),
    footerVersion: document.getElementById('footerVersion'),
    
    // 本地模式資訊
    localModelInfo: document.getElementById('localModelInfo'),
    
    // 雲端模式資訊
    cloudModelInfo: document.getElementById('cloudModelInfo'),
    
    // 模式鎖定提示
    modeLockHint: document.getElementById('modeLockHint')
};

// ===== 初始化流程：載入設定、檢查服務狀態、綁定按鈕事件 =====
// 頁面載入後依序完成：讀取設定 → 健康檢查 → 綁定事件
// 這樣可確保使用者看到的按鈕狀態與後端實際能力一致
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setDownloadButtonsEnabled(false);
    void initializeApp();
    
    // 定期檢查健康狀態
    setInterval(checkHealth, 30000);
});

async function initializeApp() {
    await Promise.allSettled([
        loadConfig(),
        checkHealth()
    ]);
}

// ===== 與後端 API 溝通的函式 =====
// 讀取後端設定：例如檔案大小上限、允許副檔名、雲端模式可用性
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`配置載入失敗: ${response.status}`);
        }
        state.config = await response.json();

        // 更新 UI
        if (elements.maxFileSize) {
            elements.maxFileSize.textContent = state.config.max_file_size_mb;
        }

        // 模型名稱到手後刷新模式卡顯示（若健康檢查已先完成）
        if (state.health) {
            updateModelInfo();
        }

        // 渲染會議類型選單（v4.4.0；唯一資料來源為後端模板註冊表）
        renderTemplateOptions(state.config.meeting_templates || []);


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
        state.config = null;
        console.error('載入配置失敗:', error);
    }
}

// 健康檢查：更新「系統狀態/GPU/排隊數」與模式可用性（本地/雲端）
async function checkHealth() {
    try {
        // v3.5.4: 使用 quick 模式，避免 GPU 滿載時阻塞
        const response = await fetch('/api/health?quick=true');
        if (!response.ok) {
            throw new Error('健康檢查失敗');
        }
        
        const data = await response.json();
        
        // 更新頁尾版本號（唯一來源：後端 VERSION 檔，避免前端寫死過期版本）
        if (elements.footerVersion && data.version) {
            elements.footerVersion.textContent = `v${data.version}`;
        }

        // 更新系統狀態
        if (elements.systemStatus) {
            elements.systemStatus.className = data.status === 'healthy' ? 'status-ok' : 'status-error';
            elements.systemStatus.textContent = data.status === 'healthy' ? '系統正常' : '系統異常';
        }
        
        // 更新 GPU 狀態（v3.5.0: 支援 MPS 偵測）
        if (elements.gpuStatus) {
            let gpuText = 'GPU 未偵測';
            let statusClass = 'status-warning';
            
            if (data.gpu_available && data.gpu_name) {
                gpuText = `GPU: ${data.gpu_name}`;
                statusClass = 'status-ok';

                // GPU 存在但 VRAM 正被模型占用（v4.3.2：不再誤報為「未偵測」）
                if (data.device_info && data.device_info.gpu_busy) {
                    gpuText += '（使用中）';
                }

                // 特別處理 MPS
                if (data.gpu_name.includes('MPS') || data.gpu_name.includes('Metal')) {
                    gpuText = `${data.gpu_name}`;
                }
            }
            
            elements.gpuStatus.className = statusClass;
            elements.gpuStatus.textContent = gpuText;
        }
        
        // 更新排隊狀態
        if (elements.queueCount && data.queue_status) {
            elements.queueCount.textContent = `排隊: ${data.queue_status.total_queued}`;
        }
        
        // 更新模式卡的模型資訊（名稱來自 /api/config，可用性來自本次健康檢查）
        state.health = data;
        updateModelInfo();
        
        // 更新本地模式可用性
        if (elements.modeLocal) {
            const localAvailable = data.ollama_available || data.lmstudio_available;
            if (!localAvailable) {
                elements.modeLocal.classList.add('disabled');
            } else {
                elements.modeLocal.classList.remove('disabled');
            }
        }
        
        // 更新雲端模式可用性（機敏模板選取中時，雲端卡維持鎖定）
        if (elements.modeCloud) {
            if (!data.gemini_available || state.templateLocalOnly) {
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

// 模式卡的模型資訊（v4.3.1）：模型名稱以後端 /api/config 為唯一來源，
// 換模型（環境變數／自動解析）後前端自動同步，不得在此寫死
function updateModelInfo() {
    const health = state.health || {};

    if (elements.localModelInfo) {
        const name = state.config?.local_llm_model || '本地 LLM';
        const localAvailable = health.ollama_available || health.lmstudio_available;
        elements.localModelInfo.textContent =
            `使用模型：${name}（${localAvailable ? '已就緒' : '未偵測'}）`;
        elements.localModelInfo.style.color = localAvailable ? '#216E1F' : '#936F38';
    }

    if (elements.cloudModelInfo) {
        const name = state.config?.cloud_llm_model || 'Gemini API';
        elements.cloudModelInfo.textContent =
            `使用模型：${name}（${health.gemini_available ? '已就緒' : '連線失敗'}）`;
        elements.cloudModelInfo.style.color = health.gemini_available ? '#216E1F' : '#B50909';
    }
}

// ===== 會議類型模板（v4.4.0） =====
// 卡片由 /api/config 的 meeting_templates 動態渲染；
// 新增會議類型只需在後端 backend/core/templates.py 註冊，前端零改動。
function renderTemplateOptions(templates) {
    if (!elements.templateSelector) return;

    const list = (templates && templates.length > 0) ? templates : [{
        id: 'general', display_name: '一般會議',
        description: '通用公務會議紀錄', local_only: false, is_default: true
    }];

    elements.templateSelector.replaceChildren();
    list.forEach(template => {
        const card = document.createElement('div');
        card.className = 'template-option';
        card.dataset.template = template.id;
        card.dataset.localOnly = String(Boolean(template.local_only));
        card.setAttribute('role', 'radio');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-checked', 'false');

        const name = document.createElement('div');
        name.className = 't-name';
        name.textContent = template.display_name;
        card.appendChild(name);

        if (template.local_only) {
            const badge = document.createElement('span');
            badge.className = 't-badge';
            badge.textContent = '機敏・僅限本地';
            name.appendChild(badge);
        }

        const desc = document.createElement('div');
        desc.className = 't-desc';
        desc.textContent = template.description || '';
        card.appendChild(desc);

        const choose = () => {
            if (!state.modeLocked) selectTemplate(template.id);
        };
        card.addEventListener('click', choose);
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                choose();
            }
        });

        elements.templateSelector.appendChild(card);
    });

    // 預設選取（後端指定的預設模板，通常為 general）
    const defaultId = state.config?.default_meeting_template || 'general';
    selectTemplate(state.currentTemplate || defaultId);
}

function selectTemplate(templateId) {
    const cards = elements.templateSelector
        ? Array.from(elements.templateSelector.querySelectorAll('.template-option'))
        : [];
    const target = cards.find(card => card.dataset.template === templateId) || cards[0];
    if (!target) return;

    state.currentTemplate = target.dataset.template;
    state.templateLocalOnly = target.dataset.localOnly === 'true';

    cards.forEach(card => {
        const selected = card === target;
        card.classList.toggle('selected', selected);
        card.setAttribute('aria-checked', String(selected));
    });

    // 機敏模板：強制本地模式並鎖定雲端卡（後端另有第二道防線）
    if (state.templateLocalOnly) {
        selectMode('local');
        if (elements.modeCloud) {
            elements.modeCloud.classList.add('disabled');
        }
        if (elements.templateHint) {
            elements.templateHint.textContent =
                '此會議類型涉及機敏內容，僅限本地模式處理（資料不外傳）';
            elements.templateHint.style.display = 'block';
        }
    } else {
        if (elements.templateHint) {
            elements.templateHint.style.display = 'none';
        }
        // 依系統實際能力恢復雲端卡（沿用 /api/config 與健康檢查判斷）
        if (elements.modeCloud) {
            const geminiOk = Boolean(state.config?.gemini_available) &&
                (!state.health || Boolean(state.health.gemini_available));
            elements.modeCloud.classList.toggle('disabled', !geminiOk);
        }
    }
}

// 任務送出後鎖定／解鎖會議類型卡（與模式卡一致的鎖定體驗）
function lockTemplateSelection(locked) {
    if (!elements.templateSelector) return;
    elements.templateSelector.querySelectorAll('.template-option').forEach(card => {
        card.classList.toggle('locked', locked);
        card.style.pointerEvents = locked ? 'none' : 'auto';
        card.style.opacity = locked ? '0.6' : '1';
    });
}

// v4.3.0：頂部三步驟流程列（1=設定與上傳 2=處理中 3=完成下載）
function setWizardStage(stage) {
    document.querySelectorAll('#wizard > li').forEach((li, i) => {
        const n = i + 1;
        li.dataset.state = n < stage ? 'done' : (n === stage ? 'active' : '');
    });
}

// 上傳檔案：送出使用者選擇的音訊/影片，並建立任務開始追蹤進度
// 成功後進入「排隊/進度追蹤」；失敗則進入統一錯誤顯示
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_mode', state.currentMode);
    formData.append('meeting_template', state.currentTemplate);
    
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
        
        // 連接 WebSocket：後續所有進度、排隊位置、完成/失敗訊息都由此接收
        connectWebSocket(result.task_id);
        
    } catch (error) {
        // 解鎖模式選擇（失敗時）
        lockModeSelection(false);
        showError(error.message);
    }
}

function getAllowedExtensions() {
    const configuredExtensions = state.config?.allowed_extensions;
    if (Array.isArray(configuredExtensions) && configuredExtensions.length > 0) {
        return configuredExtensions;
    }

    return (elements.fileInput?.accept || '')
        .split(',')
        .map(value => value.trim().toLowerCase())
        .filter(Boolean);
}

// 🔒 鎖定/解鎖模式選擇
// 目的：任務提交後避免使用者在中途改模式，造成「顯示模式」與「實際處理模式」不一致
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
    
    // 會議類型卡與模式卡一併鎖定（v4.4.0）
    lockTemplateSelection(locked);

    // 顯示/隱藏鎖定提示
    if (elements.modeLockHint) {
        elements.modeLockHint.style.display = locked ? 'block' : 'none';
    }
}

// 顯示錯誤訊息（支援重試）
// 錯誤顯示邏輯：只保留錯誤區塊，隱藏排隊/進度/結果，避免畫面資訊互相衝突
function showError(message) {
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
    if (elements.processCard) {
        elements.processCard.style.display = 'none';
    }
    if (elements.resultSection) {
        elements.resultSection.style.display = 'none';
    }

    // 隱藏「模式＋上傳」整區，只留錯誤卡
    if (elements.setupSection) {
        elements.setupSection.style.display = 'none';
    }
}

// 下載檔名以後端 Content-Disposition 為唯一來源（v4.2.3：YYYYMMDDhhmmss_會議紀錄）
// 後端對中文檔名會使用 RFC 5987 的 filename*=utf-8'' 編碼形式
function filenameFromResponse(response, fallback) {
    const header = response.headers.get('Content-Disposition') || '';
    const star = header.match(/filename\*=utf-8''([^;]+)/i);
    if (star) {
        try {
            return decodeURIComponent(star[1].trim());
        } catch (e) {
            console.warn('檔名解碼失敗，改用預設檔名:', e);
        }
    }
    const plain = header.match(/filename="?([^";]+)"?/);
    if (plain) {
        return plain[1].trim();
    }
    return fallback;
}

// 後端不可用時的備援檔名時間戳（與後端同格式 YYYYMMDDhhmmss）
function timestampForFilename() {
    const d = new Date();
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}` +
        `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function setDownloadButtonsEnabled(enabled) {
    [elements.downloadBtn, elements.downloadDocxBtn, elements.downloadTranscriptBtn].forEach(button => {
        if (button) {
            button.disabled = !enabled;
        }
    });
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
        a.download = filenameFromResponse(response, `${timestampForFilename()}_會議紀錄.md`);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('下載失敗:', error);
        alert('下載失敗，請重試');
    }
}

async function downloadDocxResult() {
    if (!state.taskId) return;
    
    try {
        const response = await fetch(`/api/tasks/${state.taskId}/result?format=docx`);
        if (!response.ok) {
            throw new Error('DOCX 下載失敗');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filenameFromResponse(response, `${timestampForFilename()}_會議紀錄.docx`);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('DOCX 下載失敗:', error);
        alert('Word 文件下載失敗，請重試');
    }
}

async function downloadTranscript() {
    if (!state.taskId) return;

    try {
        const response = await fetch(`/api/tasks/${state.taskId}/transcript`);
        if (!response.ok) {
            const err = await response.json().catch(() => null);
            throw new Error(err?.detail || '逐字稿下載失敗');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filenameFromResponse(response, `${timestampForFilename()}_逐字稿.txt`);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('逐字稿下載失敗:', error);
        alert(error.message || '逐字稿下載失敗，請重試');
    }
}

// WebSocket 心跳 - 使用獨立的 interval ID 以便清理
// 目的：長任務時維持連線活性，降低閒置斷線機率
let heartbeatIntervalId = null;

// ===== WebSocket 即時進度通道 =====
// WebSocket 任務通道：
// - onmessage: 交給 handleProgressUpdate 更新畫面
// - onclose/onerror: 紀錄狀態並清理心跳資源
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

// 更新排隊顯示狀態（讓使用者知道自己目前在隊列中的位置）
// 將畫面切換為「排隊模式」，並呈現目前位置與總排隊數
function updateQueueDisplay(position, total, statusMessage) {
    if (elements.processCard) {
        elements.processCard.style.display = 'block';
    }
    setWizardStage(2);
    if (elements.queueSection) {
        elements.queueSection.style.display = 'block';
    }
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    // 顯示當前排隊人數（total）和您的位置（position）
    if (elements.queuePosition) {
        elements.queuePosition.textContent = position || '--';
    }
    if (elements.queueTotal) {
        elements.queueTotal.textContent = total || 0;
    }
    if (elements.queueStatus) {
        elements.queueStatus.textContent = statusMessage || '排隊中';
    }
}

function handleProgressUpdate(message) {
    const progress = message.progress || 0;
    const status = message.status;
    
    // 如果任務在排隊中，維持排隊畫面，先不顯示進度條
    if (status === 'queued' && message.queue_position) {
        // 修正：使用 queue_position 作為當前排隊人數（而非 total_queued）
        const totalQueued = message.queue_total || 0;
        updateQueueDisplay(message.queue_position, totalQueued, message.message);
        return;
    }
    
    // 任務開始處理後，切換到進度畫面
    if (elements.queueSection && status !== 'queued') {
        elements.queueSection.style.display = 'none';
    }
    
    // 更新進度條與文字說明（由後端訊息驅動畫面）
    if (elements.progressBar) {
        elements.progressBar.style.width = `${progress}%`;
    }
    if (elements.progressPercent) {
        elements.progressPercent.textContent = `${Math.round(progress)}%`;
    }
    if (elements.progressText) {
        elements.progressText.textContent = message.message || '處理中...';
    }
    
    // 顯示進度區塊（合併卡 + 內層進度）
    if (elements.processCard) {
        elements.processCard.style.display = 'block';
    }
    if (elements.setupSection) {
        elements.setupSection.style.display = 'none';
    }
    setWizardStage(2);
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
    
    // 根據百分比推估當前階段（純 UI 呈現，不影響後端真實任務狀態）
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
    
    // 任務完成：顯示結果區塊（可複製/下載）
    if (message.status === 'completed') {
        setWizardStage(3);
        showResult(message);
    }
    
    // 任務失敗：導向統一錯誤顯示邏輯
    if (message.status === 'failed') {
        showError(message.message || '處理失敗，請重試');
    }
}

// 首次上傳成功時先顯示排隊資訊，後續由 WebSocket 持續更新
function showQueueStatus(result) {
    if (elements.setupSection) {
        elements.setupSection.style.display = 'none';
    }

    const minutes = Math.ceil((result.estimated_wait_seconds || 0) / 60);
    updateQueueDisplay(result.queue_position, null, `預計等待: ${minutes} 分鐘`);
}

async function showResult(message) {
    if (message && message.task_id) {
        state.taskId = message.task_id;
    }

    if (elements.resultSection) {
        elements.resultSection.style.display = 'block';
        elements.resultSection.dataset.taskId = state.taskId || '';
    }
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    if (elements.processCard) {
        elements.processCard.style.display = 'none';
    }

    setDownloadButtonsEnabled(Boolean(state.taskId));
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
    
    // 重置所有區塊（回到一開始可再次上傳的畫面）
    if (elements.setupSection) {
        elements.setupSection.style.display = '';  // 清空 inline 值，恢復 CSS grid 排版
    }
    setWizardStage(1);
    if (elements.queueSection) {
        elements.queueSection.style.display = 'none';
    }
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.processCard) {
        elements.processCard.style.display = 'none';
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
    
    // 重置文件輸入
    if (elements.fileInput) {
        elements.fileInput.value = '';
    }
    
    // 🔓 解鎖模式選擇
    lockModeSelection(false);
    
    // 更新健康狀態
    checkHealth();
}

// ===== 事件處理：滑鼠點擊、拖拉上傳、按鈕操作 =====
// 將使用者操作（點擊/拖放/按鈕）轉成對應流程函式
function setupEventListeners() {
    // 模式選擇（滑鼠＋鍵盤 Enter/Space，無障礙全鍵盤可操作）
    if (elements.modeLocal) {
        elements.modeLocal.addEventListener('click', () => selectMode('local'));
        elements.modeLocal.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectMode('local');
            }
        });
    }
    if (elements.modeCloud) {
        const selectCloud = () => {
            // 機敏模板強制本地：即使 class 被繞過也不得切雲端（後端另有 400 防線）
            if (!elements.modeCloud.classList.contains('disabled') && !state.templateLocalOnly) {
                selectMode('cloud');
            }
        };
        elements.modeCloud.addEventListener('click', selectCloud);
        elements.modeCloud.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectCloud();
            }
        });
    }

    // 上傳區域（滑鼠拖放＋點擊＋鍵盤 Enter/Space）
    if (elements.uploadArea) {
        elements.uploadArea.addEventListener('dragover', handleDragOver);
        elements.uploadArea.addEventListener('dragleave', handleDragLeave);
        elements.uploadArea.addEventListener('drop', handleDrop);
        elements.uploadArea.addEventListener('click', () => {
            elements.fileInput.click();
        });
        elements.uploadArea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                elements.fileInput.click();
            }
        });
    }
    
    // 檔案輸入
    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', handleFileSelect);
    }
    
    // 操作按鈕
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadResult);
    }
    if (elements.downloadDocxBtn) {
        elements.downloadDocxBtn.addEventListener('click', downloadDocxResult);
    }
    if (elements.downloadTranscriptBtn) {
        elements.downloadTranscriptBtn.addEventListener('click', downloadTranscript);
    }
    if (elements.resetBtn) {
        elements.resetBtn.addEventListener('click', resetUI);
    }
    
    // 錯誤頁面的重新開始按鈕
    if (elements.resetFromErrorBtn) {
        elements.resetFromErrorBtn.addEventListener('click', resetUI);
    }
}

function selectMode(mode) {
    state.currentMode = mode;
    
    // 更新 UI（selected class＋aria-checked 同步，供鍵盤與報讀器使用）
    if (elements.modeLocal) {
        elements.modeLocal.classList.toggle('selected', mode === 'local');
        elements.modeLocal.setAttribute('aria-checked', String(mode === 'local'));
    }
    if (elements.modeCloud) {
        elements.modeCloud.classList.toggle('selected', mode === 'cloud');
        elements.modeCloud.setAttribute('aria-checked', String(mode === 'cloud'));
    }

    // 更新頁尾說明：讓使用者隨時確認目前資料處理路徑
    if (elements.footerMode) {
        if (mode === 'local') {
            elements.footerMode.textContent = '本地模式：完全離線，資料不外傳';
            elements.footerMode.className = 'footer-mode local';
        } else {
            elements.footerMode.textContent = '雲端模式：使用 Gemini API';
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
    // 驗證檔案大小（在前端先擋下過大檔案，減少無效等待）
    const maxSize = (state.config?.max_file_size_mb || DEFAULT_MAX_FILE_SIZE_MB) * 1024 * 1024;
    if (file.size > maxSize) {
        showError(`檔案過大，上限: ${state.config?.max_file_size_mb || DEFAULT_MAX_FILE_SIZE_MB}MB`);
        return;
    }
    
    // 驗證檔案類型（僅接受後端允許的副檔名）
    const allowedExtensions = getAllowedExtensions();
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
        showError(`不支援的檔案格式: ${fileExt}`);
        return;
    }
    
    setDownloadButtonsEnabled(false);
    uploadFile(file);
}
