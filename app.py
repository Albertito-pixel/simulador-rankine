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
    <div class="hero-sub">Simulador de ciclos Rankine con diagramas T-s estilo textbook y resolución analítica por IA.</div>
</div>
""", unsafe_allow_html=True)

API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# VARIABLES POR DEFECTO
# ==========================================
defaults = {
    "P_cald": 15000.0,
    "T_max": 600.0,
    "P_cond": 10.0,
    "tiene_recal": False,
    "P_recal": 4000.0,
    "T_recal": 600.0,
    "num_fwh": 1,
    "fwh_data": [{"tipo": "Abierto (CAA)", "presion": 1200.0}],
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
                Eres un profesor titular de Termodinámica de ingeniería. Analiza la imagen.
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
                Reglas: presiones en kPa (ej: 15 MPa = 15000, 1.2 MPa = 1200, 75 kPa = 75).
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
P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=500.0)
T_max = st.sidebar.number_input("Vapor Vivo (T_max) [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=5.0)

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

def resolver_manual_con_ia():
    desc_fwh = "\n".join([f"- Calentador #{i+1}: {c['tipo']} a {c['presion']} kPa" for i, c in enumerate(fwh_configuracion)])
    prompt_manual = f"""
    Eres un profesor de Termodinámica experto en ciclos Rankine del libro de Çengel.
    El estudiante configuró estos parámetros del ciclo:
    - Presión Caldera: {P_cald} kPa ({(P_cald/1000):.2f} MPa)
    - Temperatura Vapor Vivo: {T_max} °C
    - Presión Condensador: {P_cond} kPa
    - Recalentamiento: {"Sí, a " + str(P_recal) + " kPa y " + str(T_recal) + " °C" if tiene_recal else "No"}
    - Calentadores FWH: {num_fwh}
    {desc_fwh if num_fwh > 0 else "- Ninguno"}
    - Eficiencias Isentrópicas: Turbina {eta_t*100:.1f}%, Bomba {eta_p*100:.1f}%
    - Entorno: T_fuente = {TH} K, T_ambiente = {T0} K

    TAREA:
    Resuelve el problema paso a paso:
    1. Propiedades de cada estado (entalpías en kJ/kg y entropías en kJ/kg·K).
    2. Fracciones extraídas (y, z) con los balances de masa y energía.
    3. Trabajo neto (W_neto) y calor suministrado (Qin).
    4. Eficiencia térmica de la Primera Ley (η_th).
    5. Análisis de Segunda Ley: destrucción de exergía en cada componente (X_dest = T0 * S_gen) y eficiencia exergética (η_II).
    Resalta los resultados numéricos finales en negrita.
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
    # Estado 1: Salida del condensador
    h1 = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
    T1 = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

    # Vapor vivo a la entrada de la turbina
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
        # Formato de títulos de presión
        str_pcald = f"{P_cald/1000:.1f} MPa" if P_cald >= 1000 else f"{P_cald:.0f} kPa"
        str_pcond = f"{P_cond/1000:.2f} MPa" if P_cond >= 1000 else f"{P_cond:.0f} kPa"

        # Campana de saturación en gris neutro fino
        T_crit = CP.PropsSI('Tcrit', fluido)
        T_campana = np.linspace(273.16, T_crit - 0.2, 250)
        s_liq = [CP.PropsSI('S', 'T', t, 'Q', 0, fluido)/1e3 for t in T_campana]
        s_vap = [CP.PropsSI('S', 'T', t, 'Q', 1, fluido)/1e3 for t in T_campana]

        fig = go.Figure()

        # 1. Trazo de la campana
        fig.add_trace(go.Scatter(
            x=s_liq + s_vap[::-1],
            y=[t - 273.15 for t in T_campana] + [t - 273.15 for t in T_campana[::-1]],
            mode='lines',
            line=dict(color='#00f0ff', width=1.4),
            name='Campana',
            hoverinfo='skip'
        ))

        # Propiedades de la caldera
        T_sat_cald = CP.PropsSI('T', 'P', P_cald_Pa, 'Q', 0, fluido) - 273.15
        s_f_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 0, fluido) / 1e3
        s_g_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 1, fluido) / 1e3

        # Curva de sobrecalentamiento real con CoolProp (swoop hacia arriba)
        T_sup = np.linspace(T_sat_cald + 0.1, T_max, 35)
        s_sup = [CP.PropsSI('S', 'P', P_cald_Pa, 'T', t + 273.15, fluido)/1e3 for t in T_sup]

        # Flechas de anotación del gráfico
        flechas_anotaciones = []

        # ====================================================
        # CASO A: CICLO CON 1 CALENTADOR REGENERATIVO (IDÉNTICO A LA FOTO)
        # ====================================================
        if num_fwh == 1 and not tiene_recal:
            p_fwh_Pa = fwh_configuracion[0]['presion'] * 1e3
            str_pfwh = f"{fwh_configuracion[0]['presion']/1000:.1f} MPa" if fwh_configuracion[0]['presion'] >= 1000 else f"{fwh_configuracion[0]['presion']:.0f} kPa"
            
            T_sat_fwh = CP.PropsSI('T', 'P', p_fwh_Pa, 'Q', 0, fluido) - 273.15
            s_f_fwh = CP.PropsSI('S', 'P', p_fwh_Pa, 'Q', 0, fluido) / 1e3
            s_g_fwh = CP.PropsSI('S', 'P', p_fwh_Pa, 'Q', 1, fluido) / 1e3

            # Estados didácticos
            # 1: Salida condensador
            pt1 = (s1/1e3, T1)
            # 2: Salida Bomba 1 (despegado didácticamente)
            pt2 = (s1/1e3, T1 + 28.0)
            # 3: Salida del calentador abierto (líquido saturado a P_fwh)
            pt3 = (s_f_fwh, T_sat_fwh)
            # 4: Salida Bomba 2 (despegado hacia la caldera)
            pt4 = (s_f_fwh, T_sat_fwh + 18.0)
            # 5: Entrada a turbina (vapor vivo)
            pt5 = (s_in_turb/1e3, T_max)
            # 6: Extracción hacia el FWH
            h_6_iso = CP.PropsSI('H', 'P', p_fwh_Pa, 'S', s_in_turb, fluido)
            t_6 = get_T_safe(p_fwh_Pa, h_6_iso)
            pt6 = (s_in_turb/1e3, t_6)
            # 7: Salida de turbina hacia condensador
            pt7 = (s_out_turb/1e3, T_out_turb)

            # Trayectoria líquida 2 -> 3
            T_liq_23 = np.linspace(pt2[1], pt3[1], 20)
            s_liq_23 = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_liq_23]

            # Trayectoria líquida 4 -> ebullición caldera
            T_liq_4c = np.linspace(pt4[1], T_sat_cald, 25)
            s_liq_4c = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_liq_4c]

            # Unir ciclo continuo
            x_ciclo = [pt1[0], pt2[0]] + s_liq_23 + [pt3[0], pt4[0]] + s_liq_4c + [s_f_cald, s_g_cald] + list(s_sup) + [pt6[0], pt7[0], pt1[0]]
            y_ciclo = [pt1[1], pt2[1]] + list(T_liq_23) + [pt3[1], pt4[1]] + list(T_liq_4c) + [T_sat_cald, T_sat_cald] + list(T_sup) + [pt6[1], pt7[1], pt1[1]]

            fig.add_trace(go.Scatter(
                x=x_ciclo, y=y_ciclo,
                mode='lines',
                line=dict(color='#ff6b35', width=2.4),
                name='Ciclo',
                hoverinfo='skip'
            ))

            # Extracción FWH (línea horizontal desde 6 hacia 3)
            fig.add_trace(go.Scatter(
                x=[pt6[0], s_g_fwh, pt3[0]],
                y=[pt6[1], T_sat_fwh, pt3[1]],
                mode='lines',
                line=dict(color='#ff6b35', width=2.0),
                name='Extracción FWH',
                hoverinfo='skip'
            ))

            # Marcadores cuadrados blancos idénticos a la foto
            pts_x = [pt1[0], pt2[0], pt3[0], pt4[0], pt5[0], pt6[0], pt7[0]]
            pts_y = [pt1[1], pt2[1], pt3[1], pt4[1], pt5[1], pt6[1], pt7[1]]
            pts_txt = ["1", "2", "3", "4", "5", "6", "7"]
            pts_pos = ["bottom left", "top left", "bottom left", "top left", "middle right", "middle right", "middle right"]

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y,
                mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt,
                textposition=pts_pos,
                textfont=dict(color='white', size=12, family="Inter, sans-serif", weight='bold'),
                name='Estados',
                hovertemplate="<b>Estado %{text}</b><br>T: %{y:.1f} °C<br>s: %{x:.3f} kJ/kg·K<extra></extra>"
            ))

            # Rótulos de texto con flechas en las líneas (como en la captura)
            flechas_anotaciones = [
                # 15 MPa en caldera
                dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{str_pcald}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
                # 1.2 MPa en FWH
                dict(x=(pt3[0] + pt6[0])/2, y=T_sat_fwh + 10, text=f"<b>{str_pfwh}</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(pt3[0] + pt6[0])/2 + 1.2, y=T_sat_fwh + 10, text="y ◀", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                # 10 kPa en condensador
                dict(x=(pt1[0] + pt7[0])/2, y=pt1[1] + 10, text=f"<b>{str_pcond}</b>", showarrow=False, font=dict(color='white', size=11)),
                # Flechas verticales de expansión
                dict(x=pt5[0] + 0.18, y=(pt5[1] + pt6[1])/2, text="1 ▼", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                dict(x=pt6[0] + 0.32, y=(pt6[1] + pt7[1])/2, text="(1-y) ▼", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                # Flecha subida bomba 1
                dict(x=pt1[0] - 0.08, y=(pt1[1] + pt2[1])/2, text="▲", showarrow=False, font=dict(color='#ff6b35', size=10)),
                # Flecha calentamiento líquido
                dict(x=(pt2[0] + pt3[0])/2, y=(pt2[1] + pt3[1])/2 + 4, text="▶", showarrow=False, font=dict(color='#ff6b35', size=9))
            ]

        # ====================================================
        # CASO B: CICLO RANKINE SIMPLE (4 ESTADOS)
        # ====================================================
        elif num_fwh == 0 and not tiene_recal:
            pt1 = (s1/1e3, T1)
            pt2 = (s1/1e3, T1 + 30.0)
            pt3 = (s_in_turb/1e3, T_max)
            pt4 = (s_out_turb/1e3, T_out_turb)

            T_liq = np.linspace(pt2[1], T_sat_cald, 25)
            s_liq = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_liq]

            x_ciclo = [pt1[0], pt2[0]] + s_liq + [s_f_cald, s_g_cald] + list(s_sup) + [pt4[0], pt1[0]]
            y_ciclo = [pt1[1], pt2[1]] + list(T_liq) + [T_sat_cald, T_sat_cald] + list(T_sup) + [pt4[1], pt1[1]]

            fig.add_trace(go.Scatter(
                x=x_ciclo, y=y_ciclo,
                mode='lines',
                line=dict(color='#ff6b35', width=2.4),
                name='Ciclo',
                hoverinfo='skip'
            ))

            pts_x = [pt1[0], pt2[0], pt3[0], pt4[0]]
            pts_y = [pt1[1], pt2[1], pt3[1], pt4[1]]
            pts_txt = ["1", "2", "3", "4"]
            pts_pos = ["bottom left", "top left", "middle right", "middle right"]

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y,
                mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt,
                textposition=pts_pos,
                textfont=dict(color='white', size=12, family="Inter, sans-serif", weight='bold'),
                name='Estados',
                hovertemplate="<b>Estado %{text}</b><br>T: %{y:.1f} °C<br>s: %{x:.3f} kJ/kg·K<extra></extra>"
            ))

            flechas_anotaciones = [
                dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{str_pcald}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(pt1[0] + pt4[0])/2, y=pt1[1] + 10, text=f"<b>{str_pcond}  ◀</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=pt3[0] + 0.18, y=(pt3[1] + pt4[1])/2, text="1 ▼", showarrow=False, font=dict(color='#cbd5e1', size=10)),
                dict(x=pt1[0] - 0.08, y=(pt1[1] + pt2[1])/2, text="▲", showarrow=False, font=dict(color='#ff6b35', size=10))
            ]

        # ====================================================
        # CASO C: CICLOS CON RECALENTAMIENTO / MÚLTIPLES FWH
        # ====================================================
        else:
            p_fwh_abierto = min(f['presion'] for f in fwh_configuracion) * 1e3 if num_fwh > 0 else P_cond_Pa
            h_10_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
            t_10 = get_T_safe(P_recal_Pa, h_10_iso)
            
            T_rec_c = np.linspace(t_10 + 273.15, T_recal_K, 15)
            s_rec_c = [CP.PropsSI('S', 'P', P_recal_Pa, 'T', t, fluido)/1e3 for t in T_rec_c]

            pt1 = (s1/1e3, T1)
            pt2 = (s1/1e3, T1 + 28.0)
            pt_in = (s_in_turb/1e3, T_max)
            pt_rec_sal = (s_in_turb/1e3, t_10)
            pt_rec_in = (s_rec_in2/1e3, T_recal)
            pt_out = (s_out_turb/1e3, T_out_turb)

            T_liq = np.linspace(pt2[1], T_sat_cald, 25)
            s_liq = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in T_liq]

            x_ciclo = [pt1[0], pt2[0]] + s_liq + [s_f_cald, s_g_cald] + list(s_sup) + [pt_rec_sal[0]] + s_rec_c + [pt_rec_in[0], pt_out[0], pt1[0]]
            y_ciclo = [pt1[1], pt2[1]] + list(T_liq) + [T_sat_cald, T_sat_cald] + list(T_sup) + [pt_rec_sal[1]] + [t-273.15 for t in T_rec_c] + [pt_rec_in[1], pt_out[1], pt1[1]]

            fig.add_trace(go.Scatter(
                x=x_ciclo, y=y_ciclo,
                mode='lines',
                line=dict(color='#ff6b35', width=2.4),
                name='Ciclo',
                hoverinfo='skip'
            ))

            pts_x = [pt1[0], pt2[0], pt_in[0], pt_rec_sal[0], pt_rec_in[0], pt_out[0]]
            pts_y = [pt1[1], pt2[1], pt_in[1], pt_rec_sal[1], pt_rec_in[1], pt_out[1]]
            pts_txt = ["1", "2", "3", "4", "5", "6"]
            pts_pos = ["bottom left", "top left", "middle right", "middle right", "middle right", "middle right"]

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y,
                mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt,
                textposition=pts_pos,
                textfont=dict(color='white', size=12, family="Inter, sans-serif", weight='bold'),
                name='Estados',
                hovertemplate="<b>Estado %{text}</b><br>T: %{y:.1f} °C<br>s: %{x:.3f} kJ/kg·K<extra></extra>"
            ))

            flechas_anotaciones = [
                dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{str_pcald}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(pt1[0] + pt_out[0])/2, y=pt1[1] + 10, text=f"<b>{str_pcond}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
            ]

        # ==========================================
        # ESTILO DEL LIENZO (DARK TEXTBOOK LOOK)
        # ==========================================
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
