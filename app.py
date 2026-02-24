#app.py

"""
Interactive Radiation Zone Mapping Web Application
Built with Streamlit

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from radiation_mapper import RadiationZoneMapper, create_sample_data
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from mu_values import (
    get_mu, get_halfvalue_layer, get_tenthvalue_layer,
    required_thickness, compare_mu_at_energy,
    MATERIAL_DATA, MATERIAL_KEYS, MATERIAL_LABELS
)

def calculate_shielding_thickness(current_dose, target_dose, material='concrete', energy_MeV=1.0):
    """Wrapper around mu_values.required_thickness — all physics lives in mu_values.py"""
    return required_thickness(material, current_dose, target_dose, energy_MeV)

st.set_page_config(
    page_title="Radiation Zone Mapper & Shielding Tool",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #E74C3C;
        text-align: center;
        padding: 1rem 0;
        text-shadow: 1px 1px 2px #0000001a;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        padding-bottom: 2rem;
    }
    .eng-box {
        background-color: #E9F7EF;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #27AE60;
        margin: 1rem 0;
    }
    .danger-box {
        background-color: #FADBD8;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #E74C3C;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Radiation Zone & Shielding Manager</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated Classification & Civil Engineering Controls for Accelerator Facilities</div>', unsafe_allow_html=True)


with st.sidebar:
    st.header("⚙️ Configuration")
    
    data_source = st.radio(
        "Data Source",
        ["Upload CSV", "Use Sample Data", "Manual Entry"]
    )
    
    st.markdown("---")
    
    st.subheader("Advanced Settings")
    interpolation_method = st.selectbox(
    "Interpolation Method",
    ["idw", "linear", "cubic", "nearest"]
    )
    
    st.markdown("---")
    
    adaptive_scale = st.checkbox("Adaptive Scale (for low-dose data)", value=True,
    help="Automatically adjusts color levels to match your data range")
    
    # VISUALIZATION SETTINGS
    st.subheader("Visualization")
    show_measurements = st.checkbox("Show measurement points", value=True)
    show_grid = st.checkbox("Show coordinate grid", value=True)
    add_buffers = st.checkbox("Add buffer zones", value=True)
    
    resolution = st.slider(
        "Grid Resolution",
        min_value=50, max_value=300, value=150, step=50,
        help="Higher resolution = smoother maps but slower processing"
    )

    st.markdown("---")
    
    st.subheader("Quick Shielding Calc")
    st.info("Calculate wall thickness to declassify a hotspot.")
    
    calc_dose   = st.number_input("Source Dose (µSv/hr)", value=50.0, step=10.0)
    calc_target = st.selectbox("Target Zone", [0.5, 3.0, 10.0], format_func=lambda x: f"{x} µSv/hr")
    calc_energy = st.slider("Photon Energy (MeV)", 0.1, 10.0, 1.0, 0.1)
    calc_mat    = st.selectbox("Material",
                    options=MATERIAL_KEYS,
                    format_func=lambda k: MATERIAL_LABELS[k])

    req_thickness = calculate_shielding_thickness(calc_dose, calc_target, calc_mat, calc_energy)

    if req_thickness > 0:
        mu_val = get_mu(calc_mat, calc_energy)
        hvl    = get_halfvalue_layer(calc_mat, calc_energy)
        st.markdown(f"**Required Thickness:** ### {req_thickness:.2f} cm")
        st.caption(f"μ = {mu_val:.4f} cm⁻¹ | HVL = {hvl:.2f} cm at {calc_energy} MeV")
    else:
        st.success("No shielding needed")
    
    if req_thickness > 0:
        st.markdown(f"**Required Thickness:**")
        st.markdown(f"### {req_thickness:.2f} cm")
    else:
        st.success("No shielding needed")



col1, col2 = st.columns([2, 1])

with col1:
    st.header("Data Input & Analysis")
    
    measurements_df = None
    
    
    if data_source == "Upload CSV":
        st.markdown('<div class="eng-box">Upload CSV with columns: <b>x, y, dose_rate</b><br>Units: meters, µSv/hr</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])
        if uploaded_file is not None:
            try:
                measurements_df = pd.read_csv(uploaded_file)
                if not all(col in measurements_df.columns for col in ['x', 'y', 'dose_rate']):
                    st.error("CSV must contain: x, y, dose_rate")
                    measurements_df = None
            except Exception as e:
                st.error(f"Error: {e}")
    
    elif data_source == "Use Sample Data":
        scenario = st.selectbox(
            "Select Scenario",
            ["beamline_hotspot", "tunnel", "uniform_low", "scattered_sources", "shielding_test"],
            format_func=lambda x: x.replace("_", " ").title()
        )
        if st.button("Generate Sample Data"):
            measurements_df = create_sample_data(scenario=scenario)
            st.success(f"Generated {len(measurements_df)} points")
            
    else: # Manual
        num_points = st.number_input("Points", 3, 50, 5)
        manual_data = []
        cols = st.columns(3)
        cols[0].markdown("**X (m)**")
        cols[1].markdown("**Y (m)**")
        cols[2].markdown("**Dose (µSv/hr)**")
        for i in range(num_points):
            c = st.columns(3)
            x = c[0].number_input(f"x{i}", value=float(i*5), key=f"x{i}")
            y = c[1].number_input(f"y{i}", value=float(i*3), key=f"y{i}")
            d = c[2].number_input(f"d{i}", value=1.0, key=f"d{i}")
            manual_data.append({'x': x, 'y': y, 'dose_rate': d})
        if st.button("Plot Manual Data"):
            measurements_df = pd.DataFrame(manual_data)

    if measurements_df is not None and len(measurements_df) >= 3:
        mapper = RadiationZoneMapper(standard="CERN")
        
        with st.spinner("Calculating radiation contours..."):
            fig = mapper.plot_zone_map(
                measurements_df,
                area_name="Survey Area",
                show_measurements=show_measurements,
                show_grid=show_grid,
                add_buffer_zones=add_buffers,
                interp_method=interpolation_method,
                adaptive_scale=adaptive_scale,
                figsize=(10, 7)
            )
            st.pyplot(fig)
            
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            
            st.download_button(" Download Map (High-Res PNG)", buf, "radiation_map.png", "image/png")

with col2:
    st.header("Engineering Report")
    
    if measurements_df is not None:
        max_dose = measurements_df['dose_rate'].max()
        
        st.subheader("Zone Classification")
        
        zones = {
            "Restricted (>10)":    len(measurements_df[measurements_df['dose_rate'] >= 10]),
            "Controlled (3-10)":   len(measurements_df[(measurements_df['dose_rate'] >= 3) & (measurements_df['dose_rate'] < 10)]),
            "Supervised (0.5-3)":  len(measurements_df[(measurements_df['dose_rate'] >= 0.5) & (measurements_df['dose_rate'] < 3)]),
            "Public (<0.5)":       len(measurements_df[measurements_df['dose_rate'] < 0.5])
        }
        
        
        st.bar_chart(pd.Series(zones))
        
        
        st.subheader("Environmental Boundary")
        
        # check if max dose at the edges of the surveyed area is safe
        x_min, x_max = measurements_df['x'].min(), measurements_df['x'].max()
        y_min, y_max = measurements_df['y'].min(), measurements_df['y'].max()
        
        boundary_points = measurements_df[
            (measurements_df['x'].between(x_min, x_min+2)) | 
            (measurements_df['x'].between(x_max-2, x_max)) |
            (measurements_df['y'].between(y_min, y_min+2)) |
            (measurements_df['y'].between(y_max-2, y_max))
        ]
        
        max_boundary_dose = boundary_points['dose_rate'].max() if not boundary_points.empty else 0
        
        if max_boundary_dose > 0.5:
            st.markdown(f'<div class="danger-box">⚠️ <b>LEAKAGE DETECTED</b><br>Max dose at boundary: {max_boundary_dose:.2f} µSv/hr<br>Exceeds Public Limit (0.5 µSv/hr)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="eng-box"><b>CONTAINMENT SECURE</b><br>Boundary levels within Public Limit.</div>', unsafe_allow_html=True)

        
        st.subheader("Required Controls")
        if zones["Restricted (>10)"] > 0:
            st.error("🔴 Physical Barriers & Interlocks Required")
        elif zones["Controlled (3-10)"] > 0:
            st.warning("🟠 Passive Dosimetry & Warning Signs Required")
        elif zones["Supervised (0.5-3)"] > 0:
            st.info("🟡 Radiological Monitoring Required")
        else:
            st.success("🟢 Standard Access Control Sufficient")


if measurements_df is not None:
    st.markdown("---")
    st.header("Remediation Plan")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**Compliance Report**")
        report_text = mapper.generate_compliance_report(measurements_df, area_name="Survey Area")
        st.text_area("Full Text Report", report_text, height=250)
        st.download_button("Download Report (TXT)", report_text, "report.txt")
        
    with c2:
        st.markdown("**Shielding Design Calculator**")
        st.markdown("Use this tool to design shielding walls for specific hotspots identified in the map.")
        
        s_dose = st.number_input("Hotspot Dose Rate (µSv/hr)", value=max_dose, help="Enter the highest value from your survey")
        s_target = st.selectbox("Desired Classification", [0.5, 7.5, 25.0], index=0)
        
        
        mats = ['Concrete', 'Steel', 'Lead']
        results = {}
        for m in mats:
            results[m] = calculate_shielding_thickness(s_dose, s_target, m.lower())
            
        res_df = pd.DataFrame.from_dict(results, orient='index', columns=['Thickness (cm)'])
        st.table(res_df.style.format("{:.2f}"))
        
        st.caption(f"Calculated using linear attenuation for Gamma radiation. Safety factor not included.")

else:
    st.info("Please load data to view Engineering Analysis")

st.markdown("---")
st.header("Material Reference: Attenuation Coefficients (NIST XCOM)")

ref_col1, ref_col2 = st.columns([1, 2])

with ref_col1:
    st.subheader("Lookup by Energy")
    query_energy = st.slider("Photon Energy (MeV) ", 0.1, 10.0, 1.0, 0.1,
                              key="ref_energy")   
    sel_mats = st.multiselect(
        "Select materials",
        options=MATERIAL_KEYS,
        default=["concrete", "bentonite_slurry", "polyethylene"],
        format_func=lambda k: MATERIAL_LABELS[k]
    )

    if sel_mats:
        for k in sel_mats:
            mat = MATERIAL_DATA[k]
            mu  = get_mu(k, query_energy)
            hvl = get_halfvalue_layer(k, query_energy)
            tvl = get_tenthvalue_layer(k, query_energy)
            with st.expander(mat['display_name']):
                st.metric("μ (cm⁻¹)", f"{mu:.4f}")
                c1, c2 = st.columns(2)
                c1.metric("HVL (cm)", f"{hvl:.2f}", help="Thickness that halves dose")
                c2.metric("TVL (cm)", f"{tvl:.2f}", help="Thickness for 90% reduction")
                st.caption(f" {mat['notes']}")

with ref_col2:
    st.subheader("μ vs Energy Curves")
    if sel_mats:
        energies_plot = np.linspace(0.1, 10.0, 200)
        fig_mu, ax = plt.subplots(figsize=(8, 4.5))

        for k in sel_mats:
            mu_curve = [get_mu(k, e) for e in energies_plot]
            ax.loglog(energies_plot, mu_curve,
                      linewidth=2.2,
                      label=MATERIAL_LABELS[k],
                      color=MATERIAL_DATA[k]['color'])
            ax.scatter([query_energy], [get_mu(k, query_energy)],
                       s=70, zorder=5,
                       color=MATERIAL_DATA[k]['color'],
                       edgecolors='black')

        ax.axvline(x=query_energy, color='gray', linestyle='--',
                   alpha=0.5, label=f'Selected: {query_energy} MeV')
        ax.set_xlabel("Photon Energy (MeV)", fontsize=11)
        ax.set_ylabel("μ (cm⁻¹)", fontsize=11)
        ax.set_title("Linear Attenuation Coefficients — NIST XCOM\n(log-log interpolation between tabulated points)",
                     fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, which='both')
        st.pyplot(fig_mu)
        st.caption("Narrow-beam values. Apply build-up factors for thick-wall design.")

    st.subheader(f"All Materials at {query_energy} MeV")
    st.dataframe(compare_mu_at_energy(query_energy), width='stretch')
