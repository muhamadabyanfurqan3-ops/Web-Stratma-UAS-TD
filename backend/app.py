import streamlit as st
import time
import random
import math
import pandas as pd
import altair as alt

st.set_page_config(page_title="Simulasi TD", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS
st.markdown("""
<style>
/* Menghilangkan blackbar (header Streamlit) di atas */
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 2rem !important; }

.stApp {
    background-color: #5A1C73 !important;
    background-image: radial-gradient(circle, #7a2b99, #3f1052);
    color: #e2e8f0;
}
.metric-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
    padding: 20px;
    border-radius: 10px;
    border-left: 5px solid #3b82f6;
    color: white;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255,255,255,0.1);
}
.metric-title { font-size: 14px; color: #cbd5e1; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { font-size: 28px; font-weight: bold; margin-top: 5px; }
.log-box { height: 250px; overflow-y: auto; background-color: rgba(248, 250, 252, 0.9); border: 1px solid #e2e8f0; border-radius: 5px; padding: 10px; font-family: monospace; font-size: 12px; color: #334155;}
div[role="radiogroup"] {
    background: rgba(255,255,255,0.1);
    padding: 10px 15px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.2);
}
[data-testid="stToastContainer"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# 1. STATE INITIALIZATION
if 'game_running' not in st.session_state: st.session_state.game_running = False
if 'tick' not in st.session_state: st.session_state.tick = 0
if 'base_hp' not in st.session_state: st.session_state.base_hp = 4280
if 'max_base_hp' not in st.session_state: st.session_state.max_base_hp = 4280
if 'enemies' not in st.session_state: st.session_state.enemies = []
if 'turrets' not in st.session_state: st.session_state.turrets = []
if 'wave' not in st.session_state: st.session_state.wave = 0
if 'max_waves' not in st.session_state: st.session_state.max_waves = 30
if 'enemies_spawned_current_wave' not in st.session_state: st.session_state.enemies_spawned_current_wave = 0

if 'history_hp' not in st.session_state: st.session_state.history_hp = pd.DataFrame(columns=['Tick', 'Sisa HP Markas'])
if 'event_logs' not in st.session_state: st.session_state.event_logs = []
if 'total_damage' not in st.session_state: st.session_state.total_damage = 0
if 'total_kills' not in st.session_state: st.session_state.total_kills = 0
if 'upcoming_enemies' not in st.session_state: st.session_state.upcoming_enemies = pd.DataFrame(columns=['ID', 'HP Awal', 'Type'])
if 'visual_fx' not in st.session_state: st.session_state.visual_fx = []
if 'game_finished' not in st.session_state: st.session_state.game_finished = False
if 'game_lost' not in st.session_state: st.session_state.game_lost = False
if 'game_start_time' not in st.session_state: st.session_state.game_start_time = time.time()
if 'total_game_duration' not in st.session_state: st.session_state.total_game_duration = 0.0

def add_log(msg):
    st.session_state.event_logs.insert(0, f"[{st.session_state.tick}] {msg}")
    if len(st.session_state.event_logs) > 50:
        st.session_state.event_logs.pop()

def init_wave_data():
    is_last = (st.session_state.wave == st.session_state.max_waves)
    is_boss = (st.session_state.wave % 10 == 0 or is_last)
    is_mini = (st.session_state.wave % 5 == 0 and not is_boss)
    
    data = []
    num_enemies = random.randint(5, 10)
    
    if is_boss:
        data.append({'ID': f"BOSS_{st.session_state.wave}", 'HP Awal': random.randint(10000, 15000), 'Type': 'Boss'})
        for i in range(num_enemies - 1): data.append({'ID': f"Minion-{i+1}", 'HP Awal': random.randint(800, 1500), 'Type': 'Normal'})
    elif is_mini:
        data.append({'ID': f"MINI_BOSS_{st.session_state.wave}", 'HP Awal': random.randint(4500, 5500), 'Type': 'Mini-Boss'})
        for i in range(num_enemies - 1): data.append({'ID': f"W{st.session_state.wave}-{i+1}", 'HP Awal': random.randint(800, 1500), 'Type': 'Normal'})
    else:
        for i in range(num_enemies):
            hp = random.randint(800, 1500)
            data.append({'ID': f"W{st.session_state.wave}-{i+1}", 'HP Awal': hp, 'Type': 'Normal'})
            
    st.session_state.upcoming_enemies = pd.DataFrame(data)

def render_arena_html(is_preview, preview_turrets=[]):
    html_str = []
    html_str.append("<div style='position:relative; width:100%; aspect-ratio:7/5; background-color:#f1f5f9; border:4px solid rgba(255,255,255,0.3); border-radius:12px; overflow:hidden; box-shadow:inset 0 0 20px rgba(0,0,0,0.1);'>")
    
    # Garis Merah Batas Penempatan Turret
    html_str.append("<div style='position:absolute; top:0; left:25%; width:2px; height:100%; background-color:rgba(239, 68, 68, 0.7); box-shadow:0 0 10px rgba(239, 68, 68, 0.5); z-index:10; pointer-events:none;'></div>")
    html_str.append("<div style='position:absolute; bottom:10px; left:26%; font-size:12px; font-weight:bold; color:rgba(239, 68, 68, 0.8); z-index:10; pointer-events:none;'>DEPLOYMENT ZONE -></div>")
    
    if not is_preview:
        html_str.append(f"<div style='position:absolute; top:15px; left:20px; font-size:18px; font-weight:bold; color:#475569; z-index:40;'>Wave: {st.session_state.wave} / {st.session_state.max_waves}</div>")
    else:
        html_str.append(f"<div style='position:absolute; top:15px; left:20px; font-size:18px; font-weight:bold; color:#475569; z-index:40;'>⚙️ PREVIEW MODE</div>")
        
    hp_display = max(0, st.session_state.base_hp) if not is_preview else "MAX"
    html_str.append(f"<div style='position:absolute; top:0; right:0; width:8%; height:100%; background-color:#22c55e; display:flex; flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:900; box-shadow:-5px 0 15px rgba(34,197,94,0.4); z-index:30;'><div style='font-size:1.5vw;'>BASE</div><div style='font-size:1vw;'>{hp_display}</div></div>")

    if not is_preview and len(st.session_state.visual_fx) > 0:
        svg = "<svg style='position:absolute; top:0; left:0; width:100%; height:100%; z-index:15; pointer-events:none;'>"
        for fx in st.session_state.visual_fx:
            if fx["type"] == "laser":
                svg += f"<line x1='{fx['t_x']}%' y1='{fx['t_y']}%' x2='{fx['e_x']}%' y2='{fx['e_y']}%' stroke='#ff0000' stroke-width='4' />"
        svg += "</svg>"
        html_str.append(svg)

    turret_list = preview_turrets if is_preview else st.session_state.turrets
    
    # Radius tembakan dikecilkan menjadi 40% (dari 60%)
    for t in turret_list:
        turret_svg = "<svg viewBox='0 0 16 16' xmlns='http://www.w3.org/2000/svg' style='shape-rendering: crispEdges; width:100%; height:100%;'><rect x='5' y='1' width='6' height='14' fill='#000'/><rect x='3' y='2' width='10' height='12' fill='#000'/><rect x='2' y='3' width='12' height='10' fill='#000'/><rect x='1' y='5' width='14' height='6' fill='#000'/><rect x='5' y='2' width='6' height='12' fill='#475569'/><rect x='3' y='3' width='10' height='10' fill='#475569'/><rect x='2' y='5' width='12' height='6' fill='#475569'/><rect x='6' y='3' width='5' height='10' fill='#94a3b8'/><rect x='5' y='4' width='7' height='8' fill='#94a3b8'/><rect x='4' y='5' width='9' height='6' fill='#94a3b8'/><rect x='6' y='4' width='4' height='8' fill='#cbd5e1'/><rect x='0' y='6' width='8' height='4' fill='#000'/><rect x='0' y='7' width='8' height='2' fill='#e2e8f0'/><rect x='0' y='8' width='8' height='1' fill='#94a3b8'/></svg>"
        html_str.append(f"<div style='position:absolute; top:{t['y']}%; left:{t['x']}%; width:5%; aspect-ratio:1/1; transform:translate(-50%, -50%); z-index:20; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5));'>{turret_svg}</div>")
        html_str.append(f"<div style='position:absolute; top:{t['y']}%; left:{t['x']}%; width:40%; padding-bottom:40%; border:2px solid rgba(59,130,246,0.2); border-radius:50%; background-color:rgba(59,130,246,0.03); transform:translate(-50%, -50%); pointer-events:none; z-index:5;'></div>")

    if not is_preview:
        for e in st.session_state.enemies:
            hp_pct = max(0, min(100, (e['hp'] / e['max_hp']) * 100))
            color = "#22c55e" if hp_pct > 50 else ("#f59e0b" if hp_pct > 20 else "#ef4444")
            
            if e['type'] == 'Boss':
                size_pct, e_bg, icon = 6, "#991b1b", "💀"
            elif e['type'] == 'Mini-Boss':
                size_pct, e_bg, icon = 4.5, "#b91c1c", "👹"
            else:
                size_pct, e_bg, icon = 3, "#a855f7" if hp_pct > 50 else "#475569", ""
                
            html_str.append(f"<div style='position:absolute; top:{e['y']}%; left:{e['x']}%; width:{size_pct}%; transform:translate(-50%, -50%); z-index:25; display:flex; flex-direction:column; align-items:center;'>")
            html_str.append(f"<div style='width:120%; height:6px; background-color:#cbd5e1; border-radius:3px; margin-bottom:4px; overflow:hidden;'><div style='width:{hp_pct}%; height:100%; background-color:{color};'></div></div>")
            html_str.append(f"<div style='width:100%; aspect-ratio:1/1; background-color:{e_bg}; border-radius:50%; box-shadow:0 3px 5px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; font-size:1.5vw;'>{icon}</div>")
            html_str.append(f"<div style='font-size:0.9vw; font-family:monospace; font-weight:bold; color:#334155; margin-top:4px;'>{e['hp']}</div>")
            html_str.append("</div>")

        for fx in st.session_state.visual_fx:
            if fx["type"] == "dmg_text":
                progress = 1.0 - (fx["life"] / fx["max_life"])
                current_y = fx["y"] - (progress * 5)
                opacity = max(0, 1.0 - progress)
                html_str.append(f"<div style='position:absolute; top:{current_y}%; left:{fx['x']}%; opacity:{opacity}; transform:translate(-50%, -50%); z-index:50; font-size:1.5vw; font-weight:900; color:#f97316; text-shadow:2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;'>-{fx['dmg']}</div>")

    if not is_preview and st.session_state.get('game_finished', False):
        status_text = "GAME OVER!" if st.session_state.get('game_lost', False) else "GAME SELESAI!"
        status_color = "#ef4444" if st.session_state.get('game_lost', False) else "#4ade80"
        html_str.append(f"<div style='position:absolute; top:0; left:0; width:100%; height:100%; background-color:rgba(0,0,0,0.8); z-index:100; display:flex; flex-direction:column; align-items:center; justify-content:center; color:white; text-align:center;'><div style='font-size:4vw; font-weight:900; color:{status_color}; text-shadow:2px 2px 4px rgba(0,0,0,0.8); margin-bottom:10px; letter-spacing: 2px;'>{status_text}</div><div style='font-size:1.5vw; font-weight:bold; text-shadow:1px 1px 2px rgba(0,0,0,0.8); margin-bottom:8px;'>Waktu Penyelesaian: <span style='color:#fcd34d;'>{st.session_state.total_game_duration} detik</span></div><div style='font-size:1.5vw; font-weight:bold; text-shadow:1px 1px 2px rgba(0,0,0,0.8);'>Sisa HP Markas: <span style='color:#fcd34d;'>{max(0, st.session_state.base_hp)} / {st.session_state.max_base_hp}</span></div></div>")

    html_str.append("</div>")
    return "".join(html_str)

st.title("Simulasi Game Tower Defense")

# --- MODE PRE-GAME (SETUP) ---
if not st.session_state.game_running:
    st.markdown("Sistem Pertahanan Strategis dengan algoritma cerdas memprioritaskan ancaman berdarah terendah (*Greedy: Lowest HP First*).")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Membagi layout menjadi 3 kolom: Config (Kiri), Sliders (Tengah), Preview (Kanan)
    col_cfg, col_slider, col_prev = st.columns([1.2, 1.5, 2.5])
    
    with col_cfg:
        st.markdown("### Setup Defenses")
        cfg_waves = st.number_input("Total Waves", 1, 100, 30, help="Di wave kelipatan 5 akan ada Mini-Boss. Di wave terakhir ada Final Boss.")
        cfg_base_hp = st.number_input("Base HP Capacity", 1, 50000, 4280)
        cfg_turrets = st.number_input("Jumlah Turret", 1, 10, 3)
        st.markdown("<br>", unsafe_allow_html=True)
        
    preview_turret_list = []
    with col_slider:
        st.markdown("### Posisi Turret")
        st.caption("Atur X dan Y (Limit X > 25%)")
        for i in range(cfg_turrets):
            st.markdown(f"**T{i+1}**")
            cx, cy = st.columns(2)
            
            def_y = int(20 + (i * 60 / max(1, cfg_turrets-1))) if cfg_turrets > 1 else 50
            x_pos = cx.slider("X", 25, 85, 65, key=f"tx_{i}", label_visibility="collapsed")
            y_pos = cy.slider("Y", 5, 95, def_y, key=f"ty_{i}", label_visibility="collapsed")
            preview_turret_list.append({"id": i+1, "x": x_pos, "y": y_pos, "cd": 0})
            
    with col_prev:
        st.markdown("### Arena Preview")
        st.markdown(render_arena_html(is_preview=True, preview_turrets=preview_turret_list), unsafe_allow_html=True)

    # Tombol INITIATE dirender kembali di kolom konfigurasi (paling kiri)
    with col_cfg:
        if st.button("🚀 INITIATE DEFENSE", use_container_width=True, type="primary"):
            st.session_state.game_running = True
            st.session_state.tick = 0
            st.session_state.base_hp = cfg_base_hp
            st.session_state.max_base_hp = cfg_base_hp
            st.session_state.max_waves = cfg_waves
            st.session_state.wave = 1
            st.session_state.enemies_spawned_current_wave = 0
            st.session_state.enemies = []
            st.session_state.history_hp = pd.DataFrame([{'Tick': 0, 'Sisa HP Markas': cfg_base_hp}])
            st.session_state.event_logs = []
            st.session_state.total_damage = 0
            st.session_state.total_kills = 0
            st.session_state.visual_fx = []
            st.session_state.turrets = preview_turret_list
            st.session_state.game_finished = False
            st.session_state.game_lost = False
            st.session_state.game_start_time = time.time()
            st.session_state.total_game_duration = 0.0
            
            init_wave_data()
            add_log("SYSTEM INITIATED.")
            st.rerun()

# --- MODE GAME RUNNING ---
else:
    # GAME LOGIC UPDATE
    st.session_state.tick += 1
    
    new_fx = []
    for fx in st.session_state.visual_fx:
        fx["life"] -= 1
        if fx["life"] > 0:
            new_fx.append(fx)
    st.session_state.visual_fx = new_fx
    
    total_to_spawn = len(st.session_state.upcoming_enemies)
    if st.session_state.enemies_spawned_current_wave < total_to_spawn:
        if st.session_state.tick % 4 == 0:
            row_idx = st.session_state.enemies_spawned_current_wave
            hp = st.session_state.upcoming_enemies.iloc[row_idx]['HP Awal']
            eid = st.session_state.upcoming_enemies.iloc[row_idx]['ID']
            etype = st.session_state.upcoming_enemies.iloc[row_idx]['Type']
            
            if etype == 'Boss': base_speed = random.uniform(0.15, 0.25)
            elif etype == 'Mini-Boss': base_speed = random.uniform(0.3, 0.5)
            else: base_speed = random.uniform(0.5, 0.9)
            
            st.session_state.enemies.append({
                "id": eid, "hp": hp, "max_hp": hp, "x": 0.0, "y": random.uniform(20, 80), "type": etype, "speed": base_speed
            })
            st.session_state.enemies_spawned_current_wave += 1
            if etype == 'Boss' or etype == 'Mini-Boss':
                add_log(f"WARNING: {etype} '{eid}' detected!")
            else:
                add_log(f"Enemy {eid} spawned.")
                
    elif len(st.session_state.enemies) == 0:
        if st.session_state.wave < st.session_state.max_waves:
            st.session_state.wave += 1
            st.session_state.enemies_spawned_current_wave = 0
            init_wave_data()
            add_log(f"--- WAVE {st.session_state.wave} INITIATED ---")
        else:
            if not st.session_state.get('game_finished', False):
                st.session_state.game_finished = True
                st.session_state.total_game_duration = round(time.time() - st.session_state.game_start_time, 2)
                add_log("VICTORY ACHIEVED. GAME FINISHED.")

    surviving_enemies = []
    for e in st.session_state.enemies:
        e["x"] += e["speed"]
        
        if e["x"] >= 95:
            st.session_state.base_hp = max(0, st.session_state.base_hp - e["hp"])
            add_log(f"BASE BREACHED by {e['id']}! (-{e['hp']} HP)")
            
            if st.session_state.base_hp <= 0:
                if not st.session_state.get('game_finished', False):
                    st.session_state.game_finished = True
                    st.session_state.game_lost = True
                    st.session_state.total_game_duration = round(time.time() - st.session_state.game_start_time, 2)
                    add_log("CRITICAL FAILURE. BASE DESTROYED.")
        else:
            surviving_enemies.append(e)
            
    st.session_state.enemies = surviving_enemies
    if st.session_state.tick % 5 == 0:
        st.session_state.history_hp.loc[len(st.session_state.history_hp)] = {'Tick': st.session_state.tick, 'Sisa HP Markas': st.session_state.base_hp}

    for t in st.session_state.turrets:
        if t["cd"] > 0:
            t["cd"] -= 1
            continue
            
        # Penyesuaian kalkulasi radius menjadi 20% (mengikuti CSS 40% Width)
        in_range = [e for e in st.session_state.enemies if math.hypot(e["x"] - t["x"], (e["y"] - t["y"]) * (5/7)) <= 20]
        if in_range:
            target = min(in_range, key=lambda x: x["hp"])
            if random.random() < 0.05:
                add_log(f"T{t['id']} fired at {target['id']}... MISS!")
            else:
                dmg = random.randint(50, 650)
                target["hp"] -= dmg
                st.session_state.total_damage += dmg
                
                st.session_state.visual_fx.append({"type": "laser", "t_x": t["x"], "t_y": t["y"], "e_x": target["x"], "e_y": target["y"], "life": 2})
                st.session_state.visual_fx.append({"type": "dmg_text", "x": target["x"], "y": target["y"] - 5, "dmg": dmg, "life": 8, "max_life": 8})
                
                if target["hp"] <= 0:
                    st.session_state.enemies.remove(target)
                    st.session_state.total_kills += 1
                    add_log(f"T{t['id']} ELIMINATED {target['id']} (+{dmg} DMG)")
            t["cd"] = 3

    # RENDER UI
    col_hdr1, col_hdr2 = st.columns([3, 1])
    with col_hdr2:
        if st.button("🛑 STOP & RESET", use_container_width=True):
            st.session_state.game_running = False
            add_log("SIMULATION HALTED.")
            st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='metric-card'><div class='metric-title'>Current Wave</div><div class='metric-value'>{st.session_state.wave} / {st.session_state.max_waves}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-card' style='border-left-color: {'#22c55e' if st.session_state.base_hp > st.session_state.max_base_hp*0.3 else '#ef4444'};'><div class='metric-title'>Base HP Integrity</div><div class='metric-value'>{max(0, st.session_state.base_hp)}</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric-card' style='border-left-color: #f59e0b;'><div class='metric-title'>Targets Eliminated</div><div class='metric-value'>{st.session_state.total_kills}</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='metric-card' style='border-left-color: #8b5cf6;'><div class='metric-title'>Damage Output</div><div class='metric-value'>{st.session_state.total_damage:,}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2.5, 1.2])

    with col_left:
        st.markdown("### Live Tactical Arena")
        st.markdown(render_arena_html(is_preview=False), unsafe_allow_html=True)

    with col_right:
        sim_speed = st.radio("⏱️ Fast Forward", [1, 2, 3, 4, 5], index=0, format_func=lambda x: f"{x}x Speed", horizontal=True)
        
        st.markdown("**📉 Base Integrity Chart**")
        if not st.session_state.history_hp.empty:
            chart = alt.Chart(st.session_state.history_hp).mark_area(
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#22c55e', offset=0),
                           alt.GradientStop(color='rgba(34, 197, 94, 0.1)', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                ),
                line={'color': '#16a34a'}
            ).encode(
                x='Tick:Q',
                y=alt.Y('Sisa HP Markas:Q', scale=alt.Scale(domain=[0, st.session_state.max_base_hp])),
                tooltip=['Tick', 'Sisa HP Markas']
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Awaiting simulation data...")

        st.markdown("**📋 Tactical Log**")
        log_html_box = "<div class='log-box' style='height:200px;'>" + "<br>".join(st.session_state.event_logs) + "</div>"
        st.markdown(log_html_box, unsafe_allow_html=True)

    if st.session_state.game_running and not st.session_state.get('game_finished', False):
        base_delay = 0.1
        time.sleep(base_delay / sim_speed)
        st.rerun()
