import os
import sys
import logging
import json
from dotenv import load_dotenv

# Resolve paths
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

# Load env variables
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_pipeline")

def run_analysis():
    print("====================================================")
    print("   DISPATCHING LIVE AI STOCK ANALYSIS RUNTIME")
    print("====================================================")

    # 1. Credentials Check
    gemini_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    
    if not gemini_key:
        print("[-] Credentials check: FAILED. GEMINI_API_KEY is not defined in .env")
        sys.exit(1)
    if not project_id:
        print("[-] Credentials check: FAILED. FIREBASE_PROJECT_ID is not defined in .env")
        sys.exit(1)
        
    print("[+] Credentials check: SUCCESS")

    # 2. Execute pipeline
    try:
        from app.scheduler import run_agent_pipeline_job
        print("[*] Launching Agent Pipeline sequentially (this may take up to 30 seconds to fetch and analyze)...")
        
        results = run_agent_pipeline_job()
        
        if not results:
            print("[-] Pipeline Execution: FAILED (Returned empty list of analyzed stocks)")
            sys.exit(1)
            
        print(f"[+] Pipeline Execution: SUCCESS (Calculated {len(results)} stock rankings)")
        print("\n====================================================")
        print("               TOP 10 STOCK ANALYSIS LEADERBOARD")
        print("====================================================")
        
        # Save analysis preview for reporting
        preview_list = []
        
        for i, stock in enumerate(results[:10]):
            ticker = stock.get("ticker", "")
            company = stock.get("company_name", ticker)
            score = stock.get("unified_score", 0)
            change = stock.get("daily_change", 0.0)
            price = stock.get("current_price", 0.0)
            
            ai_exp = stock.get("ai_explanation", {})
            why = ai_exp.get("why_ranked", "Opportunity asset.")
            confidence = ai_exp.get("confidence_level", "Medium")
            
            direction = "Bullish" if change >= 0 else "Bearish"
            
            print(f"{i+1}. {ticker} | {company}")
            print(f"   Score: {score}/100 | Trend: {direction} ({change:+.2f}%) | Price: ₹{price:,.2f}")
            print(f"   Confidence: {confidence}")
            print(f"   AI Explanation: {why}")
            print("-" * 52)
            
            preview_list.append({
                "rank": i + 1,
                "ticker": ticker,
                "company_name": company,
                "price": f"₹{price:,.2f}",
                "change": f"{'+' if change >= 0 else ''}{change:.2f}%",
                "score": score,
                "confidence": confidence,
                "sentiment": direction,
                "why_ranked": why
            })
            
        # Write results to a temp json file to pass payload data to report generator
        temp_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "top10": preview_list
        }
        with open(os.path.join(base_dir, "live_run_result.json"), "w") as f:
            json.dump(temp_data, f, indent=2)
            
        print("====================================================")
        print("LIVE PIPELINE RUN COMPLETED SUCCESSFULLY!")
        print("====================================================")
        sys.exit(0)
        
    except Exception as e:
        print(f"[-] Pipeline Execution: FAILED. Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Import datetime inside verification scope
from datetime import datetime

if __name__ == "__main__":
    run_analysis()
