import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster", layout="centered")

def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. DISEÑO NEÓN OSCURO (PIEL/ESCAMA) ---
def get_base64(file_path):
    with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()

fondo_path = st.secrets.get("APP_BACKGROUND_PATH", None)
logo_path = st.secrets.get("APP_LOGO_PATH", None)

estilo_css = f"""
<style>
    .stApp {{
        background-color: #000000;
        {"background-image: url(data:image/png;base64," + get_base64(fondo_path) + ");" if fondo_path and os.path.exists(fondo_path) else ""}
        background-size: cover;
        background-attachment: fixed;
    }}
    [data-testid="stAppViewBlockContainer"] {{
        background-color: rgba(15, 15, 15, 0.90);
        padding: 3rem;
        border-radius: 20px;
        border: 2px solid #25D366; /* Verde Neón */
        box-shadow: 0px 0px 15px #25D366;
    }}
    h1, h2, h3, p, span, label, .stMetric {{ color: white !important; font-weight: bold; }}
    .stButton>button {{
        background-color: #25D366 !important;
        color: black !important;
        font-weight: bold !important;
        border-radius: 10px;
        border: none;
        width: 100%;
    }}
    [data-testid="stDownloadButton"] button {{
        background-color: #D32F2F !important; /* Rojo para PDF */
        color: white !important;
        width: 100%;
        border-radius: 10px;
    }}
</style>
"""
st.markdown(estilo_css, unsafe_allow_html=True)

# --- 2. LOGIN Y PROTOCOLO ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    if logo_path and os.path.exists(logo_path): st.image(logo_path, width=200)
    st.markdown("<h1 style='text-align: center; color: #25D366 !important;'>🛡️ Aisaac Shield Systems</h1>", unsafe_allow_html=True)
    
    with st.container():
        pin = st.text_input("PIN de Acceso", type="password", placeholder="****")
        if st.button("DESBLOQUEAR SISTEMA"):
            if pin == "8715":
                st.session_state['autenticado'] = True
                st.session_state['cliente_id'] = "Dany"
                st.rerun()
            else: st.error("Acceso Denegado")
    
    st.markdown("""
    <div style="background-color: rgba(0,0,0,0.8); border-left: 5px solid #25D366; padding: 15px; border-radius: 8px; margin-top: 20px;">
        <span style="color: #25D366;">🛡️ Protocolo de Confidencialidad:</span> Sus datos están cifrados y protegidos. Propiedad de Transportes B&J.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 3. INTERFAZ PRINCIPAL ---
tabs = st.tabs(["➕ Viajes", "📉 Gastos", "🔧 Taller", "📊 Reportes"])

with tabs[0]:
    st.header("Registrar Viaje")
    with st.form("f_v"):
        f = st.date_input("Fecha", datetime.now())
        dest = st.text_input("Destino")
        monto = st.number_input("Monto (CRC)", min_value=0)
        km = st.number_input("Kilometraje Actual", min_value=0)
        if st.form_submit_button("Guardar en Nube"):
            try:
                supabase.table("viajes").insert({"fecha": str(f), "cliente": dest, "monto": monto, "km_actual": km, "cliente_id": "Dany"}).execute()
                st.success("✅ Datos guardados.")
            except: st.error("Error: Revise que la columna 'km_actual' exista en Supabase.")

with tabs[2]:
    st.header("🔧 Control de Aceite")
    try:
        # Lógica de Kilometraje
        res_v = supabase.table("viajes").select("km_actual").eq("cliente_id", "Dany").order("created_at", desc=True).limit(1).execute()
        km_h = res_v.data[0]['km_actual'] if res_v.data else 0
        
        res_m = supabase.table("mantenimiento").select("*").eq("cliente_id", "Dany").order("km_cambio", desc=True).limit(1).execute()
        
        if res_m.data:
            ultimo = res_m.data[0]
            restante = ultimo['km_proximo'] - km_h
            st.metric("KM ACTUAL", f"{km_h:,} km")
            if restante <= 500: st.error(f"🚨 CAMBIO URGENTE EN: {restante} km")
            else: st.success(f"✅ Motor Protegido: {restante} km restantes")
        
        with st.expander("Registrar Nuevo Servicio"):
            with st.form("f_t"):
                k_c = st.number_input("KM del cambio", value=km_h)
                k_p = st.number_input("Próximo cambio", value=k_c + 5000)
                if st.form_submit_button("Actualizar Taller"):
                    supabase.table("mantenimiento").insert({"fecha": str(datetime.now().date()), "km_cambio": k_c, "km_proximo": k_p, "cliente_id": "Dany"}).execute()
                    st.rerun()
    except:
        st.warning("⚠️ Configure 'cliente_id' como tipo TEXT en la tabla mantenimiento de Supabase.")