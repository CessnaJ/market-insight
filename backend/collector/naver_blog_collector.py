"""Naver Blog Content Collector

Collects content from Naver blogs using RSS feeds.
Extracts blog post information and stores in ContentItem table.
"""

import feedparser
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from sqlmodel import Session

from storage.db import get_session, add_content
from storage.models import ContentItem
from storage.vector_store import VectorStore
from analyzer.llm_router import get_llm_router


class NaverBlogCollector:
    """
    Naver blog content collector using RSS feeds

    Usage:
        collector = NaverBlogCollector()
        collector.collect_all()
        collector.collect_blog("blog_id")
    """

    def __init__(self, config_path: str = "config/sources.yaml"):
        """
        Initialize Naver blog collector

        Args:
            config_path: Path to sources.yaml configuration file
        """
        self.config_path = Path(__file__).parent.parent / config_path
        self.config = self._load_config()
        self.vector_store = VectorStore()
        self.llm = get_llm_router()

    def _load_config(self) -> List[Dict[str, Any]]:
        """Load Naver blog configuration"""
        import yaml

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config.get("naver_blogs", [])

    def _fetch_feed(self, rss_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch RSS feed from URL

        Args:
            rss_url: RSS feed URL

        Returns:
            Parsed feed or None if failed
        """
        try:
            response = httpx.get(rss_url, timeout=30.0)
            response.raise_for_status()
            return feedparser.parse(response.content)
        except Exception as e:
            print(f"Error fetching RSS feed {rss_url}: {e}")
            return None

    def _extract_post_info(self, entry: feedparser.FeedParserDict) -> Dict[str, Any]:
        """
        Extract blog post information from RSS entry

        Args:
            entry: RSS entry

        Returns:
            Blog post information dictionary
        """
        return {
            "title": entry.get("title", ""),
            "description": entry.get("description", ""),
            "url": entry.get("link", ""),
            "published_at": datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else None,
            "author": entry.get("author", ""),
            "tags": [tag.term for tag in entry.get("tags", [])] if hasattr(entry, "tags") else [],
        }

    def _extract_content_preview(self, description: str, max_length: int = 2000) -> str:
        """
        Extract content preview from blog post description

        Args:
            description: Blog post description (HTML)
            max_length: Maximum length of preview

        Returns:
            Content preview text
        """
        # Remove HTML tags
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(description, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text[:max_length]

    def _save_full_content(self, blog_id: str, post_id: str, content: str) -> str:
        """
        Save full content to file

        Args:
            blog_id: Blog ID
            post_id: Post ID (extracted from URL)
            content: Full content

        Returns:
            File path
        """
        data_dir = Path(__file__).parent.parent / "data" / "raw" / "naver_blog"
        data_dir.mkdir(parents=True, exist_ok=True)

        file_path = data_dir / f"{blog_id}_{post_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def _extract_post_id(self, url: str) -> str:
        """
        Extract post ID from Naver blog URL

        Args:
            url: Blog post URL

        Returns:
            Post ID
        """
        # Naver blog URL format: https://blog.naver.com/{blog_id}/{post_id}
        parts = url.split("/")
        if len(parts) >= 6:
            return parts[5]
        return "unknown"

    def _extract_blog_id(self, rss_url: str) -> str:
        """
        Extract blog ID from RSS URL

        Args:
            rss_url: RSS feed URL

        Returns:
            Blog ID
        """
        # Naver blog RSS format: https://rss.blog.naver.com/{blog_id}.xml
        parts = rss_url.split("/")
        if len(parts) >= 5:
            return parts[4].replace(".xml", "")
        return "unknown"

    def _summarize_content(self, title: str, description: str) -> str:
        """
        Summarize blog post content using LLM

        Args:
            title: Blog post title
            description: Blog post description

        Returns:
            Summary text
        """
        prompt = f"""다음 네이버 블로그 글의 내용을 한국어로 요약해주세요.
주요 투자 관련 인사이트를 중심으로 300자 이내로 작성해주세요.

제목: {title}

내용:
{description[:1000]}"""

        try:
            return self.llm.summarize_content(prompt, max_length=300)
        except Exception as e:
            print(f"Error summarizing content: {e}")
            return title

    def _extract_entities(self, title: str, description: str) -> Dict[str, Any]:
        """
        Extract entities from blog post content

        Args:
            title: Blog post title
            description: Blog post description

        Returns:
            Extracted entities
        """
        text = f"{title}\n{description[:500]}"
        try:
            return self.llm.extract_entities(text)
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return {"tickers": [], "companies": [], "topics": [], "sentiment": "neutral"}

    def _check_duplicate(self, session: Session, url: str) -> bool:
        """
        Check if content already exists

        Args:
            session: Database session
            url: Content URL

        Returns:
            True if duplicate exists
        """
        from sqlmodel import select
        existing = session.exec(
            select(ContentItem).where(ContentItem.url == url)
        ).first()
        return existing is not None

    def collect_blog(self, rss_url: str, blog_name: str) -> List[ContentItem]:
        """
        Collect posts from a Naver blog

        Args:
            rss_url: RSS feed URL
            blog_name: Blog name

        Returns:
            List of collected ContentItem objects
        """
        feed = self._fetch_feed(rss_url)

        if not feed:
            return []

        blog_id = self._extract_blog_id(rss_url)
        collected = []

        with next(get_session()) as session:
            for entry in feed.entries:
                post_info = self._extract_post_info(entry)

                # Check duplicate
                if self._check_duplicate(session, post_info["url"]):
                    continue

                # Extract content
                content_preview = self._extract_content_preview(post_info["description"])
                post_id = self._extract_post_id(post_info["url"])
                full_content_path = self._save_full_content(
                    blog_id,
                    post_id,
                    f"Title: {post_info['title']}\n\n{post_info['description']}"
                )

                # Generate summary and extract entities
                summary = self._summarize_content(post_info["title"], post_info["description"])
                entities = self._extract_entities(post_info["title"], post_info["description"])

                # Create ContentItem
                content_item = ContentItem(
                    source_type="naver_blog",
                    source_name=blog_name,
                    title=post_info["title"],
                    url=post_info["url"],
                    content_preview=content_preview,
                    full_content_path=full_content_path,
                    summary=summary,
                    key_tickers=json.dumps(entities["tickers"], ensure_ascii=False),
                    key_topics=json.dumps(entities["topics"], ensure_ascii=False),
                    sentiment=entities["sentiment"],
                    published_at=post_info["published_at"],
                )

                # Save to database
                saved_item = add_content(session, content_item)
                collected.append(saved_item)

                # Add to vector store
                self.vector_store.add_content(
                    content_id=saved_item.id,
                    content=f"{post_info['title']}\n{content_preview}",
                    metadata={
                        "source_type": "naver_blog",
                        "source_name": blog_name,
                        "url": post_info["url"],
                        "tickers": entities["tickers"],
                        "topics": entities["topics"],
                    }
                )

                print(f"Collected: {post_info['title']}")

        return collected

    def collect_all(self) -> Dict[str, List[ContentItem]]:
        """
        Collect posts from all enabled blogs

        Returns:
            Dictionary mapping blog names to collected items
        """
        results = {}

        for blog_config in self.config:
            if not blog_config.get("enabled", False):
                continue

            rss_url = blog_config["rss"]
            blog_name = blog_config["name"]

            print(f"Collecting from {blog_name}...")

            collected = self.collect_blog(rss_url, blog_name)
            results[blog_name] = collected

            print(f"Collected {len(collected)} posts from {blog_name}")

        return results


# ──── Convenience Functions ────
def collect_naver_blog(rss_url: Optional[str] = None) -> List[ContentItem]:
    """
    Quick Naver blog collection

    Args:
        rss_url: Specific RSS URL (None for all enabled blogs)

    Returns:
        List of collected ContentItem objects
    """
    collector = NaverBlogCollector()

    if rss_url:
        # Find blog in config
        for blog_config in collector.config:
            if blog_config["rss"] == rss_url:
                return collector.collect_blog(rss_url, blog_config["name"])
        return []
    else:
        # Collect from all enabled blogs
        all_collected = []
        results = collector.collect_all()
        for items in results.values():
            all_collected.extend(items)
        return all_collected
