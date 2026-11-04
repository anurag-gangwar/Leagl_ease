import argparse
import os

from dotenv import load_dotenv
from utils.pdf_parser import extract_text, clean_text
from utils.llm_analyzer import LLMServiceError, analyze_contract, safe_error_message

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def run_analysis(filepath):
    print(f"🔍 Starting analysis for: {filepath}")
    try:
        # 1. Extract Text
        raw_text = extract_text(filepath)
        text = clean_text(raw_text)
        print(f"✅ Text extracted ({len(text)} chars)")

        if len(text.strip()) < 50:
            print("❌ Error: Extracted text is too short or empty.")
            return

        # 2. Analyze with the configured AI service.
        result = analyze_contract(text, 'hindi')

        print("\n" + "="*60)
        print("⚖️ LEGAL-EASE ANALYSIS RESULT")
        print("="*60)
        print(f"\n📄 Contract Type: {result.get('contract_type')}")
        print(f"🚨 Overall Risk: {result.get('overall_risk')}")
        print(f"\n📝 Summary (English):")
        print(result.get('summary'))
        print(f"\n🌐 Summary (Hindi):")
        print(result.get('translated_summary'))

        print("\n" + "-"*30)
        print("🚩 KEY CLAUSES")
        print("-"*30)
        for i, clause in enumerate(result.get('clauses', []), 1):
            print(f"\n#{i} {clause.get('type')} [{clause.get('severity')}]")
            if clause.get('is_red_flag'):
                print("🚩 RED FLAG")
            print(f"Simplified: {clause.get('simplified')}")
            print(f"Risk: {clause.get('explanation')}")
            print(f"Hindi: {clause.get('translated')}")
        print("="*60)

    except LLMServiceError as exc:
        print(f"❌ Analysis failed: {safe_error_message(exc)}")
    except Exception:
        print("❌ Analysis failed. Please check the file and AI service configuration.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze a local PDF or TXT contract.')
    parser.add_argument('file', help='Path to the PDF or TXT contract')
    args = parser.parse_args()
    run_analysis(args.file)
