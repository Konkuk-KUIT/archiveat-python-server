import whisper

def transcribe_audio(file_path):
    # [Insight] 모델 크기 선택: 'tiny', 'base', 'small', 'medium', 'large'가 있습니다.
    # 'base'는 속도가 매우 빠르면서도 한국어와 영어 인식률이 준수한 편이라 
    # 테스트 및 실시간 서버 서비스용으로 가장 많이 추천됩니다.
    print(f"--- Whisper 모델 로딩 중 ('base' 모델) ---")
    model = whisper.load_model("base")

    try:
        print(f"--- 음성 인식 시작 (시간이 다소 걸릴 수 있습니다) ---")
        # [Insight] fp16=False 옵션은 CPU 환경에서도 안정적으로 돌아가게 해줍니다.
        # GPU(NVIDIA)가 있다면 훨씬 빠르겠지만, 맥북 CPU로도 충분히 가능합니다.
        result = model.transcribe(file_path, fp16=False)
        
        # 전체 텍스트 출력
        full_text = result['text']
        print(f"✅ 인식 완료!")
        return full_text
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return None

if __name__ == "__main__":
    audio_file = "downloaded_audio.mp3"
    
    # 파일이 존재하는지 확인 후 실행
    import os
    if os.path.exists(audio_file):
        text_result = transcribe_audio(audio_file)
        print("\n=== 추출된 텍스트 결과 (앞부분 300자) ===")
        print(text_result[:300] + "...")
    else:
        print("파일이 없습니다. audio_download_test.py를 먼저 실행해주세요.")