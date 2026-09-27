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

# Estilos CSS personalizados para una estética moderna y limpia
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
        padding: 1.8rem 2rem;
        margin-bottom: 1.5rem;
    }
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
    }
    .header-desc {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.4rem;
    }
    .card-res {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .sol-container {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 1.4rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Encabezado principal
st.markdown("""
<div class="header-box">
    <div class="header-title">⚡ TermoRankine Pro</div>
    <div class="header-desc">Simulador térmico de alta precisión con propiedades reales de agua y resolución analítica directa.</div>
</div>
""", unsafe_allow_html=True)

# Clave de API de Gemini
API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
valores_iniciales = {
    "P_cald": 3000.0,
    "T_max": 350.0,
    "P_cond": 75.0,
    "tiene_recal": False,
    "P_recal": 1000.0,
    "T_recal": 350.0,
    "num_fwh": 0,
    "P_exts": [],
    "eta_t": 100.0,
    "eta_p": 100.0,
    "TH": 800.0,
    "T0": 300.0,
    "solucion_texto": ""
}
for k, v in valores_iniciales.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# SELECTOR DE MODO DE ENTRADA
# ==========================================
metodo = st.radio(
    "Selecciona cómo deseas ingresar los datos del problema:",
    ["📷 Cargar Captura / Imagen del Problema", "✍️ Configurar Datos Manualmente a Mano"],
    horizontal=True
)

st.markdown("---")

# ==========================================
# MODO 1: SUBIR IMAGEN (IA)
# ==========================================
if metodo == "📷 Cargar Captura / Imagen del Problema":
    col_upload, col_preview = st.columns([1.2, 1.8])
    
    with col_upload:
        archivo = st.file_uploader("Sube el problema (libro o examen)", type=["png", "jpg", "jpeg", "webp"])
        if archivo is not None:
            btn_resolver = st.button("🚀 Resolver Directamente con IA", type="primary", use_container_width=True)
        else:
            btn_resolver = False

    with col_preview:
        if archivo is not None:
            img = Image.open(archivo)
            st.image(img, caption="Vista previa del problema", use_container_width=True)
            
            if btn_resolver:
                with st.spinner("Analizando y calculando respuestas directas..."):
                    prompt = """
                    Eres un profesor titular de Termodinámica de ingeniería. Analiza la imagen.
                    Devuelve ÚNICAMENTE un JSON con:
                    1. Los parámetros numéricos del ciclo.
                    2. Una solución directa, concisa y sin relleno innecesario a los incisos pedidos.
                    
                    Formato JSON:
                    {
                      "P_cald_kPa": float,
                      "T_max_C": float,
                      "P_cond_kPa": float,
                      "tiene_recal": bool,
                      "P_recal_kPa": float o null,
                      "T_recal_C": float o null,
                      "num_fwh": int,
                      "P_exts_kPa": [lista en kPa ordenada],
                      "eta_t": float (porcentaje, ej: 85.0),
                      "eta_p": float (porcentaje, ej: 85.0),
                      "TH_K": float,
                      "T0_K": float,
                      "respuestas_directas": "Markdown directo y al grano respondiendo cada inciso (a, b, etc.) con sus valores numéricos finales en negrita y fórmulas clave."
                    }
                    Reglas: presiones en kPa, temperaturas en °C (salvo TH y T0 en K).
                    """
                    
                    # Intentos automáticos para evitar error de saturación 503
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
                        st.session_state["num_fwh"] = int(datos.get("num_fwh", 0))
                        st.session_state["P_exts"] = [float(p) for p in datos.get("P_exts_kPa", [])]
                        st.session_state["eta_t"] = float(datos.get("eta_t", 100.0))
                        st.session_state["eta_p"] = float(datos.get("eta_p", 100.0))
                        st.session_state["TH"] = float(datos.get("TH_K", 800.0))
                        st.session_state["T0"] = float(datos.get("T0_K", 300.0))
                        st.session_state["solucion_texto"] = datos.get("respuestas_directas", "")
                        st.success("¡Problema resuelto y parámetros cargados!")
                        st.rerun()
                    else:
                        st.error("No se pudo conectar momentáneamente con el servicio de IA. Intenta hacer clic de nuevo.")

# ==========================================
# BARRA LATERAL: PARÁMETROS DEL PROBLEMA
# ==========================================
st.sidebar.markdown("### ⚙️ Datos del Ciclo")

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
num_fwh = st.sidebar.number_input("Calentadores Regenerativos (FWH)", min_value=0, max_value=4, value=int(st.session_state["num_fwh"]))

st.sidebar.markdown("---")
with st.sidebar.expander("Eficiencias y Temperaturas de Entorno"):
    eta_t = st.slider("Eficiencia Turbina (η_t) [%]", 50.0, 100.0, float(st.session_state["eta_t"]), 1.0) / 100.0
    eta_p = st.slider("Eficiencia Bomba (η_p) [%]", 50.0, 100.0, float(st.session_state["eta_p"]), 1.0) / 100.0
    TH = st.number_input("Temp. Fuente / Horno (T_H) [K]", value=float(st.session_state["TH"]), step=25.0)
    T0 = st.number_input("Temp. Ambiente / Sumidero (T_0) [K]", value=float(st.session_state["T0"]), step=5.0)

# ==========================================
# MOSTRAR SOLUCIÓN DIRECTA SI EXISTE
# ==========================================
if st.session_state["solucion_texto"]:
    st.markdown("### 📋 Respuestas Directas del Problema")
    st.markdown(f'<div class="sol-container">{st.session_state["solucion_texto"]}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# CÁLCULOS TERMODINÁMICOS (CoolProp)
# ==========================================
fluido = 'Water'
P1 = P_cond * 1e3
P3 = P_cald * 1e3
T3 = T_max + 273.15

try:
    # Estado 1: Salida de condensador (Líquido saturado)
    h1 = CP.PropsSI('H', 'P', P1, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P1, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P1, 'Q', 0, fluido)
    T1 = CP.PropsSI('T', 'P', P1, 'Q', 0, fluido) - 273.15

    # Estado 2: Salida de bomba
    w_b_ideal = v1 * (P3 - P1)
    w_b = w_b_ideal / eta_p
    h2 = h1 + w_b
    s2 = CP.PropsSI('S', 'P', P3, 'H', h2, fluido)
    T2 = CP.PropsSI('T', 'P', P3, 'H', h2, fluido) - 273.15

    # Estado 3: Entrada turbina
    h3 = CP.PropsSI('H', 'P', P3, 'T', T3, fluido)
    s3 = CP.PropsSI('S', 'P', P3, 'T', T3, fluido)

    # Estado 4: Salida turbina
    if tiene_recal:
        P_rec_pa = P_recal * 1e3
        h_rec_s = CP.PropsSI('H', 'P', P_rec_pa, 'S', s3, fluido)
        h_rec_sal = h3 - eta_t * (h3 - h_rec_s)
        w_t1 = h3 - h_rec_sal

        # Recalentamiento a Estado 5
        h5 = CP.PropsSI('H', 'P', P_rec_pa, 'T', T_recal + 273.15, fluido)
        s5 = CP.PropsSI('S', 'P', P_rec_pa, 'T', T_recal + 273.15, fluido)
        q_rec = h5 - h_rec_sal

        # Turbina BP a Estado 6
        h4s = CP.PropsSI('H', 'P', P1, 'S', s5, fluido)
        h4 = h5 - eta_t * (h5 - h4s)
        s4 = CP.PropsSI('S', 'P', P1, 'H', h4, fluido)
        T4 = CP.PropsSI('T', 'P', P1, 'H', h4, fluido) - 273.15
        w_t = w_t1 + (h5 - h4)
        q_in = (h3 - h2) + q_rec
    else:
        q_rec = 0.0
        h4s = CP.PropsSI('H', 'P', P1, 'S', s3, fluido)
        h4 = h3 - eta_t * (h3 - h4s)
        s4 = CP.PropsSI('S', 'P', P1, 'H', h4, fluido)
        T4 = CP.PropsSI('T', 'P', P1, 'H', h4, fluido) - 273.15
        w_t = h3 - h4
        q_in = h3 - h2

    q_out = h4 - h1
    w_net = w_t - w_b
    eta_th = (w_net / q_in) * 100.0

    # Segunda Ley
    s_gen_cald = (s3 - s2) - ((h3 - h2) / TH)
    if tiene_recal:
        s_gen_cald += (s5 - CP.PropsSI('S', 'P', P_rec_pa, 'H', h_rec_sal, fluido)) - (q_rec / TH)
    s_gen_cond = (s1 - s4) + (q_out / T0)
    s_gen_total = max(0.0, s_gen_cald) + max(0.0, s_gen_cond)

    x_dest_cald = T0 * max(0.0, s_gen_cald)
    x_dest_cond = T0 * max(0.0, s_gen_cond)
    x_dest_total = T0 * s_gen_total

    w_rev = q_in * (1.0 - (T0 / TH))
    eta_II = (w_net / w_rev) * 100.0 if w_rev > 0 else 0.0

    # ==========================================
    # TARJETAS DE RESULTADOS PRINCIPALES
    # ==========================================
    st.markdown("### 📊 Resumen Ejecutivo del Ciclo")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Eficiencia Térmica (η_th)", f"{eta_th:.2f} %")
    m2.metric("Eficiencia 2da Ley (η_II)", f"{eta_II:.2f} %")
    m3.metric("Trabajo Neto (W_neto)", f"{w_net/1e3:.2f} kJ/kg")
    m4.metric("Calor Suministrado (Q_in)", f"{q_in/1e3:.2f} kJ/kg")

    ex1, ex2, ex3 = st.columns(3)
    ex1.metric("Exergía Destruida Caldera", f"{x_dest_cald/1e3:.2f} kJ/kg")
    ex2.metric("Exergía Destruida Condensador", f"{x_dest_cond/1e3:.2f} kJ/kg")
    ex3.metric("Exergía Destruida Total", f"{x_dest_total/1e3:.2f} kJ/kg")

    # ==========================================
    # TABLA RESUMIDA DE ESTADOS Y DIAGRAMA T-s
    # ==========================================
    col_tab, col_graf = st.columns([1.1, 1.3])

    with col_tab:
        st.markdown("#### Estados Termodinámicos")
        tabla_datos = [
            {"Estado": "1 (Salida Condensador)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T1:.1f}", "h [kJ/kg]": f"{h1/1e3:.2f}", "s [kJ/kg·K]": f"{s1/1e3:.4f}"},
            {"Estado": "2 (Salida Bomba)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T2:.1f}", "h [kJ/kg]": f"{h2/1e3:.2f}", "s [kJ/kg·K]": f"{s2/1e3:.4f}"},
            {"Estado": "3 (Entrada Turbina)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T_max:.1f}", "h [kJ/kg]": f"{h3/1e3:.2f}", "s [kJ/kg·K]": f"{s3/1e3:.4f}"},
            {"Estado": "4 (Salida Turbina)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T4:.1f}", "h [kJ/kg]": f"{h4/1e3:.2f}", "s [kJ/kg·K]": f"{s4/1e3:.4f}"}
        ]
        st.dataframe(tabla_datos, use_container_width=True, hide_index=True)

    with col_graf:
        st.markdown("#### Diagrama T-s")
        T_crit = CP.PropsSI('Tcrit', fluido)
        T_rango = np.linspace(274.15, T_crit - 1.0, 150)
        S_liq = [CP.PropsSI('S', 'T', T, 'Q', 0, fluido)/1e3 for T in T_rango]
        S_vap = [CP.PropsSI('S', 'T', T, 'Q', 1, fluido)/1e3 for T in T_rango]

        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.plot(S_liq, T_rango - 273.15, color="#64748b", linestyle="--", linewidth=1.2, label='Campana Sat.')
        ax.plot(S_vap, T_rango - 273.15, color="#64748b", linestyle="--", linewidth=1.2)

        pts_s = [s1/1e3, s2/1e3, s3/1e3, s4/1e3, s1/1e3]
        pts_t = [T1, T2, T_max, T4, T1]
        ax.plot(pts_s, pts_t, color="#38bdf8", marker="o", markersize=4, linewidth=2, label="Ciclo Rankine")

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
