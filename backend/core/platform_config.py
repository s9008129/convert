"""
平台與設定來源判斷工具。

負責辨識目前是在 macOS、Windows 或 Docker 環境，並載入對應設定，
讓同一套程式能在不同部署方式下維持一致行為。
v3.5.0 - 支援 macOS 原生模式和 Windows Docker 模式
"""

import os
import platform
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def get_platform() -> str:
    """
    檢測當前平台
    
    Returns:
        str: "macos", "windows", "linux"
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    return system


def is_docker() -> bool:
    """
    檢測是否在 Docker 容器中運行
    
    Returns:
        bool: True 如果在 Docker 中
    """
    # 方法 1: 檢查 /.dockerenv 檔案
    if os.path.exists('/.dockerenv'):
        return True
    
    # 方法 2: 檢查 /proc/1/cgroup
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except FileNotFoundError:
        pass
    
    # 方法 3: 檢查環境變數
    return os.getenv('DOCKER_CONTAINER') == 'true'


def get_deployment_mode() -> str:
    """
    獲取部署模式
    
    Returns:
        str: "native" 或 "docker"
    """
    if is_docker():
        return "docker"
    return "native"


def load_platform_config() -> Dict[str, Any]:
    """
    載入平台特定配置
    
    載入順序（後者覆蓋前者）：
    1. config.yaml - 基礎配置
    2. config.{platform}.yaml - 平台特定配置（如 config.mac.yaml）
    3. .env - 環境變數（隱私配置，如 API Key）
    
    Returns:
        Dict: 合併後的配置字典
    """
    # 載入 .env 檔案（隱私配置）
    load_dotenv()
    
    # 專案根目錄
    project_root = Path(__file__).parent.parent.parent
    
    # 1. 載入基礎配置
    base_config_path = project_root / "config.yaml"
    config = {}
    
    if base_config_path.exists():
        with open(base_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    
    # 2. 載入平台特定配置
    current_platform = get_platform()
    platform_config_path = project_root / f"config.{current_platform}.yaml"
    
    if platform_config_path.exists():
        with open(platform_config_path, 'r', encoding='utf-8') as f:
            platform_config = yaml.safe_load(f) or {}
            # 深度合併配置
            config = deep_merge(config, platform_config)
    
    # 3. 添加平台資訊
    config['_platform'] = current_platform
    config['_deployment_mode'] = get_deployment_mode()
    config['_is_docker'] = is_docker()
    
    return config


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    深度合併兩個字典
    
    Args:
        base: 基礎字典
        override: 覆蓋字典
        
    Returns:
        Dict: 合併後的字典
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def get_config_value(config: Dict, path: str, default: Any = None) -> Any:
    """
    從配置字典中獲取嵌套值
    
    Args:
        config: 配置字典
        path: 點分隔的路徑（如 "llm.ollama.base_url"）
        default: 預設值
        
    Returns:
        Any: 配置值或預設值
    """
    keys = path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def get_env_or_config(env_key: str, config: Dict, config_path: str, default: Any = None) -> Any:
    """
    優先從環境變數獲取值，否則從配置檔案獲取
    
    Args:
        env_key: 環境變數名稱
        config: 配置字典
        config_path: 配置路徑（點分隔）
        default: 預設值
        
    Returns:
        Any: 環境變數值 > 配置值 > 預設值
    """
    # 1. 環境變數（最高優先）
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value
    
    # 2. 配置檔案
    config_value = get_config_value(config, config_path)
    if config_value is not None:
        return config_value
    
    # 3. 預設值
    return default


# 全域配置實例（單例模式）
_global_config: Optional[Dict[str, Any]] = None


def get_global_config() -> Dict[str, Any]:
    """
    獲取全域配置（單例）
    
    Returns:
        Dict: 全域配置字典
    """
    global _global_config
    
    if _global_config is None:
        _global_config = load_platform_config()
    
    return _global_config


def reload_config():
    """
    重新載入配置（用於開發模式）
    """
    global _global_config
    _global_config = None
    return get_global_config()


# 便捷函數
def get_llm_provider() -> str:
    """獲取 LLM 提供者（ollama/lmstudio/gemini）"""
    config = get_global_config()
    return get_env_or_config('LLM_PROVIDER', config, 'llm.provider', 'ollama')


def get_whisper_backend() -> str:
    """獲取 Whisper 後端（mlx/faster-whisper）"""
    config = get_global_config()
    platform_name = config.get('_platform', 'linux')
    
    # macOS 預設使用 mlx
    if platform_name == 'macos':
        return get_config_value(config, 'whisper.backend', 'mlx')
    else:
        return get_config_value(config, 'whisper.backend', 'faster-whisper')


def get_device() -> str:
    """獲取運算裝置（mps/cuda/cpu）"""
    config = get_global_config()
    platform_name = config.get('_platform', 'linux')
    
    # macOS 預設使用 MPS
    if platform_name == 'macos':
        return get_env_or_config('WHISPER_DEVICE', config, 'whisper.mlx.device', 'mps')
    else:
        return get_env_or_config('WHISPER_DEVICE', config, 'whisper.faster_whisper.device', 'auto')


if __name__ == "__main__":
    # 測試
    print(f"Platform: {get_platform()}")
    print(f"Deployment Mode: {get_deployment_mode()}")
    print(f"Is Docker: {is_docker()}")
    print(f"\nGlobal Config:")
    
    config = get_global_config()
    import json
    print(json.dumps({
        'platform': config.get('_platform'),
        'deployment_mode': config.get('_deployment_mode'),
        'llm_provider': get_llm_provider(),
        'whisper_backend': get_whisper_backend(),
        'device': get_device()
    }, indent=2))
