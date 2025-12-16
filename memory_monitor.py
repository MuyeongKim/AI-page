"""
###############################################################################################
# 🚀 AI-page 프로젝트용 메모리 모니터링 도구 (2025.08.10)
###############################################################################################
# 
# 목적: YOLO 객체탐지 프로그램의 실시간 메모리 사용량 모니터링
# 사용법: gui.py에서 import하여 MemoryMonitor 클래스 활용
# 
# 주요 기능:
# - 실시간 RAM/GPU 메모리 사용량 추적
# - 메모리 사용량 경고 시스템 (2GB RAM, 4GB GPU 초과 시)
# - 프로그램 실행 요약 정보 제공
# - 최대 메모리 사용량 기록
#
# 작성자: Claude Code AI Assistant
# 버전: 1.0
###############################################################################################
"""

import torch
import psutil
import os
from datetime import datetime

class MemoryMonitor:
    """실시간 메모리 사용량 모니터링"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.peak_gpu_memory = 0
        self.peak_ram_memory = 0
        
    def log_memory_usage(self, context=""):
        """메모리 사용량 로깅"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # GPU 메모리 (CUDA 사용 시)
        if torch.cuda.is_available():
            gpu_allocated = torch.cuda.memory_allocated() / 1024**2  # MB
            gpu_cached = torch.cuda.memory_reserved() / 1024**2
            self.peak_gpu_memory = max(self.peak_gpu_memory, gpu_allocated)
            gpu_info = f"GPU: {gpu_allocated:.1f}MB (캐시: {gpu_cached:.1f}MB)"
        else:
            gpu_info = "GPU: 사용 안함"
            
        # RAM 메모리
        process = psutil.Process(os.getpid())
        ram_mb = process.memory_info().rss / 1024**2
        self.peak_ram_memory = max(self.peak_ram_memory, ram_mb)
        
        print(f"[{timestamp}] {context} - RAM: {ram_mb:.1f}MB, {gpu_info}")
        
        # 메모리 경고
        if ram_mb > 2048:  # 2GB 이상
            print("⚠️ RAM 사용량 높음!")
        if torch.cuda.is_available() and gpu_allocated > 4096:  # 4GB 이상
            print("⚠️ GPU 메모리 사용량 높음!")
    
    def get_summary(self):
        """메모리 사용 요약"""
        runtime = datetime.now() - self.start_time
        return (f"실행시간: {runtime.total_seconds():.1f}초, "
                f"최대 RAM: {self.peak_ram_memory:.1f}MB, "
                f"최대 GPU: {self.peak_gpu_memory:.1f}MB")

# gui.py에서 사용하는 방법:
"""
# gui.py 상단에 추가
from memory_monitor import MemoryMonitor

class Ui_MainWindow:
    def __init__(self):
        # ... 기존 코드 ...
        self.memory_monitor = MemoryMonitor()
    
    def submit(self):
        self.memory_monitor.log_memory_usage("모델 로딩 전")
        # 모델 생성 코드...
        self.memory_monitor.log_memory_usage("모델 로딩 후")
        
        # 처리 루프에서
        while True:
            # ... 처리 코드 ...
            if frame_counter % 100 == 0:
                self.memory_monitor.log_memory_usage(f"프레임 {frame_counter}")
"""