import streamlit as st
import math
import matplotlib.pyplot as plt

# Page configuration
st.set_page_config(page_title="Fire Sprinkler & Smoke Calc", layout="wide")

def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    """Performs NFPA 92 smoke extraction and plug-holing calculations"""
    q_design = q_act * sf
    q_conv = 0.7 * q_design 
    
    # Mass flow rate formula (NFPA 92 Axisymmetric Plume)
    m_smoke = (0.071 * (q_conv**(1/3)) * (max(z_clear, 0.1)**(5/3))) + (0.0018 * q_conv)
    
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (max(m_smoke, 0.01) * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    
    # Plug-holing limit calculation
    d_layer = h - z_clear 
    v_max_grill = 0.41 * (max(d_layer, 0.1)**2.5) * math.sqrt(max((t_smoke_k - t_amb_k) / t_amb_k, 0.001))
    
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

st.title("🔥 Sprinkler Activation & Smoke Design (NFPA 92)")

# Sidebar Inputs
with st.sidebar:
    st.header("📋 Input Parameters")
    growth_rates = {"Slow": 0.0029, "Medium": 0.0117, "Fast": 0.0469, "Ultra Fast": 0.1875}
    gr_name = st.selectbox("1. Fire Growth Rate", list(growth_rates.keys()), index=1)
    alpha = growth_rates[gr_name]
    
    h = st.number_input("2. Ceiling Height (m)", value=3.0)
    t_amb = st.number_input("3. Ambient Temperature (°C)", value=20.0)
    t_act = st.number_input("4. Activation Temperature (°C)", value=68.0)
    r = st.number_input("5. Radial Distance (m)", value=2.0)
    rti = st.number_input("6. RTI", value=50.0)
    sf = st.number_input("7. Safety Factor (SF)", value=1.5)
    z_clear = st.number_input("8. Smoke Clear Height (m)", value=1.8)

# Simulation Execution
if st.button("🚀 Run Simulation"):
    times, hrr_list = [], []
    t, t_link = 0.0, t_amb
    dt = 1.0
    act_time = None
    q_act = 0.0
    simulation_limit = 1200 

    while t <= simulation_limit:
        if act_time is None:
            q = alpha * (t**2)
            ratio = r / h
            
            # Alpert's Correlations
            delta_t = (16.9 * q**(2/3)) / (h**(5/3)) if ratio <= 0.18 else (5.38 * (q / r)**(2/3)) / h
            t_g = t_amb + delta_t
            u = 0.96 * (q / h)**(1/3) if ratio <= 0.15 else (0.197 * q**(1/3) * h**0.5) / (r**(5/6))
            
            if q > 0.1:
                t_link += (math.sqrt(max(u, 0.1)) / rti) * (t_g - t_link) * dt
            
            if t_link >= t_act:
                act_time = t
                q_act = q
        else:
            q = q_act # Cap HRR at activation

        times.append(t)
        hrr_list.append(q)
        t += dt

    if act_time:
        # 1. Extraction Calculations
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb)
        
        # 2. Metric Display
        st.subheader("✅ Calculation Results")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Activation Time", f"{act_time:.1f} s")
        col2.metric("Q_act (at activation)", f"{q_act:.2f} kW")
        col3.metric("Q_design (SF included)*", f"{q_design:.2f} kW")
        col4.metric("Req. Extraction", f"{v_total:.2f} m³/s")
        
        st.caption(f"*Note: Q_design considers the safety factor (SF = {sf}) applied to Q_act.")

        # 3. Detailed Details
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.info(f"""
            **Smoke Parameters:**
            - Estimated Smoke Temp: {t_smoke:.2f} °C
            - Hourly Rate: {round(v_total * 3600, 1)} m³/hr
            """)
        with res_col2:
            num_vents = math.ceil(v_total / v_max_grill) if v_max_grill > 0 else 1
            st.warning(f"""
            **Vent Design (NFPA 92):**
            - Max Rate per Vent (Plug-holing): {v_max_grill:.2f} m³/s
            - **Minimum Number of Vents: {num_vents}**
            """)

        st.markdown("---")

        # 4. HRR Plot
        st.subheader("📈 Fire Development Curve (HRR)")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, hrr_list, 'r-', linewidth=2.5, label='Heat Release Rate (kW)')
        
        # Annotation & Point
        ax.axvline(x=act_time, color='gray', linestyle='--', alpha=0.6)
        ax.scatter([act_time], [q_act], color='red', zorder=5)
        
        # Annotation moved BELOW the capped line to prevent overlap
        ax.text(act_time + 20, q_act * 0.75, 
                f'Activation: {act_time:.1f}s\nQ_act: {q_act:.1f} kW', 
                fontsize=10, fontweight='bold', 
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.5'))
        
        # Plot styling
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('HRR (kW)')
        ax.set_ylim(bottom=0, top=q_act * 1.3) # Added headroom
        ax.set_xlim(0, 1200)
        ax.grid(True, which='both', linestyle='--', alpha=0.5)
        ax.legend(loc='lower right')
        
        st.pyplot(fig)
    else:
        st.error("Sprinkler did not activate within 1200 seconds.")