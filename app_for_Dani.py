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

# --- INYECTAR ESTILO DE ALTO CONTRASTE ---
if fondo_path and os.path.exists(fondo_path):
    with open(fondo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    st.markdown(
    f"""
    <style>
    .stApp {{ background-image: url(data:image/png;base64,{encoded_string}); background-size: cover; background-position: center; background-attachment: fixed; }}
    [data-testid="stSidebar"] {{ background-color: rgba(15, 15, 15, 0.95) !important; border-right: 1px solid #333 !important; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.80); padding: 2rem; border-radius: 15px; color: white; }}
    .st-emotion-cache-p4m0d2, .st-emotion-cache-1h9usn3, [data-testid="stExpander"] details summary {{ background-color: #1E1E1E !important; color: white !important; border: 1px solid #444 !important; border-radius: 8px !important; }}
    .stAlert p, .st-emotion-cache-16idsys p, label {{ color: #FFFFFF !important; font-weight: bold; }}
    h1, h2, h3, p, span {{ color: white !important; }}
    [data-testid="stFormSubmitButton"] button, div.stButton > button {{ background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 10px; border: none !important; }}
    [data-testid="stDownloadButton"] button[kind="secondary"] {{ background-color: #107C41 !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 10px; border: none !important; }}
    [data-testid="stDownloadButton"] button[kind="primary"] {{ background-color: #D32F2F !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 10px; border: none !important; }}
    [data-testid="stLinkButton"] a {{ background-color: #25D366 !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 10px; border: none !important; text-decoration: none !important; }}
    hr {{ border-color: #333 !important; }}
    header {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
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
    st.stop() 

# --- GESTIÓN DE LICENCIA ---
def obtener_licencia_remota(cliente_nombre):
    try:
        respuesta = supabase.table("licencias").select("*").eq("cliente", cliente_nombre).execute()
        if respuesta.data:
            datos = respuesta.data[0]
            return datos['fecha_vencimiento'], datos['llave_activa'], datos.get('plan', 'estandar')
        return "2000-01-01", False, "estandar"
    except Exception:
        return "2000-01-01", False, "estandar"

fecha_remota_str, llave_maestra, plan_cliente = obtener_licencia_remota(st.session_state['cliente_id'])

def verificar_licencia(fecha_fin_str, activa):
    if not activa: return "BLOQUEADO_POR_ADMIN", 0
    fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d")
    hoy = datetime.now()
    diferencia = (fecha_fin - hoy).days + 1
    if diferencia < 0: return "VENCIDO", 0
    elif diferencia <= 5: return "ALERTA", diferencia
    else: return "ACTIVO", diferencia

estado_lic, dias_restantes = verificar_licencia(fecha_remota_str, llave_maestra)

if logo_path and os.path.exists(logo_path):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2: st.image(logo_path, use_container_width=True)

with st.expander("🛡️ RutaMaster & Aisaac-Shield", expanded=True):
    if estado_lic == "ACTIVO": st.success("Soporte técnico: Activo")
    elif estado_lic == "ALERTA": st.warning(f"Soporte: {dias_restantes} días")
    else: st.error("Soporte: Finalizado")
    st.caption(f"📅 Vence el: {fecha_remota_str} | 💎 Plan: {plan_cliente.upper()}")

if estado_lic == "BLOQUEADO_POR_ADMIN" or estado_lic == "VENCIDO":
    st.title("🔒 Sistema Inactivo")
    st.stop()

# --- FUNCIONES AUXILIARES ---
def comprimir_imagen(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=30, optimize=True)
    buffer.seek(0)
    return buffer

def limpiar(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

def generar_pdf(df_gastos, mes_nombre, año):
    pdf = FPDF()
    pdf.add_page()
    if logo_path and os.path.exists(logo_path):
        try:
            img_pil = Image.open(logo_path).convert("RGB")
            img_buffer = io.BytesIO()
            img_pil.save(img_buffer, format="JPEG")
            img_buffer.seek(0)
            pdf.image(img_buffer, x=10, y=8, w=33, type='JPEG')
        except: pass
    pdf.set_font("Arial", 'B', 20); pdf.set_text_color(0, 51, 153)
    pdf.cell(0, 15, txt=limpiar("REPORTE MENSUAL DE GASTOS"), ln=True, align='R')
    pdf.set_font("Arial", size=10); pdf.set_text_color(100)
    pdf.cell(0, 5, txt=limpiar(f"Empresa: Transportes B&J"), ln=True, align='R')
    pdf.cell(0, 5, txt=limpiar(f"Periodo: {mes_nombre} {año}"), ln=True, align='R')
    pdf.ln(20)
    pdf.set_fill_color(0, 51, 153); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 12)
    w = [35, 100, 55]
    pdf.cell(w[0], 12, limpiar("Fecha"), 1, 0, 'C', True)
    pdf.cell(w[1], 12, limpiar("Concepto"), 1, 0, 'C', True)
    pdf.cell(w[2], 12, limpiar("Monto (CRC)"), 1, 1, 'C', True)
    pdf.set_text_color(0); pdf.set_font("Arial", size=11)
    fill = False
    for _, fila in df_gastos.iterrows():
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w[0], 10, limpiar(fila['fecha'].date()), 1, 0, 'C', fill)
        pdf.cell(w[1], 10, f" {limpiar(fila['concepto'])}", 1, 0, 'L', fill)
        pdf.cell(w[2], 10, f"CRC {fila['monto']:,.0f} ", 1, 1, 'R', fill)
        fill = not fill
    pdf.ln(5); pdf.set_font("Arial", 'B', 12)
    pdf.cell(w[0] + w[1], 12, limpiar("TOTAL ACUMULADO:"), 0, 0, 'R')
    pdf.set_fill_color(255, 204, 204); pdf.cell(w[2], 12, f"CRC {df_gastos['monto'].sum():,.0f} ", 1, 1, 'R', True)
    pdf.set_y(-20); pdf.set_font("Arial", 'I', 8); pdf.set_text_color(150)
    pdf.cell(0, 10, limpiar("Sistema generado por Aisaac Shield Systems - aisaac-shield.com"), 0, 0, 'C')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ DE TABS ---
nombres_tabs = ["➕ Viajes", "📉 Gastos", "🔧 Taller"]
if plan_cliente in ["premium", "pro"]: nombres_tabs.append("📊 Resumen")
tabs = st.tabs(nombres_tabs)

with tabs[0]:
    st.header("Registrar Viaje")
    with st.form("form_viaje", clear_on_submit=True):
        f = st.date_input("Fecha", datetime.now())
        cli = st.text_input("Cliente / Destino")
        mon = st.number_input("Monto Flete (CRC)", min_value=0, step=1000)
        km_v = st.number_input("Kilometraje Actual del Camión", min_value=0)
        if st.form_submit_button("Guardar Viaje"):
            datos_viaje = {"fecha": f.strftime("%Y-%m-%d"), "cliente": cli, "monto": mon, "km_actual": km_v, "cliente_id": st.session_state['cliente_id']}
            supabase.table("viajes").insert(datos_viaje).execute()
            st.success("✅ Viaje y Kilometraje registrados.")

with tabs[1]:
    st.header("Registrar Gasto")
    with st.form("form_gasto", clear_on_submit=True):
        f_g = st.date_input("Fecha Gasto", datetime.now())
        concep = st.selectbox("Concepto", ["Diesel", "Peaje", "Mantenimiento", "Comida", "Otros"])
        mon_g = st.number_input("Monto (CRC)", min_value=0, step=1000)
        img_file = st.file_uploader("📸 Foto factura", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("Registrar Gasto"):
            foto_bin = comprimir_imagen(img_file).getvalue() if img_file else None
            foto_b64 = base64.b64encode(foto_bin).decode('utf-8') if foto_bin else None
            datos_g = {"fecha": f_g.strftime("%Y-%m-%d"), "concepto": concep, "monto": mon_g, "foto": foto_b64, "cliente_id": st.session_state['cliente_id']}
            supabase.table("gastos").insert(datos_g).execute()
            st.success("✅ Gasto guardado.")

with tabs[2]:
    st.header("🔧 Control Preventivo (Aceite)")
    cliente_actual = st.session_state['cliente_id']
    
    # Obtener el KM actual del último viaje registrado
    res_km = supabase.table("viajes").select("km_actual").eq("cliente_id", cliente_actual).order("created_at", desc=True).limit(1).execute()
    km_ahora = res_km.data[0]['km_actual'] if res_km.data else 0
    
    # Obtener último mantenimiento
    res_m = supabase.table("mantenimiento").select("*").eq("cliente_id", cliente_actual).order("km_cambio", desc=True).limit(1).execute()
    
    if res_m.data:
        m = res_m.data[0]
        faltan = m['km_proximo'] - km_ahora
        
        col1, col2 = st.columns(2)
        col1.metric("KM Actual", f"{km_ahora:,}")
        
        if faltan <= 0:
            col2.error(f"⚠️ CAMBIO URGENTE: Hace {abs(faltan):,} km")
        elif faltan <= 500:
            col2.warning(f"🔔 Toca pronto: {faltan:,} km faltantes")
        else:
            col2.metric("Siguiente Cambio", f"{m['km_proximo']:,}", delta=f"{faltan:,} km restantes")
        
        st.divider()
    
    with st.expander("Registrar Nuevo Cambio de Aceite"):
        with st.form("form_mant"):
            f_m = st.date_input("Fecha de Cambio", datetime.now())
            km_c = st.number_input("Kilometraje del Cambio", min_value=0, value=km_ahora)
            km_p = st.number_input("Próximo Cambio (+5000 km)", min_value=0, value=km_c + 5000)
            if st.form_submit_button("Guardar Registro"):
                datos_m = {"fecha": f_m.strftime("%Y-%m-%d"), "km_cambio": km_c, "km_proximo": km_p, "cliente_id": cliente_actual}
                supabase.table("mantenimiento").insert(datos_m).execute()
                st.success("✅ Sistema de alertas actualizado.")
                st.rerun()

if plan_cliente in ["premium", "pro"]:
    with tabs[3]:
        st.header("📊 Resumen y Reportes")
        # (Aquí va tu código de Reportes y PDF que ya tenemos funcionando perfectamente)
        res_v = supabase.table("viajes").select("*").eq("cliente_id", st.session_state['cliente_id']).execute()
        res_g = supabase.table("gastos").select("*").eq("cliente_id", st.session_state['cliente_id']).execute()
        df_v = pd.DataFrame(res_v.data) if res_v.data else pd.DataFrame()
        df_g = pd.DataFrame(res_g.data) if res_g.data else pd.DataFrame()
        
        if not df_g.empty:
            df_g['fecha'] = pd.to_datetime(df_g['fecha'])
            a_sel = st.selectbox("Año", sorted(df_g['fecha'].dt.year.unique(), reverse=True))
            m_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel_nom = st.selectbox("Mes", m_nombres, index=datetime.now().month-1)
            df_g_f = df_g[(df_g['fecha'].dt.year == a_sel) & (df_g['fecha'].dt.month == (m_nombres.index(m_sel_nom)+1))]
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 Descargar Excel", df_g_f.drop(columns=['foto']).to_csv(index=False).encode('utf-8'), f"gastos_{m_sel_nom}.csv", "text/csv")
            with col2:
                pdf_b = generar_pdf(df_g_f, m_sel_nom, a_sel)
                st.download_button("📄 Reporte para Contador (PDF)", pdf_b, f"Reporte_{m_sel_nom}.pdf", "application/pdf", type="primary")