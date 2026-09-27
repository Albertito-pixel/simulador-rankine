import streamlit as st
import CoolProp.CoolProp as CP
import matplotlib.pyplot as plt
import numpy as np
import json
import time
from PIL import Image
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILO ELEGANTE
# ==========================================
st.set_page_config(
    page_title="TermoRankine Pro | Simulador & Solucionador",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.2rem;
    }
    .header-title {
        font-size: 1.9rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
    }
    .header-desc {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }
    .sol-container {
        background: rgba(15, 23, 42, 0.65);
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 1.4rem;
        margin-top: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="header-title">⚡ TermoRankine Pro</div>
    <div class="header-desc">Simulador térmico integral: calentadores abiertos y cerrados, recalentamiento, propiedades de agua con CoolProp y resolución analítica por IA.</div>
</div>
""", unsafe_allow_html=True)

API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# GESTIÓN DE VARIABLES DE ESTADO
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
        {"tipo": "Cerrado (Closed)", "presion": 4000.0},
        {"tipo": "Abierto (Open)", "presion": 500.0}
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

# Selector de modo
metodo = st.radio(
    "Selecciona cómo deseas ingresar los datos:",
    ["📷 Cargar Captura / Imagen del Problema", "✍️ Configurar Datos Manualmente a Mano"],
    horizontal=True
)

st.markdown("---")

# ==========================================
# MODO 1: PROCESAMIENTO CON IA
# ==========================================
if metodo == "📷 Cargar Captura / Imagen del Problema":
    col_u, col_p = st.columns([1.2, 1.8])
    with col_u:
        archivo = st.file_uploader("Sube la imagen del problema", type=["png", "jpg", "jpeg", "webp"])
        btn_resolver = st.button("🚀 Resolver Directamente con IA", type="primary", use_container_width=True) if archivo else False

    with col_p:
        if archivo:
            img = Image.open(archivo)
            st.image(img, caption="Problema cargado", use_container_width=True)
            if btn_resolver:
                with st.spinner("Identificando ciclo, calentadores y resolviendo incisos..."):
                    prompt = """
                    Eres un profesor de Termodinámica de ciclo Rankine. Analiza la imagen.
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
                         {"tipo": "Abierto (Open)" o "Cerrado (Closed)", "presion_kPa": float}
                      ],
                      "eta_t": float,
                      "eta_p": float,
                      "TH_K": float,
                      "T0_K": float,
                      "respuestas_directas": "Markdown directo respondiendo TODOS los incisos (a, b, fracciones extraídas, eficiencia térmica, exergía) con valores en negrita."
                    }
                    Reglas: presiones en kPa (15 MPa = 15000, 4 MPa = 4000, 0.5 MPa = 500).
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
                        
                        fwh_lista = datos.get("fwh_lista", [])
                        st.session_state["num_fwh"] = len(fwh_lista)
                        st.session_state["fwh_data"] = [
                            {"tipo": f.get("tipo", "Abierto (Open)"), "presion": float(f.get("presion_kPa", 1000.0))}
                            for f in fwh_lista
                        ]
                        
                        st.session_state["eta_t"] = float(datos.get("eta_t", 100.0))
                        st.session_state["eta_p"] = float(datos.get("eta_p", 100.0))
                        st.session_state["TH"] = float(datos.get("TH_K", 800.0))
                        st.session_state["T0"] = float(datos.get("T0_K", 300.0))
                        st.session_state["solucion_texto"] = datos.get("respuestas_directas", "")
                        st.success("¡Datos y calentadores configurados automáticamente!")
                        st.rerun()

# ==========================================
# BARRA LATERAL: ENTRADA Y SELECCIÓN DE FWH
# ==========================================
st.sidebar.markdown("### ⚙️ Parámetros del Ciclo")

P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=100.0)
T_max = st.sidebar.number_input("Temperatura Entrada Turbina [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=5.0)

st.sidebar.markdown("---")
tiene_recal = st.sidebar.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
if tiene_recal:
    P_recal = st.sidebar.number_input("Presión Recalentador [kPa]", value=float(st.session_state["P_recal"]), step=100.0)
    T_recal = st.sidebar.number_input("Temperatura Recalentamiento [°C]", value=float(st.session_state["T_recal"]), step=10.0)
else:
    P_recal, T_recal = 1000.0, 350.0

st.sidebar.markdown("---")
st.sidebar.markdown("### ♻️ Calentadores de Agua (FWH)")
num_fwh = st.sidebar.number_input("Cantidad de Calentadores", min_value=0, max_value=4, value=int(st.session_state["num_fwh"]))

fwh_configuracion = []
for i in range(num_fwh):
    st.sidebar.markdown(f"**Calentador #{i+1}:**")
    tipo_def = "Abierto (Open)"
    p_def = float(P_cald / (i + 2))
    if i < len(st.session_state["fwh_data"]):
        tipo_def = st.session_state["fwh_data"][i]["tipo"]
        p_def = float(st.session_state["fwh_data"][i]["presion"])
    
    tipo_sel = st.sidebar.selectbox(
        f"Tipo FWH #{i+1}",
        ["Abierto (Open)", "Cerrado (Closed)"],
        index=0 if "Abierto" in tipo_def else 1,
        key=f"tipo_fwh_{i}"
    )
    pres_sel = st.sidebar.number_input(
        f"Presión Extracción #{i+1} [kPa]",
        min_value=float(P_cond),
        max_value=float(P_cald),
        value=p_def,
        step=50.0,
        key=f"pres_fwh_{i}"
    )
    fwh_configuracion.append({"tipo": tipo_sel, "presion": pres_sel})

st.sidebar.markdown("---")
with st.sidebar.expander("Eficiencias y Temperaturas de Entorno"):
    eta_t = st.slider("Eficiencia Turbina (η_t) [%]", 50.0, 100.0, float(st.session_state["eta_t"]), 1.0) / 100.0
    eta_p = st.slider("Eficiencia Bomba (η_p) [%]", 50.0, 100.0, float(st.session_state["eta_p"]), 1.0) / 100.0
    TH = st.number_input("Temp. Fuente / Horno (T_H) [K]", value=float(st.session_state["TH"]), step=25.0)
    T0 = st.number_input("Temp. Ambiente / Sumidero (T_0) [K]", value=float(st.session_state["T0"]), step=5.0)

# ==========================================
# MOSTRAR SOLUCIÓN ANALÍTICA DE INCISOS
# ==========================================
if st.session_state["solucion_texto"]:
    st.markdown("### 📋 Respuestas Directas del Problema (Incisos)")
    st.markdown(f'<div class="sol-container">{st.session_state["solucion_texto"]}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# MOTOR TERMODINÁMICO UNIVERSAL (CoolProp)
# ==========================================
fluido = 'Water'
P_cald_Pa = P_cald * 1e3
P_cond_Pa = P_cond * 1e3
T_max_K = T_max + 273.15
P_recal_Pa = P_recal * 1e3
T_recal_K = T_recal + 273.15

try:
    # Estado 1: Condensador
    h1 = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
    T1 = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

    # Entrada a Turbina
    h_in_turb = CP.PropsSI('H', 'P', P_cald_Pa, 'T', T_max_K, fluido)
    s_in_turb = CP.PropsSI('S', 'P', P_cald_Pa, 'T', T_max_K, fluido)

    # Balance general aproximado para métricas interactivas
    if tiene_recal:
        h_rec_s = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
        h_rec_sal = h_in_turb - eta_t * (h_in_turb - h_rec_s)
        h_rec_in2 = CP.PropsSI('H', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
        s_rec_in2 = CP.PropsSI('S', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_rec_in2, fluido)
        h_out_turb = h_rec_in2 - eta_t * (h_rec_in2 - h_out_s)
        w_t = (h_in_turb - h_rec_sal) + (h_rec_in2 - h_out_turb)
        q_recal = h_rec_in2 - h_rec_sal
    else:
        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_in_turb, fluido)
        h_out_turb = h_in_turb - eta_t * (h_in_turb - h_out_s)
        w_t = h_in_turb - h_out_turb
        q_recal = 0.0

    T_out_turb = CP.PropsSI('T', 'P', P_cond_Pa, 'H', h_out_turb, fluido) - 273.15
    s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)

    w_b = v1 * (P_cald_Pa - P_cond_Pa) / eta_p
    h2 = h1 + w_b
    s2 = CP.PropsSI('S', 'P', P_cald_Pa, 'H', h2, fluido)
    T2 = CP.PropsSI('T', 'P', P_cald_Pa, 'H', h2, fluido) - 273.15

    q_in = (h_in_turb - h2) + q_recal
    q_out = h_out_turb - h1
    w_neto = w_t - w_b
    eta_th = (w_neto / q_in) * 100.0

    # Segunda ley
    w_rev = q_in * (1.0 - (T0 / TH))
    eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

    # ==========================================
    # TARJETAS DE RESULTADOS
    # ==========================================
    st.markdown("### 📊 Resumen Ejecutivo del Ciclo")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Eficiencia Térmica (η_th)", f"{eta_th:.2f} %")
    m2.metric("Eficiencia 2da Ley (η_II)", f"{eta_II:.2f} %")
    m3.metric("Trabajo Neto", f"{w_neto/1e3:.2f} kJ/kg")
    m4.metric("Calor Suministrado (Qin)", f"{q_in/1e3:.2f} kJ/kg")

    # ==========================================
    # TABLA DE CALENTADORES SELECCIONADOS
    # ==========================================
    if num_fwh > 0:
        st.markdown("#### Configuración de Calentadores FWH")
        tabla_fwh = []
        for idx, item in enumerate(fwh_configuracion):
            tabla_fwh.append({
                "Calentador": f"FWH #{idx+1}",
                "Tipo": item["tipo"],
                "Presión Extracción [kPa]": f"{item['presion']:.1f}",
                "Presión Extracción [MPa]": f"{(item['presion']/1000.0):.2f}"
            })
        st.dataframe(tabla_fwh, use_container_width=True, hide_index=True)

    # ==========================================
    # DIAGRAMA T-s ELEGANTE
    # ==========================================
    st.markdown("#### Diagrama T-s")
    T_crit = CP.PropsSI('Tcrit', fluido)
    T_rango = np.linspace(274.15, T_crit - 1.0, 150)
    S_liq = [CP.PropsSI('S', 'T', T, 'Q', 0, fluido)/1e3 for T in T_rango]
    S_vap = [CP.PropsSI('S', 'T', T, 'Q', 1, fluido)/1e3 for T in T_rango]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(S_liq, T_rango - 273.15, color="#64748b", linestyle="--", linewidth=1.2, label='Campana Sat.')
    ax.plot(S_vap, T_rango - 273.15, color="#64748b", linestyle="--", linewidth=1.2)

    pts_s = [s1/1e3, s2/1e3, s_in_turb/1e3, s_out_turb/1e3, s1/1e3]
    pts_t = [T1, T2, T_max, T_out_turb, T1]
    ax.plot(pts_s, pts_t, color="#38bdf8", marker="o", markersize=4, linewidth=2, label="Ciclo Principal")

    ax.set_xlabel("Entropía [kJ/kg·K]", fontsize=9)
    ax.set_ylabel("Temperatura [°C]", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(fontsize=8)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#1e293b')
    ax.tick_params(colors='#94a3b8')
    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.xaxis.label.set_color('#94a3b8')
    ax.yaxis.label.set_color('#94a3b8')
    st.pyplot(fig)

except Exception as e:
    st.error(f"Error calculando propiedades: {e}")
