"""
MeetingScribe LLM 摘要服務
支援本地模式（Ollama）、LM Studio（OpenAI 相容）和雲端模式（Gemini API）
"""

import re
import httpx
from typing import Optional
from openai import OpenAI, AsyncOpenAI
from datetime import datetime, timedelta

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import ProcessingMode


class SummarizationService:
    """
    LLM 摘要生成服務
    支援本地模式（Ollama + Gemma3:12B）、LM Studio（gpt-oss-20b）和雲端模式（Gemini API）
    """
    
    def __init__(self):
        self._ollama_client: Optional[httpx.AsyncClient] = None
        self._lmstudio_client: Optional[OpenAI] = None
        self._gemini_client: Optional[OpenAI] = None
        self._gemini_async_client: Optional[AsyncOpenAI] = None
        
        # 分層智能檢查快取（減少API調用成本）
        self._gemini_health_check_cache = {
            "last_check_time": None,
            "status": None,
            "ttl_seconds": 86400  # 24 小時快取
        }
        
    async def _get_ollama_client(self) -> httpx.AsyncClient:
        """取得 Ollama HTTP 客戶端"""
        if not self._ollama_client:
            self._ollama_client = httpx.AsyncClient(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=300.0
            )
        return self._ollama_client
    
    def _get_lmstudio_client(self) -> OpenAI:
        """取得 LM Studio 客戶端（OpenAI 相容介面）"""
        if not self._lmstudio_client:
            self._lmstudio_client = OpenAI(
                base_url=settings.LMSTUDIO_BASE_URL,
                api_key="lm-studio"  # LM Studio 不需要真實 API Key
            )
        return self._lmstudio_client
    
    def _get_gemini_api_key(self) -> str:
        """安全地取得 Gemini API Key"""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("未設定 GEMINI_API_KEY 環境變數")
        return api_key
    
    def _get_gemini_client(self) -> OpenAI:
        """取得 Gemini API 客戶端（OpenAI 相容介面）"""
        if not self._gemini_client:
            api_key = self._get_gemini_api_key()
            self._gemini_client = OpenAI(
                api_key=api_key,
                base_url=settings.GEMINI_BASE_URL
            )
        return self._gemini_client
    
    def _get_gemini_async_client(self) -> AsyncOpenAI:
        """取得 Gemini API 異步客戶端（OpenAI 相容介面）"""
        if not self._gemini_async_client:
            api_key = self._get_gemini_api_key()
            self._gemini_async_client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.GEMINI_BASE_URL
            )
        return self._gemini_async_client
    
    async def summarize(
        self,
        transcript: str,
        mode: ProcessingMode = ProcessingMode.LOCAL,
        user_prompt: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        生成會議摘要
        
        Args:
            transcript: 逐字稿文字
            mode: 處理模式（local/cloud）- local 會自動選擇 Ollama 或 LM Studio
            user_prompt: 使用者自訂 prompt（可選）
            progress_callback: 進度回調函數
            
        Returns:
            會議摘要（Markdown 格式）
        """
        if progress_callback:
            progress_callback(65.0, "生成摘要中...")
        
        # 組合 prompt（使用者自訂格式優先權最高）
        system_prompt = settings.DEFAULT_SYSTEM_PROMPT
        
        if user_prompt:
            # 使用者自訂格式具有最高優先權
            # 將使用者指令置於前端，並明確標示為「必須遵守」
            user_instruction = f"""【優先指令 - 使用者自訂格式要求】

以下是使用者指定的會議記錄格式或特殊要求，這些指令具有最高優先權，必須嚴格遵守：

<user_custom_format>
{user_prompt}
</user_custom_format>

請務必按照上述使用者自訂格式進行輸出。若使用者格式與系統預設格式衝突，以使用者格式為準。

---

"""
            system_prompt = user_instruction + system_prompt
        
        user_message = f"以下是會議的逐字稿，請整理成會議記錄：\n\n{transcript}"
        
        try:
            if mode == ProcessingMode.CLOUD:
                # 雲端模式：使用 Gemini API
                summary = await self._summarize_with_gemini(system_prompt, user_message, progress_callback)
            else:
                # 本地模式：自動偵測並選擇可用的引擎（Ollama 優先，其次 LM Studio）
                summary = await self._summarize_with_local_llm(system_prompt, user_message, progress_callback)
            
            if progress_callback:
                progress_callback(95.0, "摘要生成完成")
            
            return summary
            
        except Exception as e:
            log.error(f"摘要生成失敗: {e}")
            raise
    
    async def _summarize_with_local_llm(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        使用本地 LLM 生成摘要
        自動偵測並選擇可用的引擎（Ollama 優先，其次 LM Studio）
        """
        # 優先嘗試 Ollama
        ollama_available = await self.check_ollama_health()
        if ollama_available:
            log.info("使用 Ollama 本地模式")
            return await self._summarize_with_ollama(system_prompt, user_message, progress_callback)
        
        # 其次嘗試 LM Studio
        lmstudio_available = await self.check_lmstudio_health()
        if lmstudio_available:
            log.info("使用 LM Studio 本地模式")
            return await self._summarize_with_lmstudio(system_prompt, user_message, progress_callback)
        
        # 都不可用，拋出錯誤
        raise RuntimeError("本地 LLM 不可用：請確認 Ollama 或 LM Studio 已啟動")
    
    async def _summarize_with_ollama(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """使用 Ollama 本地模式生成摘要（針對 Gemma 3 優化）"""
        client = await self._get_ollama_client()
        
        try:
            # 進度更新：開始生成摘要
            if progress_callback:
                progress_callback(65.0, "載入 Ollama 模型...")
            
            # 針對 Gemma 3 模型的最佳參數配置
            # temperature 低：減少隨機性，提高格式遵循度
            # num_ctx 高：確保長逐字稿不被截斷
            # repeat_penalty：避免重複輸出
            response = await client.post(
                "/api/chat",
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,       # 低溫提高格式遵循度
                        "top_p": 0.9,             # 控制輸出多樣性
                        "top_k": 40,              # 限制候選詞數量
                        "repeat_penalty": 1.15,   # 防止重複（比預設 1.1 稍高）
                        "num_ctx": 8192,          # 擴大上下文視窗
                        "num_predict": 4096,      # 允許生成更長的輸出
                        "stop": ["---\n\n## 原始逐字稿"]  # 停止在逐字稿之前
                    }
                }
            )
            response.raise_for_status()
            
            if progress_callback:
                progress_callback(85.0, "處理摘要結果...")
            
            data = response.json()
            summary = data.get("message", {}).get("content", "")
            
            # 後處理：清理不需要的前綴
            summary = self._clean_ollama_output(summary)
            
            # 檢查摘要是否為空
            if not summary or not summary.strip():
                log.warning("Ollama 摘要生成結果為空")
                raise RuntimeError("摘要生成失敗：結果為空")
            
            log.info(f"Ollama 摘要生成成功，模型: {settings.LOCAL_LLM_MODEL}")
            return summary
            
        except httpx.ConnectError:
            log.error("無法連接到 Ollama 服務，請確認 Ollama 是否正在運行")
            raise RuntimeError("Ollama 服務不可用，請確認 Ollama 是否正在運行")
        except Exception as e:
            log.error(f"Ollama 摘要生成失敗: {e}")
            raise
    
    def _clean_ollama_output(self, summary: str) -> str:
        """
        清理 Ollama 輸出中的常見問題
        - 移除 LLM 常加的前綴（「好的，我來整理...」）
        - 確保以正確的標題開頭
        """
        import re
        
        # 常見的無用前綴模式
        prefixes_to_remove = [
            r"^好的[，,]?\s*我[來来][整幫]理.*?[：:。\n]",
            r"^以下是.*?會議記錄[：:。\n]",
            r"^我[來来]為[您你]整理.*?[：:。\n]",
            r"^根據逐字稿[，,]?\s*",
            r"^OK[,，]?\s*",
            r"^Sure[,，]?\s*",
        ]
        
        cleaned = summary.strip()
        for pattern in prefixes_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        # 確保以 # 會議記錄 開頭
        if not cleaned.startswith("#"):
            # 嘗試找到第一個 # 標題
            match = re.search(r"^#\s", cleaned, re.MULTILINE)
            if match:
                cleaned = cleaned[match.start():]
        
        return cleaned.strip()
    
    async def _summarize_with_lmstudio(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """使用 LM Studio（OpenAI 相容）生成摘要"""
        client = self._get_lmstudio_client()
        
        try:
            # 進度更新：開始生成摘要
            if progress_callback:
                progress_callback(65.0, "載入 LM Studio 模型...")
            
            # 強制設定低溫以確保中文輸出
            effective_temperature = 0.1
            
            response = client.chat.completions.create(
                model=settings.LMSTUDIO_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=effective_temperature
            )
            
            if progress_callback:
                progress_callback(85.0, "處理摘要結果...")
            
            summary = response.choices[0].message.content
            
            # 檢查摘要是否為空
            if not summary or not summary.strip():
                log.warning("LM Studio 摘要生成結果為空")
                raise RuntimeError("摘要生成失敗：結果為空")
            
            log.info(f"LM Studio 摘要生成成功，模型: {settings.LMSTUDIO_MODEL}")
            return summary
            
        except Exception as e:
            log.error(f"LM Studio 摘要生成失敗: {e}")
            raise RuntimeError(f"LM Studio 服務不可用: {e}")
    
    async def _summarize_with_gemini(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """使用 Gemini API 雲端模式生成摘要（異步流式響應）"""
        client = self._get_gemini_async_client()
        
        try:
            # 使用異步流式響應以獲得實時進度更新
            summary_parts = []
            chunk_count = 0
            
            # 創建異步流式請求
            async with await client.chat.completions.create(
                model=settings.GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                stream=True  # 啟用流式響應
            ) as response:
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        summary_parts.append(content)
                        chunk_count += 1
                        
                        # 定期更新進度（每 5 個 chunk 更新一次）
                        if progress_callback and chunk_count % 5 == 0:
                            progress = 65.0 + min((chunk_count / 10) * 10, 30)  # 65-95%
                            progress_callback(progress, f"生成摘要中... ({chunk_count} chunks)")
            
            summary = "".join(summary_parts)
            
            # 檢查摘要是否為空
            if not summary or not summary.strip():
                log.warning("Gemini 摘要生成結果為空")
                raise RuntimeError("摘要生成失敗：結果為空")
            
            log.info(f"Gemini 摘要生成成功，模型: {settings.GEMINI_MODEL}，接收 {chunk_count} 個 chunks")
            return summary
            
        except Exception as e:
            log.error(f"Gemini 摘要生成失敗: {e}")
            raise
    
    async def check_ollama_health(self) -> bool:
        """檢查 Ollama 服務是否可用"""
        try:
            client = await self._get_ollama_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def check_lmstudio_health(self) -> bool:
        """檢查 LM Studio 服務是否可用"""
        try:
            client = self._get_lmstudio_client()
            client.models.list()
            return True
        except Exception:
            return False
    
    def check_gemini_available(self) -> bool:
        """檢查 Gemini API 是否已配置"""
        try:
            self._get_gemini_api_key()
            return True
        except ValueError:
            return False
    
    async def check_gemini_health(self, force_refresh: bool = False) -> bool:
        """
        層級2：每日 Gemini API 健康檢查（輕量級，1次API調用/天）
        
        特點：
        - 自動快取24小時，避免重複調用
        - 使用最輕量的API端點（models.list()）
        - 多用戶共用快取結果（節省成本）
        - force_refresh=True 強制重新檢查
        
        Args:
            force_refresh: 是否強制刷新快取
            
        Returns:
            bool: API 是否可用
        """
        now = datetime.now()
        cache = self._gemini_health_check_cache
        
        # 檢查快取是否仍有效
        if not force_refresh and cache["last_check_time"]:
            age_seconds = (now - cache["last_check_time"]).total_seconds()
            if age_seconds < cache["ttl_seconds"] and cache["status"] is not None:
                log.debug(f"使用快取 Gemini 健康檢查結果（緩存年齡: {age_seconds:.0f}秒）")
                return cache["status"]
        
        # 執行實際的 API 檢查
        log.info("執行 Gemini API 健康檢查...")
        try:
            if not self.check_gemini_available():
                cache["status"] = False
                cache["last_check_time"] = now
                return False
            
            # 使用最輕量的 API 呼叫：列出可用模型
            client = self._get_gemini_client()
            response = client.models.list()
            
            # 驗證是否能取得模型列表
            result = len(list(response.models)) > 0
            
            cache["status"] = result
            cache["last_check_time"] = now
            log.info(f"Gemini 健康檢查完成：{'✓ 可用' if result else '✗ 不可用'}")
            return result
            
        except Exception as e:
            log.warning(f"Gemini 健康檢查失敗: {str(e)}")
            cache["status"] = False
            cache["last_check_time"] = now
            return False
    
    def reset_gemini_health_cache(self):
        """
        重置 Gemini 健康檢查快取
        用於環境變數更新或配置變更時
        """
        self._gemini_health_check_cache = {
            "last_check_time": None,
            "status": None,
            "ttl_seconds": 86400
        }
        log.info("已重置 Gemini 健康檢查快取")
    
    async def close(self):
        """關閉客戶端連接"""
        if self._ollama_client:
            await self._ollama_client.aclose()
            self._ollama_client = None


# 全域摘要服務實例
summarization_service = SummarizationService()
