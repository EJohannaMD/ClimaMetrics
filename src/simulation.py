"""
Simulation module for ClimaMetrics.

This module handles the core simulation logic for EnergyPlus simulations.
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from multiprocessing import Pool, cpu_count
import tempfile

from .config import config
from .utils import (
    ensure_directory, clean_directory, get_file_combinations,
    validate_idf_file, validate_weather_file, get_timestamp
)


class SimulationManager:
    """Manages EnergyPlus simulations."""
    
    def __init__(self):
        """Initialize simulation manager."""
        self.logger = logging.getLogger("climametrics.simulation")
        self.energyplus_path = config.get_energyplus_path()
        self.max_parallel_jobs = config.get_max_parallel_jobs()
        
        if not self.energyplus_path:
            raise RuntimeError("EnergyPlus executable not found. Please check your installation.")
        
        self.logger.info(f"Using EnergyPlus: {self.energyplus_path}")
        self.logger.info(f"Max parallel jobs: {self.max_parallel_jobs}")
    
    def get_available_simulations(self) -> List[Tuple[Path, Path]]:
        """
        Get all available simulation combinations.
        
        Returns:
            List of (idf_file, weather_file) tuples
        """
        idf_dir = config.get_idf_dir()
        weather_dir = config.get_weather_dir()
        
        combinations = get_file_combinations(idf_dir, weather_dir)
        self.logger.info(f"Found {len(combinations)} simulation combinations")
        
        return combinations
    
    def run_simulation(self, idf_file: Path, weather_file: Path, 
                      output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Run a single EnergyPlus simulation.
        
        Args:
            idf_file: Path to IDF file
            weather_file: Path to weather file
            output_dir: Output directory. If None, uses default.
            
        Returns:
            Dictionary with simulation results
        """
        if output_dir is None:
            output_dir = config.get_output_dir()
        
        # Validate input files
        if not validate_idf_file(idf_file):
            raise ValueError(f"Invalid IDF file: {idf_file}")
        
        if not validate_weather_file(weather_file):
            raise ValueError(f"Invalid weather file: {weather_file}")
        
        # Create output directory
        prefix = f"{idf_file.stem}__{weather_file.stem}"
        case_output_dir = output_dir / prefix
        ensure_directory(case_output_dir)
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory(prefix=f"climametrics{prefix}_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy input files to temp directory
            temp_idf = temp_path / idf_file.name
            temp_weather = temp_path / weather_file.name
            
            shutil.copy2(idf_file, temp_idf)
            shutil.copy2(weather_file, temp_weather)
            
            # Prepare EnergyPlus command
            command = [
                self.energyplus_path,
                '--readvars',
                '--output-directory', str(case_output_dir),
                '--output-prefix', prefix,
                '--weather', weather_file.name,
                idf_file.name
            ]
            
            self.logger.info(f"Starting simulation: {prefix}")
            self.logger.debug(f"Command: {' '.join(command)}")
            self.logger.debug(f"Working directory: {temp_path}")
            
            # Run simulation
            start_time = os.times()
            result = subprocess.run(
                command,
                cwd=str(temp_path),
                capture_output=True,
                text=True,
                timeout=config.get('simulation.timeout', 3600)
            )
            end_time = os.times()
            
            # Calculate duration
            duration = end_time.user + end_time.system - start_time.user - start_time.system
            
            # Rename output CSV file
            old_csv = case_output_dir / 'eplusout.csv'
            new_csv = case_output_dir / f'{prefix}.csv'
            if old_csv.exists():
                old_csv.rename(new_csv)
            
            # Prepare result
            simulation_result = {
                'idf_file': str(idf_file),
                'weather_file': str(weather_file),
                'prefix': prefix,
                'output_dir': str(case_output_dir),
                'success': result.returncode == 0,
                'duration': duration,
                'timestamp': get_timestamp(),
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                self.logger.info(f"Simulation completed: {prefix} (duration: {duration:.1f}s)")
            else:
                self.logger.error(f"Simulation failed: {prefix}")
                self.logger.error(f"Error output: {result.stderr}")
            
            return simulation_result
    
    def run_simulations_parallel(self, combinations: List[Tuple[Path, Path]], 
                                output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Run multiple simulations in parallel.
        
        Args:
            combinations: List of (idf_file, weather_file) tuples
            output_dir: Output directory. If None, uses default.
            
        Returns:
            List of simulation results
        """
        if not combinations:
            self.logger.warning("No simulations to run")
            return []
        
        if output_dir is None:
            output_dir = config.get_output_dir()
        
        ensure_directory(output_dir)
        
        # Prepare arguments for parallel execution
        args = [(idf, weather, output_dir) for idf, weather in combinations]
        
        self.logger.info(f"Running {len(combinations)} simulations in parallel")
        self.logger.info(f"Using {self.max_parallel_jobs} parallel processes")
        
        # Run simulations in parallel
        with Pool(processes=self.max_parallel_jobs) as pool:
            results = pool.starmap(self.run_simulation, args)
        
        # Log summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.logger.info(f"Simulation summary: {successful} successful, {failed} failed")
        
        return results
    
    def run_simulations_sequential(self, combinations: List[Tuple[Path, Path]], 
                                  output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Run multiple simulations sequentially.
        
        Args:
            combinations: List of (idf_file, weather_file) tuples
            output_dir: Output directory. If None, uses default.
            
        Returns:
            List of simulation results
        """
        if not combinations:
            self.logger.warning("No simulations to run")
            return []
        
        if output_dir is None:
            output_dir = config.get_output_dir()
        
        ensure_directory(output_dir)
        
        results = []
        total = len(combinations)
        
        self.logger.info(f"Running {total} simulations sequentially")
        
        for i, (idf_file, weather_file) in enumerate(combinations, 1):
            self.logger.info(f"Running simulation {i}/{total}: {idf_file.stem}__{weather_file.stem}")
            
            try:
                result = self.run_simulation(idf_file, weather_file, output_dir)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Simulation failed: {e}")
                results.append({
                    'idf_file': str(idf_file),
                    'weather_file': str(weather_file),
                    'prefix': f"{idf_file.stem}__{weather_file.stem}",
                    'success': False,
                    'error': str(e),
                    'timestamp': get_timestamp()
                })
        
        # Log summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.logger.info(f"Simulation summary: {successful} successful, {failed} failed")
        
        return results

