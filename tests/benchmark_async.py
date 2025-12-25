"""
Performance benchmark for async vs synchronous review bot.

This module compares performance between async and synchronous implementations.
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any
import httpx


async def benchmark_concurrent_requests(
    urls: List[str], 
    concurrent_limit: int = 5
) -> Dict[str, Any]:
    """Benchmark concurrent HTTP requests."""
    
    async def single_request(url: str) -> float:
        """Make a single request and return duration."""
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                await client.get(url, timeout=10)
            return time.time() - start
        except Exception:
            return time.time() - start
    
    semaphore = asyncio.Semaphore(concurrent_limit)
    
    async def limited_request(url: str) -> float:
        async with semaphore:
            return await single_request(url)
    
    # Concurrent requests
    start_time = time.time()
    tasks = [limited_request(url) for url in urls]
    concurrent_durations = await asyncio.gather(*tasks)
    concurrent_total = time.time() - start_time
    
    # Sequential requests for comparison
    start_time = time.time()
    sequential_durations = []
    for url in urls:
        duration = await single_request(url)
        sequential_durations.append(duration)
    sequential_total = time.time() - start_time
    
    return {
        "concurrent": {
            "total_time": concurrent_total,
            "durations": concurrent_durations,
            "avg_time": statistics.mean(concurrent_durations),
            "min_time": min(concurrent_durations),
            "max_time": max(concurrent_durations)
        },
        "sequential": {
            "total_time": sequential_total,
            "durations": sequential_durations,
            "avg_time": statistics.mean(sequential_durations),
            "min_time": min(sequential_durations),
            "max_time": max(sequential_durations)
        },
        "improvement": {
            "time_reduction": sequential_total - concurrent_total,
            "speedup_ratio": sequential_total / concurrent_total,
            "efficiency": (concurrent_total / sequential_total) * 100
        }
    }


async def benchmark_chunk_processing(
    chunks: List[str],
    processing_delay: float = 0.1,
    concurrent_limit: int = 3
) -> Dict[str, Any]:
    """Benchmark chunk processing with simulated work."""
    
    async def process_chunk(chunk: str, index: int) -> Dict[str, Any]:
        """Simulate chunk processing."""
        await asyncio.sleep(processing_delay)
        return {
            "chunk_index": index,
            "size": len(chunk),
            "processing_time": processing_delay
        }
    
    semaphore = asyncio.Semaphore(concurrent_limit)
    
    async def limited_process(chunk: str, index: int) -> Dict[str, Any]:
        async with semaphore:
            return await process_chunk(chunk, index)
    
    # Concurrent processing
    start_time = time.time()
    tasks = [limited_process(chunk, i) for i, chunk in enumerate(chunks)]
    concurrent_results = await asyncio.gather(*tasks)
    concurrent_total = time.time() - start_time
    
    # Sequential processing
    start_time = time.time()
    sequential_results = []
    for i, chunk in enumerate(chunks):
        result = await process_chunk(chunk, i)
        sequential_results.append(result)
    sequential_total = time.time() - start_time
    
    return {
        "chunks_count": len(chunks),
        "concurrent_limit": concurrent_limit,
        "concurrent": {
            "total_time": concurrent_total,
            "results": concurrent_results
        },
        "sequential": {
            "total_time": sequential_total,
            "results": sequential_results
        },
        "improvement": {
            "time_reduction": sequential_total - concurrent_total,
            "speedup_ratio": sequential_total / concurrent_total,
            "theoretical_max": len(chunks) * processing_delay / concurrent_limit
        }
    }


async def main():
    """Run performance benchmarks."""
    print("🚀 Async Performance Benchmark")
    print("=" * 50)
    
    # Test 1: HTTP request concurrency
    print("\n📡 HTTP Request Concurrency Test")
    test_urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1"
    ]
    
    try:
        http_results = await benchmark_concurrent_requests(test_urls, concurrent_limit=3)
        
        print(f"Concurrent: {http_results['concurrent']['total_time']:.2f}s")
        print(f"Sequential: {http_results['sequential']['total_time']:.2f}s")
        print(f"Speedup: {http_results['improvement']['speedup_ratio']:.2f}x")
        print(f"Efficiency: {http_results['improvement']['efficiency']:.1f}%")
        
    except Exception as e:
        print(f"HTTP test failed (network issue): {e}")
    
    # Test 2: Chunk processing
    print("\n🔄 Chunk Processing Concurrency Test")
    test_chunks = [
        "def function_1(): pass",
        "def function_2(): pass",
        "def function_3(): pass",
        "def function_4(): pass",
        "def function_5(): pass",
        "def function_6(): pass",
        "def function_7(): pass",
        "def function_8(): pass"
    ]
    
    chunk_results = await benchmark_chunk_processing(
        test_chunks, 
        processing_delay=0.2, 
        concurrent_limit=3
    )
    
    print(f"Chunks: {chunk_results['chunks_count']}")
    print(f"Concurrent limit: {chunk_results['concurrent_limit']}")
    print(f"Concurrent: {chunk_results['concurrent']['total_time']:.2f}s")
    print(f"Sequential: {chunk_results['sequential']['total_time']:.2f}s")
    print(f"Speedup: {chunk_results['improvement']['speedup_ratio']:.2f}x")
    print(f"Theoretical max: {chunk_results['improvement']['theoretical_max']:.2f}s")
    
    # Test 3: Different concurrency levels
    print("\n📊 Concurrency Scaling Test")
    for limit in [1, 2, 3, 5, 8]:
        results = await benchmark_chunk_processing(
            test_chunks[:6],  # Use 6 chunks for this test
            processing_delay=0.1,
            concurrent_limit=limit
        )
        print(f"Limit {limit}: {results['concurrent']['total_time']:.2f}s "
              f"(speedup: {results['improvement']['speedup_ratio']:.2f}x)")
    
    print("\n✅ Benchmark completed!")
    print("\nKey Takeaways:")
    print("• Async provides significant speedup for I/O bound operations")
    print("• Optimal concurrency depends on workload and external API limits")
    print("• Diminishing returns after certain concurrency levels")
    print("• Error handling and rate limiting are crucial for production")


if __name__ == "__main__":
    asyncio.run(main())