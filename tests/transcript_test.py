from youtube_transcript_api import YouTubeTranscriptApi

def get_global_transcript(video_id):
    try:
        # [Insight] list_transcripts()는 영상에 붙어있는 모든 자막의 '카탈로그'를 가져옵니다.
        # 사용자가 수동으로 올린 자막뿐만 아니라 유튜브 AI가 만든 '자동 생성' 자막도 포함됩니다.
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # [Insight] 특정 언어를 지정하지 않고 가장 적절한 자막 하나를 가져옵니다.
        # 우선순위: 1.수동 자막(Manual) -> 2.자동 생성 자막(Generated)
        # 만약 한국어(ko)나 영어(en)가 있다면 그것부터 가져오도록 설정했습니다.
        transcript = transcript_list.find_transcript(['ko', 'en', 'ja', 'zh-Hans', 'es'])
        
        # 실제 텍스트 데이터를 가져옵니다.
        data = transcript.fetch()
        full_text = " ".join([item['text'] for item in data])
        
        return {
            "language": transcript.language,      # 어떤 언어인지 (예: 한국어, 영어)
            "is_generated": transcript.is_generated, # 자동 생성된 자막인지 여부
            "text": full_text[:200]               # 확인용 앞부분 텍스트
        }

    except Exception as e:
        return f"❌ 자막을 찾을 수 없습니다: {str(e)}"

if __name__ == "__main__":
    # 테스트 1: 아까 실패했던 영상 (자막이 아예 없을 수도 있음)
    print(f"결과 1: {get_global_transcript('BboE9i7TwzM')}")
    
    # 테스트 2: 자막이 확실한 영상 (Rick Astley)
    print(f"결과 2: {get_global_transcript('dQw4w9WgXcQ')}")