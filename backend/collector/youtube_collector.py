"""YouTube Content Collector

Collects content from YouTube channels using RSS feeds.
Extracts video information and stores in ContentItem table.
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


class YouTubeCollector:
    """
    YouTube content collector using RSS feeds

    Usage:
        collector = YouTubeCollector()
        collector.collect_all()
        collector.collect_channel("UC...")
    """

    def __init__(self, config_path: str = "config/sources.yaml"):
        """
        Initialize YouTube collector

        Args:
            config_path: Path to sources.yaml configuration file
        """
        self.config_path = Path(__file__).parent.parent / config_path
        self.config = self._load_config()
        self.vector_store = VectorStore()
        self.llm = get_llm_router()

    def _load_config(self) -> Dict[str, Any]:
        """Load YouTube channel configuration"""
        import yaml

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config.get("youtube", [])

    def _get_rss_url(self, channel_id: str) -> str:
        """
        Get RSS feed URL for a YouTube channel

        Args:
            channel_id: YouTube channel ID (e.g., UC...)

        Returns:
            RSS feed URL
        """
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

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

    def _extract_video_info(self, entry: feedparser.FeedParserDict) -> Dict[str, Any]:
        """
        Extract video information from RSS entry

        Args:
            entry: RSS entry

        Returns:
            Video information dictionary
        """
        video_id = entry.yt_videoid if hasattr(entry, "yt_videoid") else None

        return {
            "video_id": video_id,
            "title": entry.get("title", ""),
            "description": entry.get("description", ""),
            "url": entry.get("link", ""),
            "published_at": datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else None,
            "author": entry.get("author", ""),
            "tags": [tag.term for tag in entry.get("tags", [])] if hasattr(entry, "tags") else [],
        }

    def _extract_content_preview(self, description: str, max_length: int = 2000) -> str:
        """
        Extract content preview from video description

        Args:
            description: Video description
            max_length: Maximum length of preview

        Returns:
            Content preview text
        """
        # Remove common YouTube description patterns
        lines = description.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and common footer patterns
            if line and not any(
                pattern in line.lower()
                for pattern in ["subscribe", "follow", "social media", "link", "http", "www."]
            ):
                cleaned_lines.append(line)

        preview = " ".join(cleaned_lines)
        return preview[:max_length]

    def _save_full_content(self, video_id: str, content: str) -> str:
        """
        Save full content to file

        Args:
            video_id: Video ID
            content: Full content

        Returns:
            File path
        """
        data_dir = Path(__file__).parent.parent / "data" / "raw" / "youtube"
        data_dir.mkdir(parents=True, exist_ok=True)

        file_path = data_dir / f"{video_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def _summarize_content(self, title: str, description: str) -> str:
        """
        Summarize video content using LLM

        Args:
            title: Video title
            description: Video description

        Returns:
            Summary text
        """
        prompt = f"""다음 YouTube 영상의 내용을 한국어로 요약해주세요.
주요 투자 관련 인사이트를 중심으로 300자 이내로 작성해주세요.

제목: {title}

설명:
{description[:1000]}"""

        try:
            return self.llm.summarize_content(prompt, max_length=300)
        except Exception as e:
            print(f"Error summarizing content: {e}")
            return title

    def _extract_entities(self, title: str, description: str) -> Dict[str, Any]:
        """
        Extract entities from video content

        Args:
            title: Video title
            description: Video description

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

    def collect_channel(self, channel_id: str, channel_name: str) -> List[ContentItem]:
        """
        Collect videos from a YouTube channel

        Args:
            channel_id: YouTube channel ID
            channel_name: Channel name

        Returns:
            List of collected ContentItem objects
        """
        rss_url = self._get_rss_url(channel_id)
        feed = self._fetch_feed(rss_url)

        if not feed:
            return []

        collected = []

        with next(get_session()) as session:
            for entry in feed.entries:
                video_info = self._extract_video_info(entry)

                # Check duplicate
                if self._check_duplicate(session, video_info["url"]):
                    continue

                # Extract content
                content_preview = self._extract_content_preview(video_info["description"])
                full_content_path = self._save_full_content(
                    video_info["video_id"],
                    f"Title: {video_info['title']}\n\n{video_info['description']}"
                )

                # Generate summary and extract entities
                summary = self._summarize_content(video_info["title"], video_info["description"])
                entities = self._extract_entities(video_info["title"], video_info["description"])

                # Create ContentItem
                content_item = ContentItem(
                    source_type="youtube",
                    source_name=channel_name,
                    title=video_info["title"],
                    url=video_info["url"],
                    content_preview=content_preview,
                    full_content_path=full_content_path,
                    summary=summary,
                    key_tickers=json.dumps(entities["tickers"], ensure_ascii=False),
                    key_topics=json.dumps(entities["topics"], ensure_ascii=False),
                    sentiment=entities["sentiment"],
                    published_at=video_info["published_at"],
                )

                # Save to database
                saved_item = add_content(session, content_item)
                collected.append(saved_item)

                # Add to vector store
                self.vector_store.add_content(
                    content_id=saved_item.id,
                    content=f"{video_info['title']}\n{content_preview}",
                    metadata={
                        "source_type": "youtube",
                        "source_name": channel_name,
                        "url": video_info["url"],
                        "tickers": entities["tickers"],
                        "topics": entities["topics"],
                    }
                )

                print(f"Collected: {video_info['title']}")

        return collected

    def collect_all(self) -> Dict[str, List[ContentItem]]:
        """
        Collect videos from all enabled channels

        Returns:
            Dictionary mapping channel names to collected items
        """
        results = {}

        for channel_config in self.config:
            if not channel_config.get("enabled", False):
                continue

            channel_id = channel_config["channel_id"]
            channel_name = channel_config["name"]

            print(f"Collecting from {channel_name}...")

            collected = self.collect_channel(channel_id, channel_name)
            results[channel_name] = collected

            print(f"Collected {len(collected)} videos from {channel_name}")

        return results


# ──── Convenience Functions ────
def collect_youtube(channel_id: Optional[str] = None) -> List[ContentItem]:
    """
    Quick YouTube collection

    Args:
        channel_id: Specific channel ID (None for all enabled channels)

    Returns:
        List of collected ContentItem objects
    """
    collector = YouTubeCollector()

    if channel_id:
        # Find channel in config
        for channel_config in collector.config:
            if channel_config["channel_id"] == channel_id:
                return collector.collect_channel(channel_id, channel_config["name"])
        return []
    else:
        # Collect from all enabled channels
        all_collected = []
        results = collector.collect_all()
        for items in results.values():
            all_collected.extend(items)
        return all_collected
