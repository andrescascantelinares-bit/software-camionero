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
# Actualización SaaS
# --- 1. DISEÑO NEÓN PREMIUM (ESTILO PUMA/ESCAMA) ---
def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

fondo_path = st.secrets.get("APP_BACKGROUND_PATH", None)
logo_path = st.secrets.get("APP_LOGO_PATH", None)
fondo_b64 = get_base64(fondo_path)

st.markdown(f"""
<style>
    .stApp {{
        background-color: #000000;
        {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""}
        background-size: cover;
        background-attachment: fixed;
    }}
    [data-testid="stAppViewBlockContainer"] {{
        background-color: rgba(10, 10, 10, 0.92);
        padding: 3rem;
        border-radius: 20px;
        border: 2px solid #25D366; /* Verde Neón */
        box-shadow: 0px 0px 20px rgba(37, 211, 102, 0.3);
        margin-top: 2rem;
    }}
    .stMetric {{ background-color: rgba(30, 30, 30, 0.5); padding: 15px; border-radius: 10px; border: 1px solid #444; }}
    h1, h2, h3, p, span, label {{ color: white !important; font-family: 'Segoe UI', sans-serif; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: #1a1a1a;
        border-radius: 5px 5px 0 0;
        color: white;
        padding: 10px 20px;
    }}
    .stTabs [aria-selected="true"] {{ background-color: #25D366 !important; color: black !important; }}
    .stButton>button {{
        background-color: #25D366 !important;
        color: black !important;
        font-weight: bold !important;
        border-radius: 12px;
        border: none;
        transition: 0.3s;
    }}
    .stButton>button:hover {{ transform: scale(1.02); box-shadow: 0px 0px 15px #25D366; }}
    [data-testid="stDownloadButton"] button[kind="primary"] {{ background-color: #D32F2F !important; color: white !important; }}
    [data-testid="stDownloadButton"] button[kind="secondary"] {{ background-color: #107C41 !important; color: white !important; }}
</style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO (PDF PROFESIONAL) ---
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
    pdf.cell(0, 5, txt=limpiar(f"Transportes B&J | {mes} {año}"), ln=True, align='R')
    pdf.ln(20)
    pdf.set_fill_color(0, 51, 153); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 12)
    w = [35, 100, 55]
    pdf.cell(w[0], 12, limpiar("Fecha"), 1, 0, 'C', True)
    pdf.cell(w[1], 12, limpiar("Concepto"), 1, 0, 'C', True)
    pdf.cell(w[2], 12, limpiar("Monto (CRC)"), 1, 1, 'C', True)
    pdf.set_text_color(0); pdf.set_font("Arial", size=11)
    for i, f in df_gastos.iterrows():
        pdf.set_fill_color(245, 245, 245) if i%2==0 else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w[0], 10, limpiar(f['fecha'].date()), 1, 0, 'C', True)
        pdf.cell(w[1], 10, f" {limpiar(f['concepto'])}", 1, 0, 'L', True)
        pdf.cell(w[2], 10, f"CRC {f['monto']:,.0f} ", 1, 1, 'R', True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 12)
    pdf.cell(w[0] + w[1], 12, limpiar("TOTAL:"), 0, 0, 'R')
    pdf.set_fill_color(255, 204, 204); pdf.cell(w[2], 12, f"CRC {df_gastos['monto'].sum():,.0f} ", 1, 1, 'R', True)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    if logo_path and os.path.exists(logo_path): st.image(logo_path, width=180)
    st.markdown("<h1 style='text-align: center; color: #25D366 !important;'>🛡️ AISAAC SHIELD</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
    if st.button("DESBLOQUEAR SISTEMA"):
        if pin == "8715":
            st.session_state['autenticado'] = True
            st.rerun()
    st.markdown('<p style="background: rgba(37,211,102,0.1); padding: 10px; border-radius: 5px; border-left: 4px solid #25D366;">🛡️ <b>Confidencialidad:</b> Sus datos están protegidos bajo el cifrado de Aisaac Shield Systems.</p>', unsafe_allow_html=True)
    st.stop()

# --- 4. PANEL PRINCIPAL ---
tabs = st.tabs(["➕ VIAJES", "📉 GASTOS", "🔧 TALLER", "📊 RESUMEN"])

with tabs[0]:
    st.header("🚚 Registro de Fletes")
    with st.form("fv", clear_on_submit=True):
        f = st.date_input("Fecha")
        d = st.text_input("Destino")
        m = st.number_input("Monto CRC", min_value=0, step=5000)
        k = st.number_input("KM Actual", min_value=0)
        if st.form_submit_button("GUARDAR EN NUBE"):
            try:
                supabase.table("viajes").insert({"fecha": str(f), "cliente": d, "monto": m, "km_actual": k, "cliente_id": "Dany"}).execute()
                st.success("✅ Datos sincronizados")
            except: st.error("Error de base de datos")

with tabs[1]:
    st.header("💸 Registro de Gastos")
    with st.form("fg", clear_on_submit=True):
        f_g = st.date_input("Fecha")
        c_g = st.selectbox("Categoría", ["Diesel", "Peajes", "Repuestos", "Comida", "Otros"])
        m_g = st.number_input("Monto Gasto", min_value=0)
        if st.form_submit_button("REGISTRAR GASTO"):
            try:
                supabase.table("gastos").insert({"fecha": str(f_g), "concepto": c_g, "monto": m_g, "cliente_id": "Dany"}).execute()
                st.success("✅ Gasto registrado")
            except: st.error("Error de conexión")

with tabs[2]:
    st.header("🔧 Mantenimiento Preventivo")
    try:
        # KM Actual
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", "Dany").order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        # Mantenimiento
        rm = supabase.table("mantenimiento").select("*").eq("cliente_id", "Dany").order("km_cambio", desc=True).limit(1).execute()
        if rm.data:
            ma = rm.data[0]
            rest = ma['km_proximo'] - kh
            c1, c2 = st.columns(2)
            c1.metric("KM Actual", f"{kh:,}")
            if rest <= 500: c2.error(f"🚨 CAMBIO YA: {rest} km")
            else: c2.metric("Vida Útil Aceite", f"{rest:,} km", delta_color="normal")
        
        with st.expander("📝 Nuevo Cambio de Aceite"):
            with st.form("ft"):
                kc = st.number_input("KM Cambio hoy", value=kh)
                kp = st.number_input("Próximo Cambio", value=kc + 5000)
                if st.form_submit_button("ACTUALIZAR"):
                    supabase.table("mantenimiento").insert({"fecha": str(datetime.now().date()), "km_cambio": kc, "km_proximo": kp, "cliente_id": "Dany"}).execute()
                    st.rerun()
    except: st.warning("⚠️ Módulo en ajustes técnicos.")

with tabs[3]:
    st.header("📈 Reportes Corporativos")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", "Dany").execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            ms = st.selectbox("Seleccione Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(ms)+1)]
            
            c1, c2 = st.columns(2)
            c1.download_button("📥 EXCEL", df_f.to_csv(index=False).encode('utf-8'), "gastos.csv", "text/csv", type="secondary")
            pdf_b = generar_pdf(df_f, ms, 2026)
            c2.download_button("📄 PDF CONTADOR", pdf_b, "reporte.pdf", "application/pdf", type="primary")
    except: st.info("No hay datos para reportes todavía.")