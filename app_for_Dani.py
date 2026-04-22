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
st.set_page_config(page_title="RutaMaster Logistics", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. FUNCIONES DE OPTIMIZACIÓN ---
def procesar_foto(uploaded_file):
    """Reduce el tamaño de la foto para no saturar Supabase"""
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)) 
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=70)
    return output.getvalue()

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
    pdf.set_font("Arial", 'B', 18); pdf.set_text_color(37, 211, 102)
    pdf.cell(0, 15, txt=limpiar("REPORTE LOGÍSTICO"), ln=True, align='R')
    pdf.ln(20)
    pdf.set_fill_color(37, 211, 102); pdf.set_text_color(0); pdf.set_font("Arial", 'B', 12)
    w = [35, 100, 55]
    pdf.cell(w[0], 12, limpiar("Fecha"), 1, 0, 'C', True)
    pdf.cell(w[1], 12, limpiar("Concepto"), 1, 0, 'C', True)
    pdf.cell(w[2], 12, limpiar("Monto (CRC)"), 1, 1, 'C', True)
    for i, row in df_gastos.iterrows():
        pdf.set_fill_color(245, 245, 245) if i%2==0 else pdf.set_fill_color(255, 255, 255)
        f_val = row['fecha'].strftime('%Y-%m-%d') if hasattr(row['fecha'], 'strftime') else str(row['fecha'])
        pdf.cell(w[0], 10, limpiar(f_val), 1, 0, 'C', True)
        pdf.cell(w[1], 10, f" {limpiar(row['concepto'])}", 1, 0, 'L', True)
        pdf.cell(w[2], 10, f"CRC {row['monto']:,.0f} ", 1, 1, 'R', True)
    return pdf.output(dest='S').encode('latin-1')

# --- 2. LOGIN (8715 y 8742) ---
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

# --- 3. INTERFAZ ---
u = st.session_state['user']
logo_path = st.secrets.get("APP_LOGO_PATH")
fondo_path = st.secrets.get("APP_BACKGROUND_PATH")
fondo_b64 = get_base64(fondo_path)

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    [data-testid="stToolbar"] {{ visibility: visible !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.93); padding: 2.5rem; border-radius: 25px; border: 1px solid #25D366; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366) !important; color: white !important; font-weight: bold; border-radius: 12px; }}
    h1, h2, .stMetric, label {{ color: #25D366 !important; }}
</style>
""", unsafe_allow_html=True)

# Título dinámico para evitar el error de base de datos
st.markdown(f"<h2 style='text-align: center;'>🚚 RUTA MASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)
tabs = st.tabs(["📝 REGISTRO", "🔧 MOTOR", "📊 REPORTES"])

with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Gasto", ["Diesel", "Peaje", "Aceite", "Otros"])
        monto = col2.number_input("Monto (CRC)", min_value=0)
        km = st.number_input("Kilometraje Actual", min_value=0)
        foto = st.file_uploader("📷 Foto del Ticket", type=['jpg', 'png', 'jpeg'])
        if st.form_submit_button("SINCRONIZAR DATOS"):
            try:
                # La función procesar_foto está lista si decidís guardar los bytes en Supabase
                # f_bytes = procesar_foto(foto) if foto else None
                supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u}).execute()
                supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                st.success(f"✅ Sincronizado para {u}")
                st.balloons()
            except Exception as e: st.error(f"Error de base de datos: {e}")

with tabs[1]:
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        rm = supabase.table("mantenimiento").select("*").eq("cliente_id", u).order("km_cambio", desc=True).limit(1).execute()
        if rm.data:
            m = rm.data[0]; rest = m['km_proximo'] - kh
            st.metric("KM Actual", f"{kh:,} km")
            if rest <= 500: st.error(f"🚨 TALLER URGENTE: {rest} km")
            else: st.success(f"✅ Motor OK: {rest} km restantes")
    except: st.info("Cargando datos del motor...")

with tabs[2]:
    st.header("📊 Reportes")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            for i, row in df_f.iterrows():
                c1, c2 = st.columns([0.8, 0.2])
                c1.write(f"📅 {row['fecha'].strftime('%d/%m')} | {row['concepto']} | `CRC {row['monto']:,.0f}`")
                if c2.button("🗑️", key=f"del_{row['id']}"):
                    supabase.table("gastos").delete().eq("id", row['id']).execute()
                    st.rerun()
            
            st.divider()
            pdf_b = generar_pdf(df_f, m_sel, 2026, logo_path)
            st.download_button("📄 Bajar PDF", pdf_b, "reporte.pdf", "application/pdf")
        else: st.info("No hay datos registrados aún.")
    except Exception as e: st.error(f"Error al cargar historial: {e}")