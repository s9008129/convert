# Docker 部署經驗指南

> 本指南基於 PromptCraft 專案的成功 Docker 部署經驗，提供可複製的最佳實踐，適用於跨平台部署（macOS、Linux、Windows）。

## 📚 目錄

1. [第一性原理分析](#第一性原理分析)
2. [核心設計理念](#核心設計理念)
3. [完整檔案範本](#完整檔案範本)
4. [Windows 部署詳細步驟](#windows-部署詳細步驟)
5. [常見問題排解](#常見問題排解)
6. [測試驗證清單](#測試驗證清單)

---

## 第一性原理分析

### 1. Docker 部署的核心需求

```
目標：將應用程式封裝成可移植的容器
  ↓
問題拆解：
  ├── 如何建構映像？ → Dockerfile
  ├── 如何管理服務？ → docker-compose.yml
  ├── 如何排除不需要的檔案？ → .dockerignore
  ├── 如何傳遞設定？ → 環境變數
  ├── 如何確保安全？ → 非 root 用戶、獨立網路
  └── 如何簡化操作？ → 部署腳本
```

### 2. 跨平台部署的關鍵考量

| 考量項目 | macOS/Linux | Windows | 解決方案 |
|---------|-------------|---------|----------|
| 容器內連接主機服務 | `host.docker.internal` | `host.docker.internal` | 使用 `extra_hosts` 設定 |
| Shell 腳本 | `.sh` (Bash) | `.ps1` (PowerShell) | 提供兩種腳本 |
| 換行符號 | LF | CRLF | `.dockerignore` 排除 |
| 路徑格式 | `/path/to/file` | `C:\path\to\file` | 容器內統一使用 Linux 路徑 |

### 3. 不影響現有服務的原則

```
原則 1: 使用獨立網路
  → 建立專屬 bridge network，不與其他容器共享

原則 2: 使用非衝突 port
  → 選擇非常用 port（如 3100），避免 80, 443, 3000, 8080 等

原則 3: 容器命名規範
  → 使用專案名稱作為前綴，如 promptcraft-app
```

---

## 核心設計理念

### 多階段建構 (Multi-Stage Build)

多階段建構是減少映像大小、提升安全性的關鍵：

```
Stage 1: deps (安裝依賴)
  → 只包含 package.json，快取依賴安裝
  
Stage 2: builder (建構應用)
  → 複製程式碼，執行建構
  
Stage 3: runner (生產環境)
  → 只複製必要檔案，使用非 root 用戶執行
```

### 環境變數分層設計

```
優先級（高到低）：
1. docker-compose.yml 中的 environment
2. .env.docker 檔案
3. Dockerfile 中的 ENV 指令
4. 程式碼中的預設值
```

---

## 完整檔案範本

### 1. Dockerfile（通用 Node.js/Next.js 版本）

```dockerfile
# ============================================
# 專案名稱 Dockerfile
# Multi-Stage Build for Production
# 
# 特性：
# - 多階段建構，最小化映像大小
# - 支援跨平台 (macOS, Linux, Windows)
# - 非 root 用戶執行，增強安全性
# - 獨立網路，不影響其他容器服務
# ============================================

# ============================================
# Stage 1: Dependencies (安裝依賴)
# ============================================
FROM node:20-alpine AS deps
WORKDIR /app

# 安裝必要系統依賴
RUN apk add --no-cache libc6-compat

# 複製 package 檔案並安裝依賴
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

# ============================================
# Stage 2: Builder (建構應用程式)
# ============================================
FROM node:20-alpine AS builder
WORKDIR /app

# 複製依賴
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 設定建構時環境變數
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# 建構應用程式
RUN npm run build

# ============================================
# Stage 3: Runner (生產環境)
# ============================================
FROM node:20-alpine AS runner
WORKDIR /app

# 設定生產環境變數
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 建立非 root 用戶 (增強安全性)
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 安裝 wget 用於健康檢查
RUN apk add --no-cache wget

# 複製 public 資料夾
COPY --from=builder /app/public ./public

# 複製 standalone 建構輸出
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 切換到非 root 用戶
USER nextjs

# 暴露端口 (使用非衝突 port)
EXPOSE 3100

# 設定 Runtime 環境變數
ENV PORT=3100
ENV HOSTNAME="0.0.0.0"

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3100/api/health || exit 1

# 啟動應用程式
CMD ["node", "server.js"]
```

### 2. Dockerfile（Python 應用版本）

```dockerfile
# ============================================
# Python 應用 Dockerfile
# Multi-Stage Build for Production
# ============================================

# ============================================
# Stage 1: Builder (建構環境)
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 建立虛擬環境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 複製並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runner (生產環境)
# ============================================
FROM python:3.11-slim AS runner

WORKDIR /app

# 建立非 root 用戶
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appuser

# 複製虛擬環境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 複製應用程式碼
COPY --chown=appuser:appgroup . .

# 建立必要目錄
RUN mkdir -p /app/input /app/output /app/temp /app/logs && \
    chown -R appuser:appgroup /app

# 切換用戶
USER appuser

# 暴露端口（如果需要）
# EXPOSE 8000

# 健康檢查（根據應用調整）
# HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
#     CMD curl -f http://localhost:8000/health || exit 1

# 啟動命令
CMD ["python", "main.py"]
```

### 3. docker-compose.yml（通用範本）

```yaml
# ============================================
# Docker Compose 配置
# 
# 設計原則：
# 1. 使用獨立網路，不影響現有服務
# 2. 使用非衝突 port
# 3. 支援連接主機服務 (host.docker.internal)
# 4. 可移轉至 Windows 工作站
# ============================================

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: myapp-container
    restart: unless-stopped
    
    # Port 映射 (使用非衝突 port)
    ports:
      - "3100:3100"
    
    # 環境變數配置
    environment:
      - NODE_ENV=production
      - PORT=3100
      - HOSTNAME=0.0.0.0
      # 自訂環境變數從 .env 檔案讀取
      - API_KEY=${API_KEY:-}
      - DATABASE_URL=${DATABASE_URL:-}
    
    # 使用獨立網路，不影響其他容器
    networks:
      - myapp-net
    
    # 健康檢查
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3100/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # macOS/Windows 連接主機服務
    extra_hosts:
      - "host.docker.internal:host-gateway"
    
    # 資料持久化（可選）
    volumes:
      - app-data:/app/data
      - ./logs:/app/logs
    
    # 資源限制（可選）
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

# 資料卷
volumes:
  app-data:

# 獨立網路配置 - 不影響現有 Docker 服務
networks:
  myapp-net:
    driver: bridge
    name: myapp-net
```

### 4. .dockerignore（完整版）

```
# ============================================
# Docker 忽略檔案
# 加快建構速度，減少映像大小
# ============================================

# 依賴目錄
node_modules
.pnp
.pnp.js
__pycache__
*.pyc
.venv
venv
env

# 建構輸出
.next
out
dist
build
*.egg-info

# 測試
coverage
.pytest_cache
.coverage

# 開發工具
.git
.gitignore
.vscode
.idea
*.swp
*.swo

# 環境變數 (敏感資訊)
.env
.env.local
.env.development
.env.development.local
.env.test
.env.test.local
.env.production
.env.production.local

# 日誌
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS 檔案
.DS_Store
Thumbs.db

# 文件（保留 README）
*.md
!README.md
LICENSE

# Docker 相關
Dockerfile*
docker-compose*.yml
.docker

# 其他
*.bak
*.tmp
.turbo
```

### 5. .env.example（範本）

```bash
# ============================================
# 環境變數範本
# 複製此檔案為 .env 並填入實際值
# ============================================

# === 應用設定 ===
NODE_ENV=production
PORT=3100

# === API 金鑰 ===
API_KEY=your-api-key-here

# === 資料庫連線 ===
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# === 外部服務 ===
# 如果使用本地 LLM (如 LM Studio)
LOCAL_LLM_BASE_URL=http://host.docker.internal:1234/v1
LOCAL_LLM_MODEL=your-model-name
```

### 6. deploy-docker.ps1（Windows PowerShell 部署腳本）

```powershell
# ============================================
# Windows Docker 部署腳本
# 
# 使用方式:
#   .\deploy-docker.ps1 [command]
#
# 可用命令:
#   build   - 建構 Docker 映像
#   up      - 啟動服務
#   down    - 停止服務
#   restart - 重啟服務
#   logs    - 查看日誌
#   status  - 查看狀態
#   test    - 執行測試
#   clean   - 清理舊映像
# ============================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# 設定
$ProjectName = "myapp"
$ContainerName = "myapp-container"
$Port = 3100
$NetworkName = "myapp-net"

# 切換到腳本所在目錄
Set-Location $PSScriptRoot

function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "[SUCCESS] $args" -ForegroundColor Green }
function Write-Warn { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

# 檢查 Docker
function Test-Docker {
    try {
        docker info | Out-Null
        return $true
    } catch {
        Write-Err "Docker 未運行，請先啟動 Docker Desktop"
        exit 1
    }
}

# 建構映像
function Invoke-Build {
    Write-Info "開始建構 Docker 映像..."
    docker compose build --no-cache
    if ($LASTEXITCODE -eq 0) {
        Write-Success "映像建構完成"
    } else {
        Write-Err "映像建構失敗"
        exit 1
    }
}

# 啟動服務
function Invoke-Up {
    Write-Info "啟動服務..."
    docker compose up -d
    
    Write-Info "等待服務啟動 (最多 60 秒)..."
    $maxAttempts = 12
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 5
        $attempt++
        
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:$Port/api/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($health) {
                Write-Success "服務啟動成功"
                Write-Host ""
                Write-Host "======================================================" -ForegroundColor Green
                Write-Host "  應用已就緒！" -ForegroundColor Green
                Write-Host "======================================================" -ForegroundColor Green
                Write-Host "  應用網址: http://localhost:$Port" -ForegroundColor Cyan
                Write-Host "======================================================" -ForegroundColor Green
                return
            }
        } catch {
            Write-Info "等待服務就緒... ($attempt/$maxAttempts)"
        }
    }
    
    Write-Err "服務啟動逾時，請查看日誌: .\deploy-docker.ps1 logs"
    exit 1
}

# 停止服務
function Invoke-Down {
    Write-Info "停止服務..."
    docker compose down
    Write-Success "服務已停止"
}

# 重啟服務
function Invoke-Restart {
    Invoke-Down
    Invoke-Up
}

# 查看日誌
function Invoke-Logs {
    docker compose logs -f --tail 100
}

# 查看狀態
function Invoke-Status {
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  Docker 狀態" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "容器狀態:"
    docker compose ps
    Write-Host ""
    
    Write-Info "健康檢查:"
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$Port/api/health" -TimeoutSec 5
        $health | ConvertTo-Json
        Write-Success "服務運行正常"
    } catch {
        Write-Warn "服務未回應或未運行"
    }
}

# 執行測試
function Invoke-Test {
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  測試套件" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $passed = 0
    $failed = 0
    
    # 測試 1: 容器運行狀態
    Write-Info "測試 1: 容器運行狀態"
    $containerStatus = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
    if ($containerStatus -match "Up") {
        Write-Success "  容器正在運行"
        $passed++
    } else {
        Write-Err "  容器未運行"
        $failed++
    }
    
    # 測試 2: 健康檢查端點
    Write-Info "測試 2: 健康檢查端點"
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$Port/api/health" -TimeoutSec 5
        Write-Success "  健康檢查端點回應正常"
        $passed++
    } catch {
        Write-Err "  健康檢查端點無回應"
        $failed++
    }
    
    # 測試 3: 首頁載入
    Write-Info "測試 3: 首頁載入"
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "  首頁載入成功 (HTTP 200)"
            $passed++
        } else {
            Write-Err "  首頁載入失敗 (HTTP $($response.StatusCode))"
            $failed++
        }
    } catch {
        Write-Err "  首頁載入失敗"
        $failed++
    }
    
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  測試結果: $passed 通過, $failed 失敗" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    
    if ($failed -eq 0) {
        Write-Success "所有測試通過"
    } else {
        Write-Err "部分測試失敗"
    }
}

# 清理
function Invoke-Clean {
    Write-Info "清理舊的 Docker 映像..."
    docker compose down --rmi local --volumes --remove-orphans 2>$null
    docker image prune -f
    Write-Success "清理完成"
}

# 顯示說明
function Show-Help {
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  Docker 部署腳本 (Windows)" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "使用方式: .\deploy-docker.ps1 [command]"
    Write-Host ""
    Write-Host "可用命令:"
    Write-Host "  build   - 建構 Docker 映像"
    Write-Host "  up      - 啟動服務"
    Write-Host "  down    - 停止服務"
    Write-Host "  restart - 重啟服務"
    Write-Host "  logs    - 查看日誌"
    Write-Host "  status  - 查看狀態"
    Write-Host "  test    - 執行測試"
    Write-Host "  clean   - 清理舊映像"
    Write-Host ""
    Write-Host "快速開始:"
    Write-Host "  .\deploy-docker.ps1 build; .\deploy-docker.ps1 up"
    Write-Host ""
}

# 主程式
Test-Docker

switch ($Command.ToLower()) {
    "build" { Invoke-Build }
    "up" { Invoke-Up }
    "down" { Invoke-Down }
    "restart" { Invoke-Restart }
    "logs" { Invoke-Logs }
    "status" { Invoke-Status }
    "test" { Invoke-Test }
    "clean" { Invoke-Clean }
    default { Show-Help }
}
```

### 7. deploy-docker.sh（macOS/Linux Bash 部署腳本）

```bash
#!/bin/bash
# ============================================
# Docker 部署腳本 (macOS/Linux)
# 
# 使用方式:
#   ./deploy-docker.sh [command]
#
# 可用命令:
#   build   - 建構 Docker 映像
#   up      - 啟動服務
#   down    - 停止服務
#   restart - 重啟服務
#   logs    - 查看日誌
#   status  - 查看狀態
#   test    - 執行測試
#   clean   - 清理舊映像
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 專案配置
PROJECT_NAME="myapp"
CONTAINER_NAME="myapp-container"
PORT=3100
NETWORK_NAME="myapp-net"

# 切換到腳本所在目錄
cd "$(dirname "$0")"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 檢查 Docker
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未運行，請先啟動 Docker Desktop"
        exit 1
    fi
}

# 建構映像
build() {
    log_info "開始建構 Docker 映像..."
    docker compose build --no-cache
    log_success "映像建構完成 ✓"
}

# 啟動服務
up() {
    log_info "啟動服務..."
    docker compose up -d
    
    log_info "等待服務啟動 (最多 60 秒)..."
    local max_attempts=12
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        sleep 5
        attempt=$((attempt + 1))
        
        if curl -s http://localhost:${PORT}/api/health > /dev/null 2>&1; then
            log_success "服務啟動成功 ✓"
            echo ""
            echo "═══════════════════════════════════════════════════"
            echo -e "${GREEN}  🚀 應用已就緒！${NC}"
            echo "═══════════════════════════════════════════════════"
            echo -e "  📍 應用網址: ${BLUE}http://localhost:${PORT}${NC}"
            echo "═══════════════════════════════════════════════════"
            return 0
        fi
        
        log_info "等待服務就緒... ($attempt/$max_attempts)"
    done
    
    log_error "服務啟動逾時，請查看日誌: ./deploy-docker.sh logs"
    exit 1
}

# 停止服務
down() {
    log_info "停止服務..."
    docker compose down
    log_success "服務已停止 ✓"
}

# 重啟服務
restart() {
    down
    up
}

# 查看日誌
logs() {
    docker compose logs -f --tail=100
}

# 查看狀態
status() {
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  📊 Docker 狀態"
    echo "═══════════════════════════════════════════════════"
    echo ""
    
    log_info "容器狀態:"
    docker compose ps
    echo ""
    
    log_info "健康檢查:"
    if curl -s http://localhost:${PORT}/api/health 2>/dev/null; then
        echo ""
        log_success "服務運行正常 ✓"
    else
        log_warn "服務未回應或未運行"
    fi
}

# 執行測試
test_service() {
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  🧪 測試套件"
    echo "═══════════════════════════════════════════════════"
    echo ""
    
    local passed=0
    local failed=0
    
    # 測試 1: 容器運行狀態
    log_info "測試 1: 容器運行狀態"
    if docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Status}}" | grep -q "Up"; then
        log_success "  ✓ 容器正在運行"
        passed=$((passed + 1))
    else
        log_error "  ✗ 容器未運行"
        failed=$((failed + 1))
    fi
    
    # 測試 2: 健康檢查端點
    log_info "測試 2: 健康檢查端點"
    if curl -s http://localhost:${PORT}/api/health | grep -q '"status"'; then
        log_success "  ✓ 健康檢查端點回應正常"
        passed=$((passed + 1))
    else
        log_error "  ✗ 健康檢查端點無回應"
        failed=$((failed + 1))
    fi
    
    # 測試 3: 首頁載入
    log_info "測試 3: 首頁載入"
    local homepage_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT}/ 2>/dev/null)
    if [ "$homepage_status" = "200" ]; then
        log_success "  ✓ 首頁載入成功 (HTTP 200)"
        passed=$((passed + 1))
    else
        log_error "  ✗ 首頁載入失敗 (HTTP $homepage_status)"
        failed=$((failed + 1))
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  📋 測試結果: $passed 通過, $failed 失敗"
    echo "═══════════════════════════════════════════════════"
    
    if [ $failed -eq 0 ]; then
        log_success "所有測試通過 ✓"
    else
        log_error "部分測試失敗"
    fi
}

# 清理
clean() {
    log_info "清理舊的 Docker 映像..."
    docker compose down --rmi local --volumes --remove-orphans 2>/dev/null || true
    docker image prune -f
    log_success "清理完成 ✓"
}

# 主程式
check_docker

case "${1:-help}" in
    build) build ;;
    up) up ;;
    down) down ;;
    restart) restart ;;
    logs) logs ;;
    status) status ;;
    test) test_service ;;
    clean) clean ;;
    *)
        echo ""
        echo "═══════════════════════════════════════════════════"
        echo "  🐳 Docker 部署腳本"
        echo "═══════════════════════════════════════════════════"
        echo ""
        echo "使用方式: ./deploy-docker.sh [command]"
        echo ""
        echo "可用命令:"
        echo "  build   - 建構 Docker 映像"
        echo "  up      - 啟動服務"
        echo "  down    - 停止服務"
        echo "  restart - 重啟服務"
        echo "  logs    - 查看日誌"
        echo "  status  - 查看狀態"
        echo "  test    - 執行測試"
        echo "  clean   - 清理舊映像"
        echo ""
        echo "快速開始:"
        echo "  ./deploy-docker.sh build && ./deploy-docker.sh up"
        echo ""
        ;;
esac
```

### 8. next.config.mjs（Next.js 專用）

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 關鍵：啟用 standalone 輸出模式
  output: 'standalone',
  
  // 禁用靜態快取
  headers: async () => [
    {
      source: '/:path*',
      headers: [
        { key: 'Cache-Control', value: 'no-store, no-cache, must-revalidate' },
      ],
    },
  ],
};

export default nextConfig;
```

---

## Windows 部署詳細步驟

### 前置作業

1. **安裝 Docker Desktop for Windows**
   - 下載：https://www.docker.com/products/docker-desktop
   - 安裝時勾選「Use WSL 2 instead of Hyper-V」（建議）
   - 安裝完成後重新啟動電腦

2. **啟用 WSL 2（如果尚未啟用）**
   ```powershell
   # 以管理員身分開啟 PowerShell
   wsl --install
   wsl --set-default-version 2
   ```

3. **驗證 Docker 安裝**
   ```powershell
   docker --version
   docker compose version
   docker run hello-world
   ```

### 部署步驟

1. **取得專案程式碼**
   ```powershell
   # 使用 Git 複製專案
   git clone https://github.com/your-org/your-project.git
   cd your-project
   ```

2. **設定環境變數**
   ```powershell
   # 複製範本
   Copy-Item .env.example .env
   
   # 編輯 .env 檔案，填入實際值
   notepad .env
   ```

3. **建構並啟動**
   ```powershell
   # 方法一：使用部署腳本（推薦）
   .\deploy-docker.ps1 build
   .\deploy-docker.ps1 up
   
   # 方法二：直接使用 docker compose
   docker compose build --no-cache
   docker compose up -d
   ```

4. **驗證部署**
   ```powershell
   .\deploy-docker.ps1 test
   .\deploy-docker.ps1 status
   ```

### 常見 Windows 問題

| 問題 | 解決方案 |
|------|----------|
| PowerShell 執行策略限制 | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Docker Desktop 未啟動 | 從開始選單啟動 Docker Desktop |
| WSL 2 未安裝 | `wsl --install` 並重新啟動 |
| Port 被佔用 | 修改 `docker-compose.yml` 中的 port 映射 |

---

## 常見問題排解

### 1. 連接主機服務失敗

**問題**：容器內無法連接 `host.docker.internal`

**解決方案**：確保 `docker-compose.yml` 中有設定：
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### 2. 映像建構失敗

**問題**：`npm ci` 或 `pip install` 失敗

**解決方案**：
- 檢查網路連線
- 確認 `.dockerignore` 沒有排除必要檔案
- 清理後重建：`docker compose build --no-cache`

### 3. 容器啟動後立即退出

**問題**：容器狀態顯示 `Exited`

**解決方案**：
```bash
# 查看日誌
docker compose logs

# 互動式執行除錯
docker compose run --rm app sh
```

### 4. 健康檢查失敗

**問題**：容器持續顯示 `unhealthy`

**解決方案**：
- 確認健康檢查端點存在
- 增加 `start_period` 給應用更多啟動時間
- 檢查應用是否正確監聽 port

---

## 測試驗證清單

### 部署前檢查

- [ ] Docker Desktop 已啟動
- [ ] 所有必要檔案已準備（Dockerfile, docker-compose.yml, .dockerignore）
- [ ] 環境變數已設定（.env）
- [ ] Port 未被佔用

### 部署後驗證

- [ ] 容器狀態為 `Up`
- [ ] 健康檢查通過 (`healthy`)
- [ ] 首頁可正常訪問
- [ ] API 端點可正常回應
- [ ] 現有服務未受影響

### 跨平台測試

- [ ] macOS 部署成功
- [ ] Linux 部署成功
- [ ] Windows 部署成功

---

## 最佳實踐總結

### ✅ 應該做

1. **使用多階段建構** - 減少映像大小
2. **使用非 root 用戶** - 提升安全性
3. **使用獨立網路** - 不影響其他服務
4. **設定健康檢查** - 確保服務可用性
5. **提供部署腳本** - 簡化操作流程
6. **使用 .dockerignore** - 加速建構
7. **環境變數外部化** - 提高可配置性

### ❌ 不應該做

1. 在 Dockerfile 中寫死敏感資訊
2. 使用常用 port（80, 443, 3000, 8080）
3. 以 root 用戶執行容器
4. 忽略健康檢查
5. 在映像中包含 node_modules 或 .git

---

## 快速開始模板

複製以下檔案到你的專案：

```
your-project/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── deploy-docker.sh      # macOS/Linux
└── deploy-docker.ps1     # Windows
```

然後執行：

```bash
# macOS/Linux
./deploy-docker.sh build && ./deploy-docker.sh up

# Windows
.\deploy-docker.ps1 build; .\deploy-docker.ps1 up
```

---

**文件版本**: 1.0.0  
**最後更新**: 2024-01-15  
**基於專案**: PromptCraft
