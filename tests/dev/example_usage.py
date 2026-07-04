#!/usr/bin/env python3
"""
Example usage script for Scenario Builder Service.

This script demonstrates how to:
1. Process documents from the data folder
2. Query the system with questions
3. Get LLM-generated answers with sources
"""

import time

import requests

# Configuration
API_BASE_URL = "http://localhost:8002"


def check_health():
    """Check if the service is running"""
    print("🔍 Checking service health...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service is healthy: {data['service']} v{data['version']}")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to service: {e}")
        print(f"   Make sure the service is running at {API_BASE_URL}")
        return False


def process_documents(data_folder="./data", force_reprocess=False):
    """Process documents from the data folder"""
    print(f"\n📚 Processing documents from {data_folder}...")

    payload = {"data_folder": data_folder, "force_reprocess": force_reprocess}

    try:
        response = requests.post(f"{API_BASE_URL}/process", json=payload)

        if response.status_code == 200:
            data = response.json()
            print("✅ Processing completed:")
            print(f"   Status: {data['status']}")
            print(f"   Message: {data['message']}")
            print(f"   Documents processed: {data['documents_processed']}")
            print(f"   Chunks created: {data['chunks_created']}")
            return True
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return False


def query_documents(query, top_k=5, use_reranking=True):
    """Query documents and get LLM-generated answer"""
    print(f"\n🔎 Querying: '{query}'")

    payload = {
        "query": query,
        "top_k": top_k,
        "use_reranking": use_reranking,
        "use_hybrid": False,
        "initial_k": 150,
        "use_advanced_reranker": True,
    }

    try:
        response = requests.post(f"{API_BASE_URL}/api/query", json=payload)

        if response.status_code == 200:
            data = response.json()

            print("\n📖 Answer:")
            print(f"   {data['answer']}")

            print(f"\n📚 Sources ({len(data['sources'])}):")
            for i, source in enumerate(data["sources"], 1):
                print(f"   {i}. {source['document_name']} (score: {source['score']:.3f})")

            print("\n📊 Metadata:")
            metadata = data["metadata"]
            print(f"   Initial retrieval: {metadata.get('initial_retrieval_count', 'N/A')}")
            print(f"   Final results: {metadata.get('final_count', 'N/A')}")
            print(f"   Reranking: {metadata.get('reranking_applied', False)}")
            print(f"   Advanced reranker: {metadata.get('advanced_reranker_used', False)}")

            return data

        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error during query: {e}")
        return None


def main():
    """Main example workflow"""
    print("=" * 60)
    print("Scenario Builder Service - Example Usage")
    print("=" * 60)

    # Check health
    if not check_health():
        print("\n⚠️  Please start the service first:")
        print("   python main.py")
        return

    # Process documents
    print("\n" + "=" * 60)
    process_success = process_documents()

    if not process_success:
        print("\n⚠️  No documents processed. Make sure:")
        print("   1. Documents exist in the ./data folder")
        print("   2. Supported formats: PDF, DOCX, XLSX, TXT, MD")
        return

    # Wait a moment for processing to complete
    time.sleep(1)

    # Example queries
    print("\n" + "=" * 60)
    print("Running example queries...")

    queries = [
        "What are the main topics covered in the documents?",
        "Summarize the key findings",
        "What are the recommendations?",
    ]

    for query in queries:
        result = query_documents(query, top_k=5)
        if result:
            print("\n" + "-" * 60)
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("✨ Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
