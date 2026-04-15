import streamlit as st
import math
import matplotlib.pyplot as plt

# 頁面配置
st.set_page_config(page_title="Fire Sprinkler & Smoke Calc", layout="wide")

def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    """執行 NFPA 92 排煙與防吸空計算"""
    q_design = q_act * sf
    q_conv = 0.7 * q_design 
    
    # 質量流率公式 (NFPA 92)
    m_smoke = (0.071 * (q_conv**(1/3)) * (max(z_clear, 0.1)**(5/3))) + (0.0018 * q_conv)
    
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (max(m_smoke, 0.01) * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    
    d_layer = h - z_clear 
    v_max_grill = 0.41 * (max(d_layer, 0.1)**2.5) * math.sqrt(max((t_smoke_k - t_amb_k) / t_amb_k, 0.001))
    
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

st.title("🔥 噴灑頭啟動與排煙設計模擬器 (NFPA 92)")
st.caption("已針對 FPETool 計算邏輯進行 +1 秒時間修正調整")

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
    dt = 1.0  # 時間步長設定為 1 秒以對應 FPETool
    act_time_raw = None
    simulation_limit = 1200 

    # 模擬循環
    while t <= simulation_limit:
        if act_time_raw is None:
            q_current = alpha * (t**2)
            ratio = r / h
            
            # Alpert 關聯式
            delta_t = (16.9 * q_current**(2/3)) / (h**(5/3)) if ratio <= 0.18 else (5.38 * (q_current / r)**(2/3)) / h
            t_g = t_amb + delta_t
            u = 0.96 * (q_current / h)**(1/3) if ratio <= 0.15 else (0.197 * q_current**(1/3) * h**0.5) / (r**(5/6))
            
            if q_current > 0.1:
                t_link += (math.sqrt(max(u, 0.1)) / rti) * (t_g - t_link) * dt
            
            if t_link >= t_act:
                act_time_raw = t
        
        # 邏輯判斷：一旦觸發啟動時間 (act_time_raw)，所有的計算與 HRR 固定點都延後 1 秒
        if act_time_raw is not None:
            # 這裡實施 +1 秒修正
            corrected_act_time = act_time_raw + 1.0
            q_at_corrected_time = alpha * (corrected_act_time**2)
            
            # 在圖表中顯示 Capped 效果
            if t < corrected_act_time:
                display_q = alpha * (t**2)
            else:
                display_q = q_at_corrected_time
        else:
            display_q = alpha * (t**2)

        times.append(t)
        hrr_list.append(display_q)
        t += dt

    if act_time_raw:
        # 使用修正後的數據進行排煙計算
        q_act_corrected = alpha * (corrected_act_time**2)
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act_corrected, sf, z_clear, h, t_amb)
        
        # 顯示結果
        st.subheader("✅ 模擬與排煙計算結果 (已校正)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("校正後啟動時間", f"{corrected_act_time:.1f} s")
        col2.metric("Q_act (at {corrected_act_time:.0f}s)", f"{q_act_corrected:.2f} kW")
        col3.metric("設計規模 (Q_design)*", f"{q_design:.2f} kW")
        col4.metric("總排煙量需求", f"{v_total:.2f} m³/s")
        st.caption(f"*註：設計規模已基於校正後的第 {corrected_act_time:.1f} 秒火災大小計算。")

        st.markdown("---")

        # 繪圖
        st.subheader("📈 火災發展曲線 (已對齊 FPETool 校正)")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, hrr_list, 'r-', linewidth=2.5, label='Heat Release Rate (kW)')
        ax.axvline(x=corrected_act_time, color='gray', linestyle='--', alpha=0.6)
        ax.scatter([corrected_act_time], [q_act_corrected], color='red', zorder=5)
        
        # 文字標註 (向下偏移以避免擋住水平線)
        ax.text(corrected_act_time + 20, q_act_corrected * 0.75, 
                f'Corrected Act: {corrected_act_time:.1f}s\nQ: {q_act_corrected:.1f} kW', 
                fontsize=10, fontweight='bold', 
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.5'))
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('HRR (kW)')
        ax.set_ylim(bottom=0, top=q_act_corrected * 1.3)
        ax.set_xlim(0, 1200)
        ax.grid(True, which='both', linestyle='--', alpha=0.5)
        ax.legend(loc='lower right')
        st.pyplot(fig)
    else:
        st.error("噴頭未能在 1200 秒內動作。")