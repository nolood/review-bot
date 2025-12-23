"""
Comprehensive async tests for the GLM Code Review Bot.

This module tests async functionality including:
- Async client operations
- Concurrent processing
- Error handling
- Performance improvements
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Test fixtures and utilities
@pytest.fixture
async def mock_gitlab_client():
    """Mock async GitLab client."""
    from src.gitlab_client_async import AsyncGitLabClient
    
    with patch('src.gitlab_client_async.settings', None):
        with patch.dict('os.environ', {
            'GITLAB_TOKEN': 'test-token',
            'GITLAB_API_URL': 'https://gitlab.example.com/api/v4',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456'
        }):
            client = AsyncGitLabClient()
            
            # Mock HTTP client
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "id": 789,
                "body": "Test comment",
                "created_at": "2023-01-01T00:00:00Z"
            }
            mock_response.raise_for_status = AsyncMock()
            
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.post.return_value = mock_response
            
            # Override the get_client context manager
            client.get_client = AsyncMock()
            client.get_client.return_value.__aenter__.return_value = mock_client
            client.get_client.return_value.__aexit__.return_value = None
            
            yield client


@pytest.fixture
async def mock_glm_client():
    """Mock async GLM client."""
    from src.glm_client_async import AsyncGLMClient
    
    with patch.dict('os.environ', {'GLM_API_KEY': 'test-api-key'}):
        client = AsyncGLMClient()
        
        # Mock HTTP client
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"comments": [{"file": "test.py", "line": 10, "comment": "Good code!", "type": "praise", "severity": "low"}]}'
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        mock_response.raise_for_status = AsyncMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        # Override the get_client context manager
        client.get_client = AsyncMock()
        client.get_client.return_value.__aenter__.return_value = mock_client
        client.get_client.return_value.__aexit__.return_value = None
        
        yield client


@pytest.fixture
async def mock_async_review_processor():
    """Mock async review processor."""
    from src.review_processor_async import AsyncReviewProcessor
    from src.config.settings import SettingsProtocol
    
    class MockSettings:
        def __init__(self):
            self.project_id = "123"
            self.mr_iid = "456"
            self.concurrent_glm_requests = 3
        
    settings = MockSettings()
    
    with patch('src.review_processor_async.AsyncClientManager') as mock_manager:
        manager_instance = AsyncMock()
        mock_manager.return_value = manager_instance
        manager_instance.initialize_clients.return_value = True
        
        with patch('src.review_processor_async.AsyncChunkProcessor') as mock_chunk_processor:
            chunk_processor_instance = AsyncMock()
            chunk_processor_instance.process_chunks.return_value = ([], 0)
            mock_chunk_processor.return_value = chunk_processor_instance
            
            processor = AsyncReviewProcessor(settings)
            yield processor


class TestAsyncGitLabClient:
    """Test async GitLab client functionality."""
    
    @pytest.mark.asyncio
    async def test_get_merge_request_diff(self, mock_gitlab_client):
        """Test async diff retrieval."""
        with mock_gitlab_client.get_client() as mock_client:
            mock_client.get.return_value.json.return_value = [{"diff": "test diff content"}]
            
            result = await mock_gitlab_client.get_merge_request_diff()
            
            assert isinstance(result, str)
            assert "test diff content" in result
            mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_post_comment(self, mock_gitlab_client):
        """Test async comment posting."""
        test_body = "Test comment body"
        
        with mock_gitlab_client.get_client() as mock_client:
            result = await mock_gitlab_client.post_comment(test_body)
            
            assert result["id"] == 789
            assert result["body"] == "Test comment"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_post_multiple_comments(self, mock_gitlab_client):
        """Test concurrent comment posting."""
        comments = [
            {"body": "Comment 1"},
            {"body": "Comment 2"},
            {"body": "Comment 3"}
        ]
        
        with mock_gitlab_client.get_client() as mock_client:
            results = await mock_gitlab_client.post_multiple_comments(comments, concurrent_limit=2)
            
            assert len(results) == 3
            assert all(r["id"] == 789 for r in results)
            # Should have called post 3 times
            assert mock_client.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_gitlab_client):
        """Test async error handling."""
        import httpx
        
        with mock_gitlab_client.get_client() as mock_client:
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", 
                request=MagicMock(), 
                response=MagicMock(status_code=404)
            )
            
            with pytest.raises(Exception):  # Should raise GitLabAPIError
                await mock_gitlab_client.get_merge_request_diff()


class TestAsyncGLMClient:
    """Test async GLM client functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_code(self, mock_glm_client):
        """Test async code analysis."""
        test_diff = "test diff content"
        
        result = await mock_glm_client.analyze_code(test_diff)
        
        assert "comments" in result
        assert len(result["comments"]) == 1
        assert result["comments"][0]["file"] == "test.py"
        assert "usage" in result
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_chunks(self, mock_glm_client):
        """Test concurrent chunk analysis."""
        chunks = [
            {"content": "chunk 1"},
            {"content": "chunk 2"},
            {"content": "chunk 3"}
        ]
        
        result = await mock_glm_client.analyze_multiple_chunks(
            chunks, concurrent_limit=2
        )
        
        assert "comments" in result
        assert "total_tokens_used" in result
        assert "chunks_processed" in result
        assert result["chunks_processed"] == 3
    
    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, mock_glm_client):
        """Test token usage tracking."""
        await mock_glm_client.analyze_code("test")
        
        stats = mock_glm_client.get_token_usage_stats()
        
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 150
        assert "prompt_tokens_total" in stats
        assert "completion_tokens_total" in stats


class TestAsyncChunkProcessor:
    """Test async chunk processor functionality."""
    
    @pytest.mark.asyncio
    async def test_process_chunks(self):
        """Test concurrent chunk processing."""
        from src.chunk_processor_async import AsyncChunkProcessor
        from src.config.settings import SettingsProtocol
        
        class MockSettings:
            concurrent_glm_requests = 3
            chunk_timeout = 120
        
        class MockGLMClient:
            async def analyze_code(self, diff, custom_prompt=None, review_type=None):
                return {
                    "comments": [{"comment": f"Analysis of {diff[:20]}"}],
                    "usage": {"total_tokens": 100}
                }
        
        settings = MockSettings()
        glm_client = MockGLMClient()
        processor = AsyncChunkProcessor(settings, glm_client)
        
        chunks = ["chunk 1 content", "chunk 2 content", "chunk 3 content"]
        comments, tokens = await processor.process_chunks(
            chunks, 
            review_type=None, 
            concurrent_limit=2
        )
        
        assert len(comments) == 3
        assert tokens == 300
    
    @pytest.mark.asyncio
    async def test_get_chunk_statistics(self):
        """Test chunk statistics calculation."""
        from src.chunk_processor_async import AsyncChunkProcessor
        
        processor = AsyncChunkProcessor(None, None)
        
        chunks = [
            "short content",
            "medium content that is longer than short but not too long",
            "very long content " * 100  # Large chunk
        ]
        
        stats = await processor.get_chunk_statistics(chunks)
        
        assert stats["total_chunks"] == 3
        assert stats["total_chars"] > 0
        assert stats["avg_chunk_size"] > 0
        assert stats["max_chunk_size"] > stats["min_chunk_size"]
        assert "chunk_size_distribution" in stats


class TestAsyncReviewProcessor:
    """Test async review processor functionality."""
    
    @pytest.mark.asyncio
    async def test_process_merge_request(self, mock_async_review_processor):
        """Test async MR processing."""
        # Mock the dependencies
        mock_gitlab_client = AsyncMock()
        mock_gitlab_client.get_merge_request_details.return_value = {
            "title": "Test MR",
            "source_branch": "feature",
            "target_branch": "main"
        }
        mock_gitlab_client.get_merge_request_diff.return_value = "test diff"
        
        mock_diff_parser = AsyncMock()
        mock_diff_parser.parse_gitlab_diff.return_value = [{"file": "test.py"}]
        mock_diff_parser.get_diff_summary.return_value = {"total_files": 1}
        mock_diff_parser.chunk_large_diff.return_value = [{"content": "chunk content"}]
        
        mock_comment_publisher = AsyncMock()
        mock_comment_publisher.format_comments.return_value = MagicMock(
            summary_comment=None, file_comments=[], inline_comments=[]
        )
        
        mock_async_review_processor.client_manager.get_client.side_effect = [
            mock_gitlab_client,
            mock_diff_parser,
            mock_comment_publisher
        ]
        
        result = await mock_async_review_processor.process_merge_request(dry_run=True)
        
        assert result["status"] == "success"
        assert "processing_time" in result
        assert "stats" in result
    
    @pytest.mark.asyncio
    async def test_process_multiple_merge_requests(self):
        """Test concurrent MR processing."""
        from src.review_processor_async import AsyncReviewProcessor
        from src.config.settings import SettingsProtocol
        
        class MockSettings:
            def __init__(self):
                self.concurrent_glm_requests = 3
        
        # Mock client manager to avoid real API calls
        with patch('src.review_processor_async.AsyncClientManager') as mock_manager:
            manager_instance = AsyncMock()
            manager_instance.initialize_clients.return_value = True
            mock_manager.return_value = manager_instance
            
            # Mock chunk processor
            with patch('src.review_processor_async.AsyncChunkProcessor') as mock_chunk_processor:
                chunk_processor_instance = AsyncMock()
                chunk_processor_instance.process_chunks.return_value = ([], 0)
                mock_chunk_processor.return_value = chunk_processor_instance
                
                processor = AsyncReviewProcessor(MockSettings())
                
                mr_list = [
                    {"project_id": "1", "mr_iid": "1"},
                    {"project_id": "1", "mr_iid": "2"},
                    {"project_id": "2", "mr_iid": "1"}
                ]
                
                results = await processor.process_multiple_merge_requests(
                    mr_list, dry_run=True, concurrent_mrs=2
                )
                
                assert len(results) == 3
                assert all("success" in r for r in results)


class TestAsyncConcurrency:
    """Test async concurrency and performance."""
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """Test that API calls can be made concurrently."""
        import httpx
        
        # Create a simple async client for testing
        client = httpx.AsyncClient()
        
        # Make multiple concurrent requests to a test endpoint
        tasks = []
        for i in range(5):
            task = client.get("https://httpbin.org/delay/1")  # 1 second delay
            tasks.append(task)
        
        # Should complete in roughly 1-2 seconds, not 5 seconds
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        # Should be much faster than sequential calls
        assert end_time - start_time < 3.0  # Allow some overhead
        
        await client.aclose()
    
    @pytest.mark.asyncio
    async def test_semaphore_rate_limiting(self):
        """Test semaphore-based rate limiting."""
        async def limited_operation(semaphore, operation_id):
            async with semaphore:
                await asyncio.sleep(0.1)  # Simulate work
                return operation_id
        
        # Limit to 2 concurrent operations
        semaphore = asyncio.Semaphore(2)
        
        # Start 5 operations
        tasks = [
            limited_operation(semaphore, i) 
            for i in range(5)
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 3 rounds * 0.1s = 0.3s due to limit
        assert end_time - start_time >= 0.25
        assert len(results) == 5
        assert sorted(results) == list(range(5))
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test async timeout handling."""
        async def slow_operation():
            await asyncio.sleep(2.0)  # Takes 2 seconds
            return "completed"
        
        # Should timeout after 1 second
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=1.0)
    
    @pytest.mark.asyncio
    async def test_error_propagation_in_concurrency(self):
        """Test that errors in concurrent operations are properly propagated."""
        async def failing_operation(operation_id):
            if operation_id == 2:
                raise ValueError("Test error")
            await asyncio.sleep(0.1)
            return operation_id
        
        tasks = [
            failing_operation(i) 
            for i in range(5)
        ]
        
        # Should raise the error from the failing operation
        with pytest.raises(ValueError, match="Test error"):
            await asyncio.gather(*tasks, return_exceptions=False)
    
    @pytest.mark.asyncio
    async def test_error_handling_with_return_exceptions(self):
        """Test error handling with return_exceptions=True."""
        async def failing_operation(operation_id):
            if operation_id == 2:
                raise ValueError("Test error")
            await asyncio.sleep(0.1)
            return operation_id
        
        tasks = [
            failing_operation(i) 
            for i in range(5)
        ]
        
        # Should return results including exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == 5
        assert results[0] == 0
        assert results[1] == 1
        assert isinstance(results[2], ValueError)
        assert results[3] == 3
        assert results[4] == 4


# Integration tests for full async workflow
class TestAsyncIntegration:
    """Integration tests for async components."""
    
    @pytest.mark.asyncio
    async def test_full_async_workflow(self):
        """Test complete async workflow with mocked components."""
        # This test simulates the full async workflow
        from src.review_processor_async import AsyncReviewProcessor
        from src.config.settings import SettingsProtocol
        
        class MockSettings:
            def __init__(self):
                self.project_id = "123"
                self.mr_iid = "456"
                self.concurrent_glm_requests = 2
        
        with patch('src.review_processor_async.AsyncClientManager') as mock_manager:
            manager_instance = AsyncMock()
            manager_instance.initialize_clients.return_value = True
            mock_manager.return_value = manager_instance
            
            # Mock GitLab client
            mock_gitlab_client = AsyncMock()
            mock_gitlab_client.get_merge_request_details.return_value = {
                "title": "Test MR",
                "source_branch": "feature",
                "target_branch": "main"
            }
            mock_gitlab_client.get_merge_request_diff.return_value = "sample diff content"
            
            # Mock GLM client
            mock_glm_client = AsyncMock()
            mock_glm_client.analyze_code.return_value = {
                "comments": [{"comment": "Good code structure"}],
                "usage": {"total_tokens": 100}
            }
            
            # Mock diff parser
            mock_diff_parser = AsyncMock()
            mock_diff_parser.parse_gitlab_diff.return_value = [{"file": "test.py"}]
            mock_diff_parser.get_diff_summary.return_value = {"total_files": 1}
            mock_diff_parser.chunk_large_diff.return_value = [{"content": "chunk content"}]
            
            # Mock comment publisher
            mock_comment_publisher = AsyncMock()
            mock_comment_publisher.format_comments.return_value = MagicMock(
                summary_comment=None, file_comments=[], inline_comments=[]
            )
            
            manager_instance.get_client.side_effect = [
                mock_gitlab_client,
                mock_diff_parser,
                mock_glm_client,
                mock_comment_publisher
            ]
            
            with patch('src.review_processor_async.AsyncChunkProcessor') as mock_chunk_processor:
                chunk_processor_instance = AsyncMock()
                chunk_processor_instance.process_chunks.return_value = (
                    [{"comment": "Good code structure"}], 
                    100
                )
                mock_chunk_processor.return_value = chunk_processor_instance
                
                processor = AsyncReviewProcessor(MockSettings())
                
                result = await processor.process_merge_request(dry_run=True)
                
                assert result["status"] == "success"
                assert result["stats"]["chunks_processed"] == 1
                assert result["stats"]["total_comments_generated"] == 1
                assert result["stats"]["total_tokens_used"] == 100


if __name__ == "__main__":
    # Run async tests
    asyncio.run(pytest.main([__file__, "-v"]))