
import os
import sys

# Move imports to top level if possible, but if they depend on sys.path modification, 
# they might need to be inside the function or a try-except block. 
# However, for a test/script in the package, standard imports should work if run correctly.
# If this script is run directly, we might need to adjust sys.path.

from services.youtube import YouTubeProcessor
from services.summarizer import GeminiSummarizer
import yt_dlp
import json

def set_up_paths():
    """Sets up the path for standalone execution."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    if script_dir not in sys.path:
        sys.path.append(script_dir)


def test_youtube_cookies_and_summary():
    print(f"📂 Current Working Directory: {os.getcwd()}")
    print("🍪 Testing YouTube Cookies Configuration & LLM Summarization...")

    # 1. Check cookies.txt existence
    # If using pytest, we might need to look for cookies.txt relative to the test file
    # or assume it's in the CWD (project root).
    # Since YouTubeProcessor assumes 'cookies.txt' in CWD, we assert that.
    cookies_path = "cookies.txt"
    if not os.path.exists(cookies_path):
        # Fallback: check if we are in tests/ and cookies is in parent
        if os.path.exists(os.path.join("..", "cookies.txt")):
             os.chdir("..") # Pytest might run from tests/, so move up
             print(f"📂 Changed CWD to {os.getcwd()} to find cookies.txt")
    
    assert os.path.exists("cookies.txt"), "❌ Error: 'cookies.txt' not found in current directory."
    print("✅ 'cookies.txt' found.")

    # 2. Initialize Processor & Summarizer
    try:
        processor = YouTubeProcessor()
        summarizer = GeminiSummarizer()
    except Exception as e:
        assert False, f"❌ Error initializing processors: {e}"

    # 3. Verify cookiefile option
    cookie_opt = processor.ydl_opts.get('cookiefile')
    assert cookie_opt == 'cookies.txt', f"❌ Error: 'cookiefile' option is NOT set to 'cookies.txt'. Current: {cookie_opt}"
    print(f"✅ YouTubeProcessor configured to use cookies: '{cookie_opt}'")

    # 4. Process Video (Extract Info + Transcript)
    test_url = "https://www.youtube.com/watch?v=7nvUzO_-P0I" 
    print(f"\n🔄 Processing URL: {test_url}")
    
    try:
        # This will download audio, transcribe (if needed), or get official captions
        video_data = processor.process(test_url)
        
        # Check for error in return dict
        assert "error" not in video_data, f"❌ Error processing video: {video_data.get('error')}"

        print(f"✅ Video Title: {video_data['title']}")
        transcript = video_data.get('transcript', '')
        assert transcript, "❌ Error: Transcript is empty"
        print(f"✅ Transcript Length: {len(transcript)} chars")

    except Exception as e:
        assert False, f"❌ Exception during video processing: {e}"

    # 5. Summarize with Gemini
    print("\n🧠 Generating AI Summary (this might take a few seconds)...")
    
    try:
        # Combine description and transcript for better context
        full_content = (video_data.get('description', '') or '') + "\n\n" + (video_data.get('transcript', '') or '')
        
        analysis_result = summarizer.summarize_content(
            video_data['title'],
            full_content
        )

        assert "error" not in analysis_result, f"❌ Summarization failed: {analysis_result['error']}"

        print("\n" + "="*60)
        print("🎉 Final Result (JSON)")
        print("="*60)
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        print("="*60)
        
        # Assertion checks for critical fields
        assert analysis_result.get('category'), "❌ Missing Category"
        assert analysis_result.get('topic'), "❌ Missing Topic"
        assert analysis_result.get('small_card_summary'), "❌ Missing Small Summary"
        assert analysis_result.get('newsletter_summary'), "❌ Missing Newsletter Summary"
        
        print(f"\n📁 Category: {analysis_result.get('category')}")
        print(f"🏷️  Topic: {analysis_result.get('topic')}")
        print(f"📝 Small Summary: {analysis_result.get('small_card_summary')}")
        print(f"📰 Newsletter Blocks: {len(analysis_result.get('newsletter_summary', []))} blocks")

    except Exception as e:
        assert False, f"❌ Exception during summarization: {e}"


if __name__ == "__main__":
    set_up_paths()
    test_youtube_cookies_and_summary()
