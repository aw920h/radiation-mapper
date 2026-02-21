"""
mu_values.py
============
Photon Linear Attenuation Coefficient Reference Module

Source: NIST XCOM Photon Cross Sections Database
        https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html
        https://physics.nist.gov/PhysRefData/XrayMassCoef/tab4.html
        https://physics.nist.gov/PhysRefData/XrayMassCoef/tab1.html
        

Provides energy-dependent mu (cm^-1) for common radiation shielding materials
including conventional materials and bentonite slurry (novel low-cost option).

Usage:
    from mu_values import get_mu, MATERIAL_DATA, get_material_info
    mu = get_mu('concrete', energy_MeV=1.0)

Notes:
    - All mu values are LINEAR attenuation coefficients (mu/rho × density)
    - "Good geometry" (narrow beam) assumption
    - Valid range: 0.1 - 10.0 MeV
    - For broad-beam / thick-wall design, apply build-up factors
      (tabulated in ANSI/ANS-6.4.3)
"""

import numpy as np
from scipy.interpolate import interp1d


# =============================================================================
# MATERIAL DATABASE
# =============================================================================
# Each entry:
#   density       : g/cm^3
#   energies_MeV  : tabulated photon energies (NIST XCOM)
#   mu_cm-1       : linear attenuation coefficients at those energies
#   H_fraction    : hydrogen mass fraction (relevant for neutron moderation)
#   B_fraction    : boron mass fraction (relevant for thermal neutron capture)
#   cost_per_m3   : indicative material cost (USD) — market estimate
#   role          : primary shielding role description
#   color         : hex color for plotting

MATERIAL_DATA = {

    'concrete': {
        'display_name': 'Ordinary Concrete',
        'density': 2.35,
        'energies_MeV': [0.1,  0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [0.402, 0.287, 0.211, 0.153, 0.116, 0.078, 0.059],
        'H_fraction': 0.010,
        'B_fraction': 0.000,
        'cost_per_m3': 190,
        'role': 'Gamma attenuation — standard structural shielding',
        'color': '#95A5A6',
        'notes': 'Workhorse shielding material. Good gamma attenuation, low cost, structural.'
    },

    'heavy_concrete': {
        'display_name': 'Heavy Concrete (Barite)',
        'density': 3.45,
        'energies_MeV': [0.1,  0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [1.029, 0.518, 0.319, 0.211, 0.164, 0.111, 0.087],
        'H_fraction': 0.008,
        'B_fraction': 0.000,
        'cost_per_m3': 1200,
        'role': 'High-density gamma shielding — thinner walls than ordinary concrete',
        'color': '#717D7E',
        'notes': 'Higher density → better gamma attenuation per cm. ~3.7× cost of ordinary concrete.'
    },

    'steel': {
        'display_name': 'Steel (Iron)',
        'density': 7.9,
        'energies_MeV': [0.1,  0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1': [2.912, 1.149, 0.662, 0.474, 0.336, 0.248, 0.236],
        'H_fraction': 0.000,
        'B_fraction': 0.000,
        'cost_per_m3': 8000,
        'role': 'High-Z gamma shielding — compact but expensive',
        'color': '#AAB7B8',
        'notes': 'Excellent gamma attenuation but zero neutron moderation. Often used as thin cap layer.'
    },

    'lead': {
        'display_name': 'Lead',
        'density': 11.34,
        'energies_MeV': [0.1,   0.2,   0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [62.93, 11.33, 1.826, 0.805, 0.518, 0.483, 0.559],
        'H_fraction': 0.000,
        'B_fraction': 0.000,
        'cost_per_m3': 21000,
        'role': 'Very high-Z gamma shielding — best at low energies (<0.5 MeV)',
        'color': '#566573',
        'notes': (
            'Note the strong energy dependence — extremely effective below 0.5 MeV '
            '(photoelectric dominates), but less advantageous above 1 MeV where '
            'Compton scattering dominates and lower-Z materials catch up.'
        )
    },

    'bentonite_slurry': {
        'display_name': 'Bentonite Slurry (~60% water)',
        'density': 1.45,
        'energies_MeV': [0.1,   0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [0.248, 0.199, 0.140, 0.103, 0.071, 0.044, 0.032],
        'H_fraction': 0.067,
        'B_fraction': 0.002,
        'cost_per_m3': 160,
        'role': 'Neutron moderation (primary) + low-cost gamma complement',
        'color': '#A9784E',
        'notes': (
            'Key advantage: extremely low cost (~$35/m³ vs $120 for concrete). '
            'High hydrogen content (0.085 mass fraction) from water makes it an '
            'effective fast neutron moderator. Low gamma mu — not a standalone '
            'gamma shield. Best used as middle layer in a composite wall '
            '(concrete → bentonite → concrete sandwich).'
        )
    },

    'borated_bentonite': {
        'display_name': 'Borated Bentonite (+5% borax)',
        'density': 1.50,
        'energies_MeV': [0.1,   0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [0.257, 0.206, 0.145, 0.106, 0.074, 0.045, 0.033],
        'H_fraction': 0.068,
        'B_fraction': 0.022,
        'cost_per_m3': 650,
        'role': 'Neutron moderation + thermal neutron capture via B-10',
        'color': '#7D6608',
        'notes': (
            'Borax (Na₂B₄O₇·10H₂O) addition raises boron content for thermal '
            'neutron capture. B-10 cross-section at thermal energies: ~3840 barns. '
            'Small cost premium over plain bentonite slurry (~$55/m³). '
            'Recommended over plain bentonite for mixed gamma+neutron fields.'
        )
    },

    'polyethylene': {
        'display_name': 'High-Density Polyethylene (HDPE)',
        'density': 0.95,
        'energies_MeV': [0.1,   0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [0.186, 0.138, 0.092, 0.069, 0.042, 0.027, 0.019],
        'H_fraction': 0.143,
        'B_fraction': 0.000,
        'cost_per_m3': 900,
        'role': 'Best solid neutron moderator — benchmark comparison material',
        'color': '#F7DC6F',
        'notes': (
            'Highest hydrogen mass fraction of any solid (0.143). '
            'Industry-standard neutron moderator. '
            'Included here as benchmark to compare bentonite slurry against — '
            'bentonite at $35/m³ vs HDPE at $900/m³ for similar H content.'
        )
    },

    'earth_soil': {
        'display_name': 'Compacted Earth / Soil',
        'density': 1.80,
        'energies_MeV': [0.1,   0.2,  0.5,   1.0,   2.0,   5.0,  10.0],
        'mu_cm-1':      [0.308, 0.220, 0.161, 0.120, 0.089, 0.060, 0.045],
        'H_fraction': 0.020,
        'B_fraction': 0.000,
        'cost_per_m3': 15,
        'role': 'Earth berm shielding — cheapest bulk option',
        'color': '#6E2C00',
        'notes': 'Lowest cost option. Often used as bulk earth berms at accelerator facilities. Moderate gamma attenuation, low hydrogen content.'
    },
}


def get_mu(material_key, energy_MeV=1.0):
    """
    Get interpolated linear attenuation coefficient (cm^-1) at a given energy.

    Uses log-log interpolation between NIST tabulated values.
    Physically motivated: mu vs E is smooth on log-log scale.

    Parameters
    ----------
    material_key : str
        Key from MATERIAL_DATA (e.g. 'concrete', 'bentonite_slurry')
    energy_MeV : float
        Photon energy in MeV. Best accuracy in range [0.1, 10.0].

    Returns
    -------
    float : mu in cm^-1

    Example
    -------
    >>> get_mu('concrete', 1.0)
    0.156
    >>> get_mu('lead', 0.1)    # Lead is very effective at low energies
    62.93
    """
    if material_key not in MATERIAL_DATA:
        raise ValueError(
            f"Unknown material '{material_key}'. "
            f"Available: {list(MATERIAL_DATA.keys())}"
        )

    data = MATERIAL_DATA[material_key]
    log_E  = np.log(data['energies_MeV'])
    log_mu = np.log(data['mu_cm-1'])

    interp_fn = interp1d(
        log_E, log_mu,
        kind='linear',
        bounds_error=False,
        fill_value=(log_mu[0], log_mu[-1])
    )
    return float(np.exp(interp_fn(np.log(energy_MeV))))


def get_material_info(material_key):
    """
    Return full info dict for a material.

    Parameters
    ----------
    material_key : str

    Returns
    -------
    dict with all material properties
    """
    if material_key not in MATERIAL_DATA:
        raise ValueError(f"Unknown material '{material_key}'.")
    return MATERIAL_DATA[material_key]


def get_mu_table(material_key):
    """
    Return a pandas DataFrame of tabulated mu values for a material.

    Parameters
    ----------
    material_key : str

    Returns
    -------
    pd.DataFrame with columns: Energy (MeV), mu (cm^-1), mu/rho (cm^2/g)
    """
    import pandas as pd
    data = MATERIAL_DATA[material_key]
    df = pd.DataFrame({
        'Energy (MeV)': data['energies_MeV'],
        'μ (cm⁻¹)': data['mu_cm-1'],
        'μ/ρ (cm²/g)': [m / data['density'] for m in data['mu_cm-1']]
    })
    return df


def compare_mu_at_energy(energy_MeV=1.0):
    """
    Return a summary DataFrame comparing all materials at a single energy.

    Parameters
    ----------
    energy_MeV : float

    Returns
    -------
    pd.DataFrame sorted by mu (descending)
    """
    import pandas as pd
    rows = []
    for key, data in MATERIAL_DATA.items():
        mu = get_mu(key, energy_MeV)
        rows.append({
            'Material': data['display_name'],
            'μ (cm⁻¹)': round(mu, 4),
            'Density (g/cm³)': data['density'],
            'H fraction': data['H_fraction'],
            'Cost ($/m³)': data['cost_per_m3'],
            'Role': data['role']
        })
    df = pd.DataFrame(rows).sort_values('μ (cm⁻¹)', ascending=False)
    return df


def get_halfvalue_layer(material_key, energy_MeV=1.0):
    """
    Calculate Half-Value Layer (HVL) — thickness that reduces dose by 50%.

    HVL = ln(2) / mu

    Parameters
    ----------
    material_key : str
    energy_MeV : float

    Returns
    -------
    float : HVL in cm
    """
    mu = get_mu(material_key, energy_MeV)
    return np.log(2) / mu


def get_tenthvalue_layer(material_key, energy_MeV=1.0):
    """
    Calculate Tenth-Value Layer (TVL) — thickness that reduces dose by 90%.

    TVL = ln(10) / mu

    Parameters
    ----------
    material_key : str
    energy_MeV : float

    Returns
    -------
    float : TVL in cm
    """
    mu = get_mu(material_key, energy_MeV)
    return np.log(10) / mu


def required_thickness(material_key, source_dose, target_dose, energy_MeV=1.0):
    """
    Calculate required shielding thickness using Beer-Lambert law.

    x = -ln(target/source) / mu

    Parameters
    ----------
    material_key : str
    source_dose : float   Source-side dose rate (any unit)
    target_dose : float   Required dose rate (same unit)
    energy_MeV : float

    Returns
    -------
    float : thickness in cm (0.0 if no shielding needed)
    """
    if source_dose <= target_dose:
        return 0.0
    mu = get_mu(material_key, energy_MeV)
    return -np.log(target_dose / source_dose) / mu


MATERIAL_KEYS   = list(MATERIAL_DATA.keys())
MATERIAL_LABELS = {k: v['display_name'] for k, v in MATERIAL_DATA.items()}
