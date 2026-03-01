"""
AI_SYNAPSE — CARL System (Context Augmentation & Reinforcement Layer)

Intelligent rule injection based on user input, context usage, and active modes.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ContextBracket(Enum):
    """Context window usage brackets."""
    FRESH = "fresh"           # 60-100% remaining
    MODERATE = "moderate"     # 40-60% remaining
    DEPLETED = "depleted"     # 25-40% remaining
    CRITICAL = "critical"     # <25% remaining


@dataclass
class CARLResult:
    """Result of CARL processing."""
    rules: List[str]
    bracket: ContextBracket
    modified_message: str
    loaded_domains: List[str]
    star_command: Optional[str] = None


class CARLSystem:
    """
    Context Augmentation & Reinforcement Layer.
    
    Analyzes user input and injects relevant rules based on:
    - Star commands (*dev, *debug, etc.)
    - Keyword matching (python, database, etc.)
    - Context bracket (FRESH, MODERATE, DEPLETED, CRITICAL)
    
    Example:
        carl = CARLSystem("~/.synapse/carl")
        result = carl.process_message("fix the python bug", context_usage=0.3)
        # result.rules will include PYTHON domain rules + FRESH bracket rules
    """
    
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path).expanduser()
        self.manifest: Dict[str, any] = {}
        self.domains: Dict[str, Dict] = {}
        self.global_rules: List[str] = []
        self.context_rules: Dict[ContextBracket, List[str]] = {}
        self.commands: Dict[str, List[str]] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all CARL configuration files."""
        self._load_manifest()
        self._load_global_rules()
        self._load_context_rules()
        self._load_commands()
        self._load_domains()
    
    def _load_manifest(self):
        """Load the manifest file."""
        manifest_path = self.config_path / "manifest"
        if not manifest_path.exists():
            logger.warning(f"CARL manifest not found: {manifest_path}")
            return
        
        with open(manifest_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Parse value
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif ',' in value:
                        value = [v.strip() for v in value.split(',')]
                    
                    self.manifest[key] = value
        
        logger.debug(f"Loaded CARL manifest with {len(self.manifest)} entries")
    
    def _load_global_rules(self):
        """Load global rules that always apply."""
        global_path = self.config_path / "global"
        if not global_path.exists():
            return
        
        with open(global_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GLOBAL_RULE_'):
                    # Extract rule text after '='
                    if '=' in line:
                        rule = line.split('=', 1)[1].strip()
                        self.global_rules.append(rule)
        
        logger.debug(f"Loaded {len(self.global_rules)} global rules")
    
    def _load_context_rules(self):
        """Load context bracket rules."""
        context_path = self.config_path / "context"
        if not context_path.exists():
            return
        
        current_bracket = None
        
        with open(context_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Detect bracket sections
                if line.startswith('# FRESH'):
                    current_bracket = ContextBracket.FRESH
                    self.context_rules[current_bracket] = []
                elif line.startswith('# MODERATE'):
                    current_bracket = ContextBracket.MODERATE
                    self.context_rules[current_bracket] = []
                elif line.startswith('# DEPLETED'):
                    current_bracket = ContextBracket.DEPLETED
                    self.context_rules[current_bracket] = []
                elif line.startswith('# CRITICAL'):
                    current_bracket = ContextBracket.CRITICAL
                    self.context_rules[current_bracket] = []
                elif current_bracket and (
                    line.startswith('FRESH_RULE_') or
                    line.startswith('MODERATE_RULE_') or
                    line.startswith('DEPLETED_RULE_') or
                    line.startswith('CRITICAL_RULE_')
                ):
                    if '=' in line:
                        rule = line.split('=', 1)[1].strip()
                        self.context_rules[current_bracket].append(rule)
        
        logger.debug(f"Loaded context rules for {len(self.context_rules)} brackets")
    
    def _load_commands(self):
        """Load star commands."""
        commands_path = self.config_path / "commands"
        if not commands_path.exists():
            return
        
        current_command = None
        
        with open(commands_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Detect command sections
                if line.startswith('# *'):
                    # Extract command name
                    match = re.match(r'# \*(\w+)', line)
                    if match:
                        current_command = match.group(1).lower()
                        self.commands[current_command] = []
                elif current_command and '_' in line and '=' in line:
                    # Rule line
                    rule = line.split('=', 1)[1].strip()
                    self.commands[current_command].append(rule)
        
        logger.debug(f"Loaded {len(self.commands)} star commands")
    
    def _load_domains(self):
        """Load domain-specific rules."""
        domains_path = self.config_path / "domains"
        if not domains_path.exists():
            return
        
        for domain_file in domains_path.glob("*"):
            if domain_file.is_file():
                domain_name = domain_file.name.upper()
                
                # Check if domain is enabled in manifest
                state_key = f"{domain_name}_STATE"
                if self.manifest.get(state_key) != "active":
                    continue
                
                # Load recall keywords from manifest
                recall_key = f"{domain_name}_RECALL"
                exclude_key = f"{domain_name}_EXCLUDE"
                
                recall = self.manifest.get(recall_key, [])
                exclude = self.manifest.get(exclude_key, [])
                
                # Load rules
                rules = []
                with open(domain_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f'{domain_name}_RULE_'):
                            if '=' in line:
                                rule = line.split('=', 1)[1].strip()
                                rules.append(rule)
                
                self.domains[domain_name.lower()] = {
                    'recall': set(recall) if isinstance(recall, list) else set(),
                    'exclude': set(exclude) if isinstance(exclude, list) else set(),
                    'rules': rules,
                    'always_on': self.manifest.get(f"{domain_name}_ALWAYS_ON", False)
                }
        
        logger.debug(f"Loaded {len(self.domains)} domains")
    
    def process_message(
        self,
        message: str,
        context_usage: float  # 0.0 to 1.0
    ) -> CARLResult:
        """
        Process a user message and return rules to inject.
        
        Args:
            message: User's input message
            context_usage: Percentage of context window used (0.0 to 1.0)
            
        Returns:
            CARLResult with rules, bracket, modified message, etc.
        """
        rules = []
        loaded_domains = []
        
        # 1. Always add global rules
        rules.extend(self.global_rules)
        
        # 2. Check for star commands
        star_command, modified_message = self._parse_star_commands(message)
        if star_command and star_command in self.commands:
            rules.extend(self.commands[star_command])
            logger.debug(f"Activated star command: *{star_command}")
        
        # 3. Keyword matching for domains
        message_lower = modified_message.lower()
        words = set(re.findall(r'\b\w+\b', message_lower))
        
        for domain_name, domain_config in self.domains.items():
            # Skip if explicitly disabled
            if not domain_config.get('always_on', False):
                state_key = f"{domain_name.upper()}_STATE"
                if self.manifest.get(state_key) != "active":
                    continue
            
            # Check for recall keywords
            recall = domain_config.get('recall', set())
            if recall and words & recall:  # Intersection
                # Check for exclude keywords
                exclude = domain_config.get('exclude', set())
                if not (words & exclude):  # No excluded words
                    rules.extend(domain_config['rules'])
                    loaded_domains.append(domain_name)
                    logger.debug(f"Loaded domain: {domain_name}")
        
        # 4. Calculate context bracket
        bracket = self._calculate_bracket(context_usage)
        
        # 5. Add bracket-specific rules
        if bracket in self.context_rules:
            rules.extend(self.context_rules[bracket])
        
        # 6. Add context tracking info
        rules.append(f"Context bracket: {bracket.value.upper()} ({int((1-context_usage)*100)}% remaining)")
        
        return CARLResult(
            rules=rules,
            bracket=bracket,
            modified_message=modified_message,
            loaded_domains=loaded_domains,
            star_command=star_command
        )
    
    def _parse_star_commands(self, message: str) -> tuple[Optional[str], str]:
        """
        Parse star commands from message.
        
        Returns:
            (command_name, message_without_command)
        """
        # Match *command at the start
        match = re.match(r'^\*(\w+)\s+(.+)$', message, re.DOTALL)
        if match:
            return match.group(1).lower(), match.group(2)
        
        # Also match just *command at start
        match = re.match(r'^\*(\w+)\s*$', message)
        if match:
            return match.group(1).lower(), ""
        
        return None, message
    
    def _calculate_bracket(self, usage: float) -> ContextBracket:
        """
        Calculate context bracket based on usage percentage.
        
        Args:
            usage: 0.0 to 1.0 (0% to 100% used)
            
        Returns:
            ContextBracket enum
        """
        remaining = 1.0 - usage
        
        if remaining < 0.25:
            return ContextBracket.CRITICAL
        elif remaining < 0.40:
            return ContextBracket.DEPLETED
        elif remaining < 0.60:
            return ContextBracket.MODERATE
        else:
            return ContextBracket.FRESH
    
    def format_rules_for_prompt(self, rules: List[str]) -> str:
        """
        Format rules as XML block for system prompt.
        
        Args:
            rules: List of rule strings
            
        Returns:
            Formatted XML block
        """
        if not rules:
            return ""
        
        lines = ["<carl-rules>"]
        lines.append("<rules>")
        for rule in rules:
            lines.append(f"  - {rule}")
        lines.append("</rules>")
        lines.append("</carl-rules>")
        
        return "\n".join(lines)
