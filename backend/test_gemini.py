import os
import sys
import time
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Setup paths to ensure local imports resolve
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

# Load environment configuration
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

def run_verification():
    print("====================================================")
    print("      GEMINI API CONNECTION VERIFICATION")
    print("====================================================")

    # 1. Load API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[-] API Key check: FAILED. GEMINI_API_KEY not found in backend/.env")
        sys.exit(1)
    
    masked_key = api_key[:8] + "..." if len(api_key) > 8 else "***"
    print(f"[+] API Key check: SUCCESS (Loaded: {masked_key})")

    # 2. Configure SDK
    try:
        genai.configure(api_key=api_key)
        print("[+] SDK Configuration: SUCCESS")
    except Exception as e:
        print(f"[-] SDK Configuration: FAILED. Error: {e}")
        sys.exit(1)

    # 3. Target Model
    model_name = "gemini-2.5-flash"
    print(f"[*] Target Model: {model_name}")

    # 4. Prepare Prompt
    news_text = "HFCL announces expansion of fiber infrastructure for AI data centers."
    prompt = f"""
    Analyze this stock news:
    "{news_text}"
    
    You must evaluate the sentiment and impact of this news on the company.
    
    Provide your response in raw JSON format with the following fields:
    - "sentiment_score": An integer between -100 (bearish) and +100 (bullish).
    - "impact_level": Expected short-term price impact (must be one of: "low", "medium", "high").
    - "sentiment_trend": Overall market direction (must be one of: "bullish", "bearish", "neutral").
    - "confidence": Your prediction confidence (must be one of: "low", "medium", "high").
    - "explanation": A brief, 1-sentence analysis summary.
    
    Return ONLY the raw JSON object. Do not include markdown codeblocks or extra text.
    """

    # 5. Call API and measure latency
    print("[*] Dispatching request to Gemini API...")
    start_time = time.time()
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        latency = time.time() - start_time
        print(f"[+] API Response received successfully (Latency: {latency:.2f}s).")
    except Exception as e:
        print(f"[-] API Call: FAILED. Error: {e}")
        sys.exit(1)

    # 6. Parse and validate output
    try:
        response_text = response.text.strip()
        parsed_response = json.loads(response_text)
        print(f"[+] Response JSON parsing: SUCCESS")
        print(f"[+] Response Payload Preview:\n{json.dumps(parsed_response, indent=2)}")
        
        # Verify required keys
        required_keys = ["sentiment_score", "impact_level", "sentiment_trend", "confidence", "explanation"]
        missing_keys = [k for k in required_keys if k not in parsed_response]
        
        if missing_keys:
            print(f"[-] Payload validation: FAILED. Missing keys: {missing_keys}")
            sys.exit(1)
            
        print("[+] Payload validation: SUCCESS")
        print("====================================================")
        print("VERIFICATION RESULT: GEMINI API IS ONLINE & FULLY STABLE!")
        print("====================================================")
        
        # Save latency and payload preview to temp JSON for report generator
        meta_result = {
            "model": model_name,
            "latency_seconds": latency,
            "preview": parsed_response,
            "status": "success"
        }
        with open(os.path.join(base_dir, "gemini_test_result.json"), "w") as f:
            json.dump(meta_result, f, indent=2)
            
        sys.exit(0)
    except Exception as e:
        print(f"[-] Parsing & Validation: FAILED. Error: {e}")
        print(f"Raw Response text was: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
