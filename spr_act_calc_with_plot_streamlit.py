import math
import matplotlib.pyplot as plt

# ==========================================
# 核心共享邏輯 (Shared Physics Logic)
# ==========================================

def get_alpha(gr_input):
    """獲取火災增長係數 alpha，預設為 Fast (0.0469)"""
    growth_rates = {"slow": 0.0029, "medium": 0.0117, "fast": 0.0469, "ultra fast": 0.1875}
    return growth_rates.get(gr_input.lower().strip(), 0.0469)

def sprinkler_sim(alpha, h, r, t_amb, t_act, rti, dt=1.0):
    """模擬噴灑頭啟動時間與當時的火災規模"""
    t, t_link = 0.0, t_amb
    while t <= 1800:
        q = alpha * (t**2)
        if q > 0.1:
            delta_t = (16.9 * q**(2/3)) / (h**(5/3)) if (r/h) <= 0.18 else (5.38 * (q/r)**(2/3)) / h
            u = 0.96 * (q/h)**(1/3) if (r/h) <= 0.15 else (0.197 * q**(1/3) * h**0.5) / (r**(5/6))
            t_link += (math.sqrt(max(0, u)) / rti) * ((t_amb + delta_t) - t_link) * dt
            if t_link >= t_act:
                return t, q
        t += dt
    return None, None

def calc_smoke_temp(q_design, z_req, t_amb):
    """計算特定規模下的煙層溫度"""
    q_conv = 0.7 * q_design
    # NFPA 92 Mass Flow
    m_s = (0.071 * q_conv**(1/3) * z_req**(5/3)) + (0.0018 * q_conv)
    if m_s <= 0: return t_amb
    t_smoke_k = (t_amb + 273.15) + (q_conv / (m_s * 1.01))
    return t_smoke_k - 273.15

# ==========================================
# 功能模組 (Functional Modules)
# ==========================================

def mode_smoke_extraction():
    print("\n--- 功能 1: 排煙量與防吸空分析 ---")
    gr = input("火災增長率 (slow/medium/fast/ultra fast): ")
    h = float(input("天花板高度 (m): "))
    r = float(input("噴灑頭距離 (m): "))
    t_act = float(input("動作溫度 (°C): "))
    rti = float(input("RTI: "))
    sf = float(input("安全係數 (SF): "))
    z_req = float(input("清晰高度 (m): "))
    t_amb = 25.0

    t_det, q_act = sprinkler_sim(get_alpha(gr), h, r, t_amb, t_act, rti)
    
    if t_det:
        q_design = q_act * sf
        q_conv = 0.7 * q_design
        m_s = (0.071 * q_conv**(1/3) * z_req**(5/3)) + (0.0018 * q_conv)
        t_smoke_k = (t_amb + 273.15) + (q_conv / (m_s * 1.01))
        v_total = m_s / (353 / t_smoke_k)
        v_max = 0.41 * ((h - z_req)**2.5) * math.sqrt(max(0, (t_smoke_k - (t_amb + 273.15)) / (t_amb + 273.15)))
        
        print(f"\n" + "-"*35)
        print(f"啟動時間: {t_det:.1f} s")
        print(f"啟動規模: {q_act:.2f} kW")
        print(f"煙層溫度: {t_smoke_k - 273.15:.2f} °C")
        print(f"總設計排煙量: {v_total:.2f} m³/s")
        print(f"單口限值: {v_max:.2f} m³/s")
        print(f"建議最少排煙口數量: {math.ceil(v_total / v_max)}")
        print("-"*35)
    else:
        print("\n噴灑頭未啟動。")

def mode_critical_tracking():
    print("\n--- 功能 2: 煙層下降關鍵時刻追蹤 ---")
    # 此處邏輯同前，已針對 2.0m 閾值優化
    gr = input("火災增長率: "); h = float(input("天花板高度: ")); a_room = float(input("面積: "))
    r = float(input("距離: ")); t_act = float(input("動作溫度: ")); rti = float(input("RTI: "))
    
    alpha = get_alpha(gr)
    t, dt, t_link, z_layer, act_time, t_haz, history = 0.0, 1.0, 25.0, h, None, None, []

    while t <= 1800:
        q = alpha * (t**2) if act_time is None else alpha * (act_time**2)
        if act_time is None:
            delta_t = (16.9 * q**(2/3)) / (h**(5/3)) if (r/h) <= 0.18 else (5.38 * (q/r)**(2/3)) / h
            u = 0.96 * (q/h)**(1/3) if (r/h) <= 0.15 else (0.197 * q**(1/3) * h**0.5) / (r**(5/6))
            t_link += (math.sqrt(max(0, u)) / rti) * ((25.0 + delta_t) - t_link) * dt
            if t_link >= t_act: act_time = t
        
        if q > 0.1:
            q_conv = 0.7 * q
            m_p = (0.071 * q_conv**(1/3) * z_layer**(5/3)) + (0.0018 * q_conv)
            v_in = m_p / (353 / ((25+273.15) + (q_conv/(max(0.1, m_p)*1.01))))
            z_layer -= (v_in / a_room); z_layer = max(0, z_layer)
        
        history.append({'t': t, 'z': z_layer})
        if t_haz is None and z_layer <= 2.0: t_haz = t
        if t_haz and (act_time or t > 1200): break
        t += dt

    if t_haz:
        print(f"\n時間: {t_haz:.1f}s, 煙層跌破 2.0m。")
    else:
        print("\n環境安全，煙層未降至 2.0m。")

def mode_hrr_plot():
    print("\n--- 功能 3: Sprinkler activation time calculation (Plot) ---")
    gr = input("火災增長率 (slow/medium/fast/ultra): ")
    h = float(input("天花板高度 (m): "))
    r = float(input("噴灑頭距離 (m): "))
    t_act = float(input("動作溫度 (°C): "))
    rti = float(input("RTI: "))
    z_req = float(input("參考清晰高度以計算煙溫 (m): "))
    t_amb = 25.0
    
    alpha = get_alpha(gr)
    t_det, q_act = sprinkler_sim(alpha, h, r, t_amb, t_act, rti)
    
    if t_det:
        # 計算啟動瞬間的煙層溫度 (假設 SF=1.0)
        t_smoke = calc_smoke_temp(q_act, z_req, t_amb)
        
        times = range(0, 1201, 2)
        hrr = [alpha*(t**2) if t < t_det else alpha*(t_det**2) for t in times]
        
        plt.figure(figsize=(10, 6))
        plt.plot(times, hrr, 'r-', linewidth=2)
        plt.axvline(x=t_det, color='g', linestyle='--')
        
        # 標籤與數據顯示
        info_text = (f"Activation Time: {t_det:.1f} s\n"
                     f"Heat Release Rate: {q_act:.2f} kW\n"
                     f"Smoke Temperature: {t_smoke:.2f} °C")
        
        plt.text(t_det + 20, q_act * 0.5, info_text, bbox=dict(facecolor='white', alpha=0.8))
        
        plt.title("Sprinkler activation time calculation")
        plt.xlabel("Time (s)")
        plt.ylabel("Heat Release Rate (kW)")
        plt.ylim(bottom=0)
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.show()
    else:
        print("\n噴灑頭未啟動，無法繪圖。")

# ==========================================
# 主選單 (Main Interface)
# ==========================================

def main():
    while True:
        print("\n" + "="*45)
        print(f"{'Sprinkler activation time calculation':^45}")
        print("="*45)
        print("1. 排煙需求與防吸空分析")
        print("2. 煙層下降關鍵時刻追蹤 (2.0m 閾值)")
        print("3. 繪製 HRR 發展曲線 (含啟動數據)")
        print("0. 退出程式")
        print("-" * 45)
        choice = input("請選擇功能序號: ")
        if choice == "1": mode_smoke_extraction()
        elif choice == "2": mode_critical_tracking()
        elif choice == "3": mode_hrr_plot()
        elif choice == "0": break
        else: print("無效選擇。")

if __name__ == "__main__":
    main()