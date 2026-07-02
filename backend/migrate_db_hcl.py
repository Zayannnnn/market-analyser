import os
import sys
import logging

# Ensure local imports resolve
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_db_hcl")

from app.db import db, MockFirestoreClient

def migrate_database():
    print("====================================================")
    print("       FIRESTORE DB MIGRATION: HCL -> HCLTECH")
    print("====================================================")
    
    if isinstance(db, MockFirestoreClient):
        print("[-] Error: Using Mock Firestore client because Firebase credentials are not set in the environment.")
        print("    Please run this script with correct FIREBASE_SERVICE_ACCOUNT_JSON or serviceAccountKey.json.")
        return
        
    print("[+] Connected to Firestore database.")
    
    # 1. Migrate stocks document
    print("\n1. Migrating 'stocks' document...")
    hcl_stock_ref = db.collection("stocks").document("HCL")
    hcl_stock_doc = hcl_stock_ref.get()
    
    if hcl_stock_doc.exists:
        data = hcl_stock_doc.to_dict()
        print(f"   Found 'stocks/HCL': {data}")
        hcltech_data = data.copy()
        hcltech_data["company_name"] = "HCL Technologies Limited"
        # Remove old cached fields to force recalculation
        hcltech_data.pop("current_price", None)
        hcltech_data.pop("daily_change", None)
        hcltech_data.pop("technical_indicators", None)
        hcltech_data.pop("unified_score", None)
        hcltech_data.pop("subscores", None)
        
        db.collection("stocks").document("HCLTECH").set(hcltech_data, merge=True)
        print("   Created 'stocks/HCLTECH'.")
        hcl_stock_ref.delete()
        print("   Deleted 'stocks/HCL'.")
    else:
        print("   'stocks/HCL' document not found. Seeding 'stocks/HCLTECH' directly...")
        db.collection("stocks").document("HCLTECH").set({
            "company_name": "HCL Technologies Limited",
            "quality_score": 75.0
        }, merge=True)
        print("   Seeded 'stocks/HCLTECH'.")
        
    # 2. Migrate news articles
    print("\n2. Migrating news collection...")
    news_query = db.collection("news").where("ticker", "==", "HCL").get()
    print(f"   Found {len(news_query)} news articles tagged with 'HCL'.")
    for doc in news_query:
        news_data = doc.to_dict()
        print(f"   Updating article {doc.id}: '{news_data.get('title')}'")
        db.collection("news").document(doc.id).update({"ticker": "HCLTECH"})
    print("   News articles migration complete.")
    
    # 3. Migrate AI Analysis explanations
    print("\n3. Migrating 'ai_analysis' document...")
    hcl_ai_ref = db.collection("ai_analysis").document("HCL")
    hcl_ai_doc = hcl_ai_ref.get()
    if hcl_ai_doc.exists:
        ai_data = hcl_ai_doc.to_dict()
        print(f"   Found 'ai_analysis/HCL': {ai_data}")
        db.collection("ai_analysis").document("HCLTECH").set(ai_data)
        hcl_ai_ref.delete()
        print("   Migrated 'ai_analysis/HCL' to 'ai_analysis/HCLTECH' and deleted old document.")
    else:
        print("   'ai_analysis/HCL' document not found.")
        
    # 4. Invalidate rankings document to force recalculation of top 10
    print("\n4. Resetting current rankings to trigger pipeline run...")
    try:
        db.collection("rankings").document("current").delete()
        print("   Deleted 'rankings/current' document.")
    except Exception as e:
        print(f"   Error resetting rankings: {e}")
        
    print("\n====================================================")
    print("               MIGRATION SCRIPT COMPLETE!")
    print("====================================================")

if __name__ == "__main__":
    migrate_database()
