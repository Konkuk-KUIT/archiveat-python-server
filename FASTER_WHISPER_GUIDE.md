# Faster Whisper 설치 및 사용 가이드

## 🚀 성능 개선

**OpenAI Whisper → Faster Whisper**로 마이그레이션 완료!

### 성능 비교

| 모델 | OpenAI Whisper | Faster Whisper | 개선 |
|------|---------------|----------------|------|
| **base** | ~10초 | ~2-3초 | **4-5배 빠름** ⚡ |
| **small** | ~20초 | ~5초 | **4배 빠름** |
| **메모리** | ~2GB | ~500MB | **75% 절감** 💾 |

### 주요 변경사항

1. **requirements.txt**
   ```diff
   - openai-whisper
   + faster-whisper
   ```

2. **services/youtube.py**
   ```python
   # Before
   import whisper
   model = whisper.load_model("base")
   result = model.transcribe("audio.mp3", fp16=False)
   text = result['text']
   
   # After
   from faster_whisper import WhisperModel
   model = WhisperModel("base", device="cpu", compute_type="int8")
   segments, info = model.transcribe("audio.mp3", language="ko", vad_filter=True)
   text = " ".join([segment.text for segment in segments])
   ```

## 🔧 로컬 설치 방법

### 1. 기존 whisper 제거 (선택)
```bash
pip uninstall openai-whisper
```

### 2. faster-whisper 설치
```bash
cd archiveat-python-server
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install faster-whisper
```

### 3. 서버 실행
```bash
python -m uvicorn main:app --reload --port 8000
```

## ⚙️ 고급 설정

### GPU 사용 (CUDA 필수)
```python
# services/youtube.py 수정
self.model = WhisperModel(
    model_size, 
    device="cuda",      # GPU 사용
    compute_type="float16"  # GPU 최적화
)
```

### 모델 크기 변경
```python
# processor.py 또는 main.py에서
processor = YouTubeProcessor(model_size="small")  # 더 정확하지만 느림
processor = YouTubeProcessor(model_size="tiny")   # 더 빠르지만 부정확
```

### 언어 자동 감지
```python
# language=None으로 설정하면 자동 감지
segments, info = self.model.transcribe(
    "audio.mp3",
    language=None,  # 자동 감지
    vad_filter=True
)
```

## 📊 옵션 설명

### transcribe() 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `language` | `"ko"` | 한국어 우선, `None`이면 자동 감지 |
| `beam_size` | `5` | 빔 서치 크기 (높을수록 정확, 느림) |
| `vad_filter` | `True` | 침묵 구간 자동 제거 (음성만 추출) |
| `word_timestamps` | `False` | 단어별 타임스탬프 (True 시 느려짐) |

### compute_type

| 타입 | 장치 | 설명 |
|------|------|------|
| `int8` | CPU | CPU 최적화 (권장) |
| `int8_float16` | CPU/GPU | 하이브리드 |
| `float16` | GPU | GPU 최적화 (CUDA 필요) |

## 🐳 Docker 설정

Dockerfile은 자동으로 faster-whisper를 설치하므로 추가 설정 불필요합니다:

```bash
docker-compose up --build
```

## ✅ 테스트

### 1. YouTube 처리 테스트
```bash
cd archiveat-python-server
python -c "from services.youtube import YouTubeProcessor; p = YouTubeProcessor(); print(p.process('https://www.youtube.com/watch?v=4I8fWk0k7Y8'))"
```

### 2. 성능 측정
```python
import time
from services.youtube import YouTubeProcessor

processor = YouTubeProcessor(model_size="base")

start = time.time()
result = processor.process("YOUTUBE_URL")
duration = time.time() - start

print(f"처리 시간: {duration:.2f}초")
```

## 🔍 트러블슈팅

### 설치 실패 시
```bash
# C++ 컴파일러 필요 (Windows)
# Visual Studio Build Tools 설치
# https://visualstudio.microsoft.com/downloads/

# 또는 conda 사용
conda install -c conda-forge faster-whisper
```

### CUDA 관련 오류
```bash
# GPU 버전 필요 시
pip install faster-whisper[cuda]
```

### 모델 다운로드 실패
```bash
# 모델 캐시 위치 확인
# ~/.cache/huggingface/hub/

# 수동 다운로드
python -c "from faster_whisper import WhisperModel; WhisperModel('base')"
```

## 📚 참고 자료

- [Faster Whisper GitHub](https://github.com/guillaumekln/faster-whisper)
- [OpenAI Whisper 원본](https://github.com/openai/whisper)
- [CTranslate2 (백엔드)](https://github.com/OpenNMT/CTranslate2)

## 💡 TIP

- **일반 영상**: `base` 모델로 충분
- **전문 용어 많음**: `small` 이상 권장
- **실시간 처리**: `tiny` 모델 사용
- **최고 품질**: `large-v2` (느림 주의)
