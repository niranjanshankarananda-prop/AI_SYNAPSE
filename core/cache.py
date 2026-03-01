"""
AI_SYNAPSE — Response Cache

Caches AI responses to save tokens and money on repeated queries.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Simple file-based cache for AI responses.
    
    Caches based on:
    - Provider name
    - Model
    - Messages hash
    
    TTL (time-to-live) configurable per query type.
    
    Example:
        cache = ResponseCache("~/.synapse/cache")
        
        # Try to get cached response
        cached = cache.get("groq", "llama-70b", messages)
        if cached:
            return cached
        
        # Generate and cache
        response = await generate(messages)
        cache.set("groq", "llama-70b", messages, response)
    """
    
    def __init__(self, cache_dir: Path, default_ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
    
    def _get_cache_key(self, provider: str, model: str, messages: list) -> str:
        """Generate cache key from query parameters."""
        # Create deterministic hash
        key_data = {
            "provider": provider,
            "model": model,
            "messages": messages
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{key}.json"
    
    def get(
        self,
        provider: str,
        model: str,
        messages: list
    ) -> Optional[str]:
        """
        Get cached response if available and not expired.
        
        Args:
            provider: Provider name
            model: Model name
            messages: Message list
            
        Returns:
            Cached response or None
        """
        key = self._get_cache_key(provider, model, messages)
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check expiry
            created = datetime.fromisoformat(data['created'])
            ttl = data.get('ttl', self.default_ttl)
            
            if datetime.now() - created > timedelta(seconds=ttl):
                logger.debug(f"Cache expired: {key}")
                cache_path.unlink()
                return None
            
            logger.debug(f"Cache hit: {key}")
            return data['response']
            
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def set(
        self,
        provider: str,
        model: str,
        messages: list,
        response: str,
        ttl: Optional[int] = None
    ):
        """
        Cache a response.
        
        Args:
            provider: Provider name
            model: Model name
            messages: Message list
            response: Response to cache
            ttl: Optional custom TTL
        """
        key = self._get_cache_key(provider, model, messages)
        cache_path = self._get_cache_path(key)
        
        data = {
            "provider": provider,
            "model": model,
            "response": response,
            "created": datetime.now().isoformat(),
            "ttl": ttl or self.default_ttl
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            
            logger.debug(f"Cached: {key}")
            
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def clear(self, older_than: Optional[int] = None):
        """
        Clear cache entries.
        
        Args:
            older_than: Clear entries older than N seconds (None = all)
        """
        count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            if older_than:
                try:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if datetime.now() - mtime < timedelta(seconds=older_than):
                        continue
                except:
                    pass
            
            try:
                cache_file.unlink()
                count += 1
            except:
                pass
        
        logger.info(f"Cleared {count} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = 0
        entry_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                total_size += cache_file.stat().st_size
                entry_count += 1
            except:
                pass
        
        return {
            "entries": entry_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }
