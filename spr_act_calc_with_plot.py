import math
import matplotlib.pyplot as plt

def calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb):
    """
    執行 NFPA 92 排煙與防吸空計算
    """
    q_design = q_act * sf
    q_conv = 0.7 * q_design # 對流熱釋放率 (kW)
    
    # 1. 計算質量流率 (Mass Flow Rate) - NFPA 92 軸對稱羽流公式
    # m = 0.071 * Qc^1/3 * z^5/3 + 0.0018 * Qc
    m_smoke = (0.071 * (q_conv**(1/3)) * (z_clear**(5/3))) + (0.0018 * q_conv)
    
    # 2. 煙層溫度與密度轉體積流率 (m3/s)
    cp = 1.01
    t_amb_k = t_amb + 273.15
    t_smoke_k = t_amb_k + (q_conv / (m_smoke * cp))
    v_total = m_smoke / (353 / t_smoke_k)
    
    # 3. 防吸空 (Plug-holing) 計算 - 每個排煙口的限制
    d_layer = h - z_clear # 煙層厚度
    v_max_grill = 0.41 * (d_layer**2.5) * math.sqrt((t_smoke_k - t_amb_k) / t_amb_k)
    
    return q_design, t_smoke_k - 273.15, v_total, v_max_grill

def run_full_simulation():
    # --- 輸入參數 ---
    growth_rates = {"slow": 0.0029, "medium": 0.0117, "fast": 0.0469, "ultra fast": 0.1875}
    gr = input("火災增長率 (slow, medium, fast, ultra fast): ").lower().strip()
    alpha = growth_rates.get(gr, 0.0117)
    
    t_amb = float(input("環境溫度 (°C): "))
    h = float(input("天花板淨高 (m): "))
    r = float(input("噴灑頭水平距離 (m): "))
    t_act = float(input("噴灑頭動作溫度 (°C): "))
    rti = float(input("RTI (噴灑頭感溫係數): "))
    sf = float(input("排煙設計安全係數 (例如 1.5): "))
    z_clear = float(input("所需煙層清晰高度 (m): "))

    # --- 啟動模擬與繪圖數據收集 ---
    times, hrr_list, t_link_list = [], [], []
    t, t_link = 0.0, t_amb
    dt = 0.5
    act_time = None

    while t < 1200:
        q = alpha * (t**2)
        
        # Alpert 關聯式計算天花板射流
        if (r / h) <= 0.18:
            delta_t = (16.9 * q**(2/3)) / (h**(5/3))
        else:
            delta_t = (5.38 * (q / r)**(2/3)) / h
        t_g = t_amb + delta_t

        if (r / h) <= 0.15:
            u = 0.96 * (q / h)**(1/3)
        else:
            u = (0.197 * q**(1/3) * h**0.5) / (r**(5/6))

        if q > 0.1:
            t_link += (math.sqrt(u) / rti) * (t_g - t_link) * dt

        times.append(t)
        hrr_list.append(q)
        t_link_list.append(t_link)

        if act_time is None and t_link >= t_act:
            act_time = t
            q_act = q
            # 觸發排煙計算
            q_design, t_smoke, v_total, v_max_grill = calculate_smoke_extraction(q_act, sf, z_clear, h, t_amb)
            
        if act_time and t >= act_time + 60: break
        t += dt

    # --- 輸出結果 ---
    if act_time:
        print(f"\n" + "="*40)
        print(f"{'模擬結果 (啟動瞬間)':^40}")
        print(f"啟動時間: {act_time:.1f} s")
        print(f"啟動時火災規模: {q_act:.2f} kW")
        print(f"設計火災規模 (SF={sf}): {q_design:.2f} kW")
        print(f"-"*40)
        print(f"{'排煙計算 (NFPA 92)':^40}")
        print(f"煙層預估溫度: {t_smoke:.2f} °C")
        print(f"總排煙需求量: {v_total:.2f} m³/s")
        print(f"單個排煙口限制: {v_max_grill:.2f} m³/s")
        print(f"建議最少排煙口數量: {math.ceil(v_total / v_max_grill)}")
        print(f"="*40)
        
        # --- 繪圖 ---
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(times, hrr_list, 'r-', label='HRR (kW)')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Heat Release Rate (kW)', color='r')
        ax1.tick_params(axis='y', labelcolor='r')
        
        ax2 = ax1.twinx()
        ax2.plot(times, t_link_list, 'b-', label='Link Temp (°C)')
        ax2.axhline(y=t_act, color='k', linestyle='--', label='Activation Temp')
        ax2.axvline(x=act_time, color='g', linestyle=':', label='Activation Point')
        ax2.set_ylabel('Temperature (°C)', color='b')
        ax2.tick_params(axis='y', labelcolor='b')
        
        plt.title(f'Fire Growth and Response Curve ({gr.capitalize()})')
        plt.grid(True, alpha=0.3)
        plt.legend(loc='upper left')
        plt.show()
    else:
        print("在模擬時間內噴灑頭未啟動。")

if __name__ == "__main__":
    run_full_simulation()