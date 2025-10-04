"""
IDF file analysis module for ClimaMetrics.

This module provides functionality to analyze EnergyPlus IDF files and extract
relevant information about buildings, zones, materials, and HVAC systems.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import json
import csv
import yaml
from tabulate import tabulate

try:
    from eppy import modeleditor
    from eppy.modeleditor import IDF
    from eppy.bunch_subclass import EpBunch
except ImportError:
    raise ImportError("eppy is required for IDF analysis. Install with: pip install eppy")


class IDFAnalyzer:
    """Analyzer for EnergyPlus IDF files."""
    
    def __init__(self, idf_file: Path):
        """
        Initialize IDF analyzer.
        
        Args:
            idf_file: Path to IDF file to analyze
        """
        self.logger = logging.getLogger("climametrics.idf_analyzer")
        self.idf_file = Path(idf_file)
        
        if not self.idf_file.exists():
            raise FileNotFoundError(f"IDF file not found: {self.idf_file}")
        
        if not self.idf_file.suffix.lower() == '.idf':
            raise ValueError(f"File must be an IDF file: {self.idf_file}")
        
        # Initialize IDF object
        try:
            # Set IDD file path (EnergyPlus Input Data Dictionary)
            idd_file = self._find_idd_file()
            if idd_file:
                IDF.setiddname(str(idd_file))
                self.logger.info(f"Using IDD file: {idd_file}")
            else:
                self.logger.warning("IDD file not found, using default")
            
            self.idf = IDF(str(self.idf_file))
            self.logger.info(f"Successfully loaded IDF file: {self.idf_file}")
        except Exception as e:
            raise ValueError(f"Failed to load IDF file: {e}")
    
    def _find_idd_file(self) -> Optional[Path]:
        """
        Find EnergyPlus IDD file.
        
        Returns:
            Path to IDD file or None if not found
        """
        # Common IDD file locations
        idd_locations = [
            # "/Applications/EnergyPlus-25-1-0/Energy+.idd",
            # "/Applications/EnergyPlus-23-1-0/Energy+.idd",
            # "/Applications/EnergyPlus-9-4-0/Energy+.idd",
            # "/usr/local/EnergyPlus-25-1-0/Energy+.idd",
            # "/usr/local/EnergyPlus-23-1-0/Energy+.idd",
            # "/usr/local/EnergyPlus-9-4-0/Energy+.idd",
            # "/opt/EnergyPlus-25-1-0/Energy+.idd",
            # "/opt/EnergyPlus-23-1-0/Energy+.idd",
            # "/opt/EnergyPlus-9-4-0/Energy+.idd",
            "/Applications/EnergyPlus-9-4-0/Energy+.idd"
        ]
        
        for idd_path in idd_locations:
            if Path(idd_path).exists():
                return Path(idd_path)
        
        return None
    
    def analyze_building(self) -> Dict[str, Any]:
        """
        Analyze building information.
        
        Returns:
            Dictionary with building information
        """
        self.logger.debug("Analyzing building information")
        
        building_info = {
            'file': str(self.idf_file),
            'building': {},
            'location': {},
            'orientation': {}
        }
        
        try:
            # Get building object
            buildings = self.idf.idfobjects['Building']
            if buildings:
                building = buildings[0]
                building_info['building'] = {
                    'name': getattr(building, 'Name', 'Unknown'),
                    'terrain': getattr(building, 'Terrain', 'Unknown'),
                    'loads_convergence_tolerance_value': getattr(building, 'Loads_Convergence_Tolerance_Value', 'Unknown'),
                    'temperature_convergence_tolerance_value': getattr(building, 'Temperature_Convergence_Tolerance_Value', 'Unknown'),
                    'solar_distribution': getattr(building, 'Solar_Distribution', 'Unknown'),
                    'maximum_number_of_warmup_days': getattr(building, 'Maximum_Number_of_Warmup_Days', 'Unknown'),
                    'minimum_number_of_warmup_days': getattr(building, 'Minimum_Number_of_Warmup_Days', 'Unknown')
                }
            
            # Get location information
            locations = self.idf.idfobjects['Site:Location']
            if locations:
                location = locations[0]
                building_info['location'] = {
                    'name': getattr(location, 'Name', 'Unknown'),
                    'latitude': getattr(location, 'Latitude', 'Unknown'),
                    'longitude': getattr(location, 'Longitude', 'Unknown'),
                    'time_zone': getattr(location, 'Time_Zone', 'Unknown'),
                    'elevation': getattr(location, 'Elevation', 'Unknown')
                }
            
            # Get orientation information
            orientations = self.idf.idfobjects['GlobalGeometryRules']
            if orientations:
                orientation = orientations[0]
                building_info['orientation'] = {
                    'starting_vertex_position': getattr(orientation, 'Starting_Vertex_Position', 'Unknown'),
                    'vertex_entry_direction': getattr(orientation, 'Vertex_Entry_Direction', 'Unknown'),
                    'coordinate_system': getattr(orientation, 'Coordinate_System', 'Unknown'),
                    'daylighting_reference_point_coordinate_system': getattr(orientation, 'Daylighting_Reference_Point_Coordinate_System', 'Unknown'),
                    'rectangular_surface_coordinate_system': getattr(orientation, 'Rectangular_Surface_Coordinate_System', 'Unknown')
                }
            
        except Exception as e:
            self.logger.error(f"Error analyzing building: {e}")
            building_info['error'] = str(e)
        
        return building_info
    
    def analyze_zones(self) -> List[Dict[str, Any]]:
        """
        Analyze zone information.
        
        Returns:
            List of dictionaries with zone information
        """
        self.logger.debug("Analyzing zone information")
        
        zones_info = []
        
        try:
            zones = self.idf.idfobjects['Zone']
            for zone in zones:
                zone_data = {
                    'name': getattr(zone, 'Name', 'Unknown'),
                    'direction_of_relative_north': getattr(zone, 'Direction_of_Relative_North', 'Unknown'),
                    'x_origin': getattr(zone, 'X_Origin', 'Unknown'),
                    'y_origin': getattr(zone, 'Y_Origin', 'Unknown'),
                    'z_origin': getattr(zone, 'Z_Origin', 'Unknown'),
                    'type': getattr(zone, 'Type', 'Unknown'),
                    'multiplier': getattr(zone, 'Multiplier', 1),
                    'list_multiplier': getattr(zone, 'List_Multiplier', 1),
                    'minimum_x_coordinate': getattr(zone, 'Minimum_X_Coordinate', 'Unknown'),
                    'maximum_x_coordinate': getattr(zone, 'Maximum_X_Coordinate', 'Unknown'),
                    'minimum_y_coordinate': getattr(zone, 'Minimum_Y_Coordinate', 'Unknown'),
                    'maximum_y_coordinate': getattr(zone, 'Maximum_Y_Coordinate', 'Unknown'),
                    'minimum_z_coordinate': getattr(zone, 'Minimum_Z_Coordinate', 'Unknown'),
                    'maximum_z_coordinate': getattr(zone, 'Maximum_Z_Coordinate', 'Unknown'),
                    'ceiling_height': getattr(zone, 'Ceiling_Height', 'Unknown'),
                    'volume': getattr(zone, 'Volume', 'Unknown'),
                    'floor_area': getattr(zone, 'Floor_Area', 'Unknown'),
                    'zone_inside_convection_algorithm': getattr(zone, 'Zone_Inside_Convection_Algorithm', 'Unknown'),
                    'zone_outside_convection_algorithm': getattr(zone, 'Zone_Outside_Convection_Algorithm', 'Unknown')
                }
                zones_info.append(zone_data)
        
        except Exception as e:
            self.logger.error(f"Error analyzing zones: {e}")
            zones_info.append({'error': str(e)})
        
        return zones_info
    
    def analyze_materials(self) -> List[Dict[str, Any]]:
        """
        Analyze material information.
        
        Returns:
            List of dictionaries with material information
        """
        self.logger.debug("Analyzing material information")
        
        materials_info = []
        
        try:
            # Get regular materials
            materials = self.idf.idfobjects['Material']
            for material in materials:
                material_data = {
                    'name': getattr(material, 'Name', 'Unknown'),
                    'type': 'Material',
                    'roughness': getattr(material, 'Roughness', 'Unknown'),
                    'thickness': getattr(material, 'Thickness', 'Unknown'),
                    'conductivity': getattr(material, 'Conductivity', 'Unknown'),
                    'density': getattr(material, 'Density', 'Unknown'),
                    'specific_heat': getattr(material, 'Specific_Heat', 'Unknown'),
                    'thermal_absorptance': getattr(material, 'Thermal_Absorptance', 'Unknown'),
                    'solar_absorptance': getattr(material, 'Solar_Absorptance', 'Unknown'),
                    'visible_absorptance': getattr(material, 'Visible_Absorptance', 'Unknown')
                }
                materials_info.append(material_data)
            
            # Get material:no mass
            no_mass_materials = self.idf.idfobjects['Material:NoMass']
            for material in no_mass_materials:
                material_data = {
                    'name': getattr(material, 'Name', 'Unknown'),
                    'type': 'Material:NoMass',
                    'roughness': getattr(material, 'Roughness', 'Unknown'),
                    'thermal_resistance': getattr(material, 'Thermal_Resistance', 'Unknown'),
                    'thermal_absorptance': getattr(material, 'Thermal_Absorptance', 'Unknown'),
                    'solar_absorptance': getattr(material, 'Solar_Absorptance', 'Unknown'),
                    'visible_absorptance': getattr(material, 'Visible_Absorptance', 'Unknown')
                }
                materials_info.append(material_data)
            
            # Get material:air gap
            air_gap_materials = self.idf.idfobjects['Material:AirGap']
            for material in air_gap_materials:
                material_data = {
                    'name': getattr(material, 'Name', 'Unknown'),
                    'type': 'Material:AirGap',
                    'thermal_resistance': getattr(material, 'Thermal_Resistance', 'Unknown')
                }
                materials_info.append(material_data)
        
        except Exception as e:
            self.logger.error(f"Error analyzing materials: {e}")
            materials_info.append({'error': str(e)})
        
        return materials_info
    
    def analyze_hvac(self) -> Dict[str, Any]:
        """
        Analyze HVAC system information.
        
        Returns:
            Dictionary with HVAC system information
        """
        self.logger.debug("Analyzing HVAC system information")
        
        hvac_info = {
            'air_loops': [],
            'plant_loops': [],
            'zones_served': [],
            'equipment': []
        }
        
        try:
            # Get air loops
            air_loops = self.idf.idfobjects['AirLoopHVAC']
            for loop in air_loops:
                loop_data = {
                    'name': getattr(loop, 'Name', 'Unknown'),
                    'controller_list_name': getattr(loop, 'Controller_List_Name', 'Unknown'),
                    'availability_manager_list_name': getattr(loop, 'Availability_Manager_List_Name', 'Unknown'),
                    'design_supply_air_flow_rate': getattr(loop, 'Design_Supply_Air_Flow_Rate', 'Unknown'),
                    'branch_list_name': getattr(loop, 'Branch_List_Name', 'Unknown'),
                    'connector_list_name': getattr(loop, 'Connector_List_Name', 'Unknown'),
                    'supply_side_inlet_node_name': getattr(loop, 'Supply_Side_Inlet_Node_Name', 'Unknown'),
                    'demand_side_outlet_node_name': getattr(loop, 'Demand_Side_Outlet_Node_Name', 'Unknown'),
                    'demand_side_inlet_node_names': getattr(loop, 'Demand_Side_Inlet_Node_Names', 'Unknown'),
                    'supply_side_outlet_node_names': getattr(loop, 'Supply_Side_Outlet_Node_Names', 'Unknown')
                }
                hvac_info['air_loops'].append(loop_data)
            
            # Get plant loops
            plant_loops = self.idf.idfobjects['PlantLoop']
            for loop in plant_loops:
                loop_data = {
                    'name': getattr(loop, 'Name', 'Unknown'),
                    'fluid_type': getattr(loop, 'Fluid_Type', 'Unknown'),
                    'user_defined_fluid_type': getattr(loop, 'User_Defined_Fluid_Type', 'Unknown'),
                    'design_loop_flow_rate': getattr(loop, 'Design_Loop_Flow_Rate', 'Unknown'),
                    'loop_volume': getattr(loop, 'Loop_Volume', 'Unknown'),
                    'loop_side_inlet_node_name': getattr(loop, 'Loop_Side_Inlet_Node_Name', 'Unknown'),
                    'loop_side_outlet_node_name': getattr(loop, 'Loop_Side_Outlet_Node_Name', 'Unknown'),
                    'branch_list_name': getattr(loop, 'Branch_List_Name', 'Unknown'),
                    'connector_list_name': getattr(loop, 'Connector_List_Name', 'Unknown')
                }
                hvac_info['plant_loops'].append(loop_data)
            
            # Get zones served by HVAC
            zone_hvac_equipment = self.idf.idfobjects['ZoneHVAC:EquipmentConnections']
            for equipment in zone_hvac_equipment:
                equipment_data = {
                    'zone_name': getattr(equipment, 'Zone_Name', 'Unknown'),
                    'zone_conditioning_equipment_list_name': getattr(equipment, 'Zone_Conditioning_Equipment_List_Name', 'Unknown'),
                    'zone_air_inlet_node_or_nodelist_name': getattr(equipment, 'Zone_Air_Inlet_Node_or_NodeList_Name', 'Unknown'),
                    'zone_air_exhaust_node_or_nodelist_name': getattr(equipment, 'Zone_Air_Exhaust_Node_or_NodeList_Name', 'Unknown'),
                    'zone_air_node_name': getattr(equipment, 'Zone_Air_Node_Name', 'Unknown'),
                    'zone_return_air_node_or_nodelist_name': getattr(equipment, 'Zone_Return_Air_Node_or_NodeList_Name', 'Unknown')
                }
                hvac_info['zones_served'].append(equipment_data)
        
        except Exception as e:
            self.logger.error(f"Error analyzing HVAC: {e}")
            hvac_info['error'] = str(e)
        
        return hvac_info
    
    def analyze_all(self) -> Dict[str, Any]:
        """
        Analyze all available information.
        
        Returns:
            Dictionary with all analysis results
        """
        self.logger.info("Performing complete IDF analysis")
        
        return {
            'file': str(self.idf_file),
            'building': self.analyze_building(),
            'zones': self.analyze_zones(),
            'materials': self.analyze_materials(),
            'hvac': self.analyze_hvac()
        }
    
    def format_output(self, data: Union[Dict, List], format_type: str = 'table', 
                     sort_by: Optional[str] = None, filter_keyword: Optional[str] = None) -> str:
        """
        Format output data in specified format.
        
        Args:
            data: Data to format
            format_type: Output format (table, json, csv, yaml)
            sort_by: Field to sort by
            filter_keyword: Keyword to filter by
            
        Returns:
            Formatted string
        """
        # Apply filtering if specified
        if filter_keyword and isinstance(data, list):
            data = [item for item in data if any(
                str(value).lower().find(filter_keyword.lower()) != -1 
                for value in item.values() if isinstance(value, (str, int, float))
            )]
        
        # Apply sorting if specified
        if sort_by and isinstance(data, list) and data:
            if sort_by in data[0]:
                data = sorted(data, key=lambda x: x.get(sort_by, ''))
        
        if format_type == 'json':
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format_type == 'yaml':
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        elif format_type == 'csv' and isinstance(data, list) and data:
            if not data:
                return ""
            output = []
            output.append(','.join(data[0].keys()))
            for item in data:
                output.append(','.join(str(item.get(key, '')) for key in data[0].keys()))
            return '\n'.join(output)
        elif format_type == 'table' and isinstance(data, list) and data:
            if not data:
                return "No data available"
            headers = list(data[0].keys())
            rows = [list(item.values()) for item in data]
            return tabulate(rows, headers=headers, tablefmt='grid')
        else:
            return str(data)
    
    def save_output(self, data: Union[Dict, List], output_file: Path, 
                   format_type: str = 'json') -> None:
        """
        Save analysis results to file.
        
        Args:
            data: Data to save
            output_file: Output file path
            format_type: Output format
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format_type == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format_type == 'yaml':
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        elif format_type == 'csv' and isinstance(data, list) and data:
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        self.logger.info(f"Results saved to: {output_file}")
