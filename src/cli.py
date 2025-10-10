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
from .powerbi_exporter import PowerBIExporter


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


@cli.command(name='config-show')
@click.option('--zones', is_flag=True, help='Show zone groups configuration')
@click.option('--export-cfg', is_flag=True, help='Show export configuration')
@click.option('--pivot-cfg', is_flag=True, help='Show pivot configuration')
@click.option('--all', 'show_all', is_flag=True, help='Show all configuration')
def config_show(zones, export_cfg, pivot_cfg, show_all):
    """
    Show configuration settings from config/settings.yaml.
    
    Examples:
    
    \b
    # Show zone groups
    energyplus-sim config-show --zones
    
    \b
    # Show export configuration
    energyplus-sim config-show --export-cfg
    
    \b
    # Show all configuration
    energyplus-sim config-show --all
    """
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # If no options, show all
        if not any([zones, export_cfg, pivot_cfg, show_all]):
            show_all = True
        
        click.echo("=== ClimaMetrics Configuration ===\n")
        
        # Zone configuration
        if zones or show_all:
            click.echo("📍 Zone Configuration:")
            click.echo("-" * 50)
            
            default_zones = config.get_default_zones()
            if default_zones:
                click.echo(f"Default zones: {', '.join(default_zones)}")
            else:
                click.echo("Default zones: (none)")
            
            zone_groups = config.get_zone_groups()
            if zone_groups:
                click.echo(f"\nZone groups ({len(zone_groups)} groups):")
                for group_name, group_zones in zone_groups.items():
                    click.echo(f"  • {group_name}:")
                    for zone in group_zones:
                        click.echo(f"      - {zone}")
            else:
                click.echo("\nZone groups: (none)")
            click.echo()
        
        # Export configuration
        if export_cfg or show_all:
            click.echo("📤 Export Configuration:")
            click.echo("-" * 50)
            click.echo(f"Output directory: {config.get_export_output_dir()}")
            click.echo(f"Auto-generate filenames: {config.get_export_auto_filename()}")
            
            default_vars = config.get_export_default_variables()
            if default_vars:
                click.echo(f"Default variables: {', '.join(default_vars)}")
            else:
                click.echo("Default variables: (none)")
            
            date_range = config.get_export_date_range()
            if date_range.get('start_date') or date_range.get('end_date'):
                click.echo(f"Date range: {date_range.get('start_date', 'N/A')} to {date_range.get('end_date', 'N/A')}")
            else:
                click.echo("Date range: (full year)")
            click.echo()
        
        # Pivot configuration
        if pivot_cfg or show_all:
            click.echo("🔄 Pivot Configuration:")
            click.echo("-" * 50)
            click.echo(f"Output directory: {config.get_pivot_output_dir()}")
            click.echo(f"Auto-generate filenames: {config.get_pivot_auto_filename()}")
            
            default_vars = config.get_pivot_default_variables()
            if default_vars:
                click.echo(f"Default variables: {', '.join(default_vars)}")
            else:
                click.echo("Default variables: (none)")
            
            default_year = config.get_pivot_default_year()
            click.echo(f"Default year: {default_year if default_year else '(none)'}")
            
            default_sim = config.get_pivot_default_simulation()
            click.echo(f"Default simulation: {default_sim if default_sim else '(none)'}")
            click.echo()
        
        click.echo("💡 Tip: Edit config/settings.yaml to customize these settings")
        
    except Exception as e:
        logger.error(f"Error showing configuration: {e}")
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
@click.option('--zone-group', '-g', help='Use predefined zone group from config (e.g., "studyrooms", "all_plant1")')
@click.option('--start-date', help='Start date filter (YYYY-MM-DD format)')
@click.option('--end-date', help='End date filter (YYYY-MM-DD format)')
@click.option('--summary', is_flag=True, help='Show data summary before export')
def export(csv_file, output, zones, zone_group, start_date, end_date, summary):
    """Export thermal data from EnergyPlus CSV to unified format."""
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Load configuration
        from .config import config
        
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
        
        # Priority: --zones > --zone-group > default_zones from config
        if zones:
            zone_list = [zone.strip() for zone in zones.split(',')]
            click.echo(f"Filtering to zones: {zone_list}")
        elif zone_group:
            # Get zone group from configuration
            zone_list = config.get_zone_group(zone_group)
            if zone_list:
                click.echo(f"Using zone group '{zone_group}': {zone_list}")
            else:
                available_groups = list(config.get_zone_groups().keys())
                click.echo(f"Error: Zone group '{zone_group}' not found in configuration.")
                if available_groups:
                    click.echo(f"Available zone groups: {', '.join(available_groups)}")
                raise click.Abort()
        else:
            # Use default zones from config if set
            default_zones = config.get_default_zones()
            if default_zones:
                zone_list = default_zones
                click.echo(f"Using default zones from config: {zone_list}")
        
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
@click.argument('energyplus_csv', type=click.Path(exists=True, path_type=Path))
@click.option('--zones', help='Comma-separated list of zones to analyze')
@click.option('--zone-group', '-g', help='Use predefined zone group from config (e.g., "studyrooms", "all_plant1")')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), 
              help='Output directory for indicator files (default: outputs/indicators/{simulation_name}/)')
@click.option('--simulation', '-s', default='Simulation', 
              help='Simulation name for output files (default: "Simulation")')
@click.option('--indicators', '-i', help='Comma-separated list of indicators to calculate (IOD,AWD,ALPHA,HI,DDH,DI,DIlevel,HIlevel)')
@click.option('--comfort-temp', type=float, default=26.5, 
              help='Comfort temperature for IOD calculation (default: 26.5°C)')
@click.option('--base-temp', type=float, default=18.0, 
              help='Base outside temperature for AWD calculation (default: 18.0°C)')
@click.option('--year', '-y', type=int, default=2020, 
              help='Year for datetime parsing (default: 2020)')
@click.option('--format', '-f', 
              type=click.Choice(['csv', 'xlsx'], case_sensitive=False),
              default='csv',
              help='Export format: csv or xlsx (default: csv)')
def indicators(energyplus_csv, zones, zone_group, output_dir, simulation, indicators, comfort_temp, base_temp, year, format):
    """
    Calculate thermal comfort indicators directly from EnergyPlus CSV output.
    
    This command reads the EnergyPlus output CSV file and calculates thermal comfort 
    indicators for specified zones. Each indicator is exported to a separate file
    in WIDE format (DateTime as rows, zones as columns).
    
    Available indicators:
    - IOD: Indoor Overheating Degree
    - AWD: Ambient Warmness Degree (environmental, no zones)
    - ALPHA: Overheating Escalator Factor (IOD/AWD)
    - HI: Heat Index (Apparent Temperature)
    - DDH: Degree-weighted Discomfort Hours
    - DI: Discomfort Index
    - DIlevel: Discomfort Index Risk Categories
    - HIlevel: Heat Index Risk Categories
    
    Export formats:
    - CSV (default): {Indicator}_{SimulationName}.csv
    - XLSX: {Indicator}_{SimulationName}.xlsx (requires openpyxl)
    
    Examples:
    
    \b
    # Calculate all indicators for zone group (CSV format)
    energyplus-sim indicators outputs/results/simulation.csv \\
        --zone-group studyrooms \\
        --simulation "Baseline_TMY2020s"
    
    \b
    # Calculate specific indicators in Excel format
    energyplus-sim indicators outputs/results/simulation.csv \\
        --zones "ZONE1,ZONE2" \\
        --indicators "IOD,AWD,HI" \\
        --simulation "Baseline_2020s" \\
        --format xlsx
    
    \b
    # Custom output directory and parameters
    energyplus-sim indicators outputs/results/simulation.csv \\
        --zone-group studyrooms \\
        --output-dir "custom/path/" \\
        --comfort-temp 25.0 \\
        --year 2025 \\
        --format xlsx
    """
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Load configuration
        from .config import config
        
        # Determine zones to analyze
        zone_list = None
        
        # Priority: --zones > --zone-group > default_zones from config
        if zones:
            zone_list = [z.strip() for z in zones.split(',')]
            click.echo(f"Analyzing zones: {zone_list}")
        elif zone_group:
            zone_list = config.get_zone_group(zone_group)
            if zone_list:
                click.echo(f"Using zone group '{zone_group}': {zone_list}")
            else:
                available_groups = list(config.get_zone_groups().keys())
                click.echo(f"Error: Zone group '{zone_group}' not found in configuration.")
                if available_groups:
                    click.echo(f"Available zone groups: {', '.join(available_groups)}")
                else:
                    click.echo("No zone groups defined in config/settings.yaml")
                raise click.Abort()
        else:
            default_zones = config.get_default_zones()
            if default_zones:
                zone_list = default_zones
                click.echo(f"Using default zones from config: {zone_list}")
            else:
                click.echo("Error: No zones specified.")
                click.echo("Use --zones, --zone-group, or set default_zones in config/settings.yaml")
                raise click.Abort()
        
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
        
        # Set default output directory
        if not output_dir:
            output_dir = Path('outputs') / 'indicators' / simulation
            click.echo(f"Using default output directory: {output_dir}")
        
        # Initialize indicators calculator
        calculator = ThermalIndicators(energyplus_csv, simulation, year)
        
        # Update constants if provided
        if comfort_temp != 26.5:
            calculator.COMFORT_TEMPERATURE = comfort_temp
            click.echo(f"Using comfort temperature: {comfort_temp}°C")
        
        if base_temp != 18.0:
            calculator.BASE_OUTSIDE_TEMPERATURE = base_temp
            click.echo(f"Using base temperature: {base_temp}°C")
        
        # Display operation info
        click.echo(f"\nCalculating thermal comfort indicators...")
        click.echo(f"  EnergyPlus CSV: {energyplus_csv}")
        click.echo(f"  Zones: {len(zone_list)} zones")
        click.echo(f"  Output directory: {output_dir}")
        click.echo(f"  Simulation: {simulation}")
        click.echo(f"  Year: {year}")
        click.echo(f"  Format: {format.upper()}")
        if indicators_list:
            click.echo(f"  Indicators: {', '.join(indicators_list)}")
        else:
            click.echo(f"  Indicators: All (IOD, AWD, ALPHA, HI, DDH, DI, DIlevel, HIlevel)")
        click.echo()
        
        # Calculate and export indicators
        calculator.export_indicators_wide(
            output_dir=output_dir,
            zones=zone_list,
            indicators=indicators_list,
            export_format=format
        )
        
        click.echo(f"\n✅ Indicators calculation completed successfully!")
        click.echo(f"📁 Output files saved in: {output_dir}")
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        click.echo(f"❌ Error: {e}")
        raise click.Abort()


@cli.command()
@click.argument('energyplus_csv', type=click.Path(exists=True, path_type=Path))
@click.option('--zones', '-z', type=str,
              help='Comma-separated list of zone names to analyze')
@click.option('--zone-group', '-g', type=str,
              help='Zone group name from settings.yaml (alternative to --zones)')
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output CSV file path (default: outputs/powerbi/{simulation}_powerbi.csv)')
@click.option('--simulation', '-s', type=str, required=True,
              help='Simulation name (required, used in output)')
@click.option('--indicators', '-i', type=str,
              help='Comma-separated list of indicators to calculate (default: all)')
@click.option('--comfort-temp', type=float, default=26.5,
              help='Comfort temperature for IOD calculation (default: 26.5°C)')
@click.option('--base-temp', type=float, default=18.0,
              help='Base outside temperature for AWD calculation (default: 18.0°C)')
@click.option('--year', '-y', type=int, default=2020,
              help='Year for datetime parsing (default: 2020)')
@click.option('--start-date', type=str,
              help='Start date for filtering in format MM/DD (e.g., "06/22")')
@click.option('--end-date', type=str,
              help='End date for filtering in format MM/DD (e.g., "08/30")')
@click.option('--format', '-f', 
              type=click.Choice(['csv', 'xlsx'], case_sensitive=False),
              default='csv',
              help='Export format: csv or xlsx (default: csv)')
def powerbi(energyplus_csv, zones, zone_group, output, simulation, indicators, comfort_temp, base_temp, year, start_date, end_date, format):
    """
    Export thermal comfort indicators in Power BI format (ULTRA-LONG).
    
    This command calculates thermal comfort indicators and exports them in a single
    consolidated CSV file optimized for Power BI analysis. The output uses ULTRA-LONG
    format with columns: Simulation, Indicator, DateTime, Zone, Value.
    
    Features:
    - Single consolidated file with all indicators (CSV or XLSX)
    - Temporal indicators: IOD, ALPHA, HI, DI, HIlevel, DIlevel (hourly values)
    - Aggregated indicators: DDH (sum across time), alphatot (global average)
    - Environmental indicator: AWD (Zone = "Environment")
    - Optimized for Power BI data modeling and DAX calculations
    
    Export formats:
    - CSV (default): Optimized for large datasets
    - XLSX: Excel format with compression (requires openpyxl)
    
    Available indicators:
    - IOD: Indoor Overheating Degree (temporal)
    - AWD: Ambient Warmness Degree (temporal, environmental)
    - ALPHA: Overheating Escalator Factor (temporal, by zone)
    - alphatot: Global ALPHA average (single aggregated value)
    - HI: Heat Index (temporal)
    - HIlevel: Heat Index Risk Categories (temporal)
    - DDH: Degree-weighted Discomfort Hours (aggregated sum)
    - DI: Discomfort Index (temporal)
    - DIlevel: Discomfort Index Risk Categories (temporal)
    
    Examples:
    
    \b
    # Export all indicators for zone group
    energyplus-sim powerbi outputs/results/simulation.csv \\
        --zone-group studyrooms \\
        --simulation "Baseline_TMY2020s"
    
    \b
    # Export specific indicators with custom output
    energyplus-sim powerbi outputs/results/simulation.csv \\
        --zones "ZONE1,ZONE2,ZONE3" \\
        --indicators "IOD,AWD,ALPHA,DDH" \\
        --simulation "Future_2050s" \\
        --output outputs/powerbi/future_scenario.csv
    
    \b
    # Customize comfort parameters
    energyplus-sim powerbi outputs/results/simulation.csv \\
        --zone-group all \\
        --simulation "Test_Run" \\
        --comfort-temp 25.0 \\
        --base-temp 19.0 \\
        --year 2025
    
    \b
    # Filter by date range (summer period)
    energyplus-sim powerbi outputs/results/simulation.csv \\
        --zone-group studyrooms \\
        --simulation "Baseline_Summer_2020s" \\
        --start-date "06/22" \\
        --end-date "08/30" \\
        --year 2020
    
    \b
    # Export in Excel format
    energyplus-sim powerbi outputs/results/simulation.csv \\
        --zone-group studyrooms \\
        --simulation "Baseline_2020s" \\
        --format xlsx
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Determine zones to analyze
        if zones and zone_group:
            click.echo("Warning: Both --zones and --zone-group provided. Using --zones.")
            zone_list = [z.strip() for z in zones.split(',')]
        elif zones:
            zone_list = [z.strip() for z in zones.split(',')]
        elif zone_group:
            zone_list = config.get_zone_group(zone_group)
            if not zone_list:
                raise click.ClickException(f"Zone group '{zone_group}' not found in settings.yaml")
            click.echo(f"Using zone group '{zone_group}': {len(zone_list)} zones")
        else:
            # Try default zones
            zone_list = config.get_default_zones()
            if not zone_list:
                raise click.ClickException(
                    "No zones specified. Use --zones, --zone-group, or configure default_zones in settings.yaml"
                )
            click.echo(f"Using default zones: {len(zone_list)} zones")
        
        # Parse indicators if provided
        indicators_list = None
        if indicators:
            indicators_list = [i.strip().upper() for i in indicators.split(',')]
            # Validate indicators
            valid_indicators = ['IOD', 'AWD', 'ALPHA', 'HI', 'DDH', 'DI', 'DILEVEL', 'HILEVEL']
            for ind in indicators_list:
                if ind not in valid_indicators:
                    raise click.ClickException(
                        f"Invalid indicator: {ind}. Valid options: {', '.join(valid_indicators)}"
                    )
        
        # Display operation info
        click.echo(f"\n🔄 Exporting Power BI format...")
        click.echo(f"  EnergyPlus CSV: {energyplus_csv}")
        click.echo(f"  Zones: {len(zone_list)} zones")
        click.echo(f"  Simulation: {simulation}")
        click.echo(f"  Year: {year}")
        click.echo(f"  Format: {format.upper()}")
        if start_date or end_date:
            date_range_str = ""
            if start_date and end_date:
                date_range_str = f"{start_date} to {end_date}"
            elif start_date:
                date_range_str = f"from {start_date}"
            elif end_date:
                date_range_str = f"to {end_date}"
            click.echo(f"  Date range: {date_range_str}")
        click.echo(f"  Comfort temp: {comfort_temp}°C")
        click.echo(f"  Base temp: {base_temp}°C")
        if indicators_list:
            click.echo(f"  Indicators: {', '.join(indicators_list)}")
        else:
            click.echo(f"  Indicators: All (IOD, AWD, ALPHA, alphatot, HI, DDH, DI, DIlevel, HIlevel)")
        if output:
            click.echo(f"  Output: {output}")
        else:
            ext = '.xlsx' if format == 'xlsx' else '.csv'
            click.echo(f"  Output: outputs/powerbi/{simulation}_powerbi{ext}")
        click.echo()
        
        # Initialize exporter
        exporter = PowerBIExporter(
            energyplus_csv=str(energyplus_csv),
            simulation_name=simulation
        )
        
        # Export
        output_file = exporter.export_powerbi(
            zones=zone_list,
            output_file=str(output) if output else None,
            indicators=indicators_list,
            comfort_temp=comfort_temp,
            base_temp=base_temp,
            year=year,
            start_date=start_date,
            end_date=end_date,
            export_format=format
        )
        
        click.echo(f"\n✅ Power BI export completed successfully!")
        click.echo(f"📁 Output file: {output_file}")
        click.echo(f"\n💡 Import this file into Power BI for advanced analysis and dashboards!")
        
    except Exception as e:
        logger.error(f"Error exporting Power BI format: {e}")
        click.echo(f"❌ Error: {e}")
        raise click.Abort()


@cli.command()
@click.option('--dir', 'directory', type=click.Path(exists=True, path_type=Path), 
              help='Directory containing exported CSV files (default: outputs/exports/)')
@click.option('--input', 'pattern', type=str,
              help='Glob pattern for input files (e.g., "outputs/exports/*STUDYROOM*.csv")')
@click.option('--variable', '-v',
              help='Variable(s) to extract (e.g., "Operative_Temperature" or "Operative_Temperature,Air_Temperature")')
@click.option('--year', '-y', type=int,
              help='Year to add to Date/Time column (e.g., 2020, 2025)')
@click.option('--simulation', '-s', type=str,
              help='Simulation name to add as a column (e.g., "Baseline_TMY2020s", "Future_2050s")')
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output CSV file path (default: outputs/pivots/{variable}_All_Zones.csv)')
@click.option('--summary', is_flag=True, help='Show detailed summary of processing')
def pivot(directory, pattern, variable, year, simulation, output, summary):
    """
    Consolidate variable(s) from multiple zone exports into a single CSV.
    
    This command takes multiple exported CSV files (one per zone) and creates
    a consolidated CSV with selected variable(s) for all zones in LONG format
    with columns: Date/Time, Zone, Indicator, Value, [Simulation].
    Optionally, you can add a year to the Date/Time column and a simulation name.
    
    Examples:
    
    \b
    # Extract single variable from all exports
    energyplus-sim pivot --variable "Operative_Temperature"
    
    \b
    # Extract multiple variables in one file
    energyplus-sim pivot --variable "Operative_Temperature,Air_Temperature,Relative_Humidity"
    
    \b
    # Extract with year 2020 added to dates
    energyplus-sim pivot --variable "Operative_Temperature" --year 2020
    
    \b
    # Extract with year and simulation name
    energyplus-sim pivot --variable "Operative_Temperature" --year 2020 --simulation "Baseline_TMY2020s"
    
    \b
    # Extract multiple variables with year and simulation
    energyplus-sim pivot -v "Operative_Temperature,Air_Temperature" -y 2020 -s "Baseline_2020s"
    
    \b
    # Extract from specific directory with simulation
    energyplus-sim pivot --dir "outputs/exports/" --variable "Air_Temperature" --simulation "Future_2050s"
    
    \b
    # Extract from files matching pattern
    energyplus-sim pivot --input "outputs/exports/*STUDYROOM*.csv" --variable "Relative_Humidity,Occupancy" --year 2025
    
    \b
    # Custom output file with simulation
    energyplus-sim pivot --variable "Operative_Temperature" --simulation "Baseline" --output "baseline_pivot.csv"
    """
    logger = logging.getLogger("climametrics.cli")
    
    try:
        # Load configuration
        from .config import config
        
        # Initialize pivot
        pivot_tool = CSVPivot()
        
        # Use defaults from config if not provided
        if not variable:
            default_vars = config.get_pivot_default_variables()
            if default_vars:
                variable = ','.join(default_vars)
                click.echo(f"Using default variables from config: {variable}")
            else:
                click.echo("Error: No variable specified and no default variables in config.")
                click.echo("Use --variable or set pivot.default_variables in config/settings.yaml")
                raise click.Abort()
        
        if not year:
            year = config.get_pivot_default_year()
            if year:
                click.echo(f"Using default year from config: {year}")
        
        if not simulation:
            simulation = config.get_pivot_default_simulation()
            if simulation:
                click.echo(f"Using default simulation from config: {simulation}")
        
        # Set default directory if neither dir nor pattern provided
        if not directory and not pattern:
            directory = config.get_pivot_output_dir()
            # Use outputs/exports as source directory
            directory = Path('outputs/exports')
            click.echo(f"Using default directory: {directory}")
        
        # Set default output file
        if not output:
            # Clean variable name for filename
            var_name = variable.replace('_', '').replace(' ', '')
            output = config.get_pivot_output_dir() / f'{variable}_All_Zones.csv'
        
        # Display operation info
        click.echo(f"Variable to extract: {variable}")
        if year:
            click.echo(f"Year: {year}")
        if simulation:
            click.echo(f"Simulation: {simulation}")
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
            year=year,
            simulation=simulation
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

