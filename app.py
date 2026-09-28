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
    page_title="TermoRankine Pro | Simulador & Solucionador",
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
        border-left: 4px solid #ff6b35;
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
    <div class="hero-sub">Simulador térmico de ciclos de potencia, diagramas T-s estilo textbook y memoria de cálculo analítica.</div>
</div>
""", unsafe_allow_html=True)

API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# VARIABLES POR DEFECTO (EJEMPLO 10-6 ÇENGEL)
# ==========================================
defaults = {
    "P_cald": 15000.0,
    "T_max": 600.0,
    "P_cond": 10.0,
    "tiene_recal": True,
    "P_recal": 4000.0,
    "T_recal": 600.0,
    "num_fwh": 2,
    "fwh_data": [
        {"tipo": "Cerrado (CCA)", "presion": 4000.0},
        {"tipo": "Abierto (CAA)", "presion": 500.0}
    ],
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
# BARRA LATERAL: CONFIGURACIÓN
# ==========================================
st.sidebar.markdown("### ⚡ Parámetros del Ciclo")

metodo = st.sidebar.radio(
    "Modo de ingreso:",
    ["✍️ Manual", "📷 Cargar Imagen / Enunciado"],
    horizontal=True
)

if metodo == "📷 Cargar Imagen / Enunciado":
    archivo = st.sidebar.file_uploader("Subir diagrama o enunciado del problema", type=["png", "jpg", "jpeg", "webp"])
    if archivo:
        img = Image.open(archivo)
        if st.sidebar.button("🔍 Extraer Datos y Procesar", type="primary", use_container_width=True):
            with st.spinner("Extrayendo parámetros termodinámicos..."):
                prompt = """
                Eres un profesor titular de Termodinámica de ingeniería técnica. Analiza el problema.
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
                  "respuestas_directas": "Markdown con la memoria de cálculo analítica detallada y resultados de los incisos a), b), etc."
                }
                Reglas: presiones en kPa (ej: 15 MPa = 15000, 4 MPa = 4000, 0.5 MPa = 500, 10 kPa = 10).
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
                    st.sidebar.success("¡Parámetros cargados con éxito!")
                    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Fronteras del Ciclo:**")
P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=500.0)
T_max = st.sidebar.number_input("Temperatura Entrada Turbina [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=1.0)

st.sidebar.markdown("---")
tiene_recal = st.sidebar.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
if tiene_recal:
    P_recal = st.sidebar.number_input("Presión Recalentador [kPa]", value=float(st.session_state["P_recal"]), step=200.0)
    T_recal = st.sidebar.number_input("Temp. Recalentamiento [°C]", value=float(st.session_state["T_recal"]), step=10.0)
else:
    P_recal, T_recal = 4000.0, 600.0

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

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Apariencia del Gráfico")
color_ciclo = st.sidebar.color_picker("Color de la Línea del Ciclo", value="#ff6b35")
color_campana = st.sidebar.color_picker("Color de la Campana", value="#47505e")

def resolver_manual_analitico():
    desc_fwh = "\n".join([f"- Calentador #{i+1}: {c['tipo']} a {c['presion']} kPa" for i, c in enumerate(fwh_configuracion)])
    prompt_manual = f"""
    Eres un profesor titular de Termodinámica técnica experto en el libro de Çengel.
    Se configuraron estos parámetros exactos del ciclo:
    - Presión Caldera: {P_cald} kPa ({(P_cald/1000):.2f} MPa)
    - Temperatura Vapor Vivo: {T_max} °C
    - Presión Condensador: {P_cond} kPa
    - Recalentamiento: {"Sí, a " + str(P_recal) + " kPa y " + str(T_recal) + " °C" if tiene_recal else "No"}
    - Calentadores FWH: {num_fwh}
    {desc_fwh if num_fwh > 0 else "- Ninguno"}
    - Eficiencias Isentrópicas: Turbina {eta_t*100:.1f}%, Bomba {eta_p*100:.1f}%
    - Entorno: T_fuente = {TH} K, T_ambiente = {T0} K

    TAREA:
    Elabora una memoria de cálculo analítica rigurosa:
    1. Propiedades termodinámicas en cada estado (entalpías en kJ/kg y entropías en kJ/kg·K).
    2. Fracciones de extracción (y, z) aplicando balances de masa y energía en cada calentador.
    3. Trabajo de las bombas, turbinas, trabajo neto y calor suministrado (Qin).
    4. Eficiencia térmica de la Primera Ley (η_th).
    5. Análisis de Segunda Ley: destrucción de exergía en cada equipo (X_dest = T0 * S_gen) y eficiencia exergética (η_II).
    Presenta fórmulas claras y resalta los resultados numéricos finales en negrita.
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
if st.sidebar.button("⚡ Calcular Procedimiento Paso a Paso", type="primary", use_container_width=True):
    with st.spinner("Calculando balances de masa, energía y 2da Ley..."):
        resolver_manual_analitico()
        st.sidebar.success("¡Memoria de cálculo generada!")
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
    # PESTAÑAS PRINCIPALES
    # ==========================================
    tab_ts, tab_estados, tab_procedimiento = st.tabs([
        "📈 Diagrama T-s Interactivo", 
        "📋 Estados Termodinámicos", 
        "📝 Procedimiento / Incisos"
    ])

    with tab_ts:
        def fmt_p(p_kpa):
            return f"{p_kpa/1000:.1f} MPa" if p_kpa >= 1000 else f"{p_kpa:.0f} kPa"

        str_pcald = fmt_p(P_cald)
        str_pcond = fmt_p(P_cond)

        # Campana de saturación
        T_crit = CP.PropsSI('Tcrit', fluido)
        T_campana = np.linspace(273.16, T_crit - 0.2, 250)
        s_liq = [CP.PropsSI('S', 'T', t, 'Q', 0, fluido)/1e3 for t in T_campana]
        s_vap = [CP.PropsSI('S', 'T', t, 'Q', 1, fluido)/1e3 for t in T_campana]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=s_liq + s_vap[::-1],
            y=[t - 273.15 for t in T_campana] + [t - 273.15 for t in T_campana[::-1]],
            mode='lines',
            line=dict(color=color_campana, width=1.4),
            name='Campana',
            hoverinfo='skip'
        ))

        # Propiedades caldera
        T_sat_cald = CP.PropsSI('T', 'P', P_cald_Pa, 'Q', 0, fluido) - 273.15
        s_f_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 0, fluido) / 1e3
        s_g_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 1, fluido) / 1e3
        T_sup = np.linspace(T_sat_cald + 0.1, T_max, 35)
        s_sup = [CP.PropsSI('S', 'P', P_cald_Pa, 'T', t + 273.15, fluido)/1e3 for t in T_sup]

        flechas_anotaciones = [
            dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{str_pcald}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
            dict(x=(s1/1e3 + s_out_turb/1e3)/2, y=T1 + 10, text=f"<b>{str_pcond}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
        ]

        # ==============================================================
        # CASO ESPECIAL TEXTBOOK: EJEMPLO 10-6 ÇENGEL (2 FWH + REHEAT)
        # ==============================================================
        if tiene_recal and num_fwh == 2:
            p_cca = max(f['presion'] for f in fwh_configuracion) * 1e3
            p_caa = min(f['presion'] for f in fwh_configuracion) * 1e3

            T_sat_cca = CP.PropsSI('T', 'P', p_cca, 'Q', 0, fluido) - 273.15
            s_f_cca = CP.PropsSI('S', 'P', p_cca, 'Q', 0, fluido) / 1e3
            s_g_cca = CP.PropsSI('S', 'P', p_cca, 'Q', 1, fluido) / 1e3

            T_sat_caa = CP.PropsSI('T', 'P', p_caa, 'Q', 0, fluido) - 273.15
            s_f_caa = CP.PropsSI('S', 'P', p_caa, 'Q', 0, fluido) / 1e3
            s_g_caa = CP.PropsSI('S', 'P', p_caa, 'Q', 1, fluido) / 1e3

            # 13 ESTADOS NUMERADOS SEGÚN EL ÇENGEL
            # 1: Salida condensador
            pt1 = (s1/1e3, T1)
            # 2: Salida Bomba I
            pt2 = (s1/1e3, T1 + 24.0)
            # 3: Salida CAA
            pt3 = (s_f_caa, T_sat_caa)
            # 4: Salida Bomba II
            pt4 = (s_f_caa, T_sat_caa + 22.0)
            # 5: Calentamiento en CCA a 15 MPa
            pt5 = (s_f_cca - 0.15, T_sat_cca - 8.0)
            # 6: Drenaje condensado del CCA
            pt6 = (s_f_cca, T_sat_cca)
            # 7: Salida bomba de condensado
            pt7 = (s_f_cca + 0.05, T_sat_cca + 18.0)
            # 8: Mezcla antes de caldera
            pt8 = (s_f_cca - 0.05, T_sat_cca + 10.0)
            # 9: Entrada turbina AP
            pt9 = (s_in_turb/1e3, T_max)
            # 10: Salida turbina AP
            h_10_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
            t_10 = get_T_safe(P_recal_Pa, h_10_iso)
            pt10 = (s_in_turb/1e3, t_10)
            # 11: Salida recalentador / Entrada turbina BP
            pt11 = (s_rec_in2/1e3, T_recal)
            # 12: Extracción a CAA en turbina BP
            h_12_iso = CP.PropsSI('H', 'P', p_caa, 'S', s_rec_in2, fluido)
            t_12 = get_T_safe(p_caa, h_12_iso)
            pt12 = (s_rec_in2/1e3, t_12)
            # 13: Salida turbina BP al condensador
            pt13 = (s_out_turb/1e3, T_out_turb)

            # Curvas del ciclo
            # Líquido 2 -> 3
            T_l23 = np.linspace(pt2[1], pt3[1], 15)
            s_l23 = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_l23]

            # Líquido 8 -> caldera sat
            T_l8c = np.linspace(pt8[1], T_sat_cald, 20)
            s_l8c = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_l8c]

            # Recalentamiento 10 -> 11
            T_rec_c = np.linspace(t_10 + 273.15, T_recal_K, 20)
            s_rec_c = [CP.PropsSI('S', 'P', P_recal_Pa, 'T', t, fluido)/1e3 for t in T_rec_c]

            # Ciclo continuo principal
            x_main = [pt1[0], pt2[0]] + s_l23 + [pt3[0], pt4[0], pt5[0], pt8[0]] + s_l8c + [s_f_cald, s_g_cald] + list(s_sup) + [pt9[0], pt10[0]] + s_rec_c + [pt11[0], pt12[0], pt13[0], pt1[0]]
            y_main = [pt1[1], pt2[1]] + list(T_l23) + [pt3[1], pt4[1], pt5[1], pt8[1]] + list(T_l8c) + [T_sat_cald, T_sat_cald] + list(T_sup) + [pt9[1], pt10[1]] + [t-273.15 for t in T_rec_c] + [pt11[1], pt12[1], pt13[1], pt1[1]]

            fig.add_trace(go.Scatter(
                x=x_main, y=y_main,
                mode='lines',
                line=dict(color=color_ciclo, width=2.4),
                name='Ciclo Principal',
                hoverinfo='skip'
            ))

            # Extracción 1 (hacia CCA a 4 MPa): desde 10 horizontal hasta 6
            T_iso_cca = np.linspace(t_10, T_sat_cca, 10)
            s_iso_cca = [CP.PropsSI('S', 'P', p_cca, 'T', t + 273.15, fluido)/1e3 for t in T_iso_cca]
            fig.add_trace(go.Scatter(
                x=s_iso_cca + [s_g_cca, pt6[0]],
                y=list(T_iso_cca) + [T_sat_cca, pt6[1]],
                mode='lines',
                line=dict(color=color_ciclo, width=2.0),
                name='Extracción CCA',
                hoverinfo='skip'
            ))

            # Bombeo de condensado 6 -> 7 -> 8
            fig.add_trace(go.Scatter(
                x=[pt6[0], pt7[0], pt8[0]],
                y=[pt6[1], pt7[1], pt8[1]],
                mode='lines',
                line=dict(color=color_ciclo, width=1.8),
                name='Purga CCA',
                hoverinfo='skip'
            ))

            # Extracción 2 (hacia CAA a 0.5 MPa): desde 12 horizontal hasta 3
            T_iso_caa = np.linspace(t_12, T_sat_caa, 10)
            s_iso_caa = [CP.PropsSI('S', 'P', p_caa, 'T', t + 273.15, fluido)/1e3 for t in T_iso_caa]
            fig.add_trace(go.Scatter(
                x=s_iso_caa + [s_g_caa, pt3[0]],
                y=list(T_iso_caa) + [T_sat_caa, pt3[1]],
                mode='lines',
                line=dict(color=color_ciclo, width=2.0),
                name='Extracción CAA',
                hoverinfo='skip'
            ))

            # Puntos cuadrados 1 al 13
            pts_x = [pt1[0], pt2[0], pt3[0], pt4[0], pt5[0], pt6[0], pt7[0], pt8[0], pt9[0], pt10[0], pt11[0], pt12[0], pt13[0]]
            pts_y = [pt1[1], pt2[1], pt3[1], pt4[1], pt5[1], pt6[1], pt7[1], pt8[1], pt9[1], pt10[1], pt11[1], pt12[1], pt13[1]]
            pts_txt = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
            pts_pos = [
                "bottom left", "top left", "bottom left", "top left", 
                "top left", "bottom right", "top right", "top left",
                "middle right", "middle right", "middle right", "middle right", "middle right"
            ]

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y,
                mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt,
                textposition=pts_pos,
                textfont=dict(color='white', size=11, family="Inter", weight='bold'),
                name='Estados',
                hovertemplate="<b>Estado %{text}</b><br>T: %{y:.1f} °C<br>s: %{x:.3f} kJ/kg·K<extra></extra>"
            ))

            flechas_anotaciones.extend([
                dict(x=(pt6[0] + pt10[0])/2, y=T_sat_cca + 10, text=f"<b>{fmt_p(p_cca/1000)}  ◀</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(pt3[0] + pt12[0])/2, y=T_sat_caa + 10, text=f"<b>{fmt_p(p_caa/1000)}  ◀</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(s_f_cald + pt9[0])/2 - 0.2, y=(T_sat_cald + pt9[1])/2, text="1 kg ▶", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                dict(x=(pt10[0] + pt11[0])/2, y=(pt10[1] + pt11[1])/2 + 15, text="1 - y ▶", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                dict(x=pt10[0] + 0.18, y=(pt9[1] + pt10[1])/2, text="y ▼", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                dict(x=pt11[0] + 0.25, y=(pt11[1] + pt12[1])/2, text="1 - y ▼", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                dict(x=pt11[0] + 0.35, y=(pt12[1] + pt13[1])/2, text="1 - y - z ▼", showarrow=False, font=dict(color='#cbd5e1', size=10))
            ])

        # ==============================================================
        # CASO GENERAL DINÁMICO (Cualquier otra combinación)
        # ==============================================================
        else:
            fwh_ordenados = sorted(fwh_configuracion, key=lambda x: x['presion'], reverse=True)
            pts_x, pts_y, pts_txt, pts_pos = [], [], [], []
            contador = 1

            pt1 = (s1/1e3, T1)
            pt2 = (s1/1e3, T1 + 25.0)
            pts_x.extend([pt1[0], pt2[0]])
            pts_y.extend([pt1[1], pt2[1]])
            pts_txt.extend([str(contador), str(contador+1)])
            pts_pos.extend(["bottom left", "top left"])
            contador += 2

            pts_liq = [pt1, pt2]
            fwh_inv = list(reversed(fwh_ordenados))

            for f in fwh_inv:
                p_pa = f['presion'] * 1e3
                t_sf = CP.PropsSI('T', 'P', p_pa, 'Q', 0, fluido) - 273.15
                s_sf = CP.PropsSI('S', 'P', p_pa, 'Q', 0, fluido) / 1e3

                t_tr = np.linspace(pts_liq[-1][1], t_sf, 12)
                s_tr = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in t_tr]
                for sx, ty in zip(s_tr, t_tr):
                    pts_liq.append((sx, ty))

                pt_f = (s_sf, t_sf)
                pt_b = (s_sf, t_sf + 15.0)
                pts_liq.extend([pt_f, pt_b])

                pts_x.extend([pt_f[0], pt_b[0]])
                pts_y.extend([pt_f[1], pt_b[1]])
                pts_txt.extend([str(contador), str(contador+1)])
                pts_pos.extend(["bottom left", "top left"])
                contador += 2

            t_cald = np.linspace(pts_liq[-1][1], T_sat_cald, 18)
            s_cald = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in t_cald]
            for sx, ty in zip(s_cald, t_cald):
                pts_liq.append((sx, ty))

            pt_in_t = (s_in_turb/1e3, T_max)
            pts_cald = [(s_f_cald, T_sat_cald), (s_g_cald, T_sat_cald)] + list(zip(s_sup, T_sup))

            pts_x.append(pt_in_t[0])
            pts_y.append(pt_in_t[1])
            pts_txt.append(str(contador))
            pts_pos.append("middle right")
            contador += 1

            x_main = [p[0] for p in pts_liq] + [p[0] for p in pts_cald]
            y_main = [p[1] for p in pts_liq] + [p[1] for p in pts_cald]

            if tiene_recal:
                h_rec_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
                t_rec_sal_val = get_T_safe(P_recal_Pa, h_rec_iso)
                pt_rec_s = (s_in_turb/1e3, t_rec_sal_val)
                x_main.append(pt_rec_s[0])
                y_main.append(pt_rec_s[1])
                pts_x.append(pt_rec_s[0])
                pts_y.append(pt_rec_s[1])
                pts_txt.append(str(contador))
                pts_pos.append("middle right")
                contador += 1

                T_rec_c = np.linspace(t_rec_sal_val + 273.15, T_recal_K, 15)
                s_rec_c = [CP.PropsSI('S', 'P', P_recal_Pa, 'T', t, fluido)/1e3 for t in T_rec_c]
                for sx, ty in zip(s_rec_c, [t-273.15 for t in T_rec_c]):
                    x_main.append(sx)
                    y_main.append(ty)

                pt_in_bp = (s_rec_in2/1e3, T_recal)
                pts_x.append(pt_in_bp[0])
                pts_y.append(pt_in_bp[1])
                pts_txt.append(str(contador))
                pts_pos.append("middle right")
                contador += 1

            # Trazar extracciones sin líneas diagonales
            for idx, f in enumerate(fwh_ordenados):
                p_pa = f['presion'] * 1e3
                t_sf = CP.PropsSI('T', 'P', p_pa, 'Q', 0, fluido) - 273.15
                s_sf = CP.PropsSI('S', 'P', p_pa, 'Q', 0, fluido) / 1e3
                s_sg = CP.PropsSI('S', 'P', p_pa, 'Q', 1, fluido) / 1e3

                # Determinar turbina correspondiente
                s_origen = (s_in_turb/1e3) if (tiene_recal and p_pa >= P_recal_Pa) else (s_rec_in2/1e3 if tiene_recal else s_in_turb/1e3)
                h_ext = CP.PropsSI('H', 'P', p_pa, 'S', s_origen * 1e3, fluido)
                t_ext = get_T_safe(p_pa, h_ext)
                pt_ext = (s_origen, t_ext)

                T_iso = np.linspace(t_ext, t_sf, 10)
                s_iso = [CP.PropsSI('S', 'P', p_pa, 'T', t + 273.15, fluido)/1e3 for t in T_iso]

                fig.add_trace(go.Scatter(
                    x=s_iso + [s_sg, s_sf],
                    y=list(T_iso) + [t_sf, t_sf],
                    mode='lines',
                    line=dict(color=color_ciclo, width=1.8),
                    name=f'Extracción {fmt_p(p_pa/1000)}',
                    hoverinfo='skip'
                ))

                pts_x.append(pt_ext[0])
                pts_y.append(pt_ext[1])
                pts_txt.append(str(contador))
                pts_pos.append("middle right")
                contador += 1

                flechas_anotaciones.append(
                    dict(x=(s_sf + s_sg)/2, y=t_sf + 8, text=f"<b>{fmt_p(p_pa/1000)}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
                )

            pt_esc = (s_out_turb/1e3, T_out_turb)
            x_main.extend([pt_esc[0], pt1[0]])
            y_main.extend([pt_esc[1], pt1[1]])

            pts_x.append(pt_esc[0])
            pts_y.append(pt_esc[1])
            pts_txt.append(str(contador))
            pts_pos.append("middle right")

            fig.add_trace(go.Scatter(
                x=x_main, y=y_main,
                mode='lines',
                line=dict(color=color_ciclo, width=2.4),
                name='Ciclo Principal',
                hoverinfo='skip'
            ))

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y,
                mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt,
                textposition=pts_pos,
                textfont=dict(color='white', size=11, family="Inter", weight='bold'),
                name='Estados',
                hovertemplate="<b>Estado %{text}</b><br>T: %{y:.1f} °C<br>s: %{x:.3f} kJ/kg·K<extra></extra>"
            ))

        fig.update_layout(
            paper_bgcolor='#111317',
            plot_bgcolor='#111317',
            margin=dict(l=55, r=40, t=30, b=45),
            xaxis=dict(
                title=dict(text='s [kJ/kg · K]', font=dict(color='#888888', size=11, family='Inter')),
                tickfont=dict(color='#888888', size=10),
                gridcolor='#1e2229',
                zeroline=False,
                showgrid=True,
                gridwidth=1,
                range=[0.0, 9.2]
            ),
            yaxis=dict(
                title=dict(text='T [°C]', font=dict(color='#888888', size=11, family='Inter')),
                tickfont=dict(color='#888888', size=10),
                gridcolor='#1e2229',
                zeroline=False,
                showgrid=True,
                gridwidth=1,
                range=[-10, max(660.0, T_max + 40.0)]
            ),
            showlegend=False,
            height=580,
            annotations=flechas_anotaciones
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
        st.markdown("#### Memoria de Cálculo Analítica (Paso a Paso)")
        
        col_btn, _ = st.columns([1.5, 2])
        with col_btn:
            if st.button("⚡ Generar / Actualizar Memoria de Cálculo", type="primary", use_container_width=True):
                with st.spinner("Calculando balances analíticos paso a paso..."):
                    resolver_manual_analitico()
                    st.rerun()

        if st.session_state["solucion_texto"]:
            st.markdown(f'<div class="incisos-box">{st.session_state["solucion_texto"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Configura los parámetros en la barra lateral izquierda y presiona el botón **'⚡ Calcular Procedimiento Paso a Paso'** para generar la memoria de cálculo completa.")

except Exception as err:
    st.error(f"Error procesando propiedades en CoolProp: {err}")
