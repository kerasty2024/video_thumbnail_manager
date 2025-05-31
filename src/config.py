import json
from pathlib import Path

from .distribution_enum import Distribution

class Config:
    """Manages configuration settings with JSON file storage."""

    def __init__(self, config_file='config.json'):
        """Initialize the Config with default settings and load existing config.

        Args:
            config_file (str): Path to the configuration file.
        """
        self.config_file = Path(config_file)
        self.defaults = {
            'cache_dir': '',  # Default cache_dir, can be set by user in GUI
            'default_folder': '',
            'thumbnails_per_video': 18,
            'thumbnails_per_column': 3,
            'thumbnail_width': 320,
            'thumbnail_quality': 4,
            'concurrent_videos': 4,
            'zoom_factor': 2.0,
            'min_size_mb': 0.0,
            'min_duration_seconds': 0.0,
            'use_peak_concentration': True, # Changed default
            'thumbnail_peak_pos': 0.6,      # Changed default
            'thumbnail_concentration': 0.2, # Changed default
            'thumbnail_distribution': Distribution.NORMAL.value,  # Changed default (already Normal, but confirming)
            'excluded_words': '',  # Comma-separated string of excluded words/patterns
            'excluded_words_regex': False,  # Whether to treat excluded_words as regex
            'excluded_words_match_full_path': False  # Whether to match against full path or just filename/dirname
        }
        self.config = self.load()

    def load(self):
        """Load configuration from file or return defaults if file is missing or invalid.

        Returns:
            dict: Loaded or default configuration.
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Ensure all default keys are present
                for key, value in self.defaults.items():
                    if key not in config:
                        config[key] = value
                # Convert thumbnail_distribution to string if it's an Enum
                if 'thumbnail_distribution' in config and isinstance(config['thumbnail_distribution'], str):
                    config['thumbnail_distribution'] = config['thumbnail_distribution'].lower()
                return config
            except Exception:
                pass
        return self.defaults.copy()

    def save(self):
        """Save the current configuration to the file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        """Retrieve a configuration value with fallback to default.

        Args:
            key (str): Configuration key.

        Returns:
            The value associated with the key or its default.
        """
        value = self.config.get(key, self.defaults.get(key))
        if key == 'thumbnail_distribution':
            try:
                return Distribution(value)  # Return Enum instance
            except ValueError:
                # Fallback to default from self.defaults if current value is invalid
                return Distribution(self.defaults.get('thumbnail_distribution', Distribution.UNIFORM.value))
        return value

    def set(self, key, value):
        """Set a configuration value and save to file.

        Args:
            key (str): Configuration key.
            value: Value to set.
        """
        if key == 'thumbnail_distribution' and isinstance(value, Distribution):
            value = value.value  # Store as string
        self.config[key] = value
        self.save()