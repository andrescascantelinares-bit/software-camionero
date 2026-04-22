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
st.set_page_config(page_title="Aisaac Shield Premium", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. MOTOR DE DISEÑO DINÁMICO ---
def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

def aplicar_estilo_premium(usuario):
    if usuario == "Padre_Andres":
        # Estilo Dorado para tu papá
        c_pri, c_sec, c_shd = "#D4AF37", "#FFD700", "rgba(212, 175, 55, 0.5)"
        titulo = "🥇 AISAAC GOLD LOGISTICS"
    else:
        # Estilo Verde para Dani
        c_pri, c_sec, c_shd = "#25D366", "#107C41", "rgba(37, 211, 102, 0.3)"
        titulo = "🛡️ AISAAC SHIELD SYSTEMS"
    return c_pri, c_sec, c_shd, titulo

# --- 2. FUNCIONES DE APOYO (PDF) ---
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
    pdf.set_font("Arial", 'B', 20); pdf.set_text_color(0, 51, 153)
    pdf.cell(0, 15, txt=limpiar("REPORTE MENSUAL DE GASTOS"), ln=True, align='R')
    pdf.set_font("Arial", size=10); pdf.set_text_color(100)
    pdf.cell(0, 5, txt=limpiar(f"Sistema Aisaac Shield | {mes} {año}"), ln=True, align='R')
    pdf.ln(20)
    pdf.set_fill_color(0, 51, 153); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 12)
    w = [35, 100, 55]
    pdf.cell(w[0], 12, limpiar("Fecha"), 1, 0, 'C', True)
    pdf.cell(w[1], 12, limpiar("Concepto"), 1, 0, 'C', True)
    pdf.cell(w[2], 12, limpiar("Monto (CRC)"), 1, 1, 'C', True)
    pdf.set_text_color(0); pdf.set_font("Arial", size=11)
    for i, row in df_gastos.iterrows():
        pdf.set_fill_color(245, 245, 245) if i%2==0 else pdf.set_fill_color(255, 255, 255)
        # Manejo de fecha seguro
        f_str = row['fecha'].strftime('%Y-%m-%d') if hasattr(row['fecha'], 'strftime') else str(row['fecha'])
        pdf.cell(w[0], 10, limpiar(f_str), 1, 0, 'C', True)
        pdf.cell(w[1], 10, f" {limpiar(row['concepto'])}", 1, 0, 'L', True)
        pdf.cell(w[2], 10, f"CRC {row['monto']:,.0f} ", 1, 1, 'R', True)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🛡️ AISAAC SHIELD</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
    if st.button("DESBLOQUEAR SISTEMA"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "Dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "Padre_Andres"})
        else: st.error("PIN incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 4. INTERFAZ DINÁMICA ---
u = st.session_state['user']
c_pri, c_sec, c_shd, txt_t = aplicar_estilo_premium(u)
logo_path = st.secrets.get("APP_LOGO_PATH")
fondo_path = st.secrets.get("APP_BACKGROUND_PATH")
fondo_b64 = get_base64(fondo_path)

st.markdown(f"""
<style>
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.96); padding: 2.5rem; border-radius: 25px; border: 2px solid {c_pri}; box-shadow: 0px 0px 35px {c_shd}; }}
    .stButton>button {{ background: linear-gradient(90deg, {c_sec}, {c_pri}) !important; color: black !important; font-weight: 900; border-radius: 12px; height: 3.8rem; border: none; }}
    h1, h2, h3, .stMetric, label {{ color: {c_pri} !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>{txt_t}</h2>", unsafe_allow_html=True)

tabs = st.tabs(["📝 REGISTRO", "🔧 MOTOR", "📊 REPORTES"])

with tabs[0]:
    st.markdown(f"<p style='text-align: center;'>Operador: <b>{u.replace('_', ' ')}</b></p>", unsafe_allow_html=True)
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo de Gasto", ["Diesel", "Aceite", "Peaje", "Repuesto", "Otros"])
        monto = col2.number_input("Monto (CRC)", min_value=0, step=1000)
        km = st.number_input("Kilometraje Actual", min_value=0)
        if st.form_submit_button("SINCRONIZAR AHORA"):
            try:
                supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u}).execute()
                supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "cliente": "SaaS Elite", "monto": 0, "km_actual": km, "cliente_id": u}).execute()
                st.success(f"✅ ¡Hecho! Datos guardados para {u}")
            except: st.error("Error de base de datos. Verifique columnas.")

with tabs[1]:
    st.header("🔧 Taller y Mantenimiento")
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        rm = supabase.table("mantenimiento").select("*").eq("cliente_id", u).order("km_cambio", desc=True).limit(1).execute()
        if rm.data:
            ma = rm.data[0]; rest = ma['km_proximo'] - kh
            st.metric("Kilometraje Actual", f"{kh:,} km")
            if rest <= 500: st.error(f"🚨 CAMBIO URGENTE: {rest} km restantes")
            else: st.success(f"✅ Aceite OK: {rest} km para el taller")
        with st.expander("📝 Registrar Nuevo Cambio"):
            with st.form("f_taller"):
                kc = st.number_input("Kilometraje hoy", value=kh)
                kp = st.number_input("Próximo cambio", value=kc + 5000)
                if st.form_submit_button("ACTUALIZAR"):
                    supabase.table("mantenimiento").insert({"fecha": str(datetime.now().date()), "km_cambio": kc, "km_proximo": kp, "cliente_id": u}).execute()
                    st.rerun()
    except: st.warning("Configure 'cliente_id' en la tabla mantenimiento.")

with tabs[2]:
    st.header("📈 Historial Mensual")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Seleccione Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)]
            st.dataframe(df_f[['fecha', 'concepto', 'monto']].sort_values(by='fecha', ascending=False), hide_index=True)
            col1, col2 = st.columns(2)
            col1.download_button("📥 Excel", df_f.to_csv(index=False).encode('utf-8'), "gastos.csv", "text/csv")
            pdf_b = generar_pdf(df_f, m_sel, 2026, logo_path if u == "Dany" else None)
            col2.download_button("📄 PDF Premium", pdf_b, "reporte.pdf", "application/pdf")
        else: st.info("No hay registros para este usuario.")
    except: st.error("Error al cargar reportes.")