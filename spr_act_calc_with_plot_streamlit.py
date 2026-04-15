import streamlit as st
import math
import matplotlib.pyplot as plt

# 頁面配置
st.set_page_config(page_title="Fire Sprinkler & Smoke Calc", layout="wide")

def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    """執行 NFPA 92 排煙與防吸空計算"""
    q_design = q_act * sf
    q_conv = 0.7 * q_design 
    # 質量流率公式
    m_smoke = (0.071 * (q_conv**(1/3)) * (max(z_clear, 0.1)**(5/3))) + (0.0018 * q_conv)
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (max(m_smoke, 0.01) * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    d_layer = h - z_clear 
    v_max_grill = 0.41 * (max(d_layer, 0.1)**2.5) * math.sqrt(max((t_smoke_k - t_amb_k) / t_amb_k, 0.001))
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

st.title("🔥 噴灑頭啟動與排煙設計模擬器 (NFPA 92)")

# 側邊欄輸入
with st.sidebar:
    st.header("📋 輸入參數")
    growth_rates = {"Slow": 0.0029, "Medium": 0.0117, "Fast": 0.0469, "Ultra Fast": 0.1875}
    gr_name = st.selectbox("1. 火災增長率 (Growth Rate)", list(growth_rates.keys()), index=1)
    alpha = growth_rates[gr_name]
    h = st.number_input("2. 天花板高度 (m)", value=3.0)
    t_amb = st.number_input("3. 環境溫度 (°C)", value=20.0)
    t_act = st.number_input("4. 噴頭動作溫度 (°C)", value=68.0)
    r = st.number_input("5. 噴頭水平距離 (m)", value=2.0)
    rti = st.number_input("6. RTI", value=50.0)
    sf = st.number_input("7. 安全係數 (SF)", value=1.5)
    z_clear = st.number_input("8. 清晰高度 (m)", value=1.8)

# 執行計算
if st.button("🚀 開始計算模擬"):
    times, hrr_list = [], []
    t, t_link = 0.0, t_amb
    dt = 1.0
    act_time = None
    q_act = 0.0
    simulation_limit = 1200 

    # 模擬循環
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
            q = q_act # 啟動後封頂

        times.append(t)
        hrr_list.append(q)
        t += dt

    if act_time:
        # 1. 執行排煙計算
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb)
        
        # 2. 顯示結果指標
        st.subheader("✅ 模擬與排煙計算結果")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("啟動時間", f"{act_time:.1f} s")
        col2.metric("啟動時規模 (Q_act)", f"{q_act:.2f} kW")
        col3.metric("設計規模 (Q_design)*", f"{q_design:.2f} kW")
        col4.metric("總排煙量需求", f"{v_total:.2f} m³/s")
        
        st.caption(f"*註：設計火災規模 (Q_design) 已計入安全係數 (SF = {sf})")

        # 3. 詳細數據區塊
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.info(f"""
            **排煙系統參數：**
            - 預估煙層溫度: {t_smoke:.2f} °C
            - 每小時排煙量: {round(v_total * 3600, 1)} m³/hr
            """)
        with res_col2:
            num_vents = math.ceil(v_total / v_max_grill) if v_max_grill > 0 else 1
            st.warning(f"""
            **排煙口設計：**
            - 單個排煙口限值 (防吸空): {v_max_grill:.2f} m³/s
            - **建議最少排煙口數量: {num_vents} 個**
            """)

        st.markdown("---")

        # 4. 繪圖：HRR 曲線
        st.subheader("📈 火災發展曲線 (HRR Curve)")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, hrr_list, 'r-', linewidth=2.5, label='Heat Release Rate (kW)')
        
        # 標註啟動點與數值
        ax.axvline(x=act_time, color='gray', linestyle='--', alpha=0.6)
        ax.scatter([act_time], [q_act], color='red', zorder=5)
        
        # 在圖表上顯示數值標籤
        ax.text(act_time + 15, q_act * 0.95, 
                f'Activation: {act_time:.1f}s\nQ_act: {q_act:.1f} kW', 
                fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))
        
        # 圖表設定
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('HRR (kW)')
        ax.set_ylim(bottom=0) # 強制 Y 軸從 0 開始
        ax.set_xlim(0, 1200) # 強制 X 軸到 1200 秒
        ax.grid(True, which='both', linestyle='--', alpha=0.5)
        ax.legend()
        
        st.pyplot(fig)
    else:
        st.error("噴頭未能在 1200 秒內動作。")