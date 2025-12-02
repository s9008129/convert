#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ollama 本地 LLM 客戶端
支援同步/串流、連線檢測、模型管理

技術細節：
- 使用 httpx 支援 HTTP/2 和更好的錯誤處理
- 支援串流回應以提升使用者體驗
- 完整的上下文視窗管理
- 自動重試機制
"""
import httpx
import json
import logging
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class OllamaResponse:
    """Ollama 回應資料結構"""
    response: str
    done: bool
    total_duration: Optional[int] = None  # 奈秒
    load_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None
    
    @property
    def tokens_per_second(self) -> Optional[float]:
        """計算每秒 token 數"""
        if self.eval_count and self.eval_duration:
            return self.eval_count / (self.eval_duration / 1e9)
        return None


class OllamaError(Exception):
    """Ollama 客戶端錯誤基類"""
    pass


class OllamaConnectionError(OllamaError):
    """連線錯誤"""
    pass


class OllamaTimeoutError(OllamaError):
    """超時錯誤"""
    pass


class OllamaModelError(OllamaError):
    """模型錯誤"""
    pass


class OllamaClient:
    """
    本地 Ollama LLM 客戶端
    
    功能特點：
    - 支援 generate 和 chat 兩種 API
    - 串流輸出支援
    - 自動連線重試
    - 詳細效能統計
    - 上下文視窗管理
    """
    
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 600  # 10 分鐘
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        model: str = "llama3.1:8b",
        num_ctx: int = 32768,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None
    ):
        """
        初始化 Ollama 客戶端
        
        Args:
            base_url: Ollama API 位址
            model: 使用的模型名稱
            num_ctx: 上下文視窗大小（token 數）
            timeout: 請求超時時間（秒）
            max_retries: 最大重試次數
            retry_delay: 重試延遲（秒）
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES
        self.retry_delay = retry_delay if retry_delay is not None else self.RETRY_DELAY
        
        logger.info("[Ollama] 初始化客戶端")
        logger.info("[Ollama] 服務位址: %s", self.base_url)
        logger.info("[Ollama] 模型: %s", model)
        logger.info("[Ollama] 上下文視窗: %d tokens", num_ctx)
    
    @contextmanager
    def _get_client(self):
        """獲取並自動關閉 HTTP 客戶端"""
        client = httpx.Client(timeout=httpx.Timeout(self.timeout))
        try:
            yield client
        finally:
            client.close()
    
    def _make_request(
        self, 
        endpoint: str, 
        payload: Dict[str, Any],
        stream: bool = False
    ) -> httpx.Response:
        """
        發送 HTTP 請求（帶重試機制）
        
        Args:
            endpoint: API 端點
            payload: 請求內容
            stream: 是否串流
        
        Returns:
            HTTP 回應
        """
        url = f"{self.base_url}{endpoint}"
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                with self._get_client() as client:
                    if stream:
                        return client.stream("POST", url, json=payload)
                    else:
                        response = client.post(url, json=payload)
                        response.raise_for_status()
                        return response
                    
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning("[Ollama] 請求超時 (嘗試 %d/%d)", attempt + 1, self.max_retries)
                
            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code
                
                if status == 404:
                    raise OllamaModelError("模型不存在: %s" % self.model)
                elif status == 503:
                    logger.warning("[Ollama] 服務暫時不可用，重試中...")
                else:
                    raise OllamaError("HTTP 錯誤 %d: %s" % (status, e.response.text))
                    
            except httpx.RequestError as e:
                last_error = e
                logger.warning("[Ollama] 連線錯誤: %s", e)
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        if isinstance(last_error, httpx.TimeoutException):
            raise OllamaTimeoutError("請求超時 (%d秒)" % self.timeout)
        raise OllamaConnectionError("連線失敗: %s" % last_error)
    
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        生成文字回應
        
        Args:
            prompt: 使用者提示詞
            system_prompt: 系統提示詞
            temperature: 生成溫度 (0-1)
            max_tokens: 最大輸出 token 數
            stream: 是否串流輸出
            on_token: 串流時的回調函數
        
        Returns:
            生成的文字
        """
        # 組合完整提示詞
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        
        # 對於多語言模型（如 Gemma3），強制使用極低溫度以確保語言一致性
        # 若 temperature > 0.15，自動降低至 0.1
        effective_temperature = min(temperature, 0.15) if temperature > 0.15 else temperature
        
        if effective_temperature != temperature:
            logger.info(
                "[Ollama] 溫度自動調整: %.2f → %.2f (多語言約束)",
                temperature,
                effective_temperature
            )
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": stream,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": effective_temperature,
                "num_predict": max_tokens
            }
        }
        
        logger.info("[Ollama] 開始生成，模型: %s", self.model)
        logger.info("[Ollama] 輸入長度: %d 字元", len(full_prompt))
        
        start_time = time.time()
        
        if stream:
            return self._generate_stream(payload, on_token)
        else:
            return self._generate_sync(payload, start_time)
    
    def _generate_sync(self, payload: Dict[str, Any], start_time: float) -> str:
        """同步生成"""
        response = self._make_request("/api/generate", payload)
        result = response.json()
        
        output = result.get("response", "")
        elapsed = time.time() - start_time
        
        logger.info("[Ollama] 生成完成，輸出長度: %d 字元", len(output))
        logger.info("[Ollama] 耗時: %.1f 秒", elapsed)
        
        # 顯示效能統計
        self._log_performance_stats(result)
        
        return output
    
    def _log_performance_stats(self, result: Dict[str, Any]) -> None:
        """記錄效能統計資訊"""
        if "eval_count" in result and "eval_duration" in result:
            tokens = result["eval_count"]
            duration = result["eval_duration"] / 1e9
            speed = tokens / duration if duration > 0 else 0
            logger.info("[Ollama] 速度: %.1f tokens/秒", speed)
    
    def _generate_stream(
        self, 
        payload: Dict[str, Any],
        on_token: Optional[Callable[[str], None]]
    ) -> str:
        """串流生成"""
        url = "%s/api/generate" % self.base_url
        full_response = []
        
        with httpx.Client(timeout=httpx.Timeout(self.timeout)) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            
                            if token:
                                full_response.append(token)
                                if on_token:
                                    on_token(token)
                                    
                        except json.JSONDecodeError:
                            continue
        
        return "".join(full_response)
    
    def chat(
        self, 
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        聊天 API（推薦用於多輪對話）
        
        Args:
            messages: 訊息列表 [{"role": "system/user/assistant", "content": "..."}]
            temperature: 生成溫度
            max_tokens: 最大輸出 token 數
            stream: 是否串流輸出
            on_token: 串流時的回調函數
        
        Returns:
            助手的回應
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        logger.info("[Ollama] 開始 Chat，訊息數: %d", len(messages))
        
        if stream:
            return self._chat_stream(payload, on_token)
        else:
            return self._chat_sync(payload)
    
    def _chat_sync(self, payload: Dict[str, Any]) -> str:
        """同步聊天"""
        response = self._make_request("/api/chat", payload)
        result = response.json()
        return result.get("message", {}).get("content", "")
    
    def _chat_stream(
        self, 
        payload: Dict[str, Any],
        on_token: Optional[Callable[[str], None]]
    ) -> str:
        """串流聊天"""
        url = "%s/api/chat" % self.base_url
        full_response = []
        
        with httpx.Client(timeout=httpx.Timeout(self.timeout)) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            
                            if content:
                                full_response.append(content)
                                if on_token:
                                    on_token(content)
                                    
                        except json.JSONDecodeError:
                            continue
        
        return "".join(full_response)
    
    def is_running(self) -> bool:
        """檢查 Ollama 服務是否運行"""
        try:
            with self._get_client() as client:
                client._timeout = httpx.Timeout(5)  # 覆蓋為短超時
                response = client.get("%s/api/tags" % self.base_url)
                return response.status_code == 200
        except Exception:
            return False
    
    def wait_for_service(self, timeout: int = 30, interval: float = 1.0) -> bool:
        """
        等待 Ollama 服務啟動
        
        Args:
            timeout: 最長等待時間（秒）
            interval: 檢查間隔（秒）
        
        Returns:
            服務是否可用
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.is_running():
                return True
            time.sleep(interval)
        return False
    
    def list_models(self) -> List[str]:
        """列出可用的模型"""
        try:
            with self._get_client() as client:
                client._timeout = httpx.Timeout(10)
                response = client.get("%s/api/tags" % self.base_url)
                response.raise_for_status()
                result = response.json()
                return [m["name"] for m in result.get("models", [])]
        except Exception as e:
            logger.warning("[Ollama] 無法列出模型: %s", e)
            return []
    
    def has_model(self, model_name: Optional[str] = None) -> bool:
        """檢查模型是否存在"""
        model = model_name or self.model
        models = self.list_models()
        
        if not models:
            return False
        
        # 完全匹配
        if model in models:
            return True
        
        # 部分匹配（處理 tag）
        for m in models:
            if model in m or m in model:
                return True
        
        return False
    
    def get_model_info(self, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """取得模型詳細資訊"""
        model = model_name or self.model
        
        try:
            with self._get_client() as client:
                client._timeout = httpx.Timeout(10)
                response = client.post(
                    "%s/api/show" % self.base_url,
                    json={"name": model}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning("[Ollama] 無法取得模型資訊: %s", e)
            return None
    
    def pull_model(
        self, 
        model_name: Optional[str] = None,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        下載模型
        
        Args:
            model_name: 模型名稱
            on_progress: 進度回調 (status, progress)
        
        Returns:
            是否成功
        """
        model = model_name or self.model
        url = "%s/api/pull" % self.base_url
        
        logger.info("[Ollama] 開始下載模型: %s", model)
        
        try:
            with httpx.Client(timeout=httpx.Timeout(3600)) as client:
                with client.stream("POST", url, json={"name": model}) as response:
                    response.raise_for_status()
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                status = data.get("status", "")
                                
                                # 計算進度
                                if "completed" in data and "total" in data:
                                    progress = data["completed"] / data["total"] * 100
                                else:
                                    progress = 0
                                
                                if on_progress:
                                    on_progress(status, progress)
                                    
                            except json.JSONDecodeError:
                                continue
            
            logger.info("[Ollama] 模型下載完成: %s", model)
            return True
            
        except Exception as e:
            logger.error("[Ollama] 模型下載失敗: %s", e)
            return False
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文字的 token 數量
        
        中文約 1.5-2 字元/token
        英文約 4 字元/token
        """
        # 簡單啟發式估算
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        return int(chinese_chars / 1.5 + other_chars / 4)
    
    def can_fit_context(self, text: str, safety_margin: float = 0.8) -> bool:
        """
        檢查文字是否能放入上下文視窗
        
        Args:
            text: 要檢查的文字
            safety_margin: 安全邊際（預留空間給輸出）
        
        Returns:
            是否能放入
        """
        estimated_tokens = self.estimate_tokens(text)
        max_input = int(self.num_ctx * safety_margin)
        
        return estimated_tokens <= max_input


# 便捷函數
def create_client(
    base_url: str = OllamaClient.DEFAULT_BASE_URL,
    model: str = "llama3.1:8b",
    **kwargs
) -> OllamaClient:
    """建立 Ollama 客戶端的便捷函數"""
    return OllamaClient(base_url=base_url, model=model, **kwargs)


def quick_generate(prompt: str, model: str = "llama3.1:8b", **kwargs) -> str:
    """快速生成文字"""
    client = create_client(model=model)
    return client.generate(prompt, **kwargs)
