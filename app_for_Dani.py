import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
import plotly.express as px

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster Logistics", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. MOTOR DE UTILIDADES ---
def procesar_foto(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)) 
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=70)
    return base64.b64encode(output.getvalue()).decode()

def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

def limpiar(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

def generar_pdf(df_gastos, mes, año, logo_p):
    pdf = FPDF()
    pdf.add_page()
    if logo_p and os.path.exists(logo_p):
        try:
            img = Image.open(logo_p).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            pdf.image(buf, x=10, y=8, w=33, type='JPEG')
        except: pass
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 15, txt=limpiar(f"REPORTE LOGÍSTICO - {mes}"), ln=True, align='R')
    pdf.ln(10)
    pdf.set_fill_color(37, 211, 102); pdf.set_text_color(0)
    w = [35, 100, 55]
    pdf.cell(w[0], 10, "Fecha", 1, 0, 'C', True)
    pdf.cell(w[1], 10, "Concepto", 1, 0, 'C', True)
    pdf.cell(w[2], 10, "Monto", 1, 1, 'C', True)
    pdf.set_text_color(0)
    for i, row in df_gastos.iterrows():
        pdf.cell(w[0], 10, str(row['fecha'].date()), 1)
        pdf.cell(w[1], 10, f" {row['concepto']}", 1)
        pdf.cell(w[2], 10, f"CRC {row['monto']:,.0f}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- 2. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "Dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "Padre_Andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 3. DISEÑO PREMIUM ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))
st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.92); padding: 2.5rem; border-radius: 25px; border: 1px solid #25D366; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; font-weight: bold; border-radius: 12px; border: none; height: 3rem; }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTA MASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)
tabs = st.tabs(["📝 REGISTRO", "🔧 MOTOR", "📊 REPORTES"])

# --- TAB 1: REGISTRO DINÁMICO ---
with tabs[0]:
    st.subheader("Añadir Nuevo Gasto")
    with st.container():
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = c2.number_input("Monto (CRC)", min_value=0, step=500)
        c3, c4 = st.columns(2)
        km = c3.number_input("KM Actual", min_value=0)
        fecha = c4.date_input("Fecha", datetime.now())
        foto = st.file_uploader("📷 Foto Ticket", type=['jpg', 'png', 'jpeg'])
        
        if st.button("🚀 GUARDAR EN NUBE"):
            try:
                f_bytes = procesar_foto(foto) if foto else None
                supabase.table("gastos").insert({"fecha": str(fecha), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": f_bytes}).execute()
                supabase.table("viajes").insert({"fecha": str(fecha), "km_actual": km, "cliente_id": u}).execute()
                st.success("✅ Sincronizado")
                st.balloons()
            except: st.error("Error de conexión.")

# --- TAB 2: MOTOR ---
with tabs[1]:
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("Kilometraje Acumulado", f"{kh:,} km")
    except: st.info("Cargando...")

# --- TAB 3: REPORTES COMPLETOS (GRÁFICO REDONDO) ---
with tabs[2]:
    st.subheader("Análisis de Operación")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            if not df_f.empty:
                # MÉTRICAS
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Gasto Total", f"CRC {df_f['monto'].sum():,.0f}")
                col_m2.metric("N° Registros", len(df_f))
                
                # GRÁFICO REDONDO (INTERACTIVO)
                st.subheader("🍩 Distribución de Gastos")
                fig = px.pie(df_f, values='monto', names='concepto', hole=.4, color_discrete_sequence=px.colors.sequential.Greens_r)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#25D366")
                st.plotly_chart(fig, use_container_width=True)
                
                # TABLA Y GESTIÓN
                st.subheader("📋 Historial")
                st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
                
                with st.expander("🛠️ Administrar Fotos y Borrar"):
                    for i, row in df_f.iterrows():
                        ca, cb, cc = st.columns([0.6, 0.2, 0.2])
                        ca.write(f"📅 {row['fecha'].strftime('%d/%m')} - {row['concepto']}")
                        if row.get('foto_comprobante'):
                            if cb.button("📷", key=f"v_{row['id']}"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
                        if cc.button("🗑️", key=f"d_{row['id']}"):
                            supabase.table("gastos").delete().eq("id", row['id']).execute()
                            st.rerun()
            else: st.info("Sin datos.")
    except: st.error("Error al cargar.")