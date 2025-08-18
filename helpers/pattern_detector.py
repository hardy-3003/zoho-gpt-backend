"""
Pattern Detection System for Auto-Expansion Capabilities

This module provides comprehensive pattern analysis capabilities for detecting
new logic needs, tracking usage patterns, and enabling autonomous system growth.

Features:
- Request pattern analysis with frequency tracking
- Usage pattern similarity detection and clustering
- Pattern evolution tracking and trend analysis
- Anomaly detection in usage patterns
- Pattern confidence scoring and validation
"""

import json
import re
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from difflib import SequenceMatcher
import hashlib
import logging

from helpers.history_store import write_event
from helpers.learning_hooks import record_feedback

logger = logging.getLogger(__name__)


@dataclass
class RequestPattern:
    """Represents a detected request pattern for analysis."""

    pattern_id: str
    query_text: str
    logic_ids: List[str]
    frequency: int
    first_seen: datetime
    last_seen: datetime
    confidence: float
    tags: List[str]
    complexity_score: float
    similarity_groups: List[str]
    evolution_trend: str  # 'increasing', 'stable', 'decreasing'
    anomaly_score: float
    metadata: Dict[str, Any]


@dataclass
class PatternCluster:
    """Represents a cluster of similar patterns."""

    cluster_id: str
    patterns: List[RequestPattern]
    centroid_query: str
    similarity_threshold: float
    total_frequency: int
    common_tags: List[str]
    complexity_range: Tuple[float, float]
    creation_date: datetime
    last_updated: datetime


@dataclass
class PatternAnalysis:
    """Results of pattern analysis."""

    patterns: List[RequestPattern]
    clusters: List[PatternCluster]
    new_logic_candidates: List[Dict[str, Any]]
    anomaly_patterns: List[RequestPattern]
    trend_analysis: Dict[str, Any]
    confidence_scores: Dict[str, float]


class PatternDetector:
    """
    Comprehensive pattern detection engine for auto-expansion capabilities.

    Analyzes request patterns to identify:
    - New logic needs
    - Usage trends and anomalies
    - Pattern similarities and clusters
    - Evolution of request patterns
    """

    def __init__(self, storage_path: str = "data/patterns/"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Pattern storage
        self.patterns_file = self.storage_path / "patterns.json"
        self.clusters_file = self.storage_path / "clusters.json"
        self.analysis_file = self.storage_path / "analysis.json"

        # Load existing patterns
        self.patterns: Dict[str, RequestPattern] = {}
        self.clusters: Dict[str, PatternCluster] = {}
        self._load_patterns()

        # Configuration
        self.similarity_threshold = 0.7
        self.min_frequency = 3
        self.max_patterns = 1000
        self.anomaly_threshold = 0.8

        # Performance tracking
        self.analysis_count = 0
        self.last_analysis = None

    def _load_patterns(self) -> None:
        """Load existing patterns from storage."""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, "r") as f:
                    data = json.load(f)
                    for pattern_data in data.get("patterns", []):
                        pattern = self._dict_to_pattern(pattern_data)
                        self.patterns[pattern.pattern_id] = pattern

            if self.clusters_file.exists():
                with open(self.clusters_file, "r") as f:
                    data = json.load(f)
                    for cluster_data in data.get("clusters", []):
                        cluster = self._dict_to_cluster(cluster_data)
                        self.clusters[cluster.cluster_id] = cluster

            logger.info(
                f"Loaded {len(self.patterns)} patterns and {len(self.clusters)} clusters"
            )
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")

    def _save_patterns(self) -> None:
        """Save patterns to storage."""
        try:
            # Save patterns
            patterns_data = {
                "patterns": [asdict(pattern) for pattern in self.patterns.values()],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.patterns_file, "w") as f:
                json.dump(patterns_data, f, indent=2, default=str)

            # Save clusters
            clusters_data = {
                "clusters": [asdict(cluster) for cluster in self.clusters.values()],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.clusters_file, "w") as f:
                json.dump(clusters_data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def _dict_to_pattern(self, data: Dict[str, Any]) -> RequestPattern:
        """Convert dictionary to RequestPattern."""
        return RequestPattern(
            pattern_id=data["pattern_id"],
            query_text=data["query_text"],
            logic_ids=data["logic_ids"],
            frequency=data["frequency"],
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            confidence=data["confidence"],
            tags=data["tags"],
            complexity_score=data["complexity_score"],
            similarity_groups=data["similarity_groups"],
            evolution_trend=data["evolution_trend"],
            anomaly_score=data["anomaly_score"],
            metadata=data["metadata"],
        )

    def _dict_to_cluster(self, data: Dict[str, Any]) -> PatternCluster:
        """Convert dictionary to PatternCluster."""
        patterns = [self._dict_to_pattern(p) for p in data["patterns"]]
        return PatternCluster(
            cluster_id=data["cluster_id"],
            patterns=patterns,
            centroid_query=data["centroid_query"],
            similarity_threshold=data["similarity_threshold"],
            total_frequency=data["total_frequency"],
            common_tags=data["common_tags"],
            complexity_range=tuple(data["complexity_range"]),
            creation_date=datetime.fromisoformat(data["creation_date"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )

    def analyze_request(
        self, query: str, logic_ids: List[str], tags: List[str] = None
    ) -> RequestPattern:
        """
        Analyze a single request and create or update a pattern.

        Args:
            query: The request query text
            logic_ids: List of logic IDs used to handle the request
            tags: Optional tags for categorization

        Returns:
            RequestPattern: The analyzed pattern
        """
        # Normalize query
        normalized_query = self._normalize_query(query)
        pattern_id = self._generate_pattern_id(normalized_query, logic_ids)

        # Check if pattern exists
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.frequency += 1
            pattern.last_seen = datetime.now()
            pattern.logic_ids = list(set(pattern.logic_ids + logic_ids))
            if tags:
                pattern.tags = list(set(pattern.tags + tags))
        else:
            # Create new pattern
            pattern = RequestPattern(
                pattern_id=pattern_id,
                query_text=normalized_query,
                logic_ids=logic_ids,
                frequency=1,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                confidence=self._calculate_confidence(normalized_query, logic_ids),
                tags=tags or [],
                complexity_score=self._calculate_complexity(normalized_query),
                similarity_groups=[],
                evolution_trend="new",
                anomaly_score=0.0,
                metadata={"original_query": query, "analysis_count": 0},
            )
            self.patterns[pattern_id] = pattern

        # Update pattern metadata
        pattern.metadata["analysis_count"] = (
            pattern.metadata.get("analysis_count", 0) + 1
        )

        # Save patterns
        self._save_patterns()

        # Record event
        write_event(
            "pattern_analysis",
            {
                "pattern_id": pattern.pattern_id,
                "query": query,
                "logic_ids": logic_ids,
                "frequency": pattern.frequency,
                "confidence": pattern.confidence,
            },
        )

        return pattern

    def detect_patterns(self, min_frequency: int = None) -> List[RequestPattern]:
        """
        Detect significant patterns based on frequency and other criteria.

        Args:
            min_frequency: Minimum frequency threshold (defaults to self.min_frequency)

        Returns:
            List of significant patterns
        """
        threshold = min_frequency or self.min_frequency
        significant_patterns = [
            pattern
            for pattern in self.patterns.values()
            if pattern.frequency >= threshold
        ]

        # Sort by frequency and confidence
        significant_patterns.sort(
            key=lambda p: (p.frequency, p.confidence), reverse=True
        )

        return significant_patterns

    def find_similar_patterns(
        self, query: str, threshold: float = None
    ) -> List[Tuple[RequestPattern, float]]:
        """
        Find patterns similar to the given query.

        Args:
            query: The query to find similarities for
            threshold: Similarity threshold (defaults to self.similarity_threshold)

        Returns:
            List of (pattern, similarity_score) tuples
        """
        threshold = threshold or self.similarity_threshold
        normalized_query = self._normalize_query(query)

        similar_patterns = []
        for pattern in self.patterns.values():
            similarity = self._calculate_similarity(
                normalized_query, pattern.query_text
            )
            if similarity >= threshold:
                similar_patterns.append((pattern, similarity))

        # Sort by similarity score
        similar_patterns.sort(key=lambda x: x[1], reverse=True)
        return similar_patterns

    def cluster_patterns(self, threshold: float = None) -> List[PatternCluster]:
        """
        Cluster similar patterns together.

        Args:
            threshold: Similarity threshold for clustering

        Returns:
            List of pattern clusters
        """
        threshold = threshold or self.similarity_threshold
        patterns = list(self.patterns.values())

        if not patterns:
            return []

        # Initialize clusters
        clusters = []
        used_patterns = set()

        for pattern in patterns:
            if pattern.pattern_id in used_patterns:
                continue

            # Find similar patterns
            cluster_patterns = [pattern]
            used_patterns.add(pattern.pattern_id)

            for other_pattern in patterns:
                if other_pattern.pattern_id in used_patterns:
                    continue

                similarity = self._calculate_similarity(
                    pattern.query_text, other_pattern.query_text
                )

                if similarity >= threshold:
                    cluster_patterns.append(other_pattern)
                    used_patterns.add(other_pattern.pattern_id)

            # Create cluster
            if len(cluster_patterns) > 1:
                cluster = self._create_cluster(cluster_patterns, threshold)
                clusters.append(cluster)
                self.clusters[cluster.cluster_id] = cluster

        # Save clusters
        self._save_patterns()

        return clusters

    def detect_anomalies(self, threshold: float = None) -> List[RequestPattern]:
        """
        Detect anomalous patterns based on various criteria.

        Args:
            threshold: Anomaly threshold (defaults to self.anomaly_threshold)

        Returns:
            List of anomalous patterns
        """
        threshold = threshold or self.anomaly_threshold
        anomalies = []

        for pattern in self.patterns.values():
            anomaly_score = self._calculate_anomaly_score(pattern)
            pattern.anomaly_score = anomaly_score

            if anomaly_score >= threshold:
                anomalies.append(pattern)

        # Sort by anomaly score
        anomalies.sort(key=lambda p: p.anomaly_score, reverse=True)
        return anomalies

    def analyze_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze pattern evolution trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend analysis
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Filter patterns by date
        recent_patterns = [
            p for p in self.patterns.values() if p.last_seen >= cutoff_date
        ]

        # Calculate trends
        trends = {
            "total_patterns": len(recent_patterns),
            "new_patterns": len(
                [p for p in recent_patterns if p.first_seen >= cutoff_date]
            ),
            "increasing_patterns": len(
                [p for p in recent_patterns if p.evolution_trend == "increasing"]
            ),
            "stable_patterns": len(
                [p for p in recent_patterns if p.evolution_trend == "stable"]
            ),
            "decreasing_patterns": len(
                [p for p in recent_patterns if p.evolution_trend == "decreasing"]
            ),
            "top_tags": self._get_top_tags(recent_patterns),
            "complexity_distribution": self._get_complexity_distribution(
                recent_patterns
            ),
            "frequency_distribution": self._get_frequency_distribution(recent_patterns),
        }

        return trends

    def identify_new_logic_candidates(self) -> List[Dict[str, Any]]:
        """
        Identify patterns that might need new logic modules.

        Returns:
            List of new logic candidates with metadata
        """
        candidates = []

        for pattern in self.patterns.values():
            # Check if pattern might need new logic
            if self._is_new_logic_candidate(pattern):
                candidate = {
                    "pattern_id": pattern.pattern_id,
                    "query_text": pattern.query_text,
                    "frequency": pattern.frequency,
                    "confidence": pattern.confidence,
                    "complexity_score": pattern.complexity_score,
                    "tags": pattern.tags,
                    "suggested_logic_name": self._suggest_logic_name(pattern),
                    "suggested_logic_id": self._suggest_logic_id(pattern),
                    "reasoning": self._get_candidate_reasoning(pattern),
                    "priority_score": self._calculate_priority_score(pattern),
                }
                candidates.append(candidate)

        # Sort by priority score
        candidates.sort(key=lambda c: c["priority_score"], reverse=True)
        return candidates

    def _normalize_query(self, query: str) -> str:
        """Normalize query text for comparison."""
        # Convert to lowercase
        normalized = query.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Remove common punctuation
        normalized = re.sub(r"[^\w\s]", "", normalized)

        return normalized

    def _generate_pattern_id(self, query: str, logic_ids: List[str]) -> str:
        """Generate unique pattern ID."""
        content = f"{query}:{','.join(sorted(logic_ids))}"
        # Use sha256 for reproducible non-security IDs
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def _calculate_confidence(self, query: str, logic_ids: List[str]) -> float:
        """Calculate confidence score for a pattern."""
        # Base confidence on query complexity and logic count
        query_words = len(query.split())
        logic_count = len(logic_ids)

        # More complex queries with fewer logics get higher confidence
        if logic_count == 0:
            return 0.0
        elif logic_count == 1 and query_words > 5:
            return 0.9
        elif logic_count <= 3 and query_words > 3:
            return 0.8
        elif logic_count <= 5:
            return 0.7
        else:
            return 0.6

    def _calculate_complexity(self, query: str) -> float:
        """Calculate complexity score for a query."""
        words = query.split()
        word_count = len(words)

        # Count unique words
        unique_words = len(set(words))

        # Calculate complexity based on word count and uniqueness
        complexity = min(1.0, (word_count * unique_words) / 100.0)

        return complexity

    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        return SequenceMatcher(None, query1, query2).ratio()

    def _calculate_anomaly_score(self, pattern: RequestPattern) -> float:
        """Calculate anomaly score for a pattern."""
        # Factors that make a pattern anomalous:
        # 1. High frequency but low confidence
        # 2. High complexity but few logics used
        # 3. Recent creation but high frequency
        # 4. Unusual tag combinations

        anomaly_factors = []

        # Factor 1: High frequency, low confidence
        if pattern.frequency > 10 and pattern.confidence < 0.5:
            anomaly_factors.append(0.3)

        # Factor 2: High complexity, few logics
        if pattern.complexity_score > 0.7 and len(pattern.logic_ids) <= 2:
            anomaly_factors.append(0.4)

        # Factor 3: Recent but frequent
        days_since_creation = (datetime.now() - pattern.first_seen).days
        if days_since_creation < 7 and pattern.frequency > 5:
            anomaly_factors.append(0.3)

        # Factor 4: Unusual tags
        if len(pattern.tags) > 5:  # Too many tags might indicate confusion
            anomaly_factors.append(0.2)

        return min(1.0, sum(anomaly_factors))

    def _create_cluster(
        self, patterns: List[RequestPattern], threshold: float
    ) -> PatternCluster:
        """Create a cluster from similar patterns."""
        cluster_id = f"cluster_{len(self.clusters) + 1}"

        # Calculate centroid query (most representative)
        centroid_query = self._find_centroid_query(patterns)

        # Calculate cluster statistics
        total_frequency = sum(p.frequency for p in patterns)
        all_tags = [tag for p in patterns for tag in p.tags]
        common_tags = [tag for tag, count in Counter(all_tags).items() if count > 1]

        complexity_scores = [p.complexity_score for p in patterns]
        complexity_range = (min(complexity_scores), max(complexity_scores))

        return PatternCluster(
            cluster_id=cluster_id,
            patterns=patterns,
            centroid_query=centroid_query,
            similarity_threshold=threshold,
            total_frequency=total_frequency,
            common_tags=common_tags,
            complexity_range=complexity_range,
            creation_date=datetime.now(),
            last_updated=datetime.now(),
        )

    def _find_centroid_query(self, patterns: List[RequestPattern]) -> str:
        """Find the most representative query in a cluster."""
        if not patterns:
            return ""

        # Use the pattern with highest frequency as centroid
        return max(patterns, key=lambda p: p.frequency).query_text

    def _get_top_tags(self, patterns: List[RequestPattern]) -> List[Tuple[str, int]]:
        """Get top tags from patterns."""
        all_tags = [tag for p in patterns for tag in p.tags]
        return Counter(all_tags).most_common(10)

    def _get_complexity_distribution(
        self, patterns: List[RequestPattern]
    ) -> Dict[str, int]:
        """Get complexity distribution."""
        distribution = {"low": 0, "medium": 0, "high": 0}

        for pattern in patterns:
            if pattern.complexity_score < 0.3:
                distribution["low"] += 1
            elif pattern.complexity_score < 0.7:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1

        return distribution

    def _get_frequency_distribution(
        self, patterns: List[RequestPattern]
    ) -> Dict[str, int]:
        """Get frequency distribution."""
        distribution = {"low": 0, "medium": 0, "high": 0}

        for pattern in patterns:
            if pattern.frequency < 5:
                distribution["low"] += 1
            elif pattern.frequency < 20:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1

        return distribution

    def _is_new_logic_candidate(self, pattern: RequestPattern) -> bool:
        """Determine if a pattern is a candidate for new logic."""
        # Criteria for new logic candidates:
        # 1. High frequency (>5)
        # 2. Low confidence (<0.6) or high complexity (>0.7)
        # 3. Not too many existing logics used (<=3)
        # 4. Recent activity (within last 30 days)

        days_since_last = (datetime.now() - pattern.last_seen).days

        return (
            pattern.frequency >= 5
            and (pattern.confidence < 0.6 or pattern.complexity_score > 0.7)
            and len(pattern.logic_ids) <= 3
            and days_since_last <= 30
        )

    def _suggest_logic_name(self, pattern: RequestPattern) -> str:
        """Suggest a name for new logic based on pattern."""
        # Extract key terms from query
        words = pattern.query_text.split()

        # Remove common words
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        key_words = [w for w in words if w not in common_words and len(w) > 3]

        if key_words:
            # Use first two key words
            name = "_".join(key_words[:2])
            return f"logic_{name}_analyzer"
        else:
            return f"logic_pattern_{pattern.pattern_id[:8]}"

    def _suggest_logic_id(self, pattern: RequestPattern) -> str:
        """Suggest a logic ID for new logic."""
        # Find next available ID
        existing_ids = set()
        for p in self.patterns.values():
            for logic_id in p.logic_ids:
                if logic_id.startswith("L-"):
                    try:
                        num = int(logic_id[2:])
                        existing_ids.add(num)
                    except ValueError:
                        pass

        next_id = 1
        while next_id in existing_ids:
            next_id += 1

        return f"L-{next_id:03d}"

    def _get_candidate_reasoning(self, pattern: RequestPattern) -> str:
        """Get reasoning for why pattern is a new logic candidate."""
        reasons = []

        if pattern.frequency >= 5:
            reasons.append(f"High frequency ({pattern.frequency} requests)")

        if pattern.confidence < 0.6:
            reasons.append(f"Low confidence ({pattern.confidence:.2f})")

        if pattern.complexity_score > 0.7:
            reasons.append(f"High complexity ({pattern.complexity_score:.2f})")

        if len(pattern.logic_ids) <= 3:
            reasons.append(f"Few existing logics used ({len(pattern.logic_ids)})")

        return "; ".join(reasons)

    def _calculate_priority_score(self, pattern: RequestPattern) -> float:
        """Calculate priority score for new logic candidate."""
        # Priority factors:
        # 1. Frequency (higher = more priority)
        # 2. Low confidence (lower = more priority)
        # 3. High complexity (higher = more priority)
        # 4. Recent activity (more recent = more priority)

        frequency_score = min(1.0, pattern.frequency / 20.0)
        confidence_score = 1.0 - pattern.confidence  # Invert confidence
        complexity_score = pattern.complexity_score

        days_since_last = (datetime.now() - pattern.last_seen).days
        recency_score = max(0.0, 1.0 - (days_since_last / 30.0))

        # Weighted average
        priority = (
            frequency_score * 0.4
            + confidence_score * 0.3
            + complexity_score * 0.2
            + recency_score * 0.1
        )

        return priority

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about patterns."""
        total_patterns = len(self.patterns)
        total_clusters = len(self.clusters)

        if total_patterns == 0:
            return {
                "total_patterns": 0,
                "total_clusters": 0,
                "average_frequency": 0,
                "average_confidence": 0,
                "top_tags": [],
                "recent_activity": 0,
            }

        # Calculate averages
        avg_frequency = (
            sum(p.frequency for p in self.patterns.values()) / total_patterns
        )
        avg_confidence = (
            sum(p.confidence for p in self.patterns.values()) / total_patterns
        )

        # Get recent activity (last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_patterns = [
            p for p in self.patterns.values() if p.last_seen >= cutoff_date
        ]

        # Get top tags
        all_tags = [tag for p in self.patterns.values() for tag in p.tags]
        top_tags = Counter(all_tags).most_common(10)

        return {
            "total_patterns": total_patterns,
            "total_clusters": total_clusters,
            "average_frequency": avg_frequency,
            "average_confidence": avg_confidence,
            "top_tags": top_tags,
            "recent_activity": len(recent_patterns),
            "analysis_count": self.analysis_count,
            "last_analysis": (
                self.last_analysis.isoformat() if self.last_analysis else None
            ),
        }


# Global instance for easy access
_pattern_detector = None


def get_pattern_detector() -> PatternDetector:
    """Get global pattern detector instance."""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector()
    return _pattern_detector


def analyze_request_pattern(
    query: str, logic_ids: List[str], tags: List[str] = None
) -> RequestPattern:
    """Convenience function to analyze a request pattern."""
    detector = get_pattern_detector()
    return detector.analyze_request(query, logic_ids, tags)


def detect_new_logic_candidates() -> List[Dict[str, Any]]:
    """Convenience function to detect new logic candidates."""
    detector = get_pattern_detector()
    return detector.identify_new_logic_candidates()


def get_pattern_statistics() -> Dict[str, Any]:
    """Convenience function to get pattern statistics."""
    detector = get_pattern_detector()
    return detector.get_statistics()
