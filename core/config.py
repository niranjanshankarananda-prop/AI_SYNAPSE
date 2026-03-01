"""
AI_SYNAPSE — Configuration Management

Handles loading and validating configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class ProviderModelConfig(BaseModel):
    """Configuration for a specific model within a provider."""
    name: str
    default: bool = False


class ProviderConfigModel(BaseModel):
    """Configuration for a provider."""
    enabled: bool = True
    priority: int = 10
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: List[ProviderModelConfig] = Field(default_factory=list)
    timeout: float = 60.0
    
    def get_default_model(self) -> Optional[str]:
        """Get the default model for this provider."""
        for model in self.models:
            if model.default:
                return model.name
        if self.models:
            return self.models[0].name
        return None


class DomainConfig(BaseModel):
    """CARL domain configuration."""
    name: str
    recall: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(default_factory=list)


class CarlConfig(BaseModel):
    """CARL system configuration."""
    enabled: bool = True
    config_path: str = "~/.synapse/carl"
    domains: List[DomainConfig] = Field(default_factory=list)


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    enabled: bool = True
    location: str = "~/.synapse/memory"
    max_lines: int = 200


class SkillConfig(BaseModel):
    """Skill system configuration."""
    enabled: bool = True
    location: str = "~/.synapse/skills"
    auto_detect: bool = True


class ConversationConfig(BaseModel):
    """Conversation management configuration."""
    max_tokens: int = 128000
    compact_threshold: float = 0.75
    history_limit: int = 100


class UIConfig(BaseModel):
    """UI/display configuration."""
    stream: bool = True
    show_provider: bool = True
    syntax_highlight: bool = True
    theme: str = "dark"


class SynapseConfig(BaseModel):
    """Main configuration model."""
    version: str = "1.0"
    
    # Provider configurations
    providers: Dict[str, ProviderConfigModel] = Field(default_factory=dict)
    
    # Subsystem configurations
    carl: CarlConfig = Field(default_factory=CarlConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    skills: SkillConfig = Field(default_factory=SkillConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    
    class Config:
        extra = "allow"  # Allow extra fields for future extensions


class ConfigManager:
    """
    Manages loading and accessing configuration.
    
    Configuration hierarchy (highest priority first):
    1. Environment variables (SYNAPSE_*)
    2. User config file (~/.synapse/config.yaml)
    3. Project config file (./.synapse/config.yaml)
    4. Default config
    """
    
    DEFAULT_CONFIG_PATH = Path.home() / ".synapse" / "config.yaml"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[SynapseConfig] = None
    
    def load(self) -> SynapseConfig:
        """Load configuration from all sources."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config_dict = self._get_default_config()
        
        # Load from file if exists
        if self.config_path.exists():
            logger.info(f"Loading config from {self.config_path}")
            with open(self.config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    config_dict = self._deep_merge(config_dict, file_config)
        else:
            logger.warning(f"Config file not found: {self.config_path}")
            logger.info("Using default configuration")
        
        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)
        
        # Parse into Pydantic model
        self._config = SynapseConfig(**config_dict)
        return self._config
    
    def save(self, config: SynapseConfig):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False)
        
        logger.info(f"Configuration saved to {self.config_path}")
    
    def get_provider_config(self, name: str) -> Optional[ProviderConfigModel]:
        """Get configuration for a specific provider."""
        config = self.load()
        return config.providers.get(name)
    
    def get_enabled_providers(self) -> Dict[str, ProviderConfigModel]:
        """Get all enabled providers, sorted by priority."""
        config = self.load()
        enabled = {
            name: pc for name, pc in config.providers.items()
            if pc.enabled
        }
        # Sort by priority (lower = higher priority)
        return dict(sorted(enabled.items(), key=lambda x: x[1].priority))
    
    def create_default_config(self):
        """Create a default configuration file."""
        default_config = self._get_default_config()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Default configuration created at {self.config_path}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration dictionary."""
        return {
            "version": "1.0",
            "providers": {
                "kilo": {
                    "enabled": True,
                    "priority": 1,
                    "models": [
                        {"name": "kilo/moonshotai/kimi-k2.5:free", "default": True},
                        {"name": "kilo/minimax/minimax-m2.5:free"},
                        {"name": "kilo/qwen/qwen3-235b-a22b-thinking-2507"}
                    ]
                },
                "kimi": {
                    "enabled": True,
                    "priority": 2,
                    "api_key": None,  # From env: KIMI_API_KEY
                    "models": [
                        {"name": "kimi-k2.5", "default": True}
                    ]
                },
                "ollama": {
                    "enabled": True,
                    "priority": 3,
                    "base_url": "http://localhost:11434",
                    "models": [
                        {"name": "qwen2.5-coder:7b", "default": True}
                    ]
                },
                "openrouter": {
                    "enabled": True,
                    "priority": 4,
                    "api_key": None,  # From env: OPENROUTER_API_KEY
                    "models": [
                        {"name": "qwen/qwen3-32b:free", "default": True},
                        {"name": "google/gemma-3-27b-it:free"},
                        {"name": "mistralai/mistral-small-3.1-24b-instruct:free"}
                    ]
                },
                "groq": {
                    "enabled": True,
                    "priority": 5,
                    "api_key": None,  # From env: GROQ_API_KEY
                    "models": [
                        {"name": "llama-3.3-70b-versatile", "default": True},
                        {"name": "qwen/qwen3-32b"}
                    ]
                },
                "gemini": {
                    "enabled": True,
                    "priority": 6,
                    "api_key": None,  # From env: GEMINI_API_KEY
                    "models": [
                        {"name": "gemini-2.5-flash", "default": True}
                    ]
                },
            },
            "carl": {
                "enabled": True,
                "config_path": "~/.synapse/carl",
                "domains": [
                    {"name": "python", "recall": ["python", "fastapi", "flask", "django", "pytest", ".py", "pip"]},
                    {"name": "frontend", "recall": ["react", "vue", "angular", "svelte", "css", "html", "frontend", "ui"]},
                    {"name": "database", "recall": ["database", "postgres", "mysql", "sqlite", "sql", "migration", "orm"]},
                    {"name": "api", "recall": ["api", "endpoint", "rest", "graphql", "cors", "jwt", "auth"]},
                    {"name": "deploy", "recall": ["deploy", "docker", "railway", "aws", "production", "ci/cd"]},
                    {"name": "security", "recall": ["security", "auth", "password", "encrypt", "hash", "xss", "injection"]}
                ]
            },
            "memory": {
                "enabled": True,
                "location": "~/.synapse/memory",
                "max_lines": 200
            },
            "skills": {
                "enabled": True,
                "location": "~/.synapse/skills",
                "auto_detect": True
            },
            "conversation": {
                "max_tokens": 128000,
                "compact_threshold": 0.75,
                "history_limit": 100
            },
            "ui": {
                "stream": True,
                "show_provider": True,
                "syntax_highlight": True,
                "theme": "dark"
            }
        }
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # Provider API keys
        provider_keys = {
            "GROQ_API_KEY": ("providers", "groq", "api_key"),
            "GEMINI_API_KEY": ("providers", "gemini", "api_key"),
            "KIMI_API_KEY": ("providers", "kimi", "api_key"),
            "OPENROUTER_API_KEY": ("providers", "openrouter", "api_key"),
        }
        
        for env_var, path in provider_keys.items():
            value = os.environ.get(env_var)
            if value:
                self._set_nested_value(config, path, value)
                logger.debug(f"Override from {env_var}")
        
        return config
    
    def _set_nested_value(self, d: Dict, path: tuple, value: Any):
        """Set a nested dictionary value by path."""
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> SynapseConfig:
    """Get the loaded configuration."""
    return get_config_manager().load()
