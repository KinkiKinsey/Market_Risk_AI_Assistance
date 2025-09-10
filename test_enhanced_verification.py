#!/usr/bin/env python3
"""
Test script for the enhanced Investment Noise Filter
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_enhanced_verification():
    """Test the enhanced verification system"""
    
    try:
        from News_Verification import verify_statement_with_user
        
        print("🚀 Testing Enhanced Investment Noise Filter")
        print("=" * 60)
        
        # Test cases
        test_cases = [
            {
                "name": "Coinbase Q2 Earnings (Original)",
                "statement": "In late July, Coinbase reported Q2 2025 earnings that missed expectations:",
                "expected": "Should pass - multiple sources confirm Q2 2025 earnings event"
            },
            {
                "name": "Coinbase Q2 Revenue (Context Variant)",
                "statement": "Coinbase Q2 2025 revenue missed analyst expectations",
                "expected": "Should pass - same company, period, financial metric"
            },
            {
                "name": "Apple Q2 Results",
                "statement": "Apple reported Q2 2025 earnings that beat expectations",
                "expected": "Should pass - clear company, period, financial metric"
            },
            {
                "name": "Unrelated Statement",
                "statement": "The weather in New York was sunny yesterday",
                "expected": "Should fail - no investment relevance"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print(f"Statement: {test_case['statement']}")
            print(f"Expected: {test_case['expected']}")
            print("-" * 40)
            
            try:
                result = await verify_statement_with_user(
                    statement=test_case['statement'],
                    user_id="test_user",
                    use_video=False
                )
                
                print(f"✅ Result: {result.final_decision}")
                print(f"📊 Reasoning: {result.final_reasoning}")
                
                # Show filter results
                for filter_result in result.filters:
                    status_emoji = "✅" if filter_result.status.value == "passed" else "❌" if filter_result.status.value == "failed" else "⏭️"
                    print(f"{status_emoji} {filter_result.name}: {filter_result.status.value}")
                
                print()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
        
        print("🎉 Enhanced verification testing complete!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the correct directory with News_Verification.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_verification())
