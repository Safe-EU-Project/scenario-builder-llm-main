"""
Test script for structured output using the new generate_structured_answer method
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.models import Incident
from llm.llm_client import LLMClient

# Sample context for testing
sample_context = """
T+0 (09:00) – SIEM Alert: Data Integrity Check Failed
A nightly reconciliation job reports a non-zero difference between total debits and credits
in the core banking database. The SIEM dashboard flashes a warning and an email is sent to
the on-duty analyst.
Inject: Screenshot of the SIEM notification and a brief log excerpt showing the error code.

Expected Actions:
- Verify the SIEM alert against the core database logs.
- Confirm the discrepancy and assess its magnitude.
- Prioritize the alert for immediate triage.
"""

sample_query = "Generate a structured incident based on the provided context."


def test_structured_output():
    """Test the structured output functionality"""
    print("=" * 60)
    print("Testing Structured Output with Incident Model")
    print("=" * 60)

    # Initialize LLM client
    print("\nInitializing LLM client...")
    llm_client = LLMClient()

    print(f"API URL: {llm_client.api_url}")
    print(f"Model: {llm_client.model}")
    print(f"Temperature: {llm_client.temperature}")

    print("\n" + "-" * 60)
    print("Context:")
    print("-" * 60)
    print(sample_context[:200] + "...")

    print("\n" + "-" * 60)
    print("Query:")
    print("-" * 60)
    print(sample_query)

    print("\n" + "-" * 60)
    print("Calling LLM with structured output...")
    print("-" * 60)

    try:
        # Call the new structured method
        incident = llm_client.generate_structured_answer(
            query=sample_query, context=sample_context, response_model=Incident
        )

        print("\nSUCCESS! Received structured response:")
        print("=" * 60)
        print(f"\nTitle: {incident.title}")
        print(f"Timestamp: {incident.message_timestamp}")
        print(f"\nDescription:\n{incident.description}")

        if incident.inject:
            print(f"\nInject:\n{incident.inject}")

        if incident.expected_actions:
            print(f"\nExpected Actions ({len(incident.expected_actions)}):")
            for i, action in enumerate(incident.expected_actions, 1):
                print(f"  {i}. {action}")

        print("\n" + "=" * 60)
        print("Structured output test completed successfully!")
        print("=" * 60)

        # Also demonstrate JSON serialization
        print("\nJSON representation:")
        print(incident.model_dump_json(indent=2))

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}")
        print(f"Details: {str(e)}")
        import traceback

        traceback.print_exc()


def test_comparison():
    """Compare old vs new method"""
    print("\n\n")
    print("=" * 60)
    print("Comparison: Old vs New Method")
    print("=" * 60)

    llm_client = LLMClient()

    # Test old method
    print("\n1. Old Method (generate_answer) - Returns free text:")
    print("-" * 60)
    try:
        answer = llm_client.generate_answer(query=sample_query, context=sample_context[:500])
        print(f"Type: {type(answer)}")
        print(f"Response:\n{answer[:300]}...")
    except Exception as e:
        print(f"Error: {e}")

    # Test new method
    print("\n\n2. New Method (generate_structured_answer) - Returns Pydantic model:")
    print("-" * 60)
    try:
        incident = llm_client.generate_structured_answer(
            query=sample_query, context=sample_context[:500], response_model=Incident
        )
        print(f"Type: {type(incident)}")
        print(f"Model: {incident.__class__.__name__}")
        print(f"Title: {incident.title}")
        print("Validated: True")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STRUCTURED OUTPUT TEST SCRIPT")
    print("=" * 60)
    print("\nThis script demonstrates the new structured output feature")
    print("using the generate_structured_answer() method with the Incident model.")
    print("\nNote: Make sure the LLM API is running and configured correctly.")
    print("=" * 60)

    test_structured_output()
    # test_comparison()  # Uncomment to run comparison test
