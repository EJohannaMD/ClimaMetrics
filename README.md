# ClimaMetrics

EnergyPlus simulation management tool with CLI interface.

## Overview

ClimaMetrics is a command-line tool for managing and executing EnergyPlus simulations with support for parallel processing, configuration management, and comprehensive logging.

## Features

- **CLI Interface**: Easy-to-use command-line interface with Click
- **Parallel Processing**: Run multiple simulations in parallel
- **Configuration Management**: YAML-based configuration system
- **Comprehensive Logging**: Structured logging with file and console output
- **File Validation**: Automatic validation of IDF and weather files
- **Data Export**: Extract and export specific thermal data from simulation results
- **Thermal Indicators**: Calculate thermal comfort indicators (IOD, AWD, ALPHA, HI, DDH, DI)
- **IDF Analysis**: Analyze IDF files to extract building, zone, and material information
- **Column Explorer**: Explore and filter column headers from EnergyPlus CSV output files
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ClimaMetrics
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Configuration

1. Place your IDF files in `data/idf/`
2. Place your weather files in `data/weather/`
3. Configure EnergyPlus paths in `config/energyplus_paths.yaml`
4. Adjust settings in `config/settings.yaml` if needed

## Usage

### Basic Commands

```bash
# List available simulations
energyplus-sim list

# Run all simulations
energyplus-sim run --all

# Run specific simulations by index
energyplus-sim run --select 0,1,2

# Run with specific files
energyplus-sim run --idf file.idf --weather file.epw

# Run sequentially instead of parallel
energyplus-sim run --all --sequential

# Check status
energyplus-sim status

# Clean output directory
energyplus-sim clean

# Analyze IDF file
energyplus-sim analyze building.idf

# Analyze specific aspects
energyplus-sim analyze building.idf --zones --materials

# Export thermal data to CSV
energyplus-sim export results.csv

# Export specific zones
energyplus-sim export results.csv --zones "ZONE1" "ZONE2"

# Export with date range
energyplus-sim export results.csv --start-date "01/01" --end-date "12/31"

# Export with summary
energyplus-sim export results.csv --summary

# Explore column headers
energyplus-sim columns simulation_results.csv

# Filter columns by zone
energyplus-sim columns simulation_results.csv --zone "0XPLANTABAJA:ZONA4"

# Search for specific patterns
energyplus-sim columns simulation_results.csv --pattern "Temperature"

# Calculate thermal comfort indicators
energyplus-sim indicators thermal_data.csv --simulation "Baseline_TMY2020s"

# Calculate specific indicators
energyplus-sim indicators thermal_data.csv --indicators "IOD,AWD,HI"

# Calculate with custom parameters
energyplus-sim indicators thermal_data.csv --comfort-temp 25.0 --base-temp 20.0
```

### Advanced Options

```bash
# Verbose logging
energyplus-sim --verbose run --all

# Quiet mode
energyplus-sim --quiet run --all

# Custom output directory
energyplus-sim run --all --output-dir /path/to/output
```

## Directory Structure

```
ClimaMetrics/
├── src/                    # Source code
│   ├── cli.py             # CLI interface
│   ├── simulation.py      # Simulation logic
│   ├── config.py          # Configuration management
│   ├── utils.py           # Utility functions
│   ├── idf_analyzer.py    # IDF file analysis
│   ├── csv_exporter.py    # CSV data export
│   ├── column_explorer.py # Column header exploration
│   └── indicators.py      # Thermal comfort indicators
├── data/                   # Input data
│   ├── idf/               # IDF files
│   └── weather/           # Weather files
├── outputs/                # Output data
│   ├── results/           # Simulation results
│   └── logs/              # Log files
├── config/                 # Configuration files
│   ├── settings.yaml      # Main settings
│   └── energyplus_paths.yaml  # EnergyPlus paths
└── tests/                  # Test files
```

## Output Files Description

EnergyPlus generates several output files for each simulation. Here's a description of each file type:

### Status and Control Files
- **`.end`**: Simulation completion status and summary statistics
- **`.audit`**: Simulation audit information including variable counts and memory usage
- **`.err`**: Error and warning messages generated during simulation
- **`.rvaudit`**: Read variables audit information

### Data Output Files
- **`.csv`**: Main output file containing all hourly time series data (largest file)
- **`.eso`**: EnergyPlus Standard Output file with detailed simulation results
- **`.mtr.csv`**: Energy meter data in CSV format
- **`.mtr`**: Energy meter data in binary format

### Metadata and Reference Files
- **`.rdd`**: Report Data Dictionary - lists all available output variables
- **`.mdd`**: Meter Data Dictionary - lists all available energy meters
- **`.edd`**: EnergyPlus Data Dictionary - comprehensive data dictionary
- **`.eio`**: EnergyPlus Input Output - processed input data summary
- **`.bnd`**: Boundary conditions and HVAC system connections
- **`.mtd`**: Meter details and energy consumption breakdown

### Report Files
- **`.tbl.htm`**: HTML report with annual building performance summary
- **`.tbl.tab`**: Tabular report in text format with key performance metrics

### Visualization Files
- **`.dxf`**: AutoCAD DXF file for 3D building visualization
- **`.shd`**: Shading data for solar analysis and visualization

### File Sizes and Usage
- **Large files** (1GB+): `.csv`, `.eso` - contain detailed time series data
- **Medium files** (50-100MB): `.mtr.csv`, `.mtr` - energy consumption data
- **Small files** (<1MB): Status, metadata, and report files

### Typical Analysis Workflow
1. Check `.end` file for simulation success
2. Review `.err` file for warnings and errors
3. Use `.tbl.htm` for quick performance overview
4. Analyze `.csv` file for detailed time series analysis
5. Use `.rdd` to understand available output variables

## Thermal Analysis Variables

When exporting thermal data for building performance analysis, the following variables are available:

### Core Thermal Variables
- **Date/Time**: Timestamp of the simulation data point (typically hourly)
- **Operative Temperature**: Average of air temperature and mean radiant temperature, representing the actual thermal sensation experienced by occupants
- **Air Temperature**: Temperature of the air within the zone (in Celsius)
- **Relative Humidity**: Percentage of moisture in the air relative to the maximum possible at that temperature
- **Outdoor Dry Bulb Temperature**: External air temperature measured in the shade (in Celsius)
- **Outdoor Dewpoint Temperature**: External air temperature at which condensation occurs, indicating moisture content (in Celsius)

### Occupancy and Usage
- **Occupancy**: Number of people present in the zone at each time step
- **Zone**: Name of the thermal zone being analyzed

### Variable Descriptions
- **Operative Temperature**: This is the most important thermal comfort parameter as it combines both air temperature and radiant temperature effects. It represents the temperature that occupants actually "feel" and is used for thermal comfort analysis.
- **Air Temperature**: The temperature of the air mass within the zone, measured at a standard height (usually 1.1m above floor level).
- **Relative Humidity**: Indicates the moisture content of the air. Values between 30-70% are generally considered comfortable for most people.
- **Outdoor Dry Bulb Temperature**: The external temperature that affects the building's thermal loads and energy consumption.
- **Outdoor Dewpoint Temperature**: The external temperature at which water vapor condenses, indicating the moisture content of outdoor air. Used for condensation analysis and humidity control.
- **Occupancy**: The number of people in the zone affects internal heat gains, ventilation requirements, and thermal comfort.
- **Zone**: Identifies which specific thermal zone the data refers to, allowing analysis of different building areas separately.

### Typical Use Cases
- **Thermal Comfort Analysis**: Using operative temperature and relative humidity to assess comfort conditions
- **Energy Performance**: Analyzing temperature differences between zones and outdoor conditions
- **Occupancy Impact**: Understanding how occupancy affects thermal conditions
- **HVAC Sizing**: Using peak temperatures and occupancy patterns for system design
- **Building Diagnostics**: Identifying thermal issues and performance problems
- **Condensation Analysis**: Using dewpoint temperature to assess condensation risk and humidity control
- **Humidity Control**: Analyzing outdoor dewpoint vs indoor conditions for moisture management

## Export Command

The `export` command allows you to extract and export specific thermal data from EnergyPlus simulation results into a unified CSV file.

### Basic Usage

```bash
# Export all thermal data from simulation results
energyplus-sim export thermal_data.csv

# Specify the source CSV file
energyplus-sim export thermal_data.csv --csv-file "path/to/simulation_results.csv"
```

### Zone Filtering

```bash
# Export data for specific zones only
energyplus-sim export thermal_data.csv --zones "ZONE1" "ZONE2"

# Export data for a single zone
energyplus-sim export thermal_data.csv --zones "0XPLANTABAJA:ZONA4"
```

### Date Range Filtering

```bash
# Export data for specific date range
energyplus-sim export thermal_data.csv --start-date "01/01" --end-date "12/31"

# Export data for a specific month
energyplus-sim export thermal_data.csv --start-date "06/01" --end-date "06/30"
```

### Output Options

```bash
# Show data summary before export
energyplus-sim export thermal_data.csv --summary

# Specify custom output directory
energyplus-sim export thermal_data.csv --output-dir "custom/path"
```

### Export Options

- `--csv-file`: Path to the EnergyPlus output CSV file (if not in default location)
- `--zones`: List of zone names to include in the export
- `--start-date`: Start date for data filtering (MM/DD format)
- `--end-date`: End date for data filtering (MM/DD format)
- `--summary`: Display data summary before export
- `--output-dir`: Custom output directory for the exported file

### Output Format

The exported CSV file contains the following columns:
- **Date/Time**: Timestamp of each data point
- **Operative_Temperature**: Calculated operative temperature (°C)
- **Occupancy**: Number of people in the zone
- **Outdoor_Dry_Bulb_Temperature**: External air temperature (°C)
- **Outdoor_Dewpoint_Temperature**: External dewpoint temperature (°C)
- **Air_Temperature**: Zone air temperature (°C)
- **Relative_Humidity**: Zone relative humidity (%)
- **Zone**: Name of the thermal zone

### Examples

```bash
# Export all thermal data with summary
energyplus-sim export thermal_data.csv --summary

# Export specific zones for summer months
energyplus-sim export summer_data.csv --zones "OFFICE1" "OFFICE2" --start-date "06/01" --end-date "08/31"

# Export single zone data
energyplus-sim export zone4_data.csv --zones "0XPLANTABAJA:ZONA4"
```

## Columns Command

The `columns` command allows you to explore and filter column headers from EnergyPlus simulation output CSV files, making it easier to find specific variables and zones.

### Basic Usage

```bash
# Show all column headers
energyplus-sim columns simulation_results.csv

# Show columns in table format
energyplus-sim columns simulation_results.csv --format table
```

### Zone Filtering

```bash
# Filter columns by specific zone
energyplus-sim columns simulation_results.csv --zone "0XPLANTABAJA:ZONA4"

# Show all available zones
energyplus-sim columns simulation_results.csv --zones
```

### Pattern Search

```bash
# Search for columns containing specific text
energyplus-sim columns simulation_results.csv --pattern "Temperature"

# Search for humidity-related columns
energyplus-sim columns simulation_results.csv --pattern "Humidity"

# Interactive search
energyplus-sim columns simulation_results.csv --search "Solar"
```

### Variable Type Grouping

```bash
# Group columns by variable type
energyplus-sim columns simulation_results.csv --types
```

### Output Control

```bash
# Limit number of results
energyplus-sim columns simulation_results.csv --zone "ZONE1" --limit 10

# Combine filters
energyplus-sim columns simulation_results.csv --pattern "Temperature" --limit 5 --format table
```

### Column Options

- `--zone ZONE_NAME`: Filter columns by zone name (e.g., "0XPLANTABAJA:ZONA4")
- `--pattern PATTERN`: Filter columns by text pattern (e.g., "Temperature", "Humidity")
- `--limit N`: Maximum number of columns to display
- `--format [list|table]`: Output format (default: list)
- `--zones`: Show all available zones in the CSV file
- `--types`: Group columns by variable type (Temperature, Humidity, Energy, etc.)
- `--search QUERY`: Interactive search for columns containing the query string

### Features

- **Zone Discovery**: Automatically extract and list all unique zones from column headers
- **Pattern Matching**: Case-insensitive search for columns containing specific text patterns
- **Variable Categorization**: Group columns by type (Temperature, Humidity, Energy, Solar, etc.)
- **Efficient Processing**: Read only header row for fast processing of large CSV files
- **Flexible Output**: Support for both list and table output formats
- **Interactive Search**: Real-time search functionality for exploring large datasets

### Examples

```bash
# Find all temperature columns for a specific zone
energyplus-sim columns results.csv --zone "0XPLANTABAJA:ZONA4" --pattern "Temperature"

# Discover all available zones
energyplus-sim columns results.csv --zones

# Group all columns by variable type
energyplus-sim columns results.csv --types

# Search for energy-related columns
energyplus-sim columns results.csv --search "Energy" --limit 20
```

## Indicators Command

The `indicators` command calculates thermal comfort indicators from exported thermal data, providing comprehensive analysis of building thermal performance.

### Basic Usage

```bash
# Calculate all thermal comfort indicators
energyplus-sim indicators thermal_data.csv --simulation "Baseline_TMY2020s"

# Calculate specific indicators only
energyplus-sim indicators thermal_data.csv --indicators "IOD,AWD,HI"

# Specify custom output file
energyplus-sim indicators thermal_data.csv --output "my_indicators.csv"
```

### Available Indicators

- **IOD**: Indoor Overheating Degree - Average excess temperature above comfort during occupied hours
- **AWD**: Ambient Warmness Degree - Average excess ambient temperature above base temperature
- **ALPHA**: Overheating Escalator Factor - Ratio of indoor to ambient overheating (IOD/AWD)
- **HI**: Heat Index - Apparent temperature considering humidity effects
- **DDH**: Degree-weighted Discomfort Hours - Thermal discomfort weighted by intensity using adaptive comfort model
- **DI**: Discomfort Index - Outdoor thermal comfort assessment combining temperature and humidity

### Configuration Options

```bash
# Custom comfort temperature for IOD calculation
energyplus-sim indicators thermal_data.csv --comfort-temp 25.0

# Custom base temperature for AWD calculation
energyplus-sim indicators thermal_data.csv --base-temp 20.0

# Custom simulation name
energyplus-sim indicators thermal_data.csv --simulation "My_Simulation_2024"
```

### Indicator Options

- `--output, -o`: Output CSV file path (default: input_file_indicators.csv)
- `--simulation, -s`: Simulation name for output (default: "Simulation")
- `--indicators, -i`: Comma-separated list of indicators to calculate (IOD,AWD,ALPHA,HI,DDH,DI)
- `--comfort-temp`: Comfort temperature for IOD calculation (default: 26.5°C)
- `--base-temp`: Base outside temperature for AWD calculation (default: 18.0°C)

### Output Format

The indicators CSV file contains the following columns:
- **DateTime**: Timestamp of each data point
- **Zone**: Name of the thermal zone
- **Value**: Calculated indicator value
- **Simulation**: Name of the simulation
- **Indicator**: Type of indicator (IOD, AWD, ALPHA, HI, DDH, DI)

### Examples

```bash
# Calculate all indicators for baseline simulation
energyplus-sim indicators baseline_data.csv --simulation "Baseline_TMY2020s"

# Calculate only overheating indicators
energyplus-sim indicators data.csv --indicators "IOD,AWD,ALPHA"

# Calculate with custom thermal parameters
energyplus-sim indicators data.csv --comfort-temp 24.0 --base-temp 19.0

# Calculate specific indicators with custom output
energyplus-sim indicators data.csv --indicators "HI,DI" --output "comfort_analysis.csv"
```

### Thermal Comfort Analysis

The indicators provide comprehensive thermal comfort analysis:

- **IOD**: Quantifies indoor overheating during occupied periods
- **AWD**: Measures environmental thermal stress
- **ALPHA**: Evaluates building thermal performance (lower is better)
- **HI**: Assesses apparent temperature with humidity effects
- **DDH**: Uses adaptive comfort model for naturally ventilated buildings
- **DI**: Evaluates outdoor thermal comfort conditions

### Use Cases

- **Building Performance Assessment**: Evaluate thermal comfort across different scenarios
- **Climate Adaptation Analysis**: Compare performance under different climate conditions
- **HVAC System Design**: Use indicators for system sizing and optimization
- **Comfort Standards Compliance**: Verify compliance with thermal comfort standards
- **Research and Development**: Support academic and professional research

## Requirements

- Python 3.8+
- EnergyPlus (9.0.0 or later)
- Click 8.0.0+
- PyYAML 6.0+
- eppy 0.5.60+ (for IDF file analysis)
- pandas 1.5.0+ (for data processing)
- tabulate 0.9.0+ (for formatted output)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

