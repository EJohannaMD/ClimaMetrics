"""
Command-line interface for ClimaMetrics.

This module provides the CLI interface using Click for managing EnergyPlus simulations.
"""

import click
import logging
from pathlib import Path
from typing import List, Tuple

from .config import config
from .simulation import SimulationManager
from .utils import setup_logging, get_file_combinations, format_duration
from .idf_analyzer import IDFAnalyzer
from .csv_exporter import CSVExporter
from .column_explorer import ColumnExplorer
from .indicators import ThermalIndicators
from .csv_pivot import CSVPivot


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, help='Suppress output except errors')
@click.pass_context
def cli(ctx, verbose, quiet):
    """
    ClimaMetrics - EnergyPlus simulation management tool.
    
    A CLI tool for managing and executing EnergyPlus simulations with support
    for parallel processing, configuration management, and comprehensive logging.
    """
    # Set up logging
    if quiet:
        log_level = "ERROR"
    elif verbose:
        log_level = "DEBUG"
    else:
        log_level = config.get_log_level()
    
    log_file = config.get_log_file()
    setup_logging(log_level, log_file)
    
    # Store context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet


@cli.command()
@click.option('--all', 'run_all', is_flag=True, help='Run all available simulations')
@click.option('--select', 'indices', help='Comma-separated indices of simulations to run')
@click.option('--idf', 'idf_file', type=click.Path(exists=True), help='Specific IDF file to run')
@click.option('--weather', 'weather_file', type=click.Path(exists=True), help='Specific weather file to run')
@click.option('--parallel/--sequential', default=True, help='Run simulations in parallel or sequentially')
@click.option('--output-dir', type=click.Path(), help='Output directory for results')
def run(run_all, indices, idf_file, weather_file, parallel, output_dir):
    """Run EnergyPlus simulations."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Initialize simulation manager
        sim_manager = SimulationManager()
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = config.get_output_dir()
        
        # Get available simulations
        available_sims = sim_manager.get_available_simulations()
        
        if not available_sims:
            click.echo("No simulation combinations found. Check your IDF and weather files.")
            return
        
        # Determine which simulations to run
        if run_all:
            sims_to_run = available_sims
            click.echo(f"Running all {len(sims_to_run)} simulations...")
        elif indices:
            try:
                selected_indices = [int(i.strip()) for i in indices.split(',')]
                sims_to_run = [available_sims[i] for i in selected_indices if 0 <= i < len(available_sims)]
                if not sims_to_run:
                    click.echo("No valid simulations selected.")
                    return
                click.echo(f"Running {len(sims_to_run)} selected simulations...")
            except (ValueError, IndexError) as e:
                click.echo(f"Invalid indices: {e}")
                return
        elif idf_file and weather_file:
            sims_to_run = [(Path(idf_file), Path(weather_file))]
            click.echo(f"Running simulation: {Path(idf_file).stem}__{Path(weather_file).stem}")
        else:
            # Interactive selection
            click.echo("Available simulations:")
            for i, (idf, weather) in enumerate(available_sims):
                click.echo(f"  {i}: {idf.stem}__{weather.stem}")
            
            choice = click.prompt("Run all simulations? (Y/n)", default="Y")
            if choice.upper() == 'Y':
                sims_to_run = available_sims
            else:
                indices_input = click.prompt("Enter comma-separated indices")
                try:
                    selected_indices = [int(i.strip()) for i in indices_input.split(',')]
                    sims_to_run = [available_sims[i] for i in selected_indices if 0 <= i < len(available_sims)]
                except (ValueError, IndexError) as e:
                    click.echo(f"Invalid indices: {e}")
                    return
        
        # Run simulations
        if parallel:
            results = sim_manager.run_simulations_parallel(sims_to_run, output_path)
        else:
            results = sim_manager.run_simulations_sequential(sims_to_run, output_path)
        
        # Display results summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        click.echo(f"\nSimulation complete!")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Results saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error running simulations: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
def list_sims():
    """List available simulation combinations."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Get available simulations
        idf_dir = config.get_idf_dir()
        weather_dir = config.get_weather_dir()
        
        combinations = get_file_combinations(idf_dir, weather_dir)
        
        if not combinations:
            click.echo("No simulation combinations found.")
            click.echo(f"IDF directory: {idf_dir}")
            click.echo(f"Weather directory: {weather_dir}")
            return
        
        click.echo(f"Found {len(combinations)} simulation combinations:")
        click.echo()
        
        for i, (idf, weather) in enumerate(combinations):
            click.echo(f"  {i:3d}: {idf.stem}__{weather.stem}")
            click.echo(f"       IDF: {idf.name}")
            click.echo(f"       Weather: {weather.name}")
            click.echo()
        
    except Exception as e:
        logger.error(f"Error listing simulations: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
@click.option('--output-dir', type=click.Path(), help='Output directory to clean')
def clean(output_dir):
    """Clean temporary files and outputs."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        if output_dir:
            clean_path = Path(output_dir)
        else:
            clean_path = config.get_output_dir()
        
        if not clean_path.exists():
            click.echo(f"Directory does not exist: {clean_path}")
            return
        
        # Clean directory
        from .utils import clean_directory
        clean_directory(clean_path)
        
        click.echo(f"Cleaned directory: {clean_path}")
        
    except Exception as e:
        logger.error(f"Error cleaning directory: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
def status():
    """Show application status and configuration."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Check EnergyPlus installation
        energyplus_path = config.get_energyplus_path()
        if energyplus_path:
            click.echo(f"EnergyPlus: {energyplus_path}")
        else:
            click.echo("EnergyPlus: Not found")
        
        # Check directories
        click.echo(f"IDF directory: {config.get_idf_dir()}")
        click.echo(f"Weather directory: {config.get_weather_dir()}")
        click.echo(f"Output directory: {config.get_output_dir()}")
        click.echo(f"Log directory: {config.get_log_dir()}")
        
        # Check available simulations
        combinations = get_file_combinations(config.get_idf_dir(), config.get_weather_dir())
        click.echo(f"Available simulations: {len(combinations)}")
        
        # Check configuration
        click.echo(f"Max parallel jobs: {config.get_max_parallel_jobs()}")
        click.echo(f"Log level: {config.get_log_level()}")
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument('idf_file', type=click.Path(exists=True, path_type=Path))
@click.option('--building', is_flag=True, help='Show building information')
@click.option('--zones', is_flag=True, help='Show zone information')
@click.option('--materials', is_flag=True, help='Show material information')
@click.option('--hvac', is_flag=True, help='Show HVAC system information')
@click.option('--all', 'show_all', is_flag=True, help='Show all available information')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv', 'yaml']), 
              default='table', help='Output format')
@click.option('--output', type=click.Path(path_type=Path), help='Save results to file')
@click.option('--filter', 'filter_keyword', help='Filter results by keyword')
@click.option('--sort-by', help='Sort results by field')
def analyze(idf_file, building, zones, materials, hvac, show_all, output_format, output, filter_keyword, sort_by):
    """Analyze IDF file and extract information."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Validate that at least one analysis option is selected
        if not any([building, zones, materials, hvac, show_all]):
            click.echo("Error: Please select at least one analysis option (--building, --zones, --materials, --hvac, or --all)")
            return
        
        # Initialize analyzer
        analyzer = IDFAnalyzer(idf_file)
        
        # Perform analysis based on selected options
        results = {}
        
        if show_all or building:
            results['building'] = analyzer.analyze_building()
        
        if show_all or zones:
            results['zones'] = analyzer.analyze_zones()
        
        if show_all or materials:
            results['materials'] = analyzer.analyze_materials()
        
        if show_all or hvac:
            results['hvac'] = analyzer.analyze_hvac()
        
        # Format and display results
        if show_all:
            # For --all, show each section separately
            for section, data in results.items():
                click.echo(f"\n=== {section.upper()} ===")
                formatted = analyzer.format_output(data, output_format, sort_by, filter_keyword)
                click.echo(formatted)
        else:
            # For specific options, show only selected sections
            for option, section in [('building', 'building'), ('zones', 'zones'), 
                                  ('materials', 'materials'), ('hvac', 'hvac')]:
                if locals()[option] and section in results:
                    click.echo(f"\n=== {section.upper()} ===")
                    formatted = analyzer.format_output(results[section], output_format, sort_by, filter_keyword)
                    click.echo(formatted)
        
        # Save to file if specified
        if output:
            if show_all:
                analyzer.save_output(results, output, output_format)
            else:
                # Save only selected sections
                filtered_results = {k: v for k, v in results.items() if k in [s for o, s in 
                    [('building', 'building'), ('zones', 'zones'), ('materials', 'materials'), ('hvac', 'hvac')] 
                    if locals()[o]]}
                analyzer.save_output(filtered_results, output, output_format)
        
    except Exception as e:
        logger.error(f"Error analyzing IDF file: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output CSV file path (default: auto-generated in outputs/exports/)')
@click.option('--zones', help='Comma-separated list of zones to include (default: all zones)')
@click.option('--start-date', help='Start date filter (YYYY-MM-DD format)')
@click.option('--end-date', help='End date filter (YYYY-MM-DD format)')
@click.option('--summary', is_flag=True, help='Show data summary before export')
def export(csv_file, output, zones, start_date, end_date, summary):
    """Export thermal data from EnergyPlus CSV to unified format."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Initialize exporter
        exporter = CSVExporter(csv_file)
        
        # Show summary if requested
        if summary:
            data_summary = exporter.get_data_summary()
            click.echo("Data Summary:")
            click.echo(f"  Total rows: {data_summary['total_rows']:,}")
            click.echo(f"  Total columns: {data_summary['total_columns']}")
            click.echo(f"  Available zones: {len(data_summary['available_zones'])}")
            for zone in data_summary['available_zones']:
                click.echo(f"    - {zone}")
            if data_summary['date_range']['start']:
                click.echo(f"  Date range: {data_summary['date_range']['start']} to {data_summary['date_range']['end']}")
            click.echo()
        
        # Parse zones filter
        zone_list = None
        if zones:
            zone_list = [zone.strip() for zone in zones.split(',')]
            click.echo(f"Filtering to zones: {zone_list}")
        
        # Auto-generate output file name if not provided
        if not output:
            # Extract base name from input CSV file
            # Example: "TR9_Baseline__2020s_TMY_TerrassaCSTout.csv" -> "TR9_Baseline"
            base_name = csv_file.stem
            # Remove common suffixes
            for suffix in ['out', '_out', '__out']:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
            
            # Generate zone suffix
            if zone_list:
                # Clean zone names: remove special characters, join with underscore
                zone_suffix = '_'.join([z.replace(':', '_').replace(' ', '_') for z in zone_list])
            else:
                zone_suffix = 'ALL_ZONES'
            
            # Generate output file name
            output_filename = f"{base_name}_{zone_suffix}.csv"
            output = Path('outputs/exports') / output_filename
        
        # Export data
        click.echo(f"Exporting thermal data to: {output}")
        exporter.export_thermal_summary(
            output_file=output,
            zones=zone_list,
            start_date=start_date,
            end_date=end_date
        )
        
        click.echo("Export completed successfully!")
        
    except Exception as e:
        logger.error(f"Error exporting thermal data: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--zone', '-z', help='Filter columns by zone name (e.g., "0XPLANTABAJA:ZONA4")')
@click.option('--pattern', '-p', help='Filter columns by text pattern (e.g., "Temperature", "Humidity")')
@click.option('--limit', '-l', type=int, help='Maximum number of columns to display')
@click.option('--format', 'format_type', type=click.Choice(['list', 'table']), default='list', help='Output format')
@click.option('--zones', is_flag=True, help='Show all available zones')
@click.option('--types', is_flag=True, help='Group columns by variable type')
@click.option('--search', '-s', help='Interactive search for columns containing the query')
def columns(csv_file, zone, pattern, limit, format_type, zones, types, search):
    """
    Explore column headers from EnergyPlus CSV output files.
    
    This command allows you to view and filter column headers from EnergyPlus
    simulation output CSV files, making it easier to find specific variables
    and zones without using complex shell commands.
    
    Examples:
    
    \b
    # Show all columns
    energyplus-sim columns simulation_results.csv
    
    \b
    # Filter by zone
    energyplus-sim columns simulation_results.csv --zone "0XPLANTABAJA:ZONA4"
    
    \b
    # Search for temperature columns
    energyplus-sim columns simulation_results.csv --pattern "Temperature"
    
    \b
    # Show all available zones
    energyplus-sim columns simulation_results.csv --zones
    
    \b
    # Group by variable type
    energyplus-sim columns simulation_results.csv --types
    """
    logger = logging.getLogger(__name__)
    
    try:
        explorer = ColumnExplorer(csv_file)
        
        # Show available zones
        if zones:
            zones_list = explorer.get_zones()
            click.echo(f"Available zones ({len(zones_list)}):")
            click.echo("-" * 40)
            for zone_name in zones_list:
                click.echo(f"  {zone_name}")
            return
        
        # Group by variable types
        if types:
            variable_types = explorer.get_variable_types()
            click.echo("Columns grouped by variable type:")
            click.echo("=" * 50)
            for var_type, cols in variable_types.items():
                click.echo(f"\n{var_type} ({len(cols)} columns):")
                click.echo("-" * 30)
                for col in cols[:10]:  # Show first 10 columns
                    click.echo(f"  {col}")
                if len(cols) > 10:
                    click.echo(f"  ... and {len(cols) - 10} more")
            return
        
        # Interactive search
        if search:
            matching_columns = explorer.search_interactive(search)
            click.echo(f"Columns containing '{search}' ({len(matching_columns)} found):")
            click.echo("-" * 50)
            for col in matching_columns[:limit or 20]:
                click.echo(f"  {col}")
            if len(matching_columns) > (limit or 20):
                click.echo(f"  ... and {len(matching_columns) - (limit or 20)} more")
            return
        
        # Get filtered columns
        columns_list = explorer.get_columns(
            zone=zone,
            pattern=pattern,
            limit=limit
        )
        
        # Format and display output
        if columns_list:
            output = explorer.format_output(columns_list, format_type)
            click.echo(output)
        else:
            click.echo("No columns found matching the criteria.")
            
    except Exception as e:
        logger.error(f"Error exploring columns: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output CSV file path (default: input_file_indicators.csv)')
@click.option('--simulation', '-s', default='Simulation', 
              help='Simulation name for output (default: "Simulation")')
@click.option('--indicators', '-i', help='Comma-separated list of indicators to calculate (IOD,AWD,ALPHA,HI,DDH,DI,DIlevel,HIlevel)')
@click.option('--comfort-temp', type=float, default=26.5, 
              help='Comfort temperature for IOD calculation (default: 26.5°C)')
@click.option('--base-temp', type=float, default=18.0, 
              help='Base outside temperature for AWD calculation (default: 18.0°C)')
@click.option('--year', '-y', type=int, default=2020, 
              help='Year for datetime parsing (default: 2020)')
def indicators(csv_file, output, simulation, indicators, comfort_temp, base_temp, year):
    """
    Calculate thermal comfort indicators from exported thermal data.
    
    This command calculates various thermal comfort indicators including:
    - IOD: Indoor Overheating Degree
    - AWD: Ambient Warmness Degree  
    - ALPHA: Overheating Escalator Factor
    - HI: Heat Index (Apparent Temperature)
    - DDH: Degree-weighted Discomfort Hours
    - DI: Discomfort Index
    - DIlevel: Discomfort Index Risk Categories
    - HIlevel: Heat Index Risk Categories
    
    The output format is: DateTime,Zone,Value,Simulation,Indicator
    
    Examples:
    
    \b
    # Calculate all indicators
    energyplus-sim indicators thermal_data.csv --simulation "Baseline_TMY2020s"
    
    \b
    # Calculate specific indicators
    energyplus-sim indicators thermal_data.csv --indicators "IOD,AWD,HI"
    
    # Calculate indicators with risk levels
    energyplus-sim indicators thermal_data.csv --indicators "HI,DI,HIlevel,DIlevel"
    
    \b
    # Custom comfort temperature
    energyplus-sim indicators thermal_data.csv --comfort-temp 25.0
    
    # Custom year for datetime parsing
    energyplus-sim indicators thermal_data.csv --year 2024
    """
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Parse indicators list
        indicators_list = None
        if indicators:
            indicators_list = [ind.strip() for ind in indicators.split(',')]
            # Validate indicators
            valid_indicators = {'IOD', 'AWD', 'ALPHA', 'HI', 'DDH', 'DI', 'DIlevel', 'HIlevel'}
            invalid_indicators = set(indicators_list) - valid_indicators
            if invalid_indicators:
                click.echo(f"Error: Invalid indicators: {', '.join(invalid_indicators)}")
                click.echo(f"Valid indicators: {', '.join(valid_indicators)}")
                return
        
        # Validate year
        if year < 1900 or year > 2100:
            click.echo(f"Error: Year must be between 1900 and 2100, got {year}")
            return
        
        # Set default output file
        if not output:
            input_stem = Path(csv_file).stem
            output = Path(f"{input_stem}_indicators.csv")
        
        # Initialize indicators calculator
        calculator = ThermalIndicators(csv_file, simulation, year)
        
        # Update constants if provided
        if comfort_temp != 26.5:
            calculator.COMFORT_TEMPERATURE = comfort_temp
            click.echo(f"Using comfort temperature: {comfort_temp}°C")
        
        if base_temp != 18.0:
            calculator.BASE_OUTSIDE_TEMPERATURE = base_temp
            click.echo(f"Using base temperature: {base_temp}°C")
        
        # Calculate indicators
        click.echo(f"Calculating thermal comfort indicators...")
        click.echo(f"  Input file: {csv_file}")
        click.echo(f"  Output file: {output}")
        click.echo(f"  Simulation: {simulation}")
        click.echo(f"  Year: {year}")
        if indicators_list:
            click.echo(f"  Indicators: {', '.join(indicators_list)}")
        else:
            click.echo(f"  Indicators: All (IOD, AWD, ALPHA, HI, DDH, DI, DIlevel, HIlevel)")
        
        # Export indicators
        calculator.export_indicators(output, indicators_list)
        
        click.echo("Indicators calculation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


@cli.command()
@click.option('--dir', 'directory', type=click.Path(exists=True, path_type=Path), 
              help='Directory containing exported CSV files (default: outputs/exports/)')
@click.option('--input', 'pattern', type=str,
              help='Glob pattern for input files (e.g., "outputs/exports/*STUDYROOM*.csv")')
@click.option('--variable', '-v', required=True,
              help='Variable to extract (e.g., "Operative_Temperature")')
@click.option('--year', '-y', type=int,
              help='Year to add to Date/Time column (e.g., 2020, 2025)')
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output CSV file path (default: outputs/pivots/{variable}_All_Zones.csv)')
@click.option('--summary', is_flag=True, help='Show detailed summary of processing')
def pivot(directory, pattern, variable, year, output, summary):
    """
    Consolidate a variable from multiple zone exports into a single CSV.
    
    This command takes multiple exported CSV files (one per zone) and creates
    a consolidated CSV with a specific variable for all zones in LONG format.
    Optionally, you can add a year to the Date/Time column for temporal analysis.
    
    Examples:
    
    \b
    # Extract Operative_Temperature from all exports
    energyplus-sim pivot --variable "Operative_Temperature"
    
    \b
    # Extract with year 2020 added to dates
    energyplus-sim pivot --variable "Operative_Temperature" --year 2020
    
    \b
    # Extract from specific directory
    energyplus-sim pivot --dir "outputs/exports/" --variable "Air_Temperature"
    
    \b
    # Extract from files matching pattern with year
    energyplus-sim pivot --input "outputs/exports/*STUDYROOM*.csv" --variable "Relative_Humidity" --year 2025
    
    \b
    # Custom output file
    energyplus-sim pivot --variable "Operative_Temperature" --output "my_pivot.csv"
    """
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Initialize pivot
        pivot_tool = CSVPivot()
        
        # Set default directory if neither dir nor pattern provided
        if not directory and not pattern:
            directory = Path('outputs/exports')
            click.echo(f"Using default directory: {directory}")
        
        # Set default output file
        if not output:
            # Clean variable name for filename
            var_name = variable.replace('_', '').replace(' ', '')
            output = Path(f'outputs/pivots/{variable}_All_Zones.csv')
        
        # Display operation info
        click.echo(f"Variable to extract: {variable}")
        if directory:
            click.echo(f"Processing CSV files from: {directory}")
        else:
            click.echo(f"Processing CSV files matching: {pattern}")
        click.echo(f"Output file: {output}")
        click.echo()
        
        # Export pivot
        pivot_tool.export_pivot(
            output_file=output,
            directory=directory,
            pattern=pattern,
            variable=variable,
            year=year
        )
        
        click.echo("\nPivot completed successfully!")
        
    except Exception as e:
        logger.error(f"Error creating pivot: {e}")
        click.echo(f"Error: {e}")
        raise click.Abort()


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()

