"""
運算裝置偵測服務。

啟動時會優先使用較快的 GPU（CUDA 或 MPS），若不符合條件則自動改用 CPU，
在穩定性與效能間取得平衡。
"""

import subprocess
from enum import Enum
from typing import Tuple, Optional, Dict
from backend.core.asr_model_resolver import infer_asr_backend, resolve_asr_model, resolve_model_revision
from backend.core.config import settings
from backend.core.logger import log


class DeviceType(str, Enum):
    """裝置類型"""
    CUDA = "cuda"
    MPS = "mps"
    CPU = "cpu"


class DeviceDetector:
    """
    智能裝置偵測器
    自動偵測最佳運算裝置，並支援動態降級
    """
    
    def __init__(self):
        """初始化偵測結果快取，讓後續服務能共用同一份裝置資訊。"""
        self.current_device: Optional[DeviceType] = None
        self.current_compute_type: str = "int8"
        self.fallback_count: int = 0
        self.gpu_name: Optional[str] = None
        self.gpu_memory_mb: Optional[int] = None
        self.cuda_runtime_available: bool = False
        self.cuda_runtime_error: Optional[str] = None
        self.torch_cuda_version: Optional[str] = None
        # v4.3.2：「GPU 存在」與「目前有足夠 VRAM 可再載入模型」是兩件事。
        # 處理中 VRAM 被占滿（正是在用 GPU！）不得被回報成「GPU 未偵測」。
        self.gpu_present: bool = False
        
    def detect_best_device(self) -> Tuple[DeviceType, str]:
        """
        偵測並回傳目前最適合的運算裝置。

        會依序嘗試 CUDA、MPS、CPU；若前一種不可用就自動降級，避免服務無法啟動。
        Returns:
            (裝置類型, 計算精度)
        """
        # MLX/Metal 是 Apple Silicon 的獨立 ASR runtime；使用 MPS enum 作為
        # 舊內部 state marker，但不再把它對外宣稱成 PyTorch MPS。
        if infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND) == "mlx_whisper":
            self.current_device = DeviceType.MPS
            self.current_compute_type = "float16"
            self.gpu_present = True
            self.gpu_name = self.gpu_name or "Apple Silicon"
            self.gpu_memory_mb = None
            log.info("✅ 偵測到 Apple Silicon，使用 MLX/Metal ASR 加速")
            return DeviceType.MPS, "float16"

        # 優先嘗試 CUDA
        cuda_available, gpu_info = self._check_cuda()
        if cuda_available:
            self.current_device = DeviceType.CUDA
            self.current_compute_type = "float16"
            self.gpu_name = gpu_info.get("name")
            self.gpu_memory_mb = gpu_info.get("memory_free")
            log.info(f"✅ 偵測到 NVIDIA GPU: {self.gpu_name}，使用 CUDA 加速")
            return DeviceType.CUDA, "float16"
        
        # 嘗試 MPS (Apple Silicon)
        if self._check_mps():
            self.current_device = DeviceType.MPS
            self.current_compute_type = "float16"
            log.info("✅ 偵測到 Apple Silicon，使用 MPS 加速")
            return DeviceType.MPS, "float16"
        
        # 降級到 CPU
        self.current_device = DeviceType.CPU
        self.current_compute_type = "int8"
        log.warning("⚠️ 無 GPU 可用，使用 CPU 模式（處理速度較慢）")
        return DeviceType.CPU, "int8"
    
    def _check_cuda(self) -> Tuple[bool, Dict]:
        """檢查 CUDA 是否可用"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.free,memory.total", 
                     "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].split(',')
                    if len(parts) >= 3:
                        name = parts[0].strip()
                        memory_free = int(parts[1].strip())
                        memory_total = int(parts[2].strip())
                        self.gpu_present = True  # nvidia-smi 成功回報 → GPU 確實存在
                        self.gpu_name = name
                        self.gpu_memory_mb = memory_free
                        self.cuda_runtime_available = False
                        self.cuda_runtime_error = None
                        self.torch_cuda_version = None
                        
                        # 至少需要 4GB VRAM
                        if memory_free >= 4000:
                            backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
                            if backend == "transformers":
                                torch_ready, runtime_info = self._check_torch_cuda_runtime()
                                self.cuda_runtime_available = torch_ready
                                self.cuda_runtime_error = runtime_info.get("error")
                                self.torch_cuda_version = runtime_info.get("cuda_version")
                                if not torch_ready:
                                    log.warning(
                                        "偵測到 NVIDIA GPU {}，但目前 PyTorch 為 CPU-only 或未啟用 CUDA，ASR 將改用 CPU。{}",
                                        name,
                                        self.cuda_runtime_error or "請安裝 CUDA 版 torch",
                                    )
                                    return False, {
                                        "name": name,
                                        "memory_free": memory_free,
                                        "memory_total": memory_total,
                                    }
                            return True, {
                                "name": name,
                                "memory_free": memory_free,
                                "memory_total": memory_total
                            }
                        else:
                            log.warning(
                                f"⚠️ GPU 使用中：可用 VRAM 僅 {memory_free}MB（<4000MB），"
                                "本次載入暫用 CPU；GPU 本身存在且正被其他模型使用"
                            )
        except FileNotFoundError:
            self.gpu_present = False
            log.debug("nvidia-smi 未找到，CUDA 不可用")
        except subprocess.TimeoutExpired:
            log.warning("nvidia-smi 執行逾時")
        except Exception as e:
            log.debug(f"CUDA 偵測失敗：{e}")
        
        return False, {}

    @staticmethod
    def _check_torch_cuda_runtime() -> Tuple[bool, Dict]:
        """檢查目前 torch 執行階段是否真的可使用 CUDA。"""
        try:
            import torch
        except ImportError:
            return False, {"error": "未安裝 torch", "cuda_version": None}

        cuda_version = getattr(getattr(torch, "version", None), "cuda", None)
        if not torch.cuda.is_available():
            build = getattr(torch, "__version__", "unknown")
            return False, {
                "error": f"目前 torch={build}，torch.cuda.is_available()=False",
                "cuda_version": cuda_version,
            }

        return True, {"error": None, "cuda_version": cuda_version}
    
    def _check_mps(self) -> bool:
        """檢查 Apple MPS 是否可用"""
        try:
            import torch
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return True
        except ImportError:
            pass
        except Exception as e:
            log.debug(f"MPS 偵測失敗：{e}")
        return False
    
    def fallback_to_cpu(self) -> Tuple[DeviceType, str]:
        """
        降級到 CPU 模式
        當 GPU 處理失敗時呼叫
        """
        self.fallback_count += 1
        self.current_device = DeviceType.CPU
        self.current_compute_type = "int8"
        log.warning(f"⚠️ 第 {self.fallback_count} 次降級到 CPU 模式")
        return DeviceType.CPU, "int8"
    
    def get_device_info(self) -> Dict:
        """取得目前裝置資訊。

        v4.3.2：gpu_available 代表「GPU 存在」（給狀態列顯示用），
        不再與「本次工作負載被排到哪個裝置」(current_device) 混為一談——
        處理中 VRAM 被占滿時 current_device 可能暫時是 CPU，
        但 GPU 未偵測的顯示是錯的。gpu_busy 標示這種「存在但忙碌」狀態。
        """
        asr_backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
        asr_model = resolve_asr_model(settings.WHISPER_MODEL, settings.ASR_BACKEND)
        is_mlx = asr_backend == "mlx_whisper"
        current_device = "mlx-metal" if is_mlx and self.current_device == DeviceType.MPS else (
            self.current_device.value if self.current_device else "unknown"
        )
        accelerator = "mlx-metal" if is_mlx else current_device
        gpu_available = self.gpu_present or self.current_device == DeviceType.CUDA or is_mlx
        gpu_busy = (
            gpu_available and self.current_device == DeviceType.CPU
            if is_mlx
            else gpu_available and self.current_device != DeviceType.CUDA
        )
        return {
            "current_device": current_device,
            "compute_type": self.current_compute_type,
            "fallback_count": self.fallback_count,
            "gpu_name": self.gpu_name or ("Apple Silicon" if is_mlx else None),
            "gpu_memory_mb": self.gpu_memory_mb,
            "gpu_available": gpu_available,
            "gpu_busy": gpu_busy,
            "mps_available": self.current_device == DeviceType.MPS and not is_mlx,
            "accelerator": accelerator,
            "asr_backend": asr_backend,
            "asr_model": {
                "identifier": asr_model,
                "revision": resolve_model_revision(asr_model, settings.WHISPER_MODEL_REVISION),
            },
            "cuda_runtime_available": self.cuda_runtime_available,
            "cuda_runtime_error": self.cuda_runtime_error,
            "torch_cuda_version": self.torch_cuda_version,
        }
    
    def check_gpu_health(self) -> bool:
        """檢查 GPU 是否健康可用"""
        if self.current_device == DeviceType.CUDA:
            cuda_ok, _ = self._check_cuda()
            return cuda_ok
        elif self.current_device == DeviceType.MPS:
            return self._check_mps()
        return True  # CPU 永遠可用


# 全域裝置偵測器實例
device_detector = DeviceDetector()
