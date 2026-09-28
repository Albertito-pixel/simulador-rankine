import streamlit as st
import CoolProp.CoolProp as CP
import plotly.graph_objects as go
import numpy as np
import json
import time
from PIL import Image
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILO INDUSTRIAL
# ==========================================
st.set_page_config(
    page_title="Termo Rankine | Simulador & Solucionador",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
    }
    
    .hero-box {
        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.2rem;
    }
    
    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
    }
    
    .hero-sub {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    
    .incisos-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 1.5rem;
        color: #e5e7eb;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-box">
    <div class="hero-title">⚡ TermoRankine Pro</div>
    <div class="hero-sub">Simulador interactivo con diagramas T-s rigurosos, Primera y Segunda Ley, y resolución analítica por IA.</div>
</div>
""", unsafe_allow_html=True)

API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# VARIABLES POR DEFECTO
# ==========================================
defaults = {
    "P_cald": 3000.0,
    "T_max": 350.0,
    "P_cond": 75.0,
    "tiene_recal": False,
    "P_recal": 1000.0,
    "T_recal": 350.0,
    "num_fwh": 0,
    "fwh_data": [],
    "eta_t": 100.0,
    "eta_p": 100.0,
    "TH": 800.0,
    "T0": 300.0,
    "solucion_texto": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN COMPLETA
# ==========================================
st.sidebar.markdown("### ⚡ Parámetros del Ciclo")

metodo = st.sidebar.radio(
    "Modo de ingreso:",
    ["✍️ Manual", "📷 Captura con IA"],
    horizontal=True
)

if metodo == "📷 Captura con IA":
    archivo = st.sidebar.file_uploader("Subir problema / diagrama", type=["png", "jpg", "jpeg", "webp"])
    if archivo:
        img = Image.open(archivo)
        if st.sidebar.button("🔍 Analizar y Cargar", type="primary", use_container_width=True):
            with st.spinner("Procesando imagen con IA..."):
                prompt = """
                Eres un profesor experto de Termodinámica técnica. Analiza la imagen.
                Devuelve ÚNICAMENTE un JSON con:
                {
                  "P_cald_kPa": float,
                  "T_max_C": float,
                  "P_cond_kPa": float,
                  "tiene_recal": bool,
                  "P_recal_kPa": float o null,
                  "T_recal_C": float o null,
                  "num_fwh": int,
                  "fwh_lista": [
                     {"tipo": "Abierto (CAA)" o "Cerrado (CCA)", "presion_kPa": float}
                  ],
                  "eta_t": float,
                  "eta_p": float,
                  "TH_K": float,
                  "T0_K": float,
                  "respuestas_directas": "Markdown con la resolución y resultados de los incisos a), b), etc."
                }
                """
                datos = None
                for intento in range(3):
                    try:
                        res = client.models.generate_content(
                            model="gemini-flash-latest",
                            contents=[img, prompt],
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        datos = json.loads(res.text)
                        break
                    except Exception:
                        time.sleep(2)
                
                if datos:
                    st.session_state["P_cald"] = float(datos.get("P_cald_kPa", st.session_state["P_cald"]))
                    st.session_state["T_max"] = float(datos.get("T_max_C", st.session_state["T_max"]))
                    st.session_state["P_cond"] = float(datos.get("P_cond_kPa", st.session_state["P_cond"]))
                    st.session_state["tiene_recal"] = bool(datos.get("tiene_recal", False))
                    if datos.get("P_recal_kPa"):
                        st.session_state["P_recal"] = float(datos.get("P_recal_kPa"))
                    if datos.get("T_recal_C"):
                        st.session_state["T_recal"] = float(datos.get("T_recal_C"))
                    fwh_l = datos.get("fwh_lista", [])
                    st.session_state["num_fwh"] = len(fwh_l)
                    st.session_state["fwh_data"] = [
                        {"tipo": f.get("tipo", "Abierto (CAA)"), "presion": float(f.get("presion_kPa", 1000.0))}
                        for f in fwh_l
                    ]
                    st.session_state["eta_t"] = float(datos.get("eta_t", 100.0))
                    st.session_state["eta_p"] = float(datos.get("eta_p", 100.0))
                    st.session_state["TH"] = float(datos.get("TH_K", 800.0))
                    st.session_state["T0"] = float(datos.get("T0_K", 300.0))
                    st.session_state["solucion_texto"] = datos.get("respuestas_directas", "")
                    st.sidebar.success("¡Datos cargados!")
                    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Fronteras del Ciclo:**")
P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=250.0)
T_max = st.sidebar.number_input("Vapor Vivo (T_max) [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=5.0)

st.sidebar.markdown("---")
tiene_recal = st.sidebar.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
if tiene_recal:
    P_recal = st.sidebar.number_input("Presión Recalentador [kPa]", value=float(st.session_state["P_recal"]), step=200.0)
    T_recal = st.sidebar.number_input("Temp. Recalentamiento [°C]", value=float(st.session_state["T_recal"]), step=10.0)
else:
    P_recal, T_recal = 1000.0, 350.0

st.sidebar.markdown("---")
num_fwh = st.sidebar.number_input("Número de Calentadores (FWH)", min_value=0, max_value=6, value=int(st.session_state["num_fwh"]))
fwh_configuracion = []
for i in range(num_fwh):
    st.sidebar.markdown(f"**Calentador #{i+1}:**")
    t_def = "Abierto (CAA)"
    p_def = float(P_cald / (i + 2))
    if i < len(st.session_state["fwh_data"]):
        t_def = st.session_state["fwh_data"][i]["tipo"]
        p_def = float(st.session_state["fwh_data"][i]["presion"])
    tipo_sel = st.sidebar.selectbox(f"Tipo #{i+1}", ["Abierto (CAA)", "Cerrado (CCA)"], index=0 if "Abierto" in t_def or "CAA" in t_def else 1, key=f"t_{i}")
    p_sel = st.sidebar.number_input(f"Presión #{i+1} [kPa]", min_value=float(P_cond), max_value=float(P_cald), value=p_def, step=100.0, key=f"p_{i}")
    fwh_configuracion.append({"tipo": tipo_sel, "presion": p_sel})

with st.sidebar.expander("Máquinas y Entorno (2da Ley)"):
    eta_t = st.slider("Isentrópica Turbina (η_t)", 0.50, 1.00, float(st.session_state["eta_t"]/100.0), 0.01)
    eta_p = st.slider("Isentrópica Bomba (η_p)", 0.50, 1.00, float(st.session_state["eta_p"]/100.0), 0.01)
    TH = st.number_input("Temp. Fuente (T_H) [K]", value=float(st.session_state["TH"]))
    T0 = st.number_input("Temp. Ambiente (T_0) [K]", value=float(st.session_state["T0"]))

def resolver_manual_con_ia():
    desc_fwh = "\n".join([f"- Calentador #{i+1}: {c['tipo']} a {c['presion']} kPa" for i, c in enumerate(fwh_configuracion)])
    prompt_manual = f"""
    Eres un profesor de Termodinámica experto en ciclos Rankine del libro de Çengel.
    El estudiante configuró estos parámetros del ciclo:
    - Presión Caldera: {P_cald} kPa ({(P_cald/1000):.2f} MPa)
    - Temperatura Entrada Turbina: {T_max} °C
    - Presión Condensador: {P_cond} kPa
    - Recalentamiento: {"Sí, a " + str(P_recal) + " kPa y " + str(T_recal) + " °C" if tiene_recal else "No"}
    - Calentadores FWH: {num_fwh}
    {desc_fwh if num_fwh > 0 else "- Ninguno"}
    - Eficiencias Isentrópicas: Turbina {eta_t*100:.1f}%, Bomba {eta_p*100:.1f}%
    - Entorno: T_fuente = {TH} K, T_ambiente = {T0} K

    TAREA:
    Resuelve detalladamente:
    1. Propiedades en cada estado (h1, h2, h3, h4, etc. en kJ/kg y s en kJ/kg·K).
    2. Si tiene calentadores, calcula las fracciones extraídas (y, z) con los balances de energía.
    3. Trabajo de la bomba, trabajo de la turbina, trabajo neto y calor suministrado (Qin).
    4. Eficiencia térmica de la Primera Ley (η_th).
    5. Análisis de la Segunda Ley:
       - Destrucción de exergía en cada uno de los 4 procesos (Bomba, Caldera, Turbina, Condensador) y la total (X_dest = T0 * S_gen).
       - Eficiencia de la Segunda Ley (η_II = W_neto / W_rev).
    Muestra los resultados finales en negrita.
    """
    for intento in range(3):
        try:
            res_m = client.models.generate_content(
                model="gemini-flash-latest",
                contents=[prompt_manual]
            )
            st.session_state["solucion_texto"] = res_m.text
            break
        except Exception:
            time.sleep(2)

st.sidebar.markdown("---")
if st.sidebar.button("⚡ Resolver Ciclo con IA", type="primary", use_container_width=True):
    with st.spinner("Calculando balances y Segunda Ley con IA..."):
        resolver_manual_con_ia()
        st.sidebar.success("¡Solución analítica generada!")
        st.rerun()

# ==========================================
# CÁLCULOS TERMODINÁMICOS REALES (CoolProp)
# ==========================================
fluido = 'Water'
P_cald_Pa = P_cald * 1e3
P_cond_Pa = P_cond * 1e3
T_max_K = T_max + 273.15
P_recal_Pa = P_recal * 1e3
T_recal_K = T_recal + 273.15

def get_T_safe(P_val, H_val):
    try:
        h_f = CP.PropsSI('H', 'P', P_val, 'Q', 0, fluido)
        h_g = CP.PropsSI('H', 'P', P_val, 'Q', 1, fluido)
        if h_f <= H_val <= h_g:
            return CP.PropsSI('T', 'P', P_val, 'Q', 0, fluido) - 273.15
        return CP.PropsSI('T', 'P', P_val, 'H', H_val, fluido) - 273.15
    except Exception:
        return CP.PropsSI('T', 'P', P_val, 'Q', 0, fluido) - 273.15

try:
    h1 = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
    T1 = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

    h_in_turb = CP.PropsSI('H', 'P', P_cald_Pa, 'T', T_max_K, fluido)
    s_in_turb = CP.PropsSI('S', 'P', P_cald_Pa, 'T', T_max_K, fluido)

    if tiene_recal:
        h_rec_s = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
        h_rec_sal = h_in_turb - eta_t * (h_in_turb - h_rec_s)
        s_rec_sal = CP.PropsSI('S', 'P', P_recal_Pa, 'H', h_rec_sal, fluido)
        T_rec_sal = get_T_safe(P_recal_Pa, h_rec_sal)

        h_rec_in2 = CP.PropsSI('H', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
        s_rec_in2 = CP.PropsSI('S', 'P', P_recal_Pa, 'T', T_recal_K, fluido)

        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_rec_in2, fluido)
        h_out_turb = h_rec_in2 - eta_t * (h_rec_in2 - h_out_s)
        w_t = (h_in_turb - h_rec_sal) + (h_rec_in2 - h_out_turb)
        q_recal = h_rec_in2 - h_rec_sal
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = get_T_safe(P_cond_Pa, h_out_turb)
    else:
        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_in_turb, fluido)
        h_out_turb = h_in_turb - eta_t * (h_in_turb - h_out_s)
        w_t = h_in_turb - h_out_turb
        q_recal = 0.0
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = get_T_safe(P_cond_Pa, h_out_turb)

    w_b = v1 * (P_cald_Pa - P_cond_Pa) / eta_p
    h2 = h1 + w_b
    s2 = CP.PropsSI('S', 'P', P_cald_Pa, 'H', h2, fluido)
    T2 = get_T_safe(P_cald_Pa, h2)

    q_in = (h_in_turb - h2) + q_recal
    q_out = h_out_turb - h1
    w_neto = w_t - w_b
    eta_th = (w_neto / q_in) * 100.0

    w_rev = q_in * (1.0 - (T0 / TH))
    eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

    # ==========================================
    # PESTAÑAS PRINCIPALES DE VISUALIZACIÓN
    # ==========================================
    tab_ts, tab_estados, tab_procedimiento = st.tabs([
        "📈 Diagrama T-s Interactivo", 
        "📋 Estados Termodinámicos", 
        "📝 Procedimiento / Incisos"
    ])

    with tab_ts:
        st.markdown(f"**Diagrama T-s — Rankine {'regenerativo con recalentamiento' if tiene_recal and num_fwh>0 else 'ideal simple' if num_fwh==0 and not tiene_recal else 'con recalentamiento'}**")
        st.caption("Pasa el cursor sobre los puntos para inspeccionar las propiedades exactas de cada estado.")

        T_crit = CP.PropsSI('Tcrit', fluido)
        T_campana = np.linspace(273.16, T_crit - 0.2, 220)
        s_liq = [CP.PropsSI('S', 'T', t, 'Q', 0, fluido)/1e3 for t in T_campana]
        s_vap = [CP.PropsSI('S', 'T', t, 'Q', 1, fluido)/1e3 for t in T_campana]

        fig = go.Figure()

        # Campana de saturación
        fig.add_trace(go.Scatter(
            x=s_liq + s_vap[::-1],
            y=[t - 273.15 for t in T_campana] + [t - 273.15 for t in T_campana[::-1]],
            mode='lines',
            line=dict(color='#475569', width=2),
            name='Campana de Saturación',
            hoverinfo='skip'
        ))

        # Trazador de Isóbaras
        def add_isobara(P_pa, nombre):
            try:
                T_sat = CP.PropsSI('T', 'P', P_pa, 'Q', 0, fluido) - 273.15
                s_f = CP.PropsSI('S', 'P', P_pa, 'Q', 0, fluido)/1e3
                s_g = CP.PropsSI('S', 'P', P_pa, 'Q', 1, fluido)/1e3
                T_sup = np.linspace(T_sat + 0.1, min(650.0, T_max + 30.0), 30)
                s_sup = [CP.PropsSI('S', 'P', P_pa, 'T', t + 273.15, fluido)/1e3 for t in T_sup]

                fig.add_trace(go.Scatter(
                    x=[s_f, s_g] + list(s_sup),
                    y=[T_sat, T_sat] + list(T_sup),
                    mode='lines',
                    line=dict(color='#334155', width=1, dash='dot'),
                    name=nombre,
                    hoverinfo='skip'
                ))
            except Exception:
                pass

        add_isobara(P_cond_Pa, f"{P_cond:.0f} kPa")
        if tiene_recal:
            add_isobara(P_recal_Pa, f"{P_recal/1e3:.1f} MPa")
        add_isobara(P_cald_Pa, f"{P_cald/1e3:.1f} MPa")

        # ====================================================
        # TRAZADO DEL CICLO SEGÚN LA CONFIGURACIÓN
        # ====================================================
        if tiene_recal and num_fwh >= 2:
            p_fwh_abierto = min(f['presion'] for f in fwh_configuracion) * 1e3
            h_10_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
            t_10 = get_T_safe(P_recal_Pa, h_10_iso)
            h_12_iso = CP.PropsSI('H', 'P', p_fwh_abierto, 'S', s_rec_in2, fluido)
            t_12 = get_T_safe(p_fwh_abierto, h_12_iso)

            s_3 = CP.PropsSI('S', 'P', p_fwh_abierto, 'Q', 0, fluido)/1e3
            t_3 = CP.PropsSI('T', 'P', p_fwh_abierto, 'Q', 0, fluido) - 273.15
            s_6 = CP.PropsSI('S', 'P', P_recal_Pa, 'Q', 0, fluido)/1e3
            t_6 = CP.PropsSI('T', 'P', P_recal_Pa, 'Q', 0, fluido) - 273.15

            T_cald_c = np.linspace(t_6 + 273.15, T_max_K, 20)
            s_cald_c = [CP.PropsSI('S', 'P', P_cald_Pa, 'T', t, fluido)/1e3 for t in T_cald_c]
            T_rec_c = np.linspace(t_10 + 273.15, T_recal_K, 15)
            s_rec_c = [CP.PropsSI('S', 'P', P_recal_Pa, 'T', t, fluido)/1e3 for t in T_rec_c]

            x_ciclo = [s1/1e3, s1/1e3, s_3, s_3] + s_cald_c + [s_in_turb/1e3, s_in_turb/1e3] + s_rec_c + [s_rec_in2/1e3, s_out_turb/1e3, s1/1e3]
            y_ciclo = [T1, T1+4, t_3, t_3+8] + [t-273.15 for t in T_cald_c] + [T_max, t_10] + [t-273.15 for t in T_rec_c] + [T_recal, T_out_turb, T1]

            fig.add_trace(go.Scatter(
                x=x_ciclo,
                y=y_ciclo,
                mode='lines',
                line=dict(color='#f97316', width=2.4),
                name='Ciclo Principal',
                hoverinfo='none'
            ))

            fig.add_trace(go.Scatter(
                x=[s_in_turb/1e3, s_6],
                y=[t_10, t_6],
                mode='lines',
                line=dict(color='#a855f7', width=1.8, dash='dash'),
                name='Extracción a CCA (y)'
            ))
            fig.add_trace(go.Scatter(
                x=[s_rec_in2/1e3, s_3],
                y=[t_12, t_3],
                mode='lines',
                line=dict(color='#a855f7', width=1.8, dash='dash'),
                name='Extracción a CAA (z)'
            ))

            puntos_x = [s1/1e3, s_3, s_6, s_in_turb/1e3, s_in_turb/1e3, s_rec_in2/1e3, s_rec_in2/1e3, s_out_turb/1e3]
            puntos_y = [T1, t_3, t_6, T_max, t_10, T_recal, t_12, T_out_turb]
            puntos_txt = ["1", "3", "6", "9", "10", "11", "12", "13"]

            fig.add_trace(go.Scatter(
                x=puntos_x,
                y=puntos_y,
                mode='markers+text',
                marker=dict(color='#f9fafb', size=7, line=dict(color='#f97316', width=2)),
                text=puntos_txt,
                textposition="top right",
                textfont=dict(color='#f9fafb', size=11),
                name='Estados',
                hovertemplate="<b>Estado %{text}</b><br>s: %{x:.3f} kJ/kg·K<br>T: %{y:.1f} °C<extra></extra>"
            ))
        else:
            # CICLO RANKINE SIMPLE O CON RECALENTAMIENTO (Rigoroso siguiendo la isóbara)
            T_sat_cald = CP.PropsSI('T', 'P', P_cald_Pa, 'Q', 0, fluido) - 273.15
            s_f_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 0, fluido) / 1e3
            s_g_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 1, fluido) / 1e3

            # Exageración visual del estado 2 (como en los libros de texto)
            T2_vis = T1 + max(30.0, (T_sat_cald - T1) * 0.18)

            # 1. Calentamiento líquido hasta saturación (sigue la campana de líquido)
            T_liq = np.linspace(T2_vis, T_sat_cald, 25)
            s_liq_line = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_liq]

            # 2. Sobrecalentamiento hasta T_max a lo largo de P_cald
            T_sup = np.linspace(T_sat_cald + 0.1, T_max, 25)
            s_sup_line = [CP.PropsSI('S', 'P', P_cald_Pa, 'T', t + 273.15, fluido)/1e3 for t in T_sup]

            # Trayectoria completa del ciclo
            x_ciclo = [s1/1e3, s1/1e3] + s_liq_line + [s_f_cald, s_g_cald] + s_sup_line + [s_out_turb/1e3, s1/1e3]
            y_ciclo = [T1, T2_vis] + list(T_liq) + [T_sat_cald, T_sat_cald] + list(T_sup) + [T_out_turb, T1]

            fig.add_trace(go.Scatter(
                x=x_ciclo,
                y=y_ciclo,
                mode='lines',
                line=dict(color='#f97316', width=2.4),
                name='Ciclo Principal',
                hoverinfo='skip'
            ))

            # Marcadores y textos en posiciones separadas para evitar colisiones
            pts_x = [s1/1e3, s1/1e3, s_in_turb/1e3, s_out_turb/1e3]
            pts_y = [T1, T2_vis, T_max, T_out_turb]
            pts_txt = ["1", "2", "3", "4"]
            pts_pos = ["bottom left", "top left", "top right", "bottom right"]
            
            pts_hover = [
                f"<b>Estado 1 (Salida Condensador)</b><br>T: {T1:.2f} °C<br>s: {s1/1e3:.4f} kJ/kg·K<br>P: {P_cond:.1f} kPa",
                f"<b>Estado 2 (Salida Bomba)</b><br>T real: {T2:.2f} °C (elevado en escala didáctica)<br>s: {s2/1e3:.4f} kJ/kg·K<br>P: {P_cald:.1f} kPa",
                f"<b>Estado 3 (Entrada Turbina)</b><br>T: {T_max:.2f} °C<br>s: {s_in_turb/1e3:.4f} kJ/kg·K<br>P: {P_cald:.1f} kPa",
                f"<b>Estado 4 (Salida Turbina)</b><br>T: {T_out_turb:.2f} °C<br>s: {s_out_turb/1e3:.4f} kJ/kg·K<br>P: {P_cond:.1f} kPa"
            ]

            fig.add_trace(go.Scatter(
                x=pts_x,
                y=pts_y,
                mode='markers+text',
                marker=dict(color='#f9fafb', size=7, line=dict(color='#f97316', width=2)),
                text=pts_txt,
                textposition=pts_pos,
                textfont=dict(color='#f9fafb', size=12, family="JetBrains Mono"),
                name='Estados (1-4)',
                hovertemplate="%{customdata}<extra></extra>",
                customdata=pts_hover
            ))

        fig.update_layout(
            paper_bgcolor='#0b0f19',
            plot_bgcolor='#0b0f19',
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(
                title=dict(text='Entropía, s [kJ/kg · K]', font=dict(color='#9ca3af', size=12)),
                tickfont=dict(color='#9ca3af'),
                gridcolor='#1e293b',
                zeroline=False,
                range=[0.0, 9.2]
            ),
            yaxis=dict(
                title=dict(text='Temperatura, T [°C]', font=dict(color='#9ca3af', size=12)),
                tickfont=dict(color='#9ca3af'),
                gridcolor='#1e293b',
                zeroline=False,
                range=[-10, max(680.0, T_max + 50.0)]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color='#9ca3af', size=10)
            ),
            height=540
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_estados:
        st.markdown("#### Tabla de Estados Termodinámicos")
        filas = [
            {"Estado": "1 (Salida Condensador)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T1:.1f}", "h [kJ/kg]": f"{h1/1e3:.2f}", "s [kJ/kg·K]": f"{s1/1e3:.4f}"},
            {"Estado": "2 (Salida Bomba Principal)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T2:.1f}", "h [kJ/kg]": f"{h2/1e3:.2f}", "s [kJ/kg·K]": f"{s2/1e3:.4f}"},
            {"Estado": "Entrada Turbina AP", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T_max:.1f}", "h [kJ/kg]": f"{h_in_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_in_turb/1e3:.4f}"},
            {"Estado": "Salida Turbina / Condensador", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_out_turb:.1f}", "h [kJ/kg]": f"{h_out_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_out_turb/1e3:.4f}"}
        ]
        st.dataframe(filas, use_container_width=True, hide_index=True)

        if num_fwh > 0:
            st.markdown("#### Calentadores FWH Configurados")
            t_fwh = []
            for idx, c in enumerate(fwh_configuracion):
                t_fwh.append({
                    "Calentador": f"FWH #{idx+1}",
                    "Tipo": c["tipo"],
                    "P [kPa]": f"{c['presion']:.0f}",
                    "P [MPa]": f"{(c['presion']/1000.0):.2f}"
                })
            st.dataframe(t_fwh, use_container_width=True, hide_index=True)

    with tab_procedimiento:
        st.markdown("#### Solución Analítica de los Incisos (Paso a Paso)")
        
        col_btn, _ = st.columns([1.5, 2])
        with col_btn:
            if st.button("⚡ Calcular / Actualizar Solución con IA", type="primary", use_container_width=True):
                with st.spinner("Generando solución analítica completa con IA..."):
                    resolver_manual_con_ia()
                    st.rerun()

        if st.session_state["solucion_texto"]:
            st.markdown(f'<div class="incisos-box">{st.session_state["solucion_texto"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Configura los parámetros en la barra lateral izquierda y presiona el botón **'⚡ Resolver Ciclo con IA'** para generar el procedimiento completo.")

except Exception as err:
    st.error(f"Error procesando propiedades en CoolProp: {err}")
