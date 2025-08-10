from ultralytics import YOLO

# 1. 변환된 OpenVINO 모델 폴더를 직접 로딩합니다.
model = YOLO('yolo11x.pt', task='detect')
# 2. 이미지나 영상으로 추론을 실행합니다.
# 내부적으로 OpenVINO 런타임이 사용되어 매우 빠르게 실행됩니다.
results = model('test_image.jpg', imgsz=1920, save=True, device='cpu') 
# results = model(source=0, show=True) # 웹캠 실시간 추론