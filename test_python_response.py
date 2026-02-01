"""
Python 서버 독립 테스트 스크립트

YouTube URL을 직접 Python 서버로 보내서 응답을 확인합니다.
"""

import requests
import json

# Python 서버 URL
PYTHON_SERVER_URL = "http://127.0.0.1:8000"

def test_youtube_endpoint():
    """YouTube 요약 엔드포인트 테스트"""
    print("=" * 60)
    print("YouTube 요약 엔드포인트 테스트")
    print("=" * 60)
    
    url = f"{PYTHON_SERVER_URL}/api/v1/summarize/youtube"
    payload = {
        "url": "https://www.youtube.com/watch?v=4I8fWk0k7Y8"
    }
    
    print(f"\n요청 URL: {url}")
    print(f"요청 데이터: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        
        print(f"\n응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ 성공! 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 주요 필드 확인
            analysis = data.get("analysis", {})
            print("\n📊 주요 필드 확인:")
            print(f"  - category_name: {analysis.get('category_name')}")
            print(f"  - topic_name: {analysis.get('topic_name')}")
            print(f"  - small_card_summary: {analysis.get('small_card_summary')[:50]}..." if analysis.get('small_card_summary') else "  - small_card_summary: None")
            print(f"  - newsletter_summary 개수: {len(analysis.get('newsletter_summary', []))}")
            
        else:
            print(f"\n❌ 에러 발생:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Python 서버에 연결할 수 없습니다!")
        print("Python 서버가 실행 중인지 확인하세요:")
        print("  cd archiveat-python-server")
        print("  python -m uvicorn main:app --reload --port 8000")
        
    except requests.exceptions.Timeout:
        print("\n❌ 요청 시간 초과 (120초)")
        print("Whisper 모델 다운로드 중일 수 있습니다. 잠시 후 다시 시도하세요.")
        
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")


if __name__ == "__main__":
    test_youtube_endpoint()
