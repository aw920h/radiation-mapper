# Radiation Zone Mapping & Shielding Tool

**Automated radiation zone classification and shielding design for particle accelerator facilities**

![Safety](https://img.shields.io/badge/Safety-Radiation%20Protection-red)
![Engineering](https://img.shields.io/badge/Engineering-Civil%20%26%20Environmental-orange)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Project Overview

This tool automates the workflow between **Radiation Safety (HSE)** and **Civil Engineering (SMB)**. It processes raw detector data, classifies hazardous zones according to **CERN Safety Code F**, and calculates required concrete shielding thicknesses for facility remediation.


## Engineering Context

Particle accelerator facilities require strict separation between public and restricted areas.
*   **The Problem:** Radiation survey data is often static and disconnected from the Civil Engineering mitigation process (shielding design).
*   **The Solution:** This tool bridges the gap by automating the detection of hotspots and immediately calculating the **Concrete Shielding Thickness** required to declassify the area.

---

## Key Features

### Civil Engineering & Safety
- **Shielding Calculator**: Integrated Linear Attenuation logic to calculate wall thickness (Concrete, Lead, Steel).
- **Compliance Automation**: Auto-classifies zones based on CERN Safety Code F & IAEA BSS.
- **Safety-First Algorithms**: Utilizes conservative peak-detection interpolation to prevent under-reporting of hazards.

### Data & Visualization
- **Real-World Validation**: Validated against environmental monitoring data (Safecast API).
- **Spatial Mapping**: Generates continuous contour maps from sparse sensor points.
- **Exportable Reports**: Generates actionable compliance reports for Facility Management.

---

## Real-World Validation: Fukushima Exclusion Zone

To validate the tool against non-simulated, hazardous data, I developed a custom API harvester to pull live environmental monitoring data from **Route 6 (Fukushima Exclusion Zone)**.

### Validation Experiment
*   **Data Source:** Safecast API (Live sensor tracks).
*   **Location:** Lat 37.40, Lon 141.01 (Tomiobka/Futaba Region).
*   **Scenario:** Linear infrastructure survey of a contaminated transport corridor.

### Results
The tool successfully identified and classified real-world "Restricted Areas" (> 25 µSv/hr) amidst environmental background noise.


![Fukushima Validation Map](./result/radiation_zone_map.png)


**Key Findings:**
*   **Max Detected Dose:** ~32.07 µSv/hr (Correctly classified as 🔴 Restricted).
*   **Pattern Recognition:** Algorithm correctly visualized the linear contamination path along the roadway.

[**View the Raw Validation Data (CSV)**](./result/real_fukushima_route6.csv)

---

## 📊 Sample Output Examples

### 1. Radiation Zone Map (Simulated Beamline)
![Zone Map Example](./examples/zone_map_example.png)

### 2. Shielding Calculation (Civil Engineering)
```text
INPUT:
  Source Dose: 100.9 µSv/hr (Hotspot)
  Target Zone: Public (< 0.5 µSv/hr)
  Material:    Concrete (Density ~2.35 g/cm3)

OUTPUT:
  Required Thickness: 35.4 cm
  Action: Construct 40cm shielding wall or restrict access.
```

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/radiation-zone-mapper.git
cd radiation-zone-mapper

# Install dependencies
pip install -r requirements.txt
```

### Running the Tool

**1. Launch the Web Interface (Recommended)**
```bash
streamlit run app.py
```

**2. Harvest Real Validation Data**
```bash
python fetch_big_data.py
# This pulls live data from Fukushima to test the system
```

---

## Technical Methodology

### Zone Classification Standards (CERN Code F)

| Zone | Dose Rate (µSv/hr) | Engineering Controls Required |
|------|-------------------|-------------------------------|
| 🟢 Public | < 0.5 | None |
| 🟡 Supervised | 0.5 - 7.5 | Radiological Monitoring |
| 🟠 Controlled | 7.5 - 25 | Dosimetry, Access Control |
| 🔴 Restricted | > 25 | **Physical Barriers / Shielding** |

### Shielding Logic
The tool calculates required thickness ($x$) using the attenuation formula:
$$I = I_0 e^{-\mu x}$$
Where $\mu$ is the linear attenuation coefficient for the selected material (Concrete/Steel/Lead).
