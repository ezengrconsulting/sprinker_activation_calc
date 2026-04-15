import streamlit as st
import math
import matplotlib.pyplot as plt

# ????
st.set_page_config(page_title="Fire Sprinkler & Smoke Calc", layout="wide")

def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    """?? NFPA 92 ????????"""
    q_design = q_act * sf
    q_conv = 0.7 * q_design 
    # ??????
    m_smoke = (0.071 * (q_conv**(1/3)) * (max(z_clear, 0.1)**(5/3))) + (0.0018 * q_conv)
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (max(m_smoke, 0.01) * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    d_layer = h - z_clear 
    v_max_grill = 0.41 * (max(d_layer, 0.1)**2.5) * math.sqrt(max((t_smoke_k - t_amb_k) / t_amb_k, 0.001))
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

st.title("?? ????????????? (NFPA 92)")

# ?????
with st.sidebar:
    st.header("?? ????")
    growth_rates = {"Slow": 0.0029, "Medium": 0.0117, "Fast": 0.0469, "Ultra Fast": 0.1875}
    gr_name = st.selectbox("1. ????? (Growth Rate)", list(growth_rates.keys()), index=1)
    alpha = growth_rates[gr_name]
    h = st.number_input("2. ????? (m)", value=3.0)
    t_amb = st.number_input("3. ???? (°C)", value=20.0)
    t_act = st.number_input("4. ?????? (°C)", value=68.0)
    r = st.number_input("5. ?????? (m)", value=2.0)
    rti = st.number_input("6. RTI", value=50.0)
    sf = st.number_input("7. ???? (SF)", value=1.5)
    z_clear = st.number_input("8. ???? (m)", value=1.8)

# ????
if st.button("?? ??????"):
    times, hrr_list = [], []
    t, t_link = 0.0, t_amb
    dt = 1.0
    act_time = None
    q_act = 0.0
    simulation_limit = 1200 

    # ????
    while t <= simulation_limit:
        if act_time is None:
            q = alpha * (t**2)
            ratio = r / h
            delta_t = (16.9 * q**(2/3)) / (h**(5/3)) if ratio <= 0.18 else (5.38 * (q / r)**(2/3)) / h
            t_g = t_amb + delta_t
            u = 0.96 * (q / h)**(1/3) if ratio <= 0.15 else (0.197 * q**(1/3) * h**0.5) / (r**(5/6))
            
            if q > 0.1:
                t_link += (math.sqrt(max(u, 0.1)) / rti) * (t_g - t_link) * dt
            
            if t_link >= t_act:
                act_time = t
                q_act = q
        else:
            q = q_act # ?????

        times.append(t)
        hrr_list.append(q)
        t += dt

    if act_time:
        # 1. ??????
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb)
        
        # 2. ????????
        st.subheader("? ?????????")
        c1, c2, c3 = st.columns(3)
        c1.metric("??????", f"{act_time:.1f} s")
        c2.metric("?????? (Q_design)", f"{q_design:.2f} kW")
        c3.metric("??????", f"{v_total:.2f} m³/s")

        # 3. ????????
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.info(f"""
            **?????**
            - ?????? (Q_act): {q_act:.2f} kW
            - ??????: {t_smoke:.2f} °C
            - ??????: {round(v_total * 3600, 1)} m³/hr
            """)
        with res_col2:
            num_vents = math.ceil(v_total / v_max_grill) if v_max_grill > 0 else 1
            st.warning(f"""
            **??????**
            - ???????: {v_max_grill:.2f} m³/s
            - **?????????: {num_vents} ?**
            """)

        st.markdown("---")

        # 4. ???HRR ??
        st.subheader("?? ?????? (HRR Curve)")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, hrr_list, 'r-', linewidth=2.5, label='Heat Release Rate (kW)')
        
        # ?????
        ax.axvline(x=act_time, color='gray', linestyle='--', alpha=0.6)
        ax.scatter([act_time], [q_act], color='red', zorder=5)
        ax.text(act_time + 20, q_act * 0.9, f'Activation: {act_time:.0f}s', fontsize=10, fontweight='bold')
        
        # ????
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('HRR (kW)')
        ax.set_ylim(bottom=0) # Y ?? 0 ??
        ax.set_xlim(0, 1200) # X ?? 1200 ?
        ax.grid(True, which='both', linestyle='--', alpha=0.5)
        ax.legend()
        
        st.pyplot(fig)
    else:
        st.error("????? 1200 ?????")