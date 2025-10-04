"""
Utility functions for ClimaMetrics.

This module contains common utility functions used throughout the application.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import json
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, logs only to console.
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("climametrics")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path to ensure exists
    """
    path.mkdir(parents=True, exist_ok=True)


def clean_directory(path: Path, keep_files: Optional[List[str]] = None) -> None:
    """
    Clean directory contents, optionally keeping specified files.
    
    Args:
        path: Directory path to clean
        keep_files: List of file patterns to keep (e.g., ['*.log', '*.txt'])
    """
    if not path.exists():
        return
    
    if keep_files is None:
        keep_files = []
    
    for item in path.iterdir():
        should_keep = False
        for pattern in keep_files:
            if item.match(pattern):
                should_keep = True
                break
        
        if not should_keep:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def find_files(directory: Path, pattern: str) -> List[Path]:
    """
    Find files matching pattern in directory.
    
    Args:
        directory: Directory to search
        pattern: File pattern (e.g., '*.idf', '*.epw')
        
    Returns:
        List of matching file paths
    """
    if not directory.exists():
        return []
    
    return sorted(directory.glob(pattern))


def validate_idf_file(file_path: Path) -> bool:
    """
    Validate IDF file exists and has correct extension.
    
    Args:
        file_path: Path to IDF file
        
    Returns:
        True if valid, False otherwise
    """
    return file_path.exists() and file_path.suffix.lower() == '.idf'


def validate_weather_file(file_path: Path) -> bool:
    """
    Validate weather file exists and has correct extension.
    
    Args:
        file_path: Path to weather file
        
    Returns:
        True if valid, False otherwise
    """
    return file_path.exists() and file_path.suffix.lower() == '.epw'


def get_file_combinations(idf_dir: Path, weather_dir: Path) -> List[Tuple[Path, Path]]:
    """
    Get all combinations of IDF and weather files.
    
    Args:
        idf_dir: Directory containing IDF files
        weather_dir: Directory containing weather files
        
    Returns:
        List of (idf_file, weather_file) tuples
    """
    idf_files = find_files(idf_dir, "*.idf")
    weather_files = find_files(weather_dir, "*.epw")
    
    combinations = []
    for idf_file in idf_files:
        for weather_file in weather_files:
            if validate_idf_file(idf_file) and validate_weather_file(weather_file):
                combinations.append((idf_file, weather_file))
    
    return combinations


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Loaded JSON data or empty list if file doesn't exist
    """
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_json_file(data: List[Dict[str, Any]], file_path: Path) -> None:
    """
    Save JSON data to file.
    
    Args:
        data: Data to save
        file_path: Path to save file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_timestamp() -> str:
    """
    Get current timestamp as string.
    
    Returns:
        Current timestamp in YYYY-MM-DD HH:MM:SS format
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

