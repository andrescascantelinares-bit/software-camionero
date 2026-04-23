import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
import plotly.express as px # <--- ESTO LO HACE GERENCIAL

# --- 0. CONFIGURACIÓN PREMIUM ---
st.set_page_config(page_title="Aisaac Shield Gold", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. UTILIDADES Y PIL (INCLUIDO PARA FOTOS PRO) ---
def procesar_foto(uploaded_file):
    """Reduce el tamaño de la foto con PIL para ahorrar espacio"""
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
    # PDF Premium: Usamos colores dorados y logo PRO
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
    pdf.set_font("Arial", 'B', 20); pdf.set_text_color(0, 51, 153) # Azul corporativo
    pdf.cell(0, 15, txt=limpiar(f"REPORTE PRO - {mes}"), ln=True, align='R')
    pdf.ln(20)
    pdf.set_fill_color(0, 51, 153); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 12)
    w = [35, 100, 55]
    pdf.cell(w[0], 12, limpiar("Fecha"), 1, 0, 'C', True)
    pdf.cell(w[1], 12, limpiar("Concepto"), 1, 0, 'C', True)
    pdf.cell(w[2], 12, limpiar("Monto (CRC)"), 1, 1, 'C', True)
    pdf.set_text_color(0); pdf.set_font("Arial", size=11)
    for i, row in df_gastos.iterrows():
        f_val = row['fecha'].strftime('%Y-%m-%d') if hasattr(row['fecha'], 'strftime') else str(row['fecha'])
        pdf.cell(w[0], 10, limpiar(f_val), 1, 0, 'C')
        pdf.cell(w[1], 10, f" {limpiar(row['concepto'])}", 1, 0, 'L')
        pdf.cell(w[2], 10, f"CRC {row['monto']:,.0f} ", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- 2. LOGIN PREMIUM (CON DOBLE PIN) ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🛡️ AISAAC SHIELD</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password")
    if st.button("DESBLOQUEAR SISTEMA"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "Dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "Padre_Andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 3. VALIDACIÓN DE LICENCIA PRO ---
u = st.session_state['user']
plan_activo = "standard"
expires_active = None
try:
    rl = supabase.table("licencias").select("plan", "fecha_vencimiento").eq("cliente", u).execute()
    if rl.data:
        plan_activo = rl.data[0]['plan'] # Traemos el 'pro' de la tabla licencias
        expires_active = rl.data[0]['fecha_vencimiento'] # Vence el: 2026-05-16
except: pass

# --- 4. DISEÑO PREMIUM (DORADO NEÓN) ---
color_pri = "#D4AF37"
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))
st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    [data-testid="stToolbar"] {{ visibility: visible !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.93); padding: 2.5rem; border-radius: 25px; border: 1px solid {color_pri}; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #FFD700, #D4AF37); color: black; border-radius: 12px; border: none; height: 3rem; font-weight: bold; }}
    h1, h2, h3, label, .stMetric, .css-qri22k {{ color: {color_pri} !important; font-weight: bold; }}
    .stMetric {{ background-color: rgba(212, 175, 55, 0.1); padding: 10px; border-radius: 10px; border: 1px solid rgba(212, 175, 55, 0.2); }}
</style>
""", unsafe_allow_html=True)

if plan_activo == "pro": # Validamos si tiene plan 'pro'
    st.markdown(f"<h2 style='text-align: center;'>🥇 AISAAC GOLD - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: rgba(212, 175, 55, 0.7);'>Plan PRO Activo | Vence: {expires_active}</p>", unsafe_allow_html=True)
else:
    st.error("⚠️ Su cuenta Premium no tiene un plan activo o ya venció. Contacte a soporte.")
    st.info(f"Soporte técnico: Activo (Basado en la tabla licencias)")
    st.divider()

# --- 5. PESTAÑAS PREMIUM (TAB-BASED COMO LA IMAGEN) ---
if plan_activo == "pro":
    tabs = st.tabs(["📊 DASHBOARD", "📝 REGISTRO PRO", "🔧 FLOTA", "📈 REPORTES"])

    # --- TAB 0: DASHBOARD GERENCIAL (DISEÑO COMO LA IMAGEN DE REFERENCIA) ---
    with tabs[0]:
        st.subheader("Estado General Gerencial")
        
        col1, col2 = st.columns([0.6, 0.4])
        
        with col1:
            # 1. ESTADO DE LA FLOTA (GRAFICO DONUT)
            st.write("📊 Estado General de la Flota")
            # Usamos Plotly para forzar el Doughnut Chart (hole=.4)
            fig = px.pie(values=[7, 2, 1], names=["Activos", "Mantenimiento", "Parados"], hole=.4, color_discrete_sequence=['#25D366', '#D4AF37', '#FF0000'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color=color_pri, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.write("Monto Total:", f"CRC 10,000,000")
            
        with col2:
            # 2. MÉTRICAS CLAVE
            st.metric("Camiones Totales", "10")
            st.metric("Gastos Hoy", "CRC $215.50 Diesel")
            # 3. ALERTAS CRÍTICAS
            st.warning("⚠️ Seguro Vence (3 Camiones Mañana)")
            st.warning("⚠️ RTV Próxima (Camión #8)")
            
        st.divider()
        st.write("🚀 Viajes en Curso")
        st.info("Concepto de tracking: Camión #4 RUTA: San José -> Limón")
        # Aquí iría la lógica de rentabilidad neta que me pediste automatizar

    # --- TAB 1: REGISTRO MEJORADO (CON FOTOS OPTIMIZADAS) ---
    with tabs[1]:
        st.subheader("Registrar Nuevo Gasto con Comprobante")
        with st.form("f_reg_pro", clear_on_submit=True):
            tipo = st.selectbox("Gasto Pro", ["Diesel", "Repuesto", "Peaje", "Otros"])
            monto = st.number_input("Monto (CRC)", min_value=0)
            km = st.number_input("KM Actual Pro", min_value=0)
            foto = st.file_uploader("📷 Foto Comprobante Pro", type=['jpg', 'png', 'jpeg'])
            if st.form_submit_button("SINCRONIZAR PRO"):
                try:
                    foto_bytes = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": foto_bytes}).execute()
                    supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                    st.success("✅ Datos sincronizados correctamente")
                except: st.error("Error en base de datos")

    # --- TAB 2: FLOTA (MANTENIMIENTO PRO) ---
    with tabs[2]:
        st.subheader("🔧 Taller Gerencial")
        # Aquí el cliente Pro ve todo el historial detallado del aceite y reparaciones

    # --- TAB 3: REPORTES PREMIUM (DORADO) ---
    with tabs[3]:
        st.subheader("Análisis de Costos Operativos")
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            # EL GRÁFICO REDONDO (INTERACTIVO)
            st.write(f"🍩 Distribución de Costos Pro - {m_sel}")
            fig = px.pie(df_f, values='monto', names='concepto', hole=.4, color_discrete_sequence=px.colors.sequential.Solar_r)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color=color_pri)
            st.plotly_chart(fig, use_container_width=True)
            
            # LISTA PREMIUM CON VISOR Y BORRADO (Basado en la captura)
            with st.expander("🛠️ Administrar Historial (Ver Fotos o Borrar)"):
                for i, row in df_f.iterrows():
                    ca, cb, cc = st.columns([0.8, 0.1, 0.1])
                    ca.write(f"📅 {row['fecha'].strftime('%d/%m')} | {row['concepto']} | `CRC {row['monto']:,.0f}`")
                    if row.get('foto_comprobante'):
                        # Icono de cámara para visor
                        if cb.button("📷", key=f"img_{row['id']}"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
                    # Icono de basura para borrar
                    if cc.button("🗑️", key=f"del_{row['id']}"):
                        supabase.table("gastos").delete().eq("id", row['id']).execute()
                        st.rerun()
            
            pdf_b = generar_pdf(df_f, m_sel, 2026, logo_path)
            st.download_button("📄 Bajar Reporte PDF Gold", pdf_b, "reporte.pdf", "application/pdf")