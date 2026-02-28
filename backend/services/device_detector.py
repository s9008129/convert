"""
運算裝置偵測服務。

啟動時會優先使用較快的 GPU（CUDA 或 MPS），若不符合條件則自動改用 CPU，
在穩定性與效能間取得平衡。
"""

import subprocess
from enum import Enum
from typing import Tuple, Optional, Dict
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
        
    def detect_best_device(self) -> Tuple[DeviceType, str]:
        """
        偵測並回傳目前最適合的運算裝置。

        會依序嘗試 CUDA、MPS、CPU；若前一種不可用就自動降級，避免服務無法啟動。
        Returns:
            (裝置類型, 計算精度)
        """
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
                        
                        # 至少需要 4GB VRAM
                        if memory_free >= 4000:
                            return True, {
                                "name": name,
                                "memory_free": memory_free,
                                "memory_total": memory_total
                            }
                        else:
                            log.warning(f"⚠️ GPU 記憶體不足: {memory_free}MB 可用，需要至少 4000MB")
        except FileNotFoundError:
            log.debug("nvidia-smi 未找到，CUDA 不可用")
        except subprocess.TimeoutExpired:
            log.warning("nvidia-smi 執行逾時")
        except Exception as e:
            log.debug(f"CUDA 偵測失敗：{e}")
        
        return False, {}
    
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
        """取得目前裝置資訊"""
        return {
            "current_device": self.current_device.value if self.current_device else "unknown",
            "compute_type": self.current_compute_type,
            "fallback_count": self.fallback_count,
            "gpu_name": self.gpu_name,
            "gpu_memory_mb": self.gpu_memory_mb,
            "gpu_available": self.current_device == DeviceType.CUDA,
            "mps_available": self.current_device == DeviceType.MPS
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
