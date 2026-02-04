"""
Radiation Zone Mapping and Visualization Tool
For particle accelerator facilities and research laboratories

This tool automates radiation zone classification according to CERN Safety Code F
and IAEA Basic Safety Standards (BSS).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class RadiationZoneMapper:
    """
    Radiation zone classification and visualization tool
    
    Implements CERN/IAEA standards for radiation area classification:
    - Public Area: < 0.5 µSv/hr
    - Supervised Area: 0.5 - 7.5 µSv/hr
    - Controlled Area: 7.5 - 25 µSv/hr
    - Restricted Area: > 25 µSv/hr
    
    References:
    - CERN Safety Code F: Radiation Protection
    - IAEA Safety Standards Series No. GSR Part 3
    """
    
    def __init__(self, standard='CERN'):
        """
        Initialize mapper with regulatory standard
        
        Parameters:
        -----------
        standard : str
            'CERN' or 'IAEA' (both use same limits currently)
        """
        self.standard = standard
        
        self.zone_limits = {
            'Public': 0.5,
            'Supervised': 7.5,
            'Controlled': 25,
            'Restricted': float('inf')
        }
        
        # Color scheme for visualization
        self.zone_colors = {
            'Public': '#2ECC71',        # Green
            'Supervised': '#F1C40F',    # Yellow
            'Controlled': '#E67E22',    # Orange
            'Restricted': '#E74C3C'     # Red
        }
        
        self.annual_limits = {
            'Public': 1.0,
            'Worker': 20.0,
            'Apprentice': 6.0
        }
        
    def classify_zone(self, dose_rate):
        """
        Classify radiation zone based on dose rate
        
        Parameters:
        -----------
        dose_rate : float
            Dose rate in µSv/hr
            
        Returns:
        --------
        tuple : (zone_name, color_code)
        """
        if dose_rate < self.zone_limits['Public']:
            return 'Public', self.zone_colors['Public']
        elif dose_rate < self.zone_limits['Supervised']:
            return 'Supervised', self.zone_colors['Supervised']
        elif dose_rate < self.zone_limits['Controlled']:
            return 'Controlled', self.zone_colors['Controlled']
        else:
            return 'Restricted', self.zone_colors['Restricted']
    
    def calculate_annual_dose(self, dose_rate, occupancy_hours=2000):
        """
        Calculate annual dose from dose rate
        
        Parameters:
        -----------
        dose_rate : float
            Dose rate in µSv/hr
        occupancy_hours : int
            Hours per year in area (default: 2000 = full-time worker)
            
        Returns:
        --------
        float : Annual dose in mSv/year
        """
        return (dose_rate * occupancy_hours) / 1000  
    
    def create_interpolated_map(self, measurements_df, method='cubic', 
                                resolution=200, buffer_distance=5):
        """
        Create interpolated dose rate map from point measurements
        
        Parameters:
        -----------
        measurements_df : pd.DataFrame
            Must contain columns: 'x', 'y', 'dose_rate'
        method : str
            Interpolation method: 'linear', 'cubic', 'nearest'
        resolution : int
            Grid resolution for interpolation
        buffer_distance : float
            Distance (m) to extend beyond measurement points
            
        Returns:
        --------
        tuple : (grid_x, grid_y, grid_dose)
        """
        points = measurements_df[['x', 'y']].values
        values = measurements_df['dose_rate'].values
        
        x_min, x_max = points[:, 0].min() - buffer_distance, points[:, 0].max() + buffer_distance
        y_min, y_max = points[:, 1].min() - buffer_distance, points[:, 1].max() + buffer_distance
        
        grid_x, grid_y = np.mgrid[
            x_min:x_max:complex(0, resolution),
            y_min:y_max:complex(0, resolution)
        ]
        
        grid_dose = griddata(points, values, (grid_x, grid_y), method=method)
        
        if np.isnan(grid_dose).any():
            mask = np.isnan(grid_dose)
            grid_dose_nearest = griddata(points, values, (grid_x, grid_y), method='nearest')
            grid_dose[mask] = grid_dose_nearest[mask]
        
        return grid_x, grid_y, grid_dose
    
    def plot_zone_map(self, measurements_df, area_name='Experimental Area',
                     show_measurements=True, show_grid=True, 
                     add_buffer_zones=True, figsize=(14, 10)):
        """
        Create comprehensive radiation zone map
        
        Parameters:
        -----------
        measurements_df : pd.DataFrame
            Measurement data with 'x', 'y', 'dose_rate' columns
        area_name : str
            Name of the area being surveyed
        show_measurements : bool
            Display measurement points on map
        show_grid : bool
            Show coordinate grid
        add_buffer_zones : bool
            Add 2m buffer zones around restricted areas
        figsize : tuple
            Figure size (width, height)
            
        Returns:
        --------
        matplotlib.figure.Figure
        """
        grid_x, grid_y, grid_dose = self.create_interpolated_map(measurements_df)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        levels = [0, 
                 self.zone_limits['Public'], 
                 self.zone_limits['Supervised'], 
                 self.zone_limits['Controlled'], 
                 grid_dose.max() * 1.1]
        
        colors = [self.zone_colors['Public'],
                 self.zone_colors['Supervised'],
                 self.zone_colors['Controlled'],
                 self.zone_colors['Restricted']]
        
        contourf = ax.contourf(grid_x, grid_y, grid_dose, 
                              levels=levels, colors=colors, alpha=0.7)
        
        contour_lines = ax.contour(grid_x, grid_y, grid_dose, 
                                   levels=levels[1:], colors='black', 
                                   linewidths=1.5, alpha=0.5)
        ax.clabel(contour_lines, inline=True, fontsize=9, fmt='%.1f µSv/hr')
        
        if show_measurements:
            scatter = ax.scatter(measurements_df['x'], measurements_df['y'], 
                               c=measurements_df['dose_rate'], 
                               s=150, edgecolors='black', linewidth=2,
                               cmap='RdYlGn_r', vmin=0, vmax=levels[-1],
                               marker='o', zorder=10, alpha=0.9)
            
            for idx, row in measurements_df.iterrows():
                ax.annotate(f"{row['dose_rate']:.1f}", 
                          (row['x'], row['y']),
                          xytext=(5, 5), textcoords='offset points',
                          fontsize=8, fontweight='bold',
                          bbox=dict(boxstyle='round,pad=0.3', 
                                  facecolor='white', alpha=0.7))
        
        if add_buffer_zones:
            restricted_mask = grid_dose > self.zone_limits['Controlled']
            if restricted_mask.any():
                ax.contour(grid_x, grid_y, restricted_mask, 
                          levels=[0.5], colors='red', 
                          linewidths=3, linestyles='--',
                          label='Restricted Area Boundary')
        
        ax.set_xlabel('X Position (meters)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Y Position (meters)', fontsize=13, fontweight='bold')
        ax.set_title(f'Radiation Zone Classification Map\n{area_name}\n' + 
                    f'Survey Date: {datetime.now().strftime("%Y-%m-%d")}',
                    fontsize=15, fontweight='bold', pad=20)
        
        cbar = plt.colorbar(scatter if show_measurements else contourf, 
                           ax=ax, pad=0.02)
        cbar.set_label('Dose Rate (µSv/hr)', fontsize=12, fontweight='bold')
        
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=self.zone_colors['Public'], 
                 edgecolor='black', label=f"Public Area (< {self.zone_limits['Public']} µSv/hr)"),
            Patch(facecolor=self.zone_colors['Supervised'], 
                 edgecolor='black', label=f"Supervised ({self.zone_limits['Public']}-{self.zone_limits['Supervised']} µSv/hr)"),
            Patch(facecolor=self.zone_colors['Controlled'], 
                 edgecolor='black', label=f"Controlled ({self.zone_limits['Supervised']}-{self.zone_limits['Controlled']} µSv/hr)"),
            Patch(facecolor=self.zone_colors['Restricted'], 
                 edgecolor='black', label=f"Restricted (> {self.zone_limits['Controlled']} µSv/hr)")
        ]
        
        ax.legend(handles=legend_elements, loc='upper left', 
                 fontsize=10, framealpha=0.9, title='Zone Classification',
                 title_fontsize=11)
        
        if show_grid:
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        return fig
        
    def calculate_shielding_required(self, current_dose, target_dose, material='concrete'):
        """
        Calculates required shielding thickness using: I = I0 * e^(-mu * x)
        Rearranged: x = -ln(I / I0) / mu
        """
        if current_dose <= target_dose:
            return 0.0, "No shielding needed"
            
        mu_values = {
            'concrete': 0.15,
            'lead': 0.55,
            'steel': 0.30
        }
        
        mu = mu_values.get(material.lower(), 0.15)
        
        thickness = -np.log(target_dose / current_dose) / mu
        return thickness
    
    def generate_compliance_report(self, measurements_df, area_name='Experimental Area',
                                   occupancy_hours=2000):
        """
        Generate detailed compliance report
        
        Parameters:
        -----------
        measurements_df : pd.DataFrame
            Measurement data
        area_name : str
            Name of surveyed area
        occupancy_hours : int
            Annual occupancy hours for dose calculation
            
        Returns:
        --------
        str : Formatted compliance report
        """
        report = []
        report.append("=" * 70)
        report.append("RADIATION ZONE CLASSIFICATION REPORT")
        report.append("=" * 70)
        report.append(f"\nArea: {area_name}")
        report.append(f"Survey Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"Standard: {self.standard} Safety Code")
        report.append(f"Total Measurement Points: {len(measurements_df)}")
        report.append("\n" + "-" * 70)
        report.append("ZONE STATISTICS")
        report.append("-" * 70)
        
        zone_stats = {}
        for zone_name, limit in self.zone_limits.items():
            if zone_name == 'Public':
                count = len(measurements_df[measurements_df['dose_rate'] < limit])
                area_points = measurements_df[measurements_df['dose_rate'] < limit]
            elif zone_name == 'Supervised':
                count = len(measurements_df[(measurements_df['dose_rate'] >= self.zone_limits['Public']) & 
                                           (measurements_df['dose_rate'] < limit)])
                area_points = measurements_df[(measurements_df['dose_rate'] >= self.zone_limits['Public']) & 
                                             (measurements_df['dose_rate'] < limit)]
            elif zone_name == 'Controlled':
                count = len(measurements_df[(measurements_df['dose_rate'] >= self.zone_limits['Supervised']) & 
                                           (measurements_df['dose_rate'] < limit)])
                area_points = measurements_df[(measurements_df['dose_rate'] >= self.zone_limits['Supervised']) & 
                                             (measurements_df['dose_rate'] < limit)]
            else:  # Restricted
                count = len(measurements_df[measurements_df['dose_rate'] >= self.zone_limits['Controlled']])
                area_points = measurements_df[measurements_df['dose_rate'] >= self.zone_limits['Controlled']]
            
            percentage = (count / len(measurements_df)) * 100
            zone_stats[zone_name] = {
                'count': count,
                'percentage': percentage,
                'points': area_points
            }
            
            report.append(f"\n{zone_name} Area:")
            report.append(f"  Measurement Points: {count} ({percentage:.1f}%)")
            if len(area_points) > 0:
                report.append(f"  Dose Rate Range: {area_points['dose_rate'].min():.2f} - {area_points['dose_rate'].max():.2f} µSv/hr")
                report.append(f"  Mean Dose Rate: {area_points['dose_rate'].mean():.2f} µSv/hr")
        
        report.append("\n" + "-" * 70)
        report.append("OVERALL STATISTICS")
        report.append("-" * 70)
        report.append(f"Maximum Dose Rate: {measurements_df['dose_rate'].max():.2f} µSv/hr")
        report.append(f"Minimum Dose Rate: {measurements_df['dose_rate'].min():.2f} µSv/hr")
        report.append(f"Mean Dose Rate: {measurements_df['dose_rate'].mean():.2f} µSv/hr")
        report.append(f"Median Dose Rate: {measurements_df['dose_rate'].median():.2f} µSv/hr")
        report.append(f"Standard Deviation: {measurements_df['dose_rate'].std():.2f} µSv/hr")
        
        report.append("\n" + "-" * 70)
        report.append("ANNUAL DOSE PROJECTIONS")
        report.append("-" * 70)
        report.append(f"Occupancy Assumption: {occupancy_hours} hours/year")
        
        max_dose_rate = measurements_df['dose_rate'].max()
        mean_dose_rate = measurements_df['dose_rate'].mean()
        
        max_annual = self.calculate_annual_dose(max_dose_rate, occupancy_hours)
        mean_annual = self.calculate_annual_dose(mean_dose_rate, occupancy_hours)
        
        report.append(f"\nMaximum Annual Dose: {max_annual:.2f} mSv/year")
        report.append(f"  Worker Limit (20 mSv/year): {'EXCEEDED' if max_annual > 20 else 'OK'}")
        
        report.append(f"\nMean Annual Dose: {mean_annual:.2f} mSv/year")
        report.append(f"  Worker Limit (20 mSv/year): {'EXCEEDED' if mean_annual > 20 else 'OK'}")
        
        report.append("\n" + "-" * 70)
        report.append("COMPLIANCE ASSESSMENT")
        report.append("-" * 70)
        
        restricted_points = zone_stats['Restricted']['count']
        if restricted_points > 0:
            report.append(f"\n⚠ WARNING: {restricted_points} restricted area points detected")
            report.append("  Action Required:")
            report.append("  - Install physical barriers and access controls")
            report.append("  - Post radiation warning signs")
            report.append("  - Implement dosimetry requirements")
            report.append("  - Establish work permits for entry")
        
        controlled_points = zone_stats['Controlled']['count']
        if controlled_points > 0:
            report.append(f"\n⚠ CAUTION: {controlled_points} controlled area points detected")
            report.append("  Action Required:")
            report.append("  - Designate as controlled area")
            report.append("  - Implement access restrictions")
            report.append("  - Provide dosimetry for workers")
        
        supervised_points = zone_stats['Supervised']['count']
        if supervised_points > 0:
            report.append(f"\nℹ INFO: {supervised_points} supervised area points detected")
            report.append("  Action Required:")
            report.append("  - Designate as supervised area")
            report.append("  - Monitor access and occupancy")
        
        if restricted_points == 0 and controlled_points == 0 and supervised_points == 0:
            report.append("\n✓ All areas classified as Public - no special controls required")
        
        report.append("\n" + "=" * 70)
        report.append("END OF REPORT")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def export_zone_data(self, measurements_df, grid_x, grid_y, grid_dose, filename='zone_data.csv'):
        """
        Export zone classification data to CSV
        
        Parameters:
        -----------
        measurements_df : pd.DataFrame
            Original measurements
        grid_x, grid_y, grid_dose : np.ndarray
            Interpolated grid data
        filename : str
            Output filename
        """
        grid_data = pd.DataFrame({
            'x': grid_x.flatten(),
            'y': grid_y.flatten(),
            'dose_rate': grid_dose.flatten()
        })
        
        grid_data['zone'] = grid_data['dose_rate'].apply(
            lambda x: self.classify_zone(x)[0]
        )
        
        grid_data.to_csv(filename, index=False)
        print(f"Zone data exported to {filename}")
        
        return grid_data


def create_sample_data(scenario='beamline_hotspot'):
    """
    Create realistic sample data for different radiation scenarios
    
    Parameters:
    -----------
    scenario : str
        'beamline_hotspot', 'uniform_low', 'scattered_sources', 'shielding_test'
    
    Returns:
    --------
    pd.DataFrame : Sample measurement data
    """
    np.random.seed(42)
    
    if scenario == 'beamline_hotspot':
        n_points = 60
        
        x_coords = []
        y_coords = []
        dose_rates = []
        
        hotspot_x, hotspot_y = 25, 15
        hotspot_intensity = 800
        
        for x in np.linspace(0, 50, 12):
            for y in np.linspace(0, 30, 10):
                x_coords.append(x)
                y_coords.append(y)
                
                distance = np.sqrt((x - hotspot_x)**2 + (y - hotspot_y)**2)
                
                if distance < 0.5:
                    distance = 0.5  #Keeping sensible value
                
                dose = hotspot_intensity / (distance**2) + np.random.normal(0.2, 0.05)
                dose = max(0.05, dose)  
                
                dose_rates.append(dose)
        
        for _ in range(n_points - len(x_coords)):
            x = np.random.uniform(0, 50)
            y = np.random.uniform(0, 30)
            distance = np.sqrt((x - hotspot_x)**2 + (y - hotspot_y)**2)
            if distance < 0.5:
                distance = 0.5
            dose = hotspot_intensity / (distance**2) + np.random.normal(0.2, 0.05)
            dose = max(0.05, dose)
            
            x_coords.append(x)
            y_coords.append(y)
            dose_rates.append(dose)
    
    elif scenario == 'uniform_low':
        n_points = 40
        x_coords = np.random.uniform(0, 30, n_points)
        y_coords = np.random.uniform(0, 20, n_points)
        dose_rates = np.random.normal(0.3, 0.1, n_points)
        dose_rates = np.clip(dose_rates, 0.1, 0.5)
    
    elif scenario == 'scattered_sources':
        n_points = 80
        x_coords = []
        y_coords = []
        dose_rates = []
        
        sources = [
            (10, 10, 50),  
            (30, 15, 80),
            (20, 25, 120)
        ]
        
        for _ in range(n_points):
            x = np.random.uniform(0, 40)
            y = np.random.uniform(0, 35)
            
            dose = 0.15  
            for sx, sy, intensity in sources:
                distance = np.sqrt((x - sx)**2 + (y - sy)**2)
                if distance < 0.5:
                    distance = 0.5
                dose += intensity / (distance**2)
            
            dose += np.random.normal(0, 0.1)
            dose = max(0.1, dose)
            
            x_coords.append(x)
            y_coords.append(y)
            dose_rates.append(dose)
    
    else:  
        n_points = 50
        x_coords = np.linspace(0, 20, n_points)
        y_coords = np.random.uniform(0, 10, n_points)
        
        dose_rates = 100 * np.exp(-0.3 * x_coords) + np.random.normal(0, 0.5, n_points)
        dose_rates = np.clip(dose_rates, 0.1, 200)
    
    df = pd.DataFrame({
        'x': x_coords,
        'y': y_coords,
        'dose_rate': dose_rates
    })
    
    return df


import os

def get_next_result_dir(base_name="result"):
    """
    Finds the next available directory name (e.g., result-1, result-2)
    and creates it.
    """
    i = 1
    while True:
        dir_name = f"{base_name}-{i}"
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            return dir_name
        i += 1

if __name__ == "__main__":
    print("Radiation Zone Mapping Tool")
    print("=" * 50)
    
    output_dir = get_next_result_dir("result")
    print(f" Output directory created: {output_dir}/")

    mapper = RadiationZoneMapper(standard='CERN')
    
    print("\nGenerating sample data (beamline hotspot scenario)...")
    sample_data = create_sample_data(scenario='beamline_hotspot')
    
    sample_csv_path = os.path.join(output_dir, 'sample_measurements.csv')
    sample_data.to_csv(sample_csv_path, index=False)
    print(f"Sample data saved: {sample_csv_path}")
    
    print("\nCreating radiation zone map...")
    fig = mapper.plot_zone_map(
        sample_data, 
        area_name='CERN North Area - Beamline T9 (Simulated)',
        show_measurements=True,
        add_buffer_zones=True
    )
    
    map_path = os.path.join(output_dir, 'radiation_zone_map.png')
    fig.savefig(map_path, dpi=300, bbox_inches='tight')
    print(f"Map saved: {map_path}")
    
    print("\nGenerating compliance report...")
    report = mapper.generate_compliance_report(
        sample_data,
        area_name='CERN North Area - Beamline T9 (Simulated)',
        occupancy_hours=2000
    )
    
    report_path = os.path.join(output_dir, 'compliance_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved: {report_path}")
    
    grid_x, grid_y, grid_dose = mapper.create_interpolated_map(sample_data)
    
    zone_data_path = os.path.join(output_dir, 'zone_data.csv')
    mapper.export_zone_data(sample_data, grid_x, grid_y, grid_dose, filename=zone_data_path)
    
    print("\n" + "=" * 50)
    print("Processing complete!")
    print(f"All files have been saved to: ./{output_dir}/")
