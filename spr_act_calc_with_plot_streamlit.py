import streamlit as st
import math
import matplotlib.pyplot as plt

# 設定網頁標題與配置
st.set_page_config(page_title="Fire Sprinkler & Smoke Calc", layout="wide")

def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    """執行 NFPA 92 排煙與防吸空計算"""
    q_design = q_act * sf
    q_conv = 0.7 * q_design # 對流熱釋放率 (kW)
    
    # 1. 計算質量流率 (Mass Flow Rate) - NFPA 92 軸對稱羽流公式
    m_smoke = (0.071 * (q_conv**(1/3)) * (z_clear**(5/3))) + (0.0018 * q_conv)
    
    # 2. 煙層溫度與密度轉體積流率 (m3/s)
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (m_smoke * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    
    # 3. 防吸空 (Plug-holing) 計算 - 每個排煙口的限制
    d_layer = h - z_clear # 煙層厚度
    # NFPA 92: Vmax = 0.41 * d^2.5 * sqrt((Ts-Ta)/Ta)
    v_max_grill = 0.41 * (max(d_layer, 0.1)**2.5) * math.sqrt(max((t_smoke_k - t_amb_k) / t_amb_k, 0.001))
    
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

# --- Streamlit 介面 ---
st.title("🔥 噴灑頭啟動與排煙設計模擬器 (NFPA 92)")
st.markdown("依據火災成長率計算噴頭啟動時間，並分析排煙需求。")

# 側邊欄輸入欄位
with st.sidebar:
    st.header("📋 輸入參數")
    
    growth_rates = {"Slow": 0.0029, "Medium": 0.0117, "Fast": 0.0469, "Ultra Fast": 0.1875}
    gr_name = st.selectbox("1. 火災增長率 (Growth Rate)", list(growth_rates.keys()), index=1)
    alpha = growth_rates[gr_name]
    
    h = st.number_input("2. 天花板高度 (Ceiling Height, m)", value=3.0, min_value=0.1)
    t_amb = st.number_input("3. 環境溫度 (Ambient Temp, °C)", value=20.0)
    t_act = st.number_input("4. 噴頭動作溫度 (Activation Temp, °C)", value=68.0)
    r = st.number_input("5. 噴頭水平距離 (Radial Distance, m)", value=2.0, min_value=0.0)
    rti = st.number_input("6. RTI (Response Time Index)", value=50.0, min_value=1.0)
    sf = st.number_input("7. 排煙設計安全係數 (Safety Factor)", value=1.5, min_value=1.0)
    z_clear = st.number_input("8. 清晰高度 (Smoke Clear Height, m)", value=1.8, max_value=h-0.1)

# --- 模擬運算 ---
if st.button("🚀 開始計算模擬"):
    times, hrr_list, t_link_list = [], [], []
    t, t_link = 0.0, t_amb
    dt = 0.5
    act_time = None
    q_act = 0.0

    # 模擬 20 分鐘 (1200s)
    while t < 1200:
        q = alpha * (t**2)
        ratio = r / h
        
        # Alpert 關聯式計算煙氣溫度與流速
        if ratio <= 0.18:
            delta_t = (16.9 * q**(2/3)) / (h**(5/3))
        else:
            delta_t = (5.38 * (q / r)**(2/3)) / h
        t_g = t_amb + delta_t

        if ratio <= 0.15:
            u = 0.96 * (q / h)**(1/3)
        else:
            u = (0.197 * q**(1/3) * h**0.5) / (r**(5/6))

        if q > 0.1:
            # 噴頭感溫元件升溫公式
            t_link += (math.sqrt(max(u, 0.1)) / rti) * (t_g - t_link) * dt

        times.append(t)
        hrr_list.append(q)
        t_link_list.append(t_link)

        if act_time is None and t_link >= t_act:
            act_time = t
            q_act = q
            # 找到啟動點後，多模擬 60 秒以繪製完整趨勢
            
        if act_time and t >= act_time + 60:
            break
        t += dt

    # --- 顯示結果 ---
    if act_time:
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb)
        
        st.success(f"✅ 計算完成：噴灑頭於 {round(act_time, 1)} 秒啟動")
        
        # 1. 第一部分：文字指標結果
        col1, col2, col3 = st.columns(3)
        col1.metric("啟動時間 (Time)", f"{act_time:.1f} s")
        col2.metric("啟動火災規模 (Q_act)", f"{q_act:.2f} kW")
        col3.metric("設計排煙火規模", f"{q_design:.2f} kW")

        st.markdown("---")
        
        # 2. 第二部分：排煙系統詳情
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.write("**💨 排煙需求量:**")
            st.write(f"- 預估煙層溫度: {t_smoke:.2f} °C")
            st.write(f"- 總體積流量: **{v_total:.2f} m³/s**")
            st.write(f"- 換算小時流量: {round(v_total * 3600, 1)} m³/hr")
        
        with res_col2:
            num_vents = math.ceil(v_total / v_max_grill) if v_max_grill > 0 else 1
            st.write("**⚠️ 物理限制 (防吸空):**")
            st.write(f"- 單個排煙口限制: {v_max_grill:.2f} m³/s")
            st.write(f"- **建議最少排煙口數量: {num_vents} 個**")

        st.markdown("---")

        # 3. 第三部分：發展曲線圖表
        st.subheader("📈 火災成長與噴頭響應曲線")
        fig, ax1 = plt.subplots(figsize=(10, 5))
        
        # HRR 曲線 (左軸)
        ax1.plot(times, hrr_list, 'r-', label='Fire Size (HRR)', linewidth=2)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Heat Release Rate (kW)', color='r')
        ax1.tick_params(axis='y', labelcolor='r')
        
        # 溫度曲線 (右軸)
        ax2 = ax1.twinx()
        ax2.plot(times, t_link_list, 'b-', label='Sprinkler Temp', linewidth=2)
        ax2.axhline(y=t_act, color='orange', linestyle='--', label='Activation Threshold')
        ax2.axvline(x=act_time, color='green', linestyle=':', label='Activation Point')
        ax2.set_ylabel('Temperature (°C)', color='b')
        ax2.tick_params(axis='y', labelcolor='b')
        
        plt.title(f'Simulation Result: {gr_name} Growth Rate')
        fig.legend(loc="upper left", bbox_to_anchor=(0.15, 0.85))
        st.pyplot(fig)
        
    else:
        st.error("❌ 噴頭在 1200 秒內未啟動。請確認環境溫度是否接近動作溫度，或增加火災成長速率。")