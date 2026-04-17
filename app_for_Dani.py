import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import base64
import os

# --- 0. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Logística B&J", layout="centered")

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
    [data-testid="stDownloadButton"] button {{ background-color: #107C41 !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 10px; border: none !important; }}
    [data-testid="stLinkButton"] a {{ background-color: #25D366 !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 10px; border: none !important; text-decoration: none !important; }}
    hr {{ border-color: #333 !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CANDADO DIGITAL (LOGIN) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center;'>🔒 Acceso Seguro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Ingrese el PIN autorizado para acceder a Transportes B&J</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN", type="password", label_visibility="collapsed", placeholder="****")
        if st.button("Desbloquear Sistema"):
            if pin == "8715": 
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("❌ PIN incorrecto. Acceso denegado.")
    st.stop() 

# --- 3. AISAAC-SHIELD NIVEL 1 (CONEXIÓN A LA NUBE) ---
def obtener_licencia_remota(cliente_nombre):
    try:
        respuesta = supabase.table("licencias").select("*").eq("cliente", cliente_nombre).execute()
        if respuesta.data:
            datos = respuesta.data[0]
            return datos['fecha_vencimiento'], datos['llave_activa']
        return "2000-01-01", False 
    except Exception:
        return "2000-01-01", False

fecha_remota_str, llave_maestra = obtener_licencia_remota("Dany")

def verificar_licencia(fecha_fin_str, activa):
    if not activa:
        return "BLOQUEADO_POR_ADMIN", 0
        
    fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d")
    hoy = datetime.now()
    diferencia = (fecha_fin - hoy).days + 1
    
    if diferencia < 0:
        return "VENCIDO", 0
    elif diferencia <= 5:
        return "ALERTA", diferencia
    else:
        return "ACTIVO", diferencia

estado_lic, dias_restantes = verificar_licencia(fecha_remota_str, llave_maestra)

# --- 4. SIDEBAR ---
with st.sidebar:
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
        st.divider()

    st.markdown("### 🛡️ Aisaac-Shield")
    
    if estado_lic == "ACTIVO":
        st.success("Soporte técnico: Activo")
    elif estado_lic == "ALERTA":
        st.warning(f"Soporte: {dias_restantes} días restantes")
    else:
        st.error("Soporte: Finalizado / Apagado")
        
    st.caption(f"Vence el: {fecha_remota_str}")

# --- 5. BLOQUEOS INTERACTIVOS (CON COBRO SINPE) ---

# Bloqueo 1: Apagado remoto
if estado_lic == "BLOQUEADO_POR_ADMIN":
    st.title("🔒 Sistema Desactivado")
    st.error("Esta aplicación ha sido apagada remotamente por el administrador.")
    url_wa = "https://wa.me/50685643342?text=Hola%20Andres!%20Mi%20app%20dice%20desactivada.%20Ocupo%20ayuda."
    st.link_button("📲 Hablar con Andrés", url_wa)
    st.stop()

# Bloqueo 2: Fecha vencida (PASARELA DE PAGO SINPE)
if estado_lic == "VENCIDO":
    st.title("🚫 Licencia Vencida")
    st.error("El período de servicio de su aplicación ha finalizado.")
    
    st.markdown("""
    ### 💳 Renovación de Sistema
    Para reactivar su acceso y proteger sus datos, por favor realice el pago de la mensualidad.
    
    * **Monto:** ₡7,500
    * **SINPE Móvil:** 8564-3342
    
    *Una vez realizado el pago, envíe el comprobante por WhatsApp y el sistema se desbloqueará de inmediato.*
    """)
    
    url_wa = "https://wa.me/50685643342?text=Hola%20Andres!%20Ya%20te%20hice%20el%20SINPE%20de%20los%207500%20para%20renovar%20la%20licencia."
    st.link_button("📲 Enviar Comprobante por WhatsApp", url_wa)
    st.stop() 

# Nagware: Alerta de pocos días
if estado_lic == "ALERTA":
    st.warning(f"⚠️ AVISO DE SOPORTE: Quedan {dias_restantes} días de servicio. Favor contactar a soporte.")

# --- 6. FUNCIONES DE BASE DE DATOS (NUBE) ---
def guardar_gasto(fecha, concepto, monto, foto_bytes):
    foto_b64 = base64.b64encode(foto_bytes).decode('utf-8') if foto_bytes else None
    datos = {"fecha": fecha, "concepto": concepto, "monto": monto, "foto": foto_b64}
    supabase.table("gastos").insert(datos).execute()

def eliminar_gasto_db(id_gasto):
    supabase.table("gastos").delete().eq("id", id_gasto).execute()

# --- 7. INTERFAZ PRINCIPAL (TABS) ---
tab1, tab2, tab3 = st.tabs(["➕ Viajes", "📉 Gastos con Foto", "📊 Resumen"])

with tab1:
    st.header("Registrar Viaje")
    with st.form("form_viaje", clear_on_submit=True):
        f = st.date_input("Fecha", datetime.now())
        cli = st.text_input("Cliente")
        ori = st.text_input("Origen")
        des = st.text_input("Destino")
        mon = st.number_input("Monto Flete (CRC)", min_value=0, step=1000)
        not_v = st.text_area("Notas")
        if st.form_submit_button("Guardar Viaje"):
            if not cli.strip() or mon == 0:
                st.error("⚠️ Datos incompletos.")
            else:
                try:
                    datos_viaje = {"fecha": f.strftime("%Y-%m-%d"), "cliente": cli, "origen": ori, "destino": des, "monto": mon, "notas": not_v}
                    supabase.table("viajes").insert(datos_viaje).execute()
                    st.success("✅ Viaje guardado.")
                except Exception:
                    st.error("📡 Sin señal.")

with tab2:
    st.header("Registrar Gasto")
    with st.form("form_gasto", clear_on_submit=True):
        f_g = st.date_input("Fecha Gasto", datetime.now())
        concep = st.selectbox("Concepto", ["Diesel", "Peaje", "Mantenimiento", "Comida", "Otros"])
        mon_g = st.number_input("Monto (CRC)", min_value=0, step=1000)
        img_file = st.camera_input("Capturar factura")
        if st.form_submit_button("Guardar Gasto"):
            if mon_g == 0:
                st.error("⚠️ Monto en cero.")
            else:
                try:
                    foto_bin = img_file.getvalue() if img_file else None
                    guardar_gasto(f_g.strftime("%Y-%m-%d"), concep, mon_g, foto_bin)
                    st.success("✅ Gasto guardado.")
                except Exception:
                    st.error("📡 Error de conexión.")

with tab3:
    st.header("📊 Resumen y Excel")
    try:
        res_viajes = supabase.table("viajes").select("*").execute()
        res_gastos = supabase.table("gastos").select("*").execute()
        datos_cargados = True
    except Exception:
        st.error("📡 Sin conexión.")
        datos_cargados = False
    
    if datos_cargados:
        cols_v = ['id', 'fecha', 'cliente', 'origen', 'destino', 'monto', 'notas']
        cols_g = ['id', 'fecha', 'concepto', 'monto', 'foto']
        df_v = pd.DataFrame(res_viajes.data) if res_viajes.data else pd.DataFrame(columns=cols_v)
        df_g = pd.DataFrame(res_gastos.data) if res_gastos.data else pd.DataFrame(columns=cols_g)

        if not df_v.empty or not df_g.empty:
            df_v['fecha'] = pd.to_datetime(df_v['fecha'])
            df_g['fecha'] = pd.to_datetime(df_g['fecha'])
            años = sorted(df_g['fecha'].dt.year.unique(), reverse=True) if not df_g.empty else [datetime.now().year]
            col1, col2 = st.columns(2)
            a_sel = col1.selectbox("Año", años)
            m_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel_nom = col2.selectbox("Mes", m_nombres, index=datetime.now().month - 1)
            m_sel = m_nombres.index(m_sel_nom) + 1

            df_v_f = df_v[(df_v['fecha'].dt.year == a_sel) & (df_v['fecha'].dt.month == m_sel)]
            df_g_f = df_g[(df_g['fecha'].dt.year == a_sel) & (df_g['fecha'].dt.month == m_sel)]

            t_v = df_v_f['monto'].sum()
            t_g = df_g_f['monto'].sum()
            st.metric("Ganancia Neta", f"₡{t_v - t_g:,.0f}", delta=f"Fletes: ₡{t_v:,.0f}")

            st.divider()
            if not df_g_f.empty:
                csv = df_g_f.drop(columns=['foto']).to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Excel", csv, f"gastos_{m_sel_nom}.csv", "text/csv")
                
                fig = px.pie(df_g_f, values='monto', names='concepto', hole=0.4, title="Distribución")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig, theme=None) 

            for _, row in df_g_f.iterrows():
                with st.expander(f"{row['concepto']} - ₡{row['monto']:,.0f}"):
                    if pd.notna(row['foto']) and row['foto'] != "": 
                        st.image(base64.b64decode(row['foto']))
                    if st.button("Eliminar", key=f"del_{row['id']}"):
                        eliminar_gasto_db(row['id'])
                        st.rerun()
        else:
            st.info("Sin datos registrados aún.")