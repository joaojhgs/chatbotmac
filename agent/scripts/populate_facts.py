"""Script to crawl web and populate MacBook Air facts in Supabase."""

import os
import re
import sys
import time
from typing import Any

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.embeddings import EmbeddingGenerator
from app.rag.supabase_client import SupabaseRAGClient

# Official sources to crawl for MacBook Air information
OFFICIAL_SOURCES = [
    {
        "url": "https://www.apple.com/macbook-air/",
        "source": "Apple Official",
        "category": "overview",
    },
    {
        "url": "https://www.apple.com/macbook-air/specs/",
        "source": "Apple Official",
        "category": "technical_specs",
        "model": "M4",
    },
    {
        "url": "https://www.apple.com/br/mac/compare/?modelList=MacBook-Air-M4,MacBook-Air-M4-15,MacBook-Air-M3",
        "source": "Apple Official",
        "category": "technical_specs",
        "model": "M3",
    },
    {
        "url": "https://www.apple.com/br/mac/compare/?modelList=MacBook-Air-M4,MacBook-Air-M4-15,MacBook-Air-M2",
        "source": "Apple Support",
        "category": "technical_specs",
        "model": "M2",
    },
    {
        "url": "https://www.apple.com/br/mac/compare/?modelList=MacBook-Air-M4,MacBook-Air-M4-15,MacBook-Air-M1",
        "source": "Apple Support",
        "category": "technical_specs",
        "model": "M1",
    },
]

# Additional reliable sources
ADDITIONAL_SOURCES = [
    {
        "url": "https://en.wikipedia.org/wiki/MacBook_Air",
        "source": "Wikipedia",
        "category": "general",
    },
    {
        "url": "https://everymac.com/systems/apple/macbook-air/index-macbook-air.html",
        "source": "EveryMac",
        "category": "technical_specs",
    },
]


def extract_facts_from_text(
    text: str, source_info: dict[str, Any], llm: ChatOpenAI
) -> list[dict[str, Any]]:
    """
    Extract relevant facts from text using LLM.

    Args:
        text: Text content to extract facts from
        source_info: Source metadata (url, source, category, model)
        llm: Language model for extraction

    Returns:
        List of extracted facts with metadata
    """
    # Split text into chunks for processing
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=200, length_function=len
    )

    chunks = text_splitter.split_text(text)
    facts = []

    for chunk in chunks:
        if len(chunk.strip()) < 100:  # Skip very short chunks
            continue

        try:
            # Use LLM to extract facts
            prompt = f"""Extract specific, factual information about MacBook Air from the following text.
Return only factual statements that would be useful for answering questions about MacBook Air.
Each fact should be a complete, standalone sentence.

Be mindful of which model is being discussed and only extract facts about that model.

In case of comparisons, extract facts about the models being compared against the latest model (M4).

Text:
{chunk}

Extract 3-5 key facts. Format each fact as a separate line starting with "- ".
Focus on:
- Technical specifications (CPU, GPU, memory, storage, display, battery)
- Features and capabilities
- Design and dimensions
- Connectivity options
- Software and operating system
- Pricing and availability (if mentioned)
- Comparisons between models

Return only the facts, one per line, starting with "- "."""

            response = llm.invoke(prompt)
            extracted_text = response.content if hasattr(response, "content") else str(response)

            # Parse extracted facts
            fact_lines = [
                line.strip()
                for line in extracted_text.split("\n")
                if line.strip().startswith("- ") and len(line.strip()) > 20
            ]

            for fact_line in fact_lines:
                # Remove the "- " prefix
                fact_content = fact_line[2:].strip()
                if fact_content and len(fact_content) > 20:
                    metadata = {
                        "source": source_info.get("source", "Unknown"),
                        "url": source_info.get("url", ""),
                        "category": source_info.get("category", "general"),
                    }
                    if "model" in source_info:
                        metadata["model"] = source_info["model"]

                    facts.append({"content": fact_content, "metadata": metadata})

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"  ⚠ Error extracting facts from chunk: {e!s}")
            continue

    return facts


def crawl_and_extract_facts(sources: list[dict[str, Any]], llm: ChatOpenAI) -> list[dict[str, Any]]:
    """
    Crawl web sources and extract facts.

    Args:
        sources: List of source dictionaries with url and metadata
        llm: Language model for fact extraction

    Returns:
        List of extracted facts
    """
    all_facts = []

    for i, source_info in enumerate(sources, 1):
        url = source_info.get("url")
        print(f"\n[{i}/{len(sources)}] Crawling: {url}")

        try:
            # Load web page content
            loader = WebBaseLoader(url)
            documents = loader.load()

            if not documents:
                print(f"No content extracted from {url}")
                continue

            # Combine all document content
            full_text = "\n\n".join([doc.page_content for doc in documents])

            if len(full_text.strip()) < 100:
                print(f"Content too short from {url}")
                continue

            print(f"Loaded {len(full_text)} characters")

            # Extract facts using LLM
            print("Extracting facts...")
            facts = extract_facts_from_text(full_text, source_info, llm)

            print(f"Extracted {len(facts)} facts")
            all_facts.extend(facts)

            # Rate limiting
            time.sleep(2)

        except Exception as e:
            print(f"Error crawling {url}: {e!s}")
            continue

    return all_facts


def deduplicate_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate facts based on content similarity.

    Args:
        facts: List of fact dictionaries

    Returns:
        Deduplicated list of facts
    """
    seen = set()
    unique_facts = []

    for fact in facts:
        # Normalize content for comparison
        content = fact["content"].lower().strip()
        # Remove extra whitespace
        content = re.sub(r"\s+", " ", content)

        # Simple deduplication: exact match
        if content not in seen:
            seen.add(content)
            unique_facts.append(fact)

    return unique_facts


def populate_facts():
    """Crawl web sources and populate MacBook Air facts in Supabase."""
    # Load environment variables
    load_dotenv()

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not all([supabase_url, supabase_key, openai_api_key]):
        print("Error: Missing required environment variables.")
        print("Please set SUPABASE_URL, SUPABASE_KEY, and OPENAI_API_KEY in your .env file.")
        return

    # Initialize clients
    print("Initializing clients...")
    rag_client = SupabaseRAGClient(supabase_url, supabase_key, openai_api_key)
    embedding_gen = EmbeddingGenerator(openai_api_key)

    # Initialize LLM for fact extraction
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=openai_api_key)

    # Combine all sources
    all_sources = OFFICIAL_SOURCES + ADDITIONAL_SOURCES

    print(f"\n{'=' * 60}")
    print("Crawling web sources for MacBook Air information...")
    print(f"{'=' * 60}\n")

    # Crawl and extract facts
    extracted_facts = crawl_and_extract_facts(all_sources, llm)

    if not extracted_facts:
        print("\nNo facts extracted. Please check the sources and try again.")
        return

    print(f"\n{'=' * 60}")
    print(f"Extracted {len(extracted_facts)} facts from web sources")
    print(f"{'=' * 60}\n")

    # Deduplicate facts
    print("Deduplicating facts...")
    unique_facts = deduplicate_facts(extracted_facts)
    print(f"{len(unique_facts)} unique facts after deduplication\n")

    # Generate embeddings and insert facts
    print(f"{'=' * 60}")
    print(f"Populating {len(unique_facts)} facts into Supabase...")
    print(f"{'=' * 60}\n")

    successful = 0
    failed = 0

    for i, fact in enumerate(unique_facts, 1):
        try:
            content = fact["content"]
            metadata = fact["metadata"]

            # Generate embedding
            if i % 10 == 0:
                print(f"Processing fact {i}/{len(unique_facts)}: {content[:60]}...")

            embedding = embedding_gen.generate_embedding(content)

            # Check if fact already exists (optional - to avoid duplicates in database)
            existing = (
                rag_client.supabase.table("macbook_facts")
                .select("id")
                .eq("content", content)
                .limit(1)
                .execute()
            )

            if existing.data:
                print(f"Fact {i} already exists, skipping...")
                continue

            # Insert into Supabase
            rag_client.supabase.table("macbook_facts").insert(
                {"content": content, "embedding": embedding, "metadata": metadata}
            ).execute()

            successful += 1
            if i % 10 == 0:
                print(f"Inserted fact {i}")

            # Rate limiting for embeddings
            time.sleep(0.1)

        except Exception as e:
            failed += 1
            print(f"Error inserting fact {i}: {e!s}")

    print(f"\n{'=' * 60}")
    print(f"Done! Successfully inserted {successful} facts.")
    if failed > 0:
        print(f"Failed to insert {failed} facts.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    populate_facts()
