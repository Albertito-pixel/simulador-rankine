import streamlit as st
import CoolProp.CoolProp as CP
import matplotlib.pyplot as plt
import numpy as np
import json
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="Simulador Ciclo Rankine + IA", layout="wide")

st.title("⚡ Simulador Interactivo: Ciclo Rankine Regenerativo")
st.markdown("Herramienta de cálculo termodinámico con propiedades reales de agua (`CoolProp`) y resolución automática por imagen vía **Gemini Vision**.")

# ==========================================
# CONFIGURACIÓN API DE GEMINI
# ==========================================
API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# 1. SECCIÓN DE SUBIDA DE IMAGEN
# ==========================================
st.subheader("📷 Resolver automáticamente desde una captura")
archivo_subido = st.file_uploader("Arrastra o selecciona la captura del problema del libro/examen", type=["png", "jpg", "jpeg", "webp"])

# Variables por defecto
P_cald_def = 15000.0
T_max_def = 600.0
P_cond_def = 10.0
eta_t_def = 1.0
eta_p_def = 1.0
P_exts_def = [4000.0, 500.0]

if archivo_subido is not None:
    imagen = Image.open(archivo_subido)
    col_img, col_info = st.columns([1, 2])
    with col_img:
        st.image(imagen, caption="Imagen cargada", use_container_width=True)
    
    with col_info:
        with st.spinner("Analizando problema con IA..."):
            prompt = """
            Eres un experto en termodinámica. Lee atentamente la imagen del enunciado y/o diagrama del ciclo.
            Extrae los parámetros termodinámicos para un ciclo Rankine.
            Devuelve ÚNICAMENTE un JSON con esta estructura exacta:
            {
              "P_cald_kPa": float,
              "T_max_C": float,
              "P_cond_kPa": float,
              "eta_t": float,
              "eta_p": float,
              "P_exts_kPa": [lista de presiones de extracciones/calentadores ordenada de mayor a menor]
            }
            Reglas:
            - Presiones en kPa.
            - Temperaturas en Celsius (°C).
            - Si no menciona eficiencias isentrópicas, asigna 1.0.
            - Si no hay calentadores (FWH), 'P_exts_kPa' debe ser [].
            """
            try:
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[imagen, prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                datos_ia = json.loads(response.text)
                st.success("¡Datos extraídos con éxito!")
                st.json(datos_ia)

                # Sobrescribir valores
                P_cald_def = float(datos_ia.get("P_cald_kPa", P_cald_def))
                T_max_def = float(datos_ia.get("T_max_C", T_max_def))
                P_cond_def = float(datos_ia.get("P_cond_kPa", P_cond_def))
                eta_t_def = float(datos_ia.get("eta_t", eta_t_def))
                eta_p_def = float(datos_ia.get("eta_p", eta_p_def))
                P_exts_def = [float(p) for p in datos_ia.get("P_exts_kPa", [])]

            except Exception as e:
                st.error(f"Error al analizar la imagen: {e}")

st.markdown("---")

# ==========================================
# 2. PARÁMETROS DEL CICLO (BARRA LATERAL)
# ==========================================
st.sidebar.header("Parámetros del Ciclo")

P_cald_kPa = st.sidebar.number_input("Presión Caldera [kPa]", min_value=100.0, value=P_cald_def)
T_max_C = st.sidebar.slider("Temperatura Entrada Turbina [°C]", min_value=100.0, max_value=800.0, value=float(min(max(T_max_def, 100.0), 800.0)))
P_cond_kPa = st.sidebar.number_input("Presión Condensador [kPa]", min_value=1.0, value=P_cond_def)

tipo_ciclo = st.sidebar.selectbox("Régimen de Operación", ["Ideal (100% isentrópico)", "Real"])
if tipo_ciclo == "Real":
    eta_t = st.sidebar.slider("Eficiencia Turbina (η_t)", 0.50, 1.00, float(eta_t_def), 0.01)
    eta_p = st.sidebar.slider("Eficiencia Bombas (η_p)", 0.50, 1.00, float(eta_p_def), 0.01)
else:
    eta_t = 1.0
    eta_p = 1.0

st.sidebar.markdown("---")
num_fwh = st.sidebar.number_input("Cantidad de Calentadores (FWH)", min_value=0, max_value=8, value=len(P_exts_def))

P_exts_kPa = []
for i in range(num_fwh):
    val_def = P_exts_def[i] if i < len(P_exts_def) else (P_cald_kPa / (i + 2))
    p_val = st.sidebar.number_input(
        f"Presión FWH #{i+1} [kPa]",
        min_value=float(P_cond_kPa),
        max_value=float(P_cald_kPa),
        value=float(val_def)
    )
    P_exts_kPa.append(p_val)

# ==========================================
# 3. MOTOR TERMODINÁMICO (CoolProp)
# ==========================================
fluido = 'Water'
P_cald = P_cald_kPa * 1e3
P_cond = P_cond_kPa * 1e3
T_max = T_max_C + 273.15
P_exts = [p * 1e3 for p in sorted(P_exts_kPa, reverse=True)]
N_fwh = len(P_exts)

try:
    h_in = CP.PropsSI('H', 'P', P_cald, 'T', T_max, fluido)
    s_in = CP.PropsSI('S', 'P', P_cald, 'T', T_max, fluido)

    h_vapor = []
    for p_ext in P_exts:
        h_s = CP.PropsSI('H', 'P', p_ext, 'S', s_in, fluido)
        h_real = h_in - eta_t * (h_in - h_s)
        h_vapor.append(h_real)

    h_out_s = CP.PropsSI('H', 'P', P_cond, 'S', s_in, fluido)
    h_out_real = h_in - eta_t * (h_in - h_out_s)
    T_out = CP.PropsSI('T', 'P', P_cond, 'H', h_out_real, fluido) - 273.15
    s_out_real = CP.PropsSI('S', 'P', P_cond, 'H', h_out_real, fluido)

    h_liq_actual = CP.PropsSI('H', 'P', P_cond, 'Q', 0, fluido)
    v_liq = 1 / CP.PropsSI('D', 'P', P_cond, 'Q', 0, fluido)
    P_actual = P_cond

    h_liq_entradas, h_liq_salidas, w_bombas_esp = [], [], []
    for p_ext in reversed(P_exts):
        w_b = v_liq * (p_ext - P_actual) / eta_p
        w_bombas_esp.append(w_b)
        h_liq_entradas.append(h_liq_actual + w_b)
        h_liq_actual = CP.PropsSI('H', 'P', p_ext, 'Q', 0, fluido)
        h_liq_salidas.append(h_liq_actual)
        v_liq = 1 / CP.PropsSI('D', 'P', p_ext, 'Q', 0, fluido)
        P_actual = p_ext

    h_liq_entradas.reverse()
    h_liq_salidas.reverse()
    w_bombas_esp.reverse()

    w_b_final = v_liq * (P_cald - P_actual) / eta_p
    h_in_caldera = h_liq_actual + w_b_final
    w_bombas_esp.insert(0, w_b_final)

    y_frac = []
    flujo_masa = 1.0
    flujos_bomba = [1.0]
    for i in range(N_fwh):
        denom = h_vapor[i] - h_liq_entradas[i]
        y = flujo_masa * (h_liq_salidas[i] - h_liq_entradas[i]) / denom if denom != 0 else 0
        y_frac.append(y)
        flujo_masa -= y
        flujos_bomba.append(flujo_masa)

    w_turb_total = 1.0 * (h_in - h_vapor[0]) if N_fwh > 0 else 1.0 * (h_in - h_out_real)
    if N_fwh > 0:
        flujo_t = 1.0
        for i in range(N_fwh - 1):
            flujo_t -= y_frac[i]
            w_turb_total += flujo_t * (h_vapor[i] - h_vapor[i+1])
        flujo_t -= y_frac[-1]
        w_turb_total += flujo_t * (h_vapor[-1] - h_out_real)

    w_bombas_total = sum(f * w for f, w in zip(flujos_bomba, w_bombas_esp))
    q_in = h_in - h_in_caldera
    w_neto = w_turb_total - w_bombas_total
    eta_th = (w_neto / q_in) * 100 if q_in != 0 else 0

    # ==========================================
    # 4. MÉTRICAS Y RESULTADOS
    # ==========================================
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Eficiencia Térmica", f"{eta_th:.2f} %")
    m2.metric("Trabajo Neto", f"{w_neto/1e3:.2f} kJ/kg")
    m3.metric("Calor Suministrado (Qin)", f"{q_in/1e3:.2f} kJ/kg")
    m4.metric("Flujo hacia Condensador", f"{(flujo_masa*100):.2f} %")

    # ==========================================
    # 5. DIAGRAMA T-s
    # ==========================================
    st.subheader("Diagrama Temperatura - Entropía (T-s)")
    T_crit = CP.PropsSI('Tcrit', fluido)
    T_rango = np.linspace(274.15, T_crit - 1.0, 200)
    S_liq = [CP.PropsSI('S', 'T', T, 'Q', 0, fluido)/1e3 for T in T_rango]
    S_vap = [CP.PropsSI('S', 'T', T, 'Q', 1, fluido)/1e3 for T in T_rango]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(S_liq, T_rango - 273.15, 'k-', label='Campana Líquido')
    ax.plot(S_vap, T_rango - 273.15, 'k-', label='Campana Vapor')

    S_p = [CP.PropsSI('S', 'P', P_cond, 'Q', 0, fluido)/1e3]
    T_p = [CP.PropsSI('T', 'P', P_cond, 'Q', 0, fluido) - 273.15]
    S_p.extend([CP.PropsSI('S', 'P', P_cald, 'H', h_in_caldera, fluido)/1e3, s_in/1e3, s_out_real/1e3, S_p[0]])
    T_p.extend([CP.PropsSI('T', 'P', P_cald, 'H', h_in_caldera, fluido) - 273.15, T_max_C, T_out, T_p[0]])

    ax.plot(S_p, T_p, 'r-o', linewidth=2, label=f'Ciclo Rankine (η = {eta_th:.2f}%)')
    ax.set_xlabel("Entropía [kJ/kg·K]")
    ax.set_ylabel("Temperatura [°C]")
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    st.pyplot(fig)

except Exception as err:
    st.error(f"Error en los cálculos termodinámicos: {err}")
