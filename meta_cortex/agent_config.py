"""
Agent configuration utilities for MetaCortex.
Loads agent configurations from YAML files.
"""
import os
import yaml
from typing import Dict, Any, Optional

class AgentConfig:
    """
    Loads and manages agent configurations from YAML files.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the agent configuration loader.
        
        Args:
            config_path: Path to the YAML configuration file.
                        If None, defaults to prompts/agents.yaml in the project directory.
        """
        # Set default config path if none provided
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, "prompts", "agents.yaml")
        else:
            self.config_path = config_path
            
        self.config: Dict[str, Any] = {}
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load the agent configuration file.
        
        Returns:
            The parsed configuration dictionary
        """
        try:
            # Check if file exists
            if not os.path.exists(self.config_path):
                print(f"Agent configuration file {self.config_path} does not exist")
                return {}
                
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                print(f"Loaded agent configuration from {self.config_path}")
                return self.config
        except yaml.YAMLError:
            print(f"Error parsing YAML in {self.config_path}")
            return {}
        except Exception as e:
            print(f"Error loading agent configuration file {self.config_path}: {str(e)}")
            return {}
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get the configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent to retrieve configuration for
            
        Returns:
            Dictionary containing the agent's configuration
        """
        if not self.config:
            self.load_config()
            
        return self.config.get(agent_name, {})
