"""
Configuration management module for ClimaMetrics.

This module handles loading and managing configuration settings from YAML files
and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import platform


class Config:
    """Configuration manager for ClimaMetrics."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to configuration directory. If None, uses default.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        
        self.config_dir = config_dir
        self.settings_file = config_dir / "settings.yaml"
        self.energyplus_paths_file = config_dir / "energyplus_paths.yaml"
        
        self._settings: Dict[str, Any] = {}
        self._energyplus_paths: Dict[str, Any] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML files."""
        # Load main settings
        if self.settings_file.exists():
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self._settings = yaml.safe_load(f) or {}
        
        # Load EnergyPlus paths
        if self.energyplus_paths_file.exists():
            with open(self.energyplus_paths_file, 'r', encoding='utf-8') as f:
                self._energyplus_paths = yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'logging.level')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_energyplus_path(self) -> Optional[str]:
        """
        Get the EnergyPlus executable path for the current platform.
        
        Returns:
            Path to EnergyPlus executable or None if not found
        """
        current_platform = platform.system().lower()
        
        # Map platform names to configuration keys
        platform_mapping = {
            'darwin': 'macos',
            'windows': 'windows',
            'linux': 'linux'
        }
        
        config_platform = platform_mapping.get(current_platform, current_platform)
        
        # Get platform-specific paths
        platform_paths = self._energyplus_paths.get('platforms', {}).get(config_platform, [])
        preferred_versions = self._energyplus_paths.get('preferred_versions', [])
        
        # Try preferred versions first
        for version in preferred_versions:
            for path in platform_paths:
                if version in path and os.path.exists(path):
                    return path
        
        # Try any available path
        for path in platform_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def get_data_dir(self) -> Path:
        """Get the data directory path."""
        return Path(self.get('paths.data_dir', 'data')).resolve()
    
    def get_idf_dir(self) -> Path:
        """Get the IDF files directory path."""
        return Path(self.get('paths.idf_dir', 'data/idf')).resolve()
    
    def get_weather_dir(self) -> Path:
        """Get the weather files directory path."""
        return Path(self.get('paths.weather_dir', 'data/weather')).resolve()
    
    def get_output_dir(self) -> Path:
        """Get the output directory path."""
        return Path(self.get('paths.output_dir', 'outputs/results')).resolve()
    
    def get_log_dir(self) -> Path:
        """Get the log directory path."""
        return Path(self.get('paths.log_dir', 'outputs/logs')).resolve()
    
    def get_temp_dir(self) -> Path:
        """Get the temporary directory path."""
        temp_dir = self.get('paths.temp_dir')
        if temp_dir:
            return Path(temp_dir).resolve()
        else:
            import tempfile
            return Path(tempfile.gettempdir()) / "climametrics"
    
    def get_max_parallel_jobs(self) -> int:
        """Get the maximum number of parallel jobs."""
        max_jobs = self.get('simulation.max_parallel_jobs')
        if max_jobs is None:
            import multiprocessing
            return max(1, multiprocessing.cpu_count() - 1)
        return max_jobs
    
    def get_log_level(self) -> str:
        """Get the logging level."""
        return self.get('logging.level', 'INFO')
    
    def get_log_file(self) -> Path:
        """Get the log file path."""
        return Path(self.get('logging.file', 'outputs/logs/simulation.log')).resolve()
    
    # Zone configuration methods
    def get_default_zones(self) -> List[str]:
        """Get the default zones list."""
        return self.get('zones.default_zones', [])
    
    def get_zone_groups(self) -> Dict[str, List[str]]:
        """Get all zone groups."""
        return self.get('zones.zone_groups', {})
    
    def get_zone_group(self, group_name: str) -> Optional[List[str]]:
        """
        Get a specific zone group by name.
        
        Args:
            group_name: Name of the zone group
            
        Returns:
            List of zone names or None if group not found
        """
        zone_groups = self.get_zone_groups()
        return zone_groups.get(group_name)
    
    # Export configuration methods
    def get_export_output_dir(self) -> Path:
        """Get the export output directory path."""
        return Path(self.get('export.output_dir', 'outputs/exports')).resolve()
    
    def get_export_auto_filename(self) -> bool:
        """Get whether to auto-generate export filenames."""
        return self.get('export.auto_filename', True)
    
    def get_export_default_variables(self) -> List[str]:
        """Get the default variables to export."""
        return self.get('export.default_variables', [])
    
    def get_export_date_range(self) -> Dict[str, Optional[str]]:
        """Get the default date range for exports."""
        return self.get('export.date_range', {'start_date': None, 'end_date': None})
    
    # Pivot configuration methods
    def get_pivot_output_dir(self) -> Path:
        """Get the pivot output directory path."""
        return Path(self.get('pivot.output_dir', 'outputs/pivots')).resolve()
    
    def get_pivot_auto_filename(self) -> bool:
        """Get whether to auto-generate pivot filenames."""
        return self.get('pivot.auto_filename', True)
    
    def get_pivot_default_variables(self) -> List[str]:
        """Get the default variables to pivot."""
        return self.get('pivot.default_variables', [])
    
    def get_pivot_default_year(self) -> Optional[int]:
        """Get the default year for pivot."""
        return self.get('pivot.default_year')
    
    def get_pivot_default_simulation(self) -> Optional[str]:
        """Get the default simulation name for pivot."""
        return self.get('pivot.default_simulation')
    
    # Indicators configuration methods
    def get_indicators_zone_variables(self) -> Dict[str, Any]:
        """Get zone variables configuration for indicators."""
        return self.get('indicators.zone_variables', {})
    
    def get_indicators_environmental_variables(self) -> Dict[str, Any]:
        """Get environmental variables configuration for indicators."""
        return self.get('indicators.environmental_variables', {})
    
    def get_indicators_calculations_config(self) -> Dict[str, Any]:
        """Get calculations configuration for indicators."""
        return self.get('indicators.calculations', {})


# Global configuration instance
config = Config()

