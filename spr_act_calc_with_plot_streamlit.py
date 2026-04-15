import streamlit as st
import math
import matplotlib.pyplot as plt

# 1. 設置標題 (必須在最前面)
st.title("🔥 噴灑頭啟動與排煙計算")

# 2. 建立輸入欄位 (確保它們在 sidebar 或是主頁面直接顯示)
# 不要把這些放在 get_float_input 這種 while 迴圈裡，Streamlit 自帶驗證功能
with st.sidebar:
    st.header("📋 設定輸入參數")
    
    growth_rates = {"Slow": 0.0029, "Medium": 0.0117, "Fast": 0.0469, "Ultra Fast": 0.1875}
    gr_name = st.selectbox("1. 火災增長率", list(growth_rates.keys()), index=1)
    alpha = growth_rates[gr_name]
    
    # 使用 st.number_input 會直接在網頁產生輸入框
    t_amb = st.number_input("2. 環境溫度 (°C)", value=20.0)
    h = st.number_input("3. 天花板淨高 (m)", value=3.0)
    r = st.number_input("4. 噴灑頭水平距離 (m)", value=2.0)
    t_act = st.number_input("5. 噴灑頭動作溫度 (°C)", value=68.0)
    rti = st.number_input("6. RTI 值", value=50.0)
    sf = st.number_input("7. 安全係數 (SF)", value=1.5)
    z_clear = st.number_input("8. 清晰高度 (m)", value=1.8)

# 3. 定義計算函數 (維持原樣)
def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    q_design = q_act * sf
    q_conv = 0.7 * q_design
    m_smoke = (0.071 * (q_conv**(1/3)) * (z_clear**(5/3))) + (0.0018 * q_conv)
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (m_smoke * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    d_layer = h - z_clear
    v_max_grill = 0.41 * (d_layer**2.5) * math.sqrt((t_smoke_k - t_amb_k) / t_amb_k)
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

# 4. 點擊按鈕才執行模擬計算
if st.button("🚀 開始執行模擬"):
    # 這裡放入模擬循環 (while 迴圈)
    times, hrr_list, t_link_list = [], [], []
    t, t_link = 0.0, t_amb
    dt = 0.5
    act_time = None

    while t < 1200:
        q = alpha * (t**2)
        ratio = r / h
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
            t_link += (math.sqrt(max(u, 0.1)) / rti) * (t_g - t_link) * dt

        times.append(t)
        hrr_list.append(q)
        t_link_list.append(t_link)

        if act_time is None and t_link >= t_act:
            act_time = t
            q_act = q
            break # 找到啟動時間就跳出
        t += dt

    if act_time:
        q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb)
        st.success(f"噴頭於 {act_time:.1f} 秒啟動")
        
        # 顯示結果圖表
        fig, ax1 = plt.subplots()
        ax1.plot(times, hrr_list, 'r-', label='HRR')
        ax2 = ax1.twinx()
        ax2.plot(times, t_link_list, 'b-', label='Temp')
        st.pyplot(fig)
    else:
        st.error("模擬時間內噴頭未啟動")