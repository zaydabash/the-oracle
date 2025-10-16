"""Ingestion module tests."""

from unittest.mock import Mock, patch

from ..ingestion.arxiv_client import ArxivClient
from ..ingestion.normalizers import SignalEventNormalizer


class TestSignalEventNormalizer:
    """Test signal event normalizer."""

    def test_normalize_arxiv_paper(self):
        """Test arXiv paper normalization."""
        normalizer = SignalEventNormalizer()

        paper = {
            "id": "arxiv:2401.00001",
            "title": "Test Paper Title",
            "authors": ["John Doe"],
            "abstract": "Test abstract",
            "categories": ["cs.AI"],
            "published": "2024-01-01T00:00:00Z",
            "updated": "2024-01-01T00:00:00Z",
            "primary_category": "cs.AI",
            "url": "https://arxiv.org/abs/2401.00001",
            "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf"
        }

        event = normalizer.normalize_arxiv_paper(paper)

        assert event is not None
        assert event.id == "arxiv:2401.00001"
        assert event.source == "arxiv"
        assert event.title == "Test Paper Title"
        assert event.url == "https://arxiv.org/abs/2401.00001"
        assert event.magnitude > 0

    def test_normalize_github_repo(self):
        """Test GitHub repository normalization."""
        normalizer = SignalEventNormalizer()

        repo = {
            "id": "github:test/repo",
            "name": "test-repo",
            "full_name": "test/repo",
            "description": "Test repository",
            "html_url": "https://github.com/test/repo",
            "language": "Python",
            "stargazers_count": 100,
            "forks_count": 20,
            "watchers_count": 50,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z",
            "topics": ["test", "example"]
        }

        event = normalizer.normalize_github_repo(repo)

        assert event is not None
        assert event.id == "github:test/repo"
        assert event.source == "github"
        assert event.title == "test-repo"
        assert event.magnitude > 0

    def test_normalize_batch(self):
        """Test batch normalization."""
        normalizer = SignalEventNormalizer()

        papers = [
            {
                "id": "arxiv:2401.00001",
                "title": "Test Paper 1",
                "authors": ["John Doe"],
                "abstract": "Test abstract 1",
                "categories": ["cs.AI"],
                "published": "2024-01-01T00:00:00Z",
                "updated": "2024-01-01T00:00:00Z",
                "primary_category": "cs.AI",
                "url": "https://arxiv.org/abs/2401.00001",
                "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf"
            },
            {
                "id": "arxiv:2401.00002",
                "title": "Test Paper 2",
                "authors": ["Jane Doe"],
                "abstract": "Test abstract 2",
                "categories": ["cs.LG"],
                "published": "2024-01-02T00:00:00Z",
                "updated": "2024-01-02T00:00:00Z",
                "primary_category": "cs.LG",
                "url": "https://arxiv.org/abs/2401.00002",
                "pdf_url": "https://arxiv.org/pdf/2401.00002.pdf"
            }
        ]

        events = normalizer.normalize_batch(papers, "arxiv")

        assert len(events) == 2
        assert all(event.source == "arxiv" for event in events)
        assert events[0].title == "Test Paper 1"
        assert events[1].title == "Test Paper 2"


class TestArxivClient:
    """Test arXiv client."""

    @patch('requests.get')
    def test_fetch_recent_papers_mock_mode(self, mock_get):
        """Test fetching papers in mock mode."""
        with patch('..ingestion.arxiv_client.settings') as mock_settings:
            mock_settings.is_mock_mode = True
            mock_settings.mock_data_path = Mock()
            mock_settings.mock_data_path.exists.return_value = True

            client = ArxivClient()

            with patch('builtins.open', mock_open()):
                papers = client.fetch_recent_papers()
                assert isinstance(papers, list)

    def test_parse_arxiv_entry(self):
        """Test arXiv entry parsing."""
        client = ArxivClient()

        entry = Mock()
        entry.id = "http://arxiv.org/abs/2401.00001"
        entry.title = "Test Paper"
        entry.authors = [Mock(name="John Doe")]
        entry.summary = "Test abstract"
        entry.tags = [Mock(term="cs.AI")]
        entry.published = "2024-01-01T00:00:00Z"
        entry.updated = "2024-01-01T00:00:00Z"
        entry.link = "https://arxiv.org/abs/2401.00001"

        paper = client._parse_arxiv_entry(entry)

        assert paper is not None
        assert paper["id"] == "arxiv:2401.00001"
        assert paper["title"] == "Test Paper"
        assert paper["authors"] == ["John Doe"]


def mock_open():
    """Mock open function for testing."""
    import json
    from unittest.mock import mock_open as original_mock_open

    mock_data = [
        {
            "id": "arxiv:2401.00001",
            "title": "Test Paper",
            "authors": ["John Doe"],
            "abstract": "Test abstract",
            "categories": ["cs.AI"],
            "published": "2024-01-01T00:00:00Z",
            "updated": "2024-01-01T00:00:00Z",
            "primary_category": "cs.AI"
        }
    ]

    return original_mock_open(read_data=json.dumps(mock_data))
