import streamlit as st
import math
import matplotlib.pyplot as plt

# Page Configuration
st.set_page_config(page_title="Sprinkler & Smoke Design Tool", layout="wide")

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

st.title("🔥 Sprinkler Activation & Smoke Extraction Simulator")
st.markdown("This tool calculates sprinkler response time using **Alpert's Correlations** and evaluates smoke exhaust requirements per **NFPA 92**.")
st.caption("Time correction applied (+1.0s) for alignment with FPETool/DETACT-QS logic.")

# Sidebar Inputs with new Default Values
with st.sidebar:
    st.header("📋 Input Parameters")
    
    growth_rates = {"Slow": 0.0029, "Medium": 0.0117, "Fast": 0.0469, "Ultra Fast": 0.1875}
    # Default set to 'Fast'
    gr_name = st.selectbox("1. Fire Growth Rate", list(growth_rates.keys()), index=2)
    alpha = growth_rates[gr_name]
    
    # Updated default values
    h = st.number_input("2. Ceiling Height (m)", value=5.0)
    t_amb = st.number_input("3. Ambient Temperature (°C)", value=25.0)
    t_act = st.number_input("4. Activation Temperature (°C)", value=68.0)
    r = st.number_input("5. Horizontal Distance (m)", value=2.5)
    rti = st.number_input("6. Response Time Index (RTI)", value=50.0)
    sf = st.number_input("7. Safety Factor (SF)", value=1.5)
    z_clear = st.number_input("8. Required Clear Height (m)", value=3.0)

# Simulation Execution
if st.button("🚀 Run Simulation"):
    times, hrr_list = [], []
    t, t_link = 0.0, t_amb
    dt = 1.0  # 1-second time step for engineering tool consistency
    act_time_raw = None
    simulation_limit = 1200 

    # Simulation Loop
    while t <= simulation_limit:
        if act_time_raw is None:
            q_current = alpha * (t**2)
            ratio = r / h
            
            # Alpert's Correlations for Ceiling Jet
            if ratio <= 0.18:
                delta_tg = (16.9 * q_current**(2/3)) / (h**(5/3))
            else:
                delta_tg = (5.38 * (q_current / r)**(2/3)) / h
                
            t_g = t_amb + delta_tg
            
            if ratio <= 0.15:
                u = 0.96 * (q_current / h)**(1/3)
            else:
                u = (0.197 * q_current**(1/3) * h**0.5) / (r**(5/6))
            
            if q_current > 0.1:
                # Heat transfer to sprinkler link
                t_link += (math.sqrt(max(u, 0.1)) / rti) * (t_g - t_link) * dt
            
            if t_link >= t_act:
                act_time_raw = t
        
        # Apply +1 second manual adjustment for alignment
        if act_time_raw is not None:
            corrected_act_time = act_time_raw + 1.0
            q_at_corrected = alpha * (corrected_act_time**2)
            
            # Cap HRR at corrected activation time
            display_q = alpha * (t**2) if t < corrected_act_time else q_at_corrected
        else:
            display_q = alpha * (t**2)

        times.append(t)
        hrr_list.append(display_q)
        t += dt

    if act_time_raw:
        # Perform calculations based on corrected time
        q_act_final = alpha * (corrected_act_time**2)
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act_final, sf, z_clear, h, t_amb)
        
        # Display Results
        st.subheader("✅ Simulation Results (Corrected)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Activation Time", f"{corrected_act_time:.1f} s")
        col2.metric("Q_act (at activation)", f"{q_act_final:.2f} kW")
        col3.metric("Q_design (SF included)*", f"{q_design:.2f} kW")
        col4.metric("Req. Extraction", f"{v_total:.2f} m³/s")
        
        st.caption(f"*Note: Q_design incorporates a Safety Factor of {sf} based on fire size at {corrected_act_time:.1f}s.")

        # Detailed Report
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.info(f"""
            **Smoke System Details:**
            - Predicted Smoke Temp: {t_smoke:.2f} °C
            - Volume Flow Rate: {round(v_total * 3600, 1)} m³/hr
            """)
        with res_col2:
            num_vents = math.ceil(v_total / v_max_grill) if v_max_grill > 0 else 1
            st.warning(f"""
            **Vent Configuration (NFPA 92):**
            - Max Rate per Vent (Plug-holing): {v_max_grill:.2f} m³/s
            - **Min. Vents Required: {num_vents}**
            """)

        st.markdown("---")

        # HRR Plot
        st.subheader("📈 Fire Development Curve (Capped at Activation)")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, hrr_list, 'r-', linewidth=2.5, label='Heat Release Rate (kW)')
        
        # Annotation & Point
        ax.axvline(x=corrected_act_time, color='gray', linestyle='--', alpha=0.6)
        ax.scatter([corrected_act_time], [q_act_final], color='red', zorder=5)
        
        # Label offset lower to prevent blocking the line
        ax.text(corrected_act_time + 20, q_act_final * 0.75, 
                f'Act: {corrected_act_time:.1f}s\nQ: {q_act_final:.1f} kW', 
                fontsize=10, fontweight='bold', 
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.5'))
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('HRR (kW)')
        ax.set_ylim(bottom=0, top=q_act_final * 1.3)
        ax.set_xlim(0, 1200)
        ax.grid(True, which='both', linestyle='--', alpha=0.5)
        ax.legend(loc='lower right')
        st.pyplot(fig)
    else:
        st.error("The sprinkler did not reach the activation temperature within the 1200s limit.")