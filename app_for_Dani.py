import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import base64
import os

# --- 0. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="RutaMaster", layout="centered")

# --- INICIALIZAR SUPABASE ---
@st.cache_resource
def init_conexion():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_conexion()

# --- 1. GESTIÓN DE MARCA (LOGO Y FONDO) ---
@st.cache_resource
def obtener_marca():
    try:
        logo = st.secrets.get("APP_LOGO_PATH", None)
        fondo = st.secrets.get("APP_BACKGROUND_PATH", None)
        return logo, fondo
    except Exception:
        return None, None

logo_path, fondo_path = obtener_marca()

# --- INYECTAR ESTILO ---
if fondo_path and os.path.exists(fondo_path):
    with open(fondo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    st.markdown(
    f"""
    <style>
    .stApp {{ background-image: url(data:image/png;base64,{encoded_string}); background-size: cover; background-position: center; background-attachment: fixed; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.80); padding: 2rem; border-radius: 15px; color: white; }}
    h1, h2, h3, p, span {{ color: white !important; }}
    [data-testid="stFormSubmitButton"] button {{ background-color: #FF4B4B !important; color: white !important; width: 100%; border-radius: 10px; }}
    [data-testid="stDownloadButton"] button[kind="primary"] {{ background-color: #D32F2F !important; color: white !important; width: 100%; border-radius: 10px; }}
    [data-testid="stDownloadButton"] button[kind="secondary"] {{ background-color: #107C41 !important; color: white !important; width: 100%; border-radius: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CANDADO DIGITAL (LOGIN) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'cliente_id' not in st.session_state:
    st.session_state['cliente_id'] = None

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center;'>🛡️ Aisaac Shield Systems</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Acceso oficial a la plataforma de gestión logística</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN", type="password", label_visibility="collapsed", placeholder="****")
        if st.button("Desbloquear Sistema"):
            if pin == "8715": 
                st.session_state['autenticado'] = True
                st.session_state['cliente_id'] = "Dany"  
                st.rerun()
            else:
                st.error("❌ PIN incorrecto.")
    
    st.markdown("""
    <div style="background-color: rgba(30, 30, 30, 0.8); border-left: 5px solid #25D366; padding: 15px; border-radius: 8px; margin-top: 30px;">
        <h4 style="margin-top:0; color: #25D366; font-size: 16px;">🛡️ Protocolo de Confidencialidad</h4>
        <p style="font-size: 13px; color: #E0E0E0; line-height: 1.5; margin-bottom: 0;">
            <b>Propiedad:</b> Toda la información ingresada es propiedad exclusiva de <b>Transportes B&J</b>.<br><br>
            <b>Seguridad:</b> Sus datos están resguardados en servidores cifrados en la nube. El desarrollador no tiene acceso de lectura.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop() 

# --- GESTIÓN DE LICENCIA ---
def obtener_licencia_remota(cliente_nombre):
    try:
        respuesta = supabase.table("licencias").select("*").eq("cliente", cliente_nombre).execute()
        if respuesta.data:
            d = respuesta.data[0]
            return d['fecha_vencimiento'], d['llave_activa'], d.get('plan', 'estandar')
    except: pass
    return "2000-01-01", False, "estandar"

fecha_v, activa_l, plan_c = obtener_licencia_remota(st.session_state['cliente_id'])

def verificar_licencia(f_v, act):
    if not act: return "BLOQUEADO"
    if datetime.strptime(f_v, "%Y-%m-%d") < datetime.now(): return "VENCIDO"
    return "ACTIVO"

if verificar_licencia(fecha_v, activa_l) != "ACTIVO":
    st.error("⚠️ Licencia inactiva o vencida. Contacte a soporte.")
    st.stop()

# --- FUNCIONES DE PDF ---
def limpiar(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

def generar_pdf(df_gastos, mes, año):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image.open(logo_path).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            pdf.image(buf, x=10, y=8, w=33, type='JPEG')
        except: pass
    pdf.set_font("Arial", 'B', 20); pdf.set_text_color(0, 51, 153)
    pdf.cell(0, 15, txt=limpiar("REPORTE MENSUAL DE GASTOS"), ln=True, align='R')
    pdf.set_font("Arial", size=10); pdf.set_text_color(100)
    pdf.cell(0, 5, txt=limpiar(f"Periodo: {mes} {año}"), ln=True, align='R')
    pdf.ln(20)
    pdf.set_fill_color(0, 51, 153); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 12)
    w = [35, 100, 55]
    pdf.cell(w[0], 12, limpiar("Fecha"), 1, 0, 'C', True)
    pdf.cell(w[1], 12, limpiar("Concepto"), 1, 0, 'C', True)
    pdf.cell(w[2], 12, limpiar("Monto (CRC)"), 1, 1, 'C', True)
    pdf.set_text_color(0); pdf.set_font("Arial", size=11)
    fill = False
    for _, f in df_gastos.iterrows():
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w[0], 10, limpiar(f['fecha'].date()), 1, 0, 'C', fill)
        pdf.cell(w[1], 10, f" {limpiar(f['concepto'])}", 1, 0, 'L', fill)
        pdf.cell(w[2], 10, f"CRC {f['monto']:,.0f} ", 1, 1, 'R', fill)
        fill = not fill
    pdf.set_y(-20); pdf.set_font("Arial", 'I', 8); pdf.set_text_color(150)
    pdf.cell(0, 10, limpiar("Generado por Aisaac Shield Systems - aisaac-shield.com"), 0, 0, 'C')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ ---
if logo_path and os.path.exists(logo_path):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2: st.image(logo_path, use_container_width=True)

tabs = st.tabs(["➕ Viajes", "📉 Gastos", "🔧 Taller", "📊 Resumen"])

with tabs[0]:
    st.header("Registrar Viaje")
    with st.form("f_v", clear_on_submit=True):
        f = st.date_input("Fecha", datetime.now())
        c = st.text_input("Cliente / Destino")
        m = st.number_input("Monto Flete (CRC)", min_value=0)
        km = st.number_input("Kilometraje Actual", min_value=0)
        if st.form_submit_button("Guardar"):
            try:
                supabase.table("viajes").insert({"fecha": f.strftime("%Y-%m-%d"), "cliente": c, "monto": m, "km_actual": km, "cliente_id": st.session_state['cliente_id']}).execute()
                st.success("✅ Guardado.")
            except: st.error("❌ Error: Asegúrese de que la columna 'km_actual' existe en la tabla 'viajes'.")

with tabs[1]:
    st.header("Registrar Gasto")
    with st.form("f_g", clear_on_submit=True):
        f_g = st.date_input("Fecha", datetime.now())
        con = st.selectbox("Concepto", ["Diesel", "Peaje", "Mantenimiento", "Comida", "Otros"])
        mon = st.number_input("Monto", min_value=0)
        if st.form_submit_button("Registrar"):
            try:
                supabase.table("gastos").insert({"fecha": f_g.strftime("%Y-%m-%d"), "concepto": con, "monto": mon, "cliente_id": st.session_state['cliente_id']}).execute()
                st.success("✅ Registrado.")
            except: st.error("❌ Error al guardar gasto.")

with tabs[2]:
    st.header("🔧 Taller (Aceite)")
    cli = st.session_state['cliente_id']
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", cli).order("created_at", desc=True).limit(1).execute()
        km_h = rk.data[0]['km_actual'] if rk.data else 0
        rm = supabase.table("mantenimiento").select("*").eq("cliente_id", cli).order("km_cambio", desc=True).limit(1).execute()
        
        if rm.data:
            ma = rm.data[0]
            fal = ma['km_proximo'] - km_h
            st.metric("KM Actual", f"{km_h:,}")
            if fal <= 500: st.error(f"🚨 Toca cambio en: {fal:,} km")
            else: st.success(f"✅ Aceite OK: {fal:,} km restantes")
        
        with st.expander("Registrar Nuevo Cambio"):
            with st.form("f_m"):
                km_ca = st.number_input("KM del Cambio", value=km_h)
                km_pr = st.number_input("Próximo Cambio", value=km_ca + 5000)
                if st.form_submit_button("Actualizar Taller"):
                    supabase.table("mantenimiento").insert({"fecha": datetime.now().strftime("%Y-%m-%d"), "km_cambio": km_ca, "km_proximo": km_pr, "cliente_id": cli}).execute()
                    st.rerun()
    except: st.error("❌ Error de Taller: Verifique que la columna 'cliente_id' en 'mantenimiento' sea tipo TEXT.")

with tabs[3]:
    st.header("📊 Reportes")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", st.session_state['cliente_id']).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_s = st.selectbox("Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_s)+1)]
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 Excel", df_f.to_csv(index=False).encode('utf-8'), "gastos.csv", "text/csv")
            with col2:
                pb = generar_pdf(df_f, m_s, 2026)
                st.download_button("📄 PDF", pb, "reporte.pdf", "application/pdf", type="primary")
    except: st.info("Sin datos para mostrar.")