import streamlit as st
import CoolProp.CoolProp as CP
import matplotlib.pyplot as plt
import numpy as np
import json
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="Simulador Universal Ciclo Rankine + IA", layout="wide")

st.title("⚡ Simulador Universal de Ciclos Rankine")
st.markdown("Herramienta integral de termodinámica: Primera y Segunda Ley, recalentamiento, regeneración, exergía y resolución automática por visión artificial.")

# ==========================================
# CONFIGURACIÓN API DE GEMINI
# ==========================================
API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# Inicializar variables por defecto en st.session_state
defaults = {
    "P_cald_kPa": 3000.0,
    "T_max_C": 350.0,
    "P_cond_kPa": 75.0,
    "tiene_recal": False,
    "P_recal_kPa": 1000.0,
    "T_recal_C": 350.0,
    "num_fwh": 0,
    "P_exts_kPa": [],
    "eta_t": 100.0,
    "eta_p": 100.0,
    "TH_K": 800.0,
    "T0_K": 300.0,
    "calc_potencia": "Ninguno",
    "valor_potencia": 100.0,
    "solucion_incisos": ""
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 1. SECCIÓN DE SUBIDA Y ANÁLISIS DE IMAGEN
# ==========================================
st.subheader("📷 Cargar Captura del Problema / Diagrama")
archivo_subido = st.file_uploader("Arrastra o selecciona la captura de tu libro o examen", type=["png", "jpg", "jpeg", "webp"])

if archivo_subido is not None:
    imagen = Image.open(archivo_subido)
    col_img, col_info = st.columns([1, 2])
    with col_img:
        st.image(imagen, caption="Problema cargado", use_container_width=True)
    
    with col_info:
        if st.button("🔍 Extraer Datos y Resolver Incisos con IA"):
            with st.spinner("Analizando ciclo, extrayendo datos y calculando incisos..."):
                prompt = """
                Eres un profesor titular de Termodinámica Aplicada (libro de Çengel). Analiza exhaustivamente la imagen adjunta.
                
                Debes extraer todos los datos del problema y devolver ÚNICAMENTE un JSON con esta estructura:
                {
                  "P_cald_kPa": float,
                  "T_max_C": float,
                  "P_cond_kPa": float,
                  "tiene_recal": bool,
                  "P_recal_kPa": float o null,
                  "T_recal_C": float o null,
                  "num_fwh": int,
                  "P_exts_kPa": [lista de presiones intermedias de extracción en kPa de mayor a menor],
                  "eta_t": float (porcentaje, ej: 85.0 para 85%),
                  "eta_p": float (porcentaje, ej: 85.0 para 85%),
                  "TH_K": float (temperatura de la fuente/horno en Kelvin; si no la dice, pon 800.0),
                  "T0_K": float (temperatura ambiente/sumidero en Kelvin; si no la dice, pon 300.0),
                  "calc_potencia": "Potencia Neta (MW)" o "Flujo Másico (kg/s)" o "Ninguno",
                  "valor_potencia": float (el valor numérico asociado si dan potencia o flujo),
                  "solucion_incisos": "Texto en formato Markdown bien organizado que responda TODOS los incisos del problema (a, b, c, destrucción de exergía, balances, trabajo reversible, etc.) con fórmulas, sustitución y resultados numéricos claros en negrita."
                }
                
                Reglas:
                - Convierte siempre presiones a kPa (1 MPa = 1000 kPa, 1 bar = 100 kPa).
                - Convierte temperaturas principales a °C.
                - Si las eficiencias isentrópicas son ideales, asigna 100.0.
                """
                try:
                    response = client.models.generate_content(
                        model="gemini-flash-latest",
                        contents=[imagen, prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    datos = json.loads(response.text)
                    st.success("¡Datos extraídos e integrados en la barra lateral!")
                    
                    # Actualizar session_state
                    st.session_state["P_cald_kPa"] = float(datos.get("P_cald_kPa", st.session_state["P_cald_kPa"]))
                    st.session_state["T_max_C"] = float(datos.get("T_max_C", st.session_state["T_max_C"]))
                    st.session_state["P_cond_kPa"] = float(datos.get("P_cond_kPa", st.session_state["P_cond_kPa"]))
                    st.session_state["tiene_recal"] = bool(datos.get("tiene_recal", False))
                    if datos.get("P_recal_kPa"):
                        st.session_state["P_recal_kPa"] = float(datos.get("P_recal_kPa"))
                    if datos.get("T_recal_C"):
                        st.session_state["T_recal_C"] = float(datos.get("T_recal_C"))
                    st.session_state["num_fwh"] = int(datos.get("num_fwh", 0))
                    st.session_state["P_exts_kPa"] = [float(p) for p in datos.get("P_exts_kPa", [])]
                    st.session_state["eta_t"] = float(datos.get("eta_t", 100.0))
                    st.session_state["eta_p"] = float(datos.get("eta_p", 100.0))
                    st.session_state["TH_K"] = float(datos.get("TH_K", 800.0))
                    st.session_state["T0_K"] = float(datos.get("T0_K", 300.0))
                    st.session_state["solucion_incisos"] = datos.get("solucion_incisos", "")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error procesando la imagen: {e}")

# ==========================================
# MOSTRAR SOLUCIÓN ANALÍTICA DE INCISOS
# ==========================================
if st.session_state["solucion_incisos"]:
    st.markdown("---")
    st.subheader("📝 Solución Paso a Paso del Problema (Incisos)")
    st.markdown(st.session_state["solucion_incisos"])

st.markdown("---")

# ==========================================
# 2. BARRA LATERAL: TODOS LOS DATOS DEL PROBLEMA
# ==========================================
st.sidebar.title("⚙️ Parámetros del Ciclo")

with st.sidebar.expander("🔥 1. Presiones y Temperaturas Principales", expanded=True):
    P_cald_kPa = st.number_input("Presión Caldera [kPa]", min_value=10.0, max_value=50000.0, value=st.session_state["P_cald_kPa"], step=50.0)
    T_max_C = st.number_input("Temperatura Entrada Turbina [°C]", min_value=50.0, max_value=850.0, value=st.session_state["T_max_C"], step=10.0)
    P_cond_kPa = st.number_input("Presión Condensador [kPa]", min_value=1.0, max_value=500.0, value=st.session_state["P_cond_kPa"], step=5.0)

with st.sidebar.expander("🔄 2. Recalentamiento (Reheat)", expanded=True):
    tiene_recal = st.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
    P_recal_kPa = st.number_input("Presión Recalentador [kPa]", min_value=10.0, max_value=float(P_cald_kPa), value=min(float(st.session_state["P_recal_kPa"]), float(P_cald_kPa)), step=50.0, disabled=not tiene_recal)
    T_recal_C = st.number_input("Temperatura Post-Recalentamiento [°C]", min_value=50.0, max_value=850.0, value=st.session_state["T_recal_C"], step=10.0, disabled=not tiene_recal)

with st.sidebar.expander("♻️ 3. Regeneración (Calentadores FWH)", expanded=True):
    num_fwh = st.number_input("Número de Calentadores (FWH)", min_value=0, max_value=6, value=st.session_state["num_fwh"])
    P_exts_kPa = []
    for i in range(num_fwh):
        def_p = st.session_state["P_exts_kPa"][i] if i < len(st.session_state["P_exts_kPa"]) else (P_cald_kPa / (i + 2))
        p_val = st.number_input(f"Presión Extracción FWH #{i+1} [kPa]", min_value=float(P_cond_kPa), max_value=float(P_cald_kPa), value=float(def_p), step=50.0)
        P_exts_kPa.append(p_val)

with st.sidebar.expander("⚙️ 4. Eficiencias Isentrópicas", expanded=False):
    eta_t_pct = st.slider("Eficiencia Turbina (η_t) [%]", min_value=50.0, max_value=100.0, value=st.session_state["eta_t"], step=1.0)
    eta_p_pct = st.slider("Eficiencia Bombas (η_p) [%]", min_value=50.0, max_value=100.0, value=st.session_state["eta_p"], step=1.0)
    eta_t = eta_t_pct / 100.0
    eta_p = eta_p_pct / 100.0

with st.sidebar.expander("🌡️ 5. Segunda Ley y Exergía (Entorno)", expanded=True):
    TH_K = st.number_input("Temp. Fuente de Calor / Horno (T_H) [K]", min_value=300.0, max_value=2500.0, value=st.session_state["TH_K"], step=25.0)
    T0_K = st.number_input("Temp. Ambiente / Sumidero (T_0) [K]", min_value=250.0, max_value=350.0, value=st.session_state["T0_K"], step=5.0)

with st.sidebar.expander("⚡ 6. Flujo Másico y Potencia", expanded=False):
    opcion_potencia = st.selectbox("Dato Adicional:", ["Ninguno (Base: 1 kg/s)", "Potencia Neta Deseada (MW)", "Flujo Másico Conocido (kg/s)"])
    val_pot = st.number_input("Valor Numérico:", min_value=0.1, value=100.0, step=1.0)

# ==========================================
# 3. MOTOR TERMODINÁMICO UNIVERSAL (CoolProp)
# ==========================================
fluido = 'Water'
P_cald = P_cald_kPa * 1e3
P_cond = P_cond_kPa * 1e3
T_max = T_max_C + 273.15
P_recal = P_recal_kPa * 1e3
T_recal = T_recal_C + 273.15

try:
    # --- Estado 3: Entrada Turbina Alta Presión ---
    h3 = CP.PropsSI('H', 'P', P_cald, 'T', T_max, fluido)
    s3 = CP.PropsSI('S', 'P', P_cald, 'T', T_max, fluido)

    # --- Expansión en Turbina (Simple, Recalentamiento o Regenerativo) ---
    if tiene_recal:
        # Turbina AP
        h4s = CP.PropsSI('H', 'P', P_recal, 'S', s3, fluido)
        h4 = h3 - eta_t * (h3 - h4s)
        s4 = CP.PropsSI('S', 'P', P_recal, 'H', h4, fluido)
        w_turb_AP = h3 - h4

        # Recalentamiento (Estado 5)
        h5 = CP.PropsSI('H', 'P', P_recal, 'T', T_recal, fluido)
        s5 = CP.PropsSI('S', 'P', P_recal, 'T', T_recal, fluido)
        q_recal = h5 - h4

        # Turbina BP
        h6s = CP.PropsSI('H', 'P', P_cond, 'S', s5, fluido)
        h6 = h5 - eta_t * (h5 - h6s)
        s6 = CP.PropsSI('S', 'P', P_cond, 'H', h6, fluido)
        T6 = CP.PropsSI('T', 'P', P_cond, 'H', h6, fluido) - 273.15
        w_turb_BP = h5 - h6

        w_turb_total = w_turb_AP + w_turb_BP
        h_salida_turb = h6
        s_salida_turb = s6
    else:
        # Turbina única sin recalentamiento
        q_recal = 0.0
        h4s = CP.PropsSI('H', 'P', P_cond, 'S', s3, fluido)
        h4 = h3 - eta_t * (h3 - h4s)
        s4 = CP.PropsSI('S', 'P', P_cond, 'H', h4, fluido)
        T4 = CP.PropsSI('T', 'P', P_cond, 'H', h4, fluido) - 273.15
        w_turb_total = h3 - h4
        h_salida_turb = h4
        s_salida_turb = s4

    # --- Bomba y Condensador ---
    h1 = CP.PropsSI('H', 'P', P_cond, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P_cond, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P_cond, 'Q', 0, fluido)

    w_bomba_s = v1 * (P_cald - P_cond)
    w_bomba_total = w_bomba_s / eta_p
    h2 = h1 + w_bomba_total
    s2 = CP.PropsSI('S', 'P', P_cald, 'H', h2, fluido)

    # --- Balances de Energía Globales ---
    q_in = (h3 - h2) + q_recal
    q_out = h_salida_turb - h1
    w_neto = w_turb_total - w_bomba_total
    eta_th = (w_neto / q_in) * 100.0

    # --- Segunda Ley y Destrucción de Exergía ---
    s_gen_bomba = max(0.0, s2 - s1)
    s_gen_cald = (s3 - s2) - ((h3 - h2) / TH_K)
    if tiene_recal:
        s_gen_cald += (s5 - s4) - (q_recal / TH_K)

    s_gen_turb = max(0.0, s_salida_turb - (s5 if tiene_recal else s3))
    s_gen_cond = (s1 - s_salida_turb) + (q_out / T0_K)
    s_gen_total = s_gen_bomba + s_gen_cald + s_gen_turb + s_gen_cond

    x_dest_bomba = T0_K * s_gen_bomba
    x_dest_cald = T0_K * s_gen_cald
    x_dest_turb = T0_K * s_gen_turb
    x_dest_cond = T0_K * s_gen_cond
    x_dest_total = T0_K * s_gen_total

    w_rev = q_in * (1.0 - (T0_K / TH_K))
    eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

    # --- Manejo de Flujo Másico o Potencia Neta ---
    if opcion_potencia == "Potencia Neta Deseada (MW)":
        flujo_masico = (val_pot * 1e6) / w_neto
        potencia_neta = val_pot
    elif opcion_potencia == "Flujo Másico Conocido (kg/s)":
        flujo_masico = val_pot
        potencia_neta = (flujo_masico * w_neto) / 1e6
    else:
        flujo_masico = 1.0
        potencia_neta = (w_neto) / 1e6

    # ==========================================
    # 4. TABLERO DE RESULTADOS
    # ==========================================
    st.subheader("📊 Resultados Numéricos del Ciclo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Eficiencia Térmica (1ra Ley)", f"{eta_th:.2f} %")
    c2.metric("Eficiencia Exergética (2da Ley)", f"{eta_II:.2f} %")
    c3.metric("Trabajo Neto Específico", f"{w_neto/1e3:.2f} kJ/kg")
    c4.metric("Calor Entrada (Qin)", f"{q_in/1e3:.2f} kJ/kg")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Exergía Destruida Caldera", f"{x_dest_cald/1e3:.2f} kJ/kg")
    c6.metric("Exergía Destruida Condensador", f"{x_dest_cond/1e3:.2f} kJ/kg")
    c7.metric("Exergía Destruida Turbina", f"{x_dest_turb/1e3:.2f} kJ/kg")
    c8.metric("Exergía Destruida Total", f"{x_dest_total/1e3:.2f} kJ/kg")

    if opcion_potencia != "Ninguno (Base: 1 kg/s)":
        cp1, cp2 = st.columns(2)
        cp1.info(f"**Flujo Másico Requerido:** {flujo_masico:.2f} kg/s")
        cp2.info(f"**Potencia Neta Total:** {potencia_neta:.2f} MW")

    # ==========================================
    # 5. DIAGRAMA T-s REAL Y CAMPANA DE SATURACIÓN
    # ==========================================
    st.subheader("📈 Diagrama Temperatura - Entropía (T-s)")
    T_crit = CP.PropsSI('Tcrit', fluido)
    T_rango = np.linspace(274.15, T_crit - 1.0, 200)
    S_liq = [CP.PropsSI('S', 'T', T, 'Q', 0, fluido)/1e3 for T in T_rango]
    S_vap = [CP.PropsSI('S', 'T', T, 'Q', 1, fluido)/1e3 for T in T_rango]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(S_liq, T_rango - 273.15, 'k--', label='Campana Sat. Líquido')
    ax.plot(S_vap, T_rango - 273.15, 'k-', label='Campana Sat. Vapor')

    # Puntos del ciclo
    if tiene_recal:
        s_pts = [s1/1e3, s2/1e3, s3/1e3, s4/1e3, s5/1e3, s6/1e3, s1/1e3]
        t_pts = [CP.PropsSI('T', 'P', P_cond, 'Q', 0, fluido)-273.15, 
                 CP.PropsSI('T', 'P', P_cald, 'H', h2, fluido)-273.15, 
                 T_max_C, 
                 CP.PropsSI('T', 'P', P_recal, 'H', h4, fluido)-273.15, 
                 T_recal_C, 
                 T6, 
                 CP.PropsSI('T', 'P', P_cond, 'Q', 0, fluido)-273.15]
    else:
        s_pts = [s1/1e3, s2/1e3, s3/1e3, s4/1e3, s1/1e3]
        t_pts = [CP.PropsSI('T', 'P', P_cond, 'Q', 0, fluido)-273.15, 
                 CP.PropsSI('T', 'P', P_cald, 'H', h2, fluido)-273.15, 
                 T_max_C, 
                 T4, 
                 CP.PropsSI('T', 'P', P_cond, 'Q', 0, fluido)-273.15]

    ax.plot(s_pts, t_pts, 'ro-', linewidth=2, label=f'Ciclo Rankine (η_th={eta_th:.1f}%, η_II={eta_II:.1f}%)')
    ax.set_xlabel("Entropía [kJ/kg·K]")
    ax.set_ylabel("Temperatura [°C]")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()
    st.pyplot(fig)

except Exception as err:
    st.error(f"Error en los cálculos de CoolProp: {err}")
