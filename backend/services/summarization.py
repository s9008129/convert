"""
MeetingScribe LLM 摘要服務
支援本地模式（Ollama）、LM Studio（OpenAI 相容）和雲端模式（Gemini API）

v3.5.2 改進：
- 實現 Ollama 模型 VRAM 釋放機制（keep_alive=0）
- 自訂格式功能完全重構：使用者格式具有絕對優先權
- 優化本地模型摘要品質：改善參數和提示詞策略
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
            
        v3.5.2 改進：
        - 自訂格式優先權重構：user_prompt 完全取代系統預設格式
        - 提升本地模式輸出品質
        """
        if progress_callback:
            progress_callback(65.0, "生成摘要中...")
        
        # v3.5.2: 自訂格式處理邏輯完全重構
        # 如果使用者提供自訂格式，則【完全使用】使用者格式，不混合系統預設
        if user_prompt and user_prompt.strip():
            # 檢測是否為格式範本（包含 Markdown 結構或明確的格式指令）
            is_format_template = self._is_format_template(user_prompt)
            
            if is_format_template:
                # 使用者提供的是格式範本，完全按照使用者格式生成
                system_prompt = self._build_custom_format_prompt(user_prompt)
                log.info("使用自訂格式範本生成會議記錄")
            else:
                # 使用者提供的是額外指令，附加到系統預設格式
                system_prompt = self._build_enhanced_system_prompt(user_prompt)
                log.info("使用增強系統提示詞（附加使用者指令）")
        else:
            # 無自訂格式，使用系統預設
            system_prompt = settings.DEFAULT_SYSTEM_PROMPT
            log.info("使用系統預設格式")
        
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
    
    def _is_format_template(self, user_prompt: str) -> bool:
        """
        判斷使用者輸入是否為格式範本
        v3.5.2: 新增智能判斷邏輯
        """
        # 格式範本的特徵
        format_indicators = [
            "範本", "範例", "格式", "template", "format",
            "---範本", "---格式", "---範例",
            "會議紀錄", "會議記錄",
            "決議事項", "待辦事項", "出席人員",
            "中華民國", "年月日",
        ]
        
        # Markdown 結構特徵
        markdown_indicators = [
            r"^#\s", r"^\|.*\|", r"^\*\*.*\*\*", r"^-\s+\*\*"
        ]
        
        lower_prompt = user_prompt.lower()
        
        # 檢查關鍵詞
        for indicator in format_indicators:
            if indicator.lower() in lower_prompt:
                return True
        
        # 檢查 Markdown 結構
        for pattern in markdown_indicators:
            if re.search(pattern, user_prompt, re.MULTILINE):
                return True
        
        # 如果包含多行且有明顯的文檔結構
        lines = user_prompt.strip().split('\n')
        if len(lines) > 10:
            return True
        
        return False
    
    def _build_custom_format_prompt(self, user_format: str) -> str:
        """
        構建基於使用者自訂格式的系統提示詞
        v3.5.2: 完全按照使用者格式生成，不混合系統預設
        """
        return f"""<system>
<role>
你是專業的會議記錄秘書，你的任務是【嚴格按照使用者指定的格式】將會議逐字稿轉換為會議記錄。
</role>

<critical_instruction>
以下是使用者指定的會議記錄格式範本，你必須【100% 遵循此格式】：
- 標題層級必須與範本完全一致
- 表格結構必須與範本完全一致  
- 項目符號風格必須與範本完全一致
- 用詞風格必須與範本完全一致
- 如果範本有特定區塊（如決議事項追蹤表），輸出必須包含相同區塊

【警告】：不要使用任何其他格式，不要添加範本中沒有的區塊，不要省略範本中有的區塊。
</critical_instruction>

<user_format_template>
{user_format}
</user_format_template>

<output_rules>
1. 第一行直接開始會議記錄內容（按照範本格式）
2. 不要有任何開場白或解釋
3. 所有內容必須使用繁體中文
4. 如果逐字稿資訊不足，標註「（待補充）」或「（逐字稿未提及）」
5. 輸出格式必須與範本結構完全一致
</output_rules>
</system>"""
    
    def _build_enhanced_system_prompt(self, user_instructions: str) -> str:
        """
        構建增強版系統提示詞（系統預設 + 使用者額外指令）
        """
        return f"""{settings.DEFAULT_SYSTEM_PROMPT}

<additional_user_instructions>
使用者額外要求（請在生成時納入考量）：
{user_instructions}
</additional_user_instructions>"""
    
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
        """
        使用 Ollama 本地模式生成摘要（針對 Gemma 3 優化）
        
        v3.5.2 改進：
        - 新增 keep_alive=0 參數，使用完畢後立即釋放 VRAM
        - 優化參數以提升長逐字稿處理品質
        - 增加 num_ctx 到 16384 以處理更長的逐字稿
        """
        client = await self._get_ollama_client()
        
        try:
            # 進度更新：開始生成摘要
            if progress_callback:
                progress_callback(65.0, "載入 Ollama 模型...")
            
            # v3.5.2: 大幅優化參數配置
            # - temperature 0.05: 極低溫度確保格式遵循和輸出穩定
            # - num_ctx 16384: 擴大上下文視窗以處理長逐字稿
            # - num_predict 6144: 允許生成更完整的會議記錄
            # - keep_alive "0": 生成完成後立即卸載模型，釋放 VRAM
            response = await client.post(
                "/api/chat",
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": False,
                    "keep_alive": "0",  # v3.5.2: 關鍵！使用完畢後立即釋放 VRAM
                    "options": {
                        "temperature": 0.05,      # v3.5.2: 極低溫提高格式遵循度和內容準確度
                        "top_p": 0.85,            # 稍微收緊以提高輸出品質
                        "top_k": 30,              # 限制候選詞數量，提高準確度
                        "repeat_penalty": 1.2,    # v3.5.2: 提高重複懲罰，避免內容重複
                        "num_ctx": 16384,         # v3.5.2: 大幅擴大上下文視窗
                        "num_predict": 6144,      # v3.5.2: 允許生成更長的輸出
                        "stop": ["</details>", "---\n\n---"]  # 更精確的停止標記
                    }
                },
                timeout=600.0  # v3.5.2: 增加超時時間以處理長逐字稿
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
            
            log.info(f"Ollama 摘要生成成功，模型: {settings.LOCAL_LLM_MODEL}，VRAM 將自動釋放")
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
