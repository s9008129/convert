"""獨立 worker 程序（v4.7.0）。

ASR 在長駐程序內反覆 load/unload 會累積 CUDA context 與分配器殘留
（faster-whisper#992 實測每次 ~312MB，直到程序退出才釋回），蠶食
Ollama 可載入的 VRAM。worker 以子程序執行、結束即退出，
VRAM 由作業系統保證完全歸還。
"""
