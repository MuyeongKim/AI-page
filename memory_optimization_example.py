###############################################################################################
# 🚀 AI-page 메모리 최적화 패턴 예시 코드 (2025.08.10)
###############################################################################################
#
# 목적: YOLO 객체탐지 프로그램을 위한 고급 메모리 최적화 패턴 제시
# 상태: 학습용 예시 코드 (직접 실행 X, gui.py 개선 시 참고용)
#
# 포함된 최적화 패턴:
# - Context Manager를 활용한 자동 메모리 관리
# - 배치 처리용 메모리 최적화 (BatchProcessor)
# - 실시간 처리 루프 최적화
# - deque를 활용한 FPS 버퍼 최적화
# - 주기적 메모리 정리 시스템
#
# 작성자: Claude Code AI Assistant
# 버전: 1.0
###############################################################################################

# 🚀 개선된 메모리 관리 패턴들

import torch
import gc
import cv2
import numpy as np
from collections import deque
from contextlib import contextmanager

class OptimizedMemoryManager:
    """메모리 효율적인 YOLO 처리 매니저"""
    
    def __init__(self, buffer_size=30):
        # deque 사용으로 O(1) 시간복잡도 확보
        self.fps_buffer = deque(maxlen=buffer_size)
        self.frame_counter = 0
        self.cleanup_interval = 100  # 100프레임마다 메모리 정리
        
    @contextmanager
    def yolo_inference(self, model, frame):
        """YOLO 추론 결과 자동 메모리 관리"""
        results_list = None
        try:
            results_list = model(frame)
            yield results_list
        finally:
            # 추론 결과 즉시 정리
            if results_list:
                del results_list
            torch.cuda.empty_cache() if torch.cuda.is_available() else None

    @contextmanager 
    def frame_processing(self, cap):
        """프레임 처리 자동 메모리 관리"""
        frame = None
        try:
            ret, frame = cap.read()
            if ret:
                yield frame
        finally:
            # 프레임 메모리 즉시 해제
            if frame is not None:
                del frame
            
    def periodic_cleanup(self):
        """주기적 메모리 정리"""
        self.frame_counter += 1
        if self.frame_counter % self.cleanup_interval == 0:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print(f"🧹 주기적 정리 완료 (프레임: {self.frame_counter})")

    def add_fps(self, fps_value):
        """FPS 버퍼 효율적 관리"""
        self.fps_buffer.append(fps_value)
        return np.mean(self.fps_buffer)

# 🎯 사용 예시: 개선된 실시간 처리 루프
def optimized_realtime_processing(model, cap):
    """메모리 효율적인 실시간 처리"""
    memory_manager = OptimizedMemoryManager()
    
    try:
        while True:
            # 컨텍스트 매니저로 프레임 자동 관리
            with memory_manager.frame_processing(cap) as frame:
                if frame is None:
                    break
                    
                # 컨텍스트 매니저로 추론 결과 자동 관리    
                with memory_manager.yolo_inference(model, frame) as results:
                    if len(results) > 0:
                        result = results[0]
                        
                        # 결과 처리 (메모리 효율적)
                        process_detection_results(result, memory_manager)
                        
            # 주기적 메모리 정리
            memory_manager.periodic_cleanup()
            
            # ESC 키로 종료
            if cv2.waitKey(1) & 0xFF == 27:
                break
                
    except Exception as e:
        print(f"처리 중 오류: {e}")
    finally:
        # 최종 메모리 정리
        cleanup_all_resources()

def process_detection_results(result, memory_manager):
    """탐지 결과 처리 (메모리 효율적)"""
    # 즉시 사용하고 바로 해제되는 임시 변수들
    im_array = result.plot()
    
    try:
        # FPS 계산
        frame_time_ms = sum(result.speed.values())
        if frame_time_ms > 0:
            fps = 1000 / frame_time_ms
            avg_fps = memory_manager.add_fps(fps)
            
            # 화면 표시 (복사본 사용)
            display_frame = im_array.copy()
            cv2.putText(display_frame, f"FPS: {avg_fps:.1f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Detections', display_frame)
            
    finally:
        # 임시 변수들 즉시 정리
        del im_array
        if 'display_frame' in locals():
            del display_frame

def cleanup_all_resources():
    """전체 리소스 정리"""
    cv2.destroyAllWindows()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("🧹 전체 메모리 정리 완료")

# 🔧 배치 처리 최적화 (대용량 이미지 폴더 처리용)
class BatchProcessor:
    """배치 처리 메모리 최적화"""
    
    def __init__(self, batch_size=8, cleanup_every=50):
        self.batch_size = batch_size
        self.cleanup_every = cleanup_every
        self.processed_count = 0
        
    def process_images_batch(self, model, image_paths):
        """메모리 효율적 배치 처리"""
        total_images = len(image_paths)
        
        for i in range(0, total_images, self.batch_size):
            batch = image_paths[i:i + self.batch_size]
            
            # 배치 처리
            with self.batch_context():
                self.process_single_batch(model, batch)
            
            # 주기적 정리
            self.processed_count += len(batch)
            if self.processed_count % self.cleanup_every == 0:
                self.deep_cleanup()
                print(f"🧹 배치 정리: {self.processed_count}/{total_images}")
    
    @contextmanager
    def batch_context(self):
        """배치 처리 컨텍스트"""
        try:
            yield
        finally:
            # 배치 완료 후 정리
            gc.collect()
    
    def process_single_batch(self, model, image_paths):
        """단일 배치 처리"""
        for image_path in image_paths:
            try:
                # 이미지 로드 및 처리
                results = model(image_path)
                # 결과 처리...
                
            finally:
                # 즉시 정리
                if 'results' in locals():
                    del results
    
    def deep_cleanup(self):
        """깊은 메모리 정리"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()  # CUDA 작업 완료 대기

# 🏥 메모리 모니터링 도구
class MemoryMonitor:
    """메모리 사용량 모니터링"""
    
    @staticmethod
    def get_memory_info():
        """현재 메모리 사용량 조회"""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**2  # MB
            cached = torch.cuda.memory_reserved() / 1024**2      # MB
            return f"CUDA 메모리 - 할당: {allocated:.1f}MB, 캐시: {cached:.1f}MB"
        return "CPU 메모리 모드"
    
    @staticmethod
    def memory_alert(threshold_mb=1024):
        """메모리 사용량 경고"""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**2
            if allocated > threshold_mb:
                print(f"⚠️ 메모리 경고: {allocated:.1f}MB 사용 중")
                return True
        return False

# 사용 예시:
if __name__ == "__main__":
    print("메모리 최적화 패턴 예시 코드")
    print("실제 gui.py에 적용하여 사용하세요.")