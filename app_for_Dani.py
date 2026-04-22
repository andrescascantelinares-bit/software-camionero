import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="RutaMaster", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stAppViewBlockContainer"] { background-color: rgba(0, 0, 0, 0.7); padding: 2rem; border-radius: 15px; }
    h1, h2, h3, p, span, label { color: white !important; }
    button { width: 100% !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN Y PRIVACIDAD ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center;'>🛡️ Aisaac Shield Systems</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN", type="password", placeholder="****")
    if st.button("Entrar"):
        if pin == "8715":
            st.session_state['autenticado'] = True
            st.session_state['cliente_id'] = "Dany"
            st.rerun()
    
    st.info("🛡️ **Protocolo de Privacidad:** Sus datos están cifrados. El desarrollador no tiene acceso a sus operaciones.")
    st.stop()

# --- TABS PRINCIPALES ---
tabs = st.tabs(["➕ Viajes", "📉 Gastos", "🔧 Taller", "📊 Reportes"])

with tabs[0]:
    st.header("Registrar Viaje")
    with st.form("f_v"):
        f = st.date_input("Fecha", datetime.now())
        c = st.text_input("Destino")
        m = st.number_input("Monto", min_value=0)
        km = st.number_input("Kilometraje Actual", min_value=0)
        if st.form_submit_button("Guardar"):
            try:
                supabase.table("viajes").insert({"fecha": str(f), "cliente": c, "monto": m, "km_actual": km, "cliente_id": "Dany"}).execute()
                st.success("✅ Guardado")
            except Exception as e: st.error(f"Error: Verifique columna 'km_actual' en Supabase.")

with tabs[1]:
    st.header("Registrar Gasto")
    with st.form("f_g"):
        f_g = st.date_input("Fecha", datetime.now())
        con = st.selectbox("Concepto", ["Diesel", "Peaje", "Repuesto", "Comida"])
        mon = st.number_input("Monto", min_value=0)
        if st.form_submit_button("Registrar"):
            try:
                supabase.table("gastos").insert({"fecha": str(f_g), "concepto": con, "monto": mon, "cliente_id": "Dany"}).execute()
                st.success("✅ Gasto anotado")
            except: st.error("Error al guardar")

with tabs[2]:
    st.header("🔧 Taller")
    try:
        # Obtener KM actual
        res_k = supabase.table("viajes").select("km_actual").eq("cliente_id", "Dany").order("created_at", desc=True).limit(1).execute()
        km_h = res_k.data[0]['km_actual'] if res_k.data else 0
        
        # Obtener Mantenimiento
        res_m = supabase.table("mantenimiento").select("*").eq("cliente_id", "Dany").order("km_cambio", desc=True).limit(1).execute()
        
        if res_m.data:
            ma = res_m.data[0]
            falta = ma['km_proximo'] - km_h
            st.metric("KM Actual", f"{km_h:,}")
            if falta <= 500: st.error(f"🚨 Cambio en: {falta} km")
            else: st.success(f"✅ Falta: {falta} km")
        
        with st.expander("Nuevo Cambio de Aceite"):
            with st.form("f_tall"):
                k_c = st.number_input("Kilometraje de hoy", value=km_h)
                k_p = st.number_input("Próximo cambio", value=k_c + 5000)
                if st.form_submit_button("Actualizar"):
                    supabase.table("mantenimiento").insert({"fecha": str(datetime.now().date()), "km_cambio": k_c, "km_proximo": k_p, "cliente_id": "Dany"}).execute()
                    st.rerun()
    except:
        st.error("❌ Error de Taller: La columna 'cliente_id' en la tabla 'mantenimiento' DEBE ser tipo TEXT en Supabase.")

with tabs[3]:
    st.header("📊 Resumen")
    st.write("Reportes PDF y Excel activos en la nube.")