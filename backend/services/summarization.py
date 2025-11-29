"""
MeetingScribe LLM 摘要服務
支援本地模式（Ollama）和雲端模式（Gemini API）
"""

import httpx
from typing import Optional
from openai import OpenAI

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import ProcessingMode


class SummarizationService:
    """
    LLM 摘要生成服務
    支援本地模式（Ollama + Gemma3:12B）和雲端模式（Gemini API）
    """
    
    def __init__(self):
        self._ollama_client: Optional[httpx.AsyncClient] = None
        self._gemini_client: Optional[OpenAI] = None
        
    async def _get_ollama_client(self) -> httpx.AsyncClient:
        """取得 Ollama HTTP 客戶端"""
        if not self._ollama_client:
            self._ollama_client = httpx.AsyncClient(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=300.0
            )
        return self._ollama_client
    
    def _get_gemini_client(self) -> OpenAI:
        """取得 Gemini API 客戶端（OpenAI 相容介面）"""
        if not self._gemini_client:
            api_key = settings.gemini_api_key_value if hasattr(settings, 'gemini_api_key_value') else settings.GEMINI_API_KEY
            if not api_key:
                raise ValueError("未設定 GEMINI_API_KEY 環境變數")
            
            self._gemini_client = OpenAI(
                api_key=api_key,
                base_url=settings.GEMINI_BASE_URL
            )
        return self._gemini_client
    
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
            mode: 處理模式（local/cloud）
            user_prompt: 使用者自訂 prompt（可選）
            progress_callback: 進度回調函數
            
        Returns:
            會議摘要（Markdown 格式）
        """
        if progress_callback:
            progress_callback(65.0, f"使用{'本地' if mode == ProcessingMode.LOCAL else '雲端'}模式生成摘要...")
        
        # 組合 prompt
        system_prompt = settings.DEFAULT_SYSTEM_PROMPT
        
        if user_prompt:
            # 將使用者 prompt 加到 system prompt 後面
            system_prompt = f"{system_prompt}\n\n使用者額外要求：\n{user_prompt}"
        
        user_message = f"以下是會議的逐字稿，請整理成會議記錄：\n\n{transcript}"
        
        try:
            if mode == ProcessingMode.LOCAL:
                summary = await self._summarize_with_ollama(system_prompt, user_message, progress_callback)
            else:
                summary = await self._summarize_with_gemini(system_prompt, user_message, progress_callback)
            
            if progress_callback:
                progress_callback(95.0, "摘要生成完成")
            
            return summary
            
        except Exception as e:
            log.error(f"摘要生成失敗: {e}")
            raise
    
    async def _summarize_with_ollama(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """使用 Ollama 本地模式生成摘要"""
        client = await self._get_ollama_client()
        
        try:
            response = await client.post(
                "/api/chat",
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": False
                }
            )
            response.raise_for_status()
            
            data = response.json()
            summary = data.get("message", {}).get("content", "")
            
            log.info(f"Ollama 摘要生成成功，模型: {settings.LOCAL_LLM_MODEL}")
            return summary
            
        except httpx.ConnectError:
            log.error("無法連接到 Ollama 服務，請確認 Ollama 是否正在運行")
            raise RuntimeError("Ollama 服務不可用，請確認 Ollama 是否正在運行")
        except Exception as e:
            log.error(f"Ollama 摘要生成失敗: {e}")
            raise
    
    async def _summarize_with_gemini(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """使用 Gemini API 雲端模式生成摘要"""
        client = self._get_gemini_client()
        
        try:
            response = client.chat.completions.create(
                model=settings.GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            summary = response.choices[0].message.content
            
            log.info(f"Gemini 摘要生成成功，模型: {settings.GEMINI_MODEL}")
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
    
    def check_gemini_available(self) -> bool:
        """檢查 Gemini API 是否已配置"""
        api_key = settings.gemini_api_key_value if hasattr(settings, 'gemini_api_key_value') else settings.GEMINI_API_KEY
        return bool(api_key)
    
    async def close(self):
        """關閉客戶端連接"""
        if self._ollama_client:
            await self._ollama_client.aclose()
            self._ollama_client = None


# 全域摘要服務實例
summarization_service = SummarizationService()
