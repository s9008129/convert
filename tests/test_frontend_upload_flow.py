"""
前端上傳流程回歸測試。

這個測試直接在 Node.js 中載入 frontend/js/app.js，
驗證使用者選到合法檔案後，不會在呼叫 uploadFile 之前就拋出前端錯誤。
"""

import subprocess
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_JS = PROJECT_ROOT / "frontend" / "js" / "app.js"


def _render_gpu_status(accelerator, extras=None):
    """以 Node vm 載入 app.js，餵入 mock /api/health 後回傳狀態列文字。"""
    node_script = """
const fs = require('fs');
const vm = require('vm');

const elements = new Map();
function makeElement(id) {
  if (!elements.has(id)) {
    elements.set(id, {
      style: {},
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      addEventListener() {}, click() {}, parentElement: { style: {} },
      dataset: {}, textContent: '', value: '', disabled: false, className: ''
    });
  }
  return elements.get(id);
}

const health = Object.assign({
  status: 'healthy',
  version: '4.7.2',
  gpu_available: false,
  device_info: { accelerator: __ACCELERATOR__ },
  queue_status: { total_queued: 0 }
}, __EXTRAS__);

const context = {
  console,
  document: {
    addEventListener() {},
    getElementById(id) { return makeElement(id); },
    querySelectorAll() { return []; }
  },
  window: { location: { protocol: 'http:', host: 'localhost:9527' } },
  WebSocket: function () {},
  fetch: async () => ({ ok: true, json: async () => health }),
  setInterval() { return 1; }, clearInterval() {}, alert() {}
};

vm.createContext(context);
vm.runInContext(fs.readFileSync(__APP_JS__, 'utf8'), context);
const rendered = vm.runInContext(
  '(async () => { await checkHealth(); return elements.gpuStatus.textContent; })()',
  context
);
rendered.then(
  (text) => { console.log(text); },
  (error) => { console.error(error && error.stack || error); process.exit(1); }
);
"""
    node_script = node_script.replace("__APP_JS__", repr(str(APP_JS)))
    node_script = node_script.replace("__ACCELERATOR__", json.dumps(accelerator))
    node_script = node_script.replace("__EXTRAS__", json.dumps(extras or {}))

    result = subprocess.run(
        ["node", "-e", node_script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout.strip().splitlines()[-1]


def test_frontend_renders_apple_engine_status_for_apple_neural_accelerator():
    """macOS 的 apple-neural 應顯示 Apple 本機引擎；既有 Mac 分支不受影響。"""
    assert _render_gpu_status("apple-neural") == "Apple 神經引擎（本機）"
    assert _render_gpu_status("mlx-metal") == "Apple Silicon（MLX/Metal）"
    assert _render_gpu_status("mps", {"gpu_available": True, "gpu_name": "M4 GPU"}) == "Apple GPU：M4 GPU"


def test_frontend_windows_accelerators_render_no_apple_wording():
    """Windows 常見 accelerator（cpu/cuda）不得出現任何 Apple/Xcode/helper 字樣。"""
    forbidden = ("apple", "xcode", "swift", "helper", "神經", "speechanalyzer", "apple-speech-cli")

    cpu_text = _render_gpu_status("cpu")
    cuda_text = _render_gpu_status("cuda", {"gpu_available": True, "gpu_name": "NVIDIA RTX 4090"})

    assert "CPU" in cpu_text
    assert "CUDA" in cuda_text and "RTX 4090" in cuda_text
    for rendered in (cpu_text, cuda_text):
        lowered = rendered.lower()
        assert not any(token in lowered for token in forbidden), rendered


def test_handle_file_triggers_upload_without_runtime_error():
    """合法音檔應能通過前端驗證並進入 uploadFile 流程。"""
    node_script = """
const fs = require('fs');
const vm = require('vm');

function makeElement() {
  return {
    style: {},
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains() { return false; }
    },
    addEventListener() {},
    click() {},
    parentElement: { style: {} },
    dataset: {},
    textContent: '',
    value: '',
    disabled: false
  };
}

const context = {
  console,
  document: {
    addEventListener() {},
    getElementById() { return makeElement(); },
    querySelectorAll() { return []; }
  },
  window: {
    location: { protocol: 'http:', host: 'localhost:9527' },
    URL: {
      createObjectURL() { return 'blob:test'; },
      revokeObjectURL() {}
    }
  },
  WebSocket: function () {},
  FormData: function () {
    this.append = () => {};
  },
  fetch: async () => ({
    ok: true,
    json: async () => ({}),
    blob: async () => ({})
  }),
  setInterval() { return 1; },
  clearInterval() {},
  alert() {}
};

vm.createContext(context);
vm.runInContext(fs.readFileSync(__APP_JS__, 'utf8'), context);
vm.runInContext(`
  state.config = { allowed_extensions: ['.mp3'], max_file_size_mb: 100 };
  uploadFile = (file) => { globalThis.__uploadTriggered = file.name; };
  handleFile({ name: 'demo.mp3', size: 1024 });
  if (globalThis.__uploadTriggered !== 'demo.mp3') {
    throw new Error('uploadFile was not called');
  }
`, context);
"""
    node_script = node_script.replace("__APP_JS__", repr(str(APP_JS)))

    result = subprocess.run(
        ["node", "-e", node_script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_frontend_renders_actionable_lmstudio_selection_state():
    """LM Studio 的 zero-loaded 狀態應提示處理方式，不把本地模式鎖死。"""
    node_script = """
const fs = require('fs');
const vm = require('vm');

function makeElement() {
  return {
    style: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {}, click() {}, parentElement: { style: {} },
    dataset: {}, textContent: '', value: '', disabled: false
  };
}

const context = {
  console,
  document: {
    addEventListener() {},
    getElementById() { return makeElement(); },
    querySelectorAll() { return []; }
  },
  window: { location: { protocol: 'http:', host: 'localhost:9527' } },
  WebSocket: function () {},
  fetch: async () => ({ ok: true, json: async () => ({}) }),
  setInterval() { return 1; }, clearInterval() {}, alert() {}
};

vm.createContext(context);
vm.runInContext(fs.readFileSync(__APP_JS__, 'utf8'), context);
vm.runInContext(`
  const status = getLocalLlmStatus({device_info: {llm: {
    selection_status: 'LMSTUDIO_NO_LOADED_LLM'
  }}});
  if (!status.text.includes('請載入一個 LLM')) throw new Error(status.text);
`, context);
"""
    node_script = node_script.replace("__APP_JS__", repr(str(APP_JS)))

    result = subprocess.run(
        ["node", "-e", node_script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
