"""
AI_SYNAPSE — Skill System

Progressive skill loading based on user intent.
Skills provide structured workflows for specific tasks.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Lightweight skill metadata (Level 1 disclosure)."""
    name: str
    description: str
    triggers: List[str]
    priority: str
    category: str
    path: Path


@dataclass
class Skill:
    """Full skill with metadata and content (Level 2 disclosure)."""
    metadata: SkillMetadata
    content: str  # Full SKILL.md content


class SkillSystem:
    """
    Manages skill discovery and loading with progressive disclosure.
    
    Level 1: Only metadata is loaded (name, description, triggers)
    Level 2: Full SKILL.md is loaded when skill is triggered
    Level 3: Reference files loaded when skill requests them
    
    Example:
        skills = SkillSystem("~/.synapse/skills")
        
        # Auto-detect skills based on message
        detected = skills.detect_skills("using TDD, add a feature")
        # Returns [Skill(TDD)] because "TDD" matches triggers
        
        # Or load by name
        tdd_skill = skills.get_by_name("tdd")
    """
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = Path(skills_dir).expanduser()
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._loaded_skills: Dict[str, Skill] = {}
        
        # Load all metadata on init
        self._load_all_metadata()
    
    def _load_all_metadata(self):
        """Load metadata for all skills."""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                metadata_file = skill_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            data = json.load(f)
                        
                        metadata = SkillMetadata(
                            name=data['name'],
                            description=data['description'],
                            triggers=data.get('triggers', []),
                            priority=data.get('priority', 'medium'),
                            category=data.get('category', 'general'),
                            path=skill_dir
                        )
                        
                        self._metadata_cache[metadata.name] = metadata
                        logger.debug(f"Loaded skill metadata: {metadata.name}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load skill metadata from {metadata_file}: {e}")
        
        logger.info(f"Loaded {len(self._metadata_cache)} skill metadata entries")
    
    def detect_skills(self, message: str) -> List[Skill]:
        """
        Auto-detect applicable skills from user message.
        
        Args:
            message: User's input message
            
        Returns:
            List of loaded Skill objects that match
        """
        message_lower = message.lower()
        words = set(self._extract_words(message_lower))
        detected = []
        
        for name, metadata in self._metadata_cache.items():
            # Check if any trigger word appears in message
            for trigger in metadata.triggers:
                trigger_lower = trigger.lower()
                
                # Check for exact match or word boundary match
                if trigger_lower in message_lower:
                    # Load the full skill
                    skill = self._load_full_skill(metadata)
                    if skill:
                        detected.append(skill)
                        logger.info(f"Auto-detected skill: {name} (trigger: {trigger})")
                    break
        
        return detected
    
    def get_by_name(self, name: str) -> Optional[Skill]:
        """
        Load skill by explicit name.
        
        Args:
            name: Skill name (e.g., "tdd", "debugging")
            
        Returns:
            Skill object or None if not found
        """
        # Check if already loaded
        if name in self._loaded_skills:
            return self._loaded_skills[name]
        
        # Load from metadata
        metadata = self._metadata_cache.get(name)
        if metadata:
            return self._load_full_skill(metadata)
        
        logger.warning(f"Skill not found: {name}")
        return None
    
    def _load_full_skill(self, metadata: SkillMetadata) -> Optional[Skill]:
        """
        Load full skill content (Level 2 disclosure).
        
        Args:
            metadata: Skill metadata
            
        Returns:
            Full Skill object or None if failed
        """
        # Check if already loaded
        if metadata.name in self._loaded_skills:
            return self._loaded_skills[metadata.name]
        
        # Load SKILL.md
        skill_file = metadata.path / "SKILL.md"
        if not skill_file.exists():
            logger.warning(f"Skill file not found: {skill_file}")
            return None
        
        try:
            with open(skill_file, 'r') as f:
                content = f.read()
            
            skill = Skill(metadata=metadata, content=content)
            self._loaded_skills[metadata.name] = skill
            
            logger.debug(f"Loaded full skill: {metadata.name} ({len(content)} chars)")
            return skill
            
        except Exception as e:
            logger.error(f"Failed to load skill {metadata.name}: {e}")
            return None
    
    def list_skills(self) -> List[SkillMetadata]:
        """
        List all available skills (metadata only).
        
        Returns:
            List of skill metadata
        """
        return list(self._metadata_cache.values())
    
    def get_skill_names(self) -> List[str]:
        """
        Get list of all skill names.
        
        Returns:
            List of skill names
        """
        return list(self._metadata_cache.keys())
    
    def format_for_prompt(self, skills: List[Skill]) -> str:
        """
        Format skills as XML block for system prompt.
        
        Args:
            skills: List of loaded skills
            
        Returns:
            Formatted XML string
        """
        if not skills:
            return ""
        
        lines = ["<skills>"]
        
        for skill in skills:
            lines.append(f"<skill-{skill.metadata.name}>")
            lines.append(f"<description>{skill.metadata.description}</description>")
            lines.append("<instructions>")
            lines.append(skill.content)
            lines.append("</instructions>")
            lines.append(f"</skill-{skill.metadata.name}>")
        
        lines.append("</skills>")
        
        return "\n".join(lines)
    
    def _extract_words(self, text: str) -> List[str]:
        """
        Extract words from text for matching.
        
        Args:
            text: Input text
            
        Returns:
            List of words
        """
        import re
        return re.findall(r'\b\w+\b', text)
    
    def reload(self):
        """Reload all skill metadata (useful after adding new skills)."""
        self._metadata_cache.clear()
        self._loaded_skills.clear()
        self._load_all_metadata()
        logger.info("Skill cache reloaded")
