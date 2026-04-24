import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. UTILIDADES Y PROCESAMIENTO DE FOTOS ---
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

# --- 2. LOGIN (DANI Y PAPÁ) ---
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

# --- 3. DISEÑO ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.9); padding: 2rem; border-radius: 20px; border: 1px solid #25D366; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 10px; font-weight: bold; border: none; }}
    h1, h2, label, .stMetric {{ color: #25D366 !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)

meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
m_sel = st.selectbox("📅 Filtrar información por mes:", meses, index=datetime.now().month-1)

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- PESTAÑA 1: REGISTRO (CAMPOS LIMPIOS) ---
with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo de Gasto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        
        # Al usar value=None, el campo aparece limpio y listo para escribir
        monto = col2.number_input("Monto (CRC)", value=None, placeholder="Escriba el monto...", step=500)
        km = st.number_input("Kilometraje Actual", value=None, placeholder="Ingrese el kilometraje...", step=1)
        
        foto = st.file_uploader("📷 Foto del Comprobante", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("SINCRONIZAR DATOS"):
            if monto is None or km is None:
                st.warning("⚠️ Por favor, ingrese el monto y el kilometraje.")
            else:
                try:
                    foto_final = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": foto_final}).execute()
                    supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                    st.success("✅ Sincronizado correctamente.")
                    st.balloons()
                except: st.error("Error al guardar.")

# --- PESTAÑA 2: GASTOS ---

with tabs[1]:
    st.subheader(f"Lista de Gastos - {m_sel}")
    
    try:
        # 1. Traemos los datos frescos de Supabase filtrados por usuario
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df_raw = pd.DataFrame(rg.data)
        
        if not df_raw.empty:
            # 2. Convertimos la fecha y extraemos el mes
            df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
            numero_mes_sel = meses.index(m_sel) + 1
            
            # 3. Filtramos por el mes seleccionado en el buscador de arriba
            df_f = df_raw[df_raw['fecha'].dt.month == numero_mes_sel].sort_values(by='fecha', ascending=False)
            
            if not df_f.empty:
                for i, row in df_f.iterrows():
                    # Formato de fila con columnas
                    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                    
                    # Info principal: Fecha, Concepto y Monto
                    fecha_str = row['fecha'].strftime('%d/%m')
                    c1.write(f"📅 {fecha_str} | **{row['concepto']}** | `CRC {row['monto']:,.0f}`")
                    
                    # --- NUEVO VISOR DE FOTO CERRABLE ---
                    # Verificamos si existe la foto
                    if row.get('foto_comprobante'):
                        # Usamos popover para crear la ventana flotante cerrable
                        with c2.popover("📷 Ver", use_container_width=True):
                            st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}", use_column_width=True)
                            st.write("*(Toque fuera de la foto para cerrar)*")
                    else:
                        c2.write("🚫") # Icono si no hay foto
                    
                    # Botón para borrar el registro
                    if c3.button("🗑️", key=f"del_{row['id']}"):
                        supabase.table("gastos").delete().eq("id", row['id']).execute()
                        st.success("Registro eliminado.")
                        st.rerun()
            else:
                st.info(f"🔎 No se encontraron gastos registrados para el mes de {m_sel}.")
        else:
            st.warning("📭 La base de datos está vacía para este usuario.")
            
    except Exception as e:
        st.error(f"❌ Error de conexión con Supabase: {e}")

# --- PESTAÑA 3: DATOS ---
with tabs[2]:
    st.subheader("Análisis de Operación")
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("Kilometraje Actual Flota", f"{kh:,} km")
    except: pass
    
    # Se vuelven a cargar datos para los gráficos
    try:
        if not df_f.empty:
            st.metric(f"Total Gastado ({m_sel})", f"CRC {df_f['monto'].sum():,.0f}")
            st.write("📈 Gráfico de Gastos")
            st.bar_chart(df_f.groupby('concepto')['monto'].sum())
            st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
    except: pass