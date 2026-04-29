"""
前端上傳流程回歸測試。

這個測試直接在 Node.js 中載入 frontend/js/app.js，
驗證使用者選到合法檔案後，不會在呼叫 uploadFile 之前就拋出前端錯誤。
"""

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_JS = PROJECT_ROOT / "frontend" / "js" / "app.js"


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
