import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io
import plotly.express as px
import time

# --- 0. CONFIGURACIÓN Y ZONA HORARIA ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")
ZONA_CR = timezone(timedelta(hours=-6)) # Ajuste estricto para Costa Rica

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. UTILIDADES ---
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

# --- 2. DISEÑO VISUAL CON LUCES DE NEÓN ANIMADAS ---
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH") if "APP_BACKGROUND_PATH" in st.secrets else None)

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2rem; border-radius: 30px; border: 1px solid #25D366; }}
    .gasto-card {{ background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; border-left: 5px solid #25D366; margin-bottom: 10px; }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; }}
    
    /* ANIMACIÓN DE PULSO DE NEÓN AISAAC-SHIELD */
    @keyframes neon-glow {{
        0% {{ border-color: rgba(37, 211, 102, 0.3); box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); }}
        50% {{ border-color: rgba(37, 211, 102, 1); box-shadow: 0 0 20px rgba(37, 211, 102, 0.6); }}
        100% {{ border-color: rgba(37, 211, 102, 0.3); box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); }}
    }}

    .shield-box {{ 
        margin: 20px 0; padding: 20px; text-align: center; border: 2px solid #25D366;
        animation: neon-glow 2s infinite ease-in-out;
        background: 
            linear-gradient(to right, #25D366 4px, transparent 4px) 0 0,
            linear-gradient(to bottom, #25D366 4px, transparent 4px) 0 0,
            linear-gradient(to left, #25D366 4px, transparent 4px) 100% 0,
            linear-gradient(to bottom, #25D366 4px, transparent 4px) 100% 0,
            linear-gradient(to right, #25D366 4px, transparent 4px) 0 100%,
            linear-gradient(to top, #25D366 4px, transparent 4px) 0 100%,
            linear-gradient(to left, #25D366 4px, transparent 4px) 100% 100%,
            linear-gradient(to top, #25D366 4px, transparent 4px) 100% 100%;
        background-repeat: no-repeat; background-size: 20px 20px;
        background-color: rgba(37, 211, 102, 0.05);
    }}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN CON AVISO DE SEGURIDAD ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div class='shield-box'>
        <b style='color: #25D366; font-size: 1.1rem;'>⚠️ AVISO DE SEGURIDAD</b><br>
        <span style='color: white;'>Esta aplicación está protegida por <b>Aisaac-Shield</b>.</span><br>
        <small style='color: #25D366;'>El acceso no autorizado será registrado.</small>
    </div>
    """, unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "padre_andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 4. CARGA DE DATOS ---
u = st.session_state['user']
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy_cr_dt = datetime.now(ZONA_CR)
mes_actual_cr = hoy_cr_dt.month

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.upper()}</h2>", unsafe_allow_html=True)

# Filtro desplegable para evitar el teclado en móviles
with st.expander(f"📅 PERIODO: {st.session_state.get('mes_f', meses_nombres[mes_actual_cr-1])}", expanded=False):
    m_sel = st.segmented_control("Mes:", options=meses_nombres, default=meses_nombres[mes_actual_cr-1], key="mes_f")

df_f = pd.DataFrame()
km_actual = 0
try:
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    if rg.data:
        df_raw = pd.DataFrame(rg.data)
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        df_f = df_raw[df_raw['fecha'].dt.month == (meses_nombres.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
    
    rv = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("id", desc=True).limit(1).execute()
    km_actual = rv.data[0]['km_actual'] if rv.data else 0
except: pass

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO ---
with tabs[0]:
    # Selección de qué tipo de actividad registrar
    opcion = st.radio("QUÉ REGISTRAMOS:", ["💸 Gasto Operativo", "🛣️ Finalizar Viaje"], horizontal=True)
    hoy_cr = hoy_cr_dt.date()
    
    if opcion == "💸 Gasto Operativo":
        st.markdown("### 📝 Nuevo Gasto")
        with st.form("f_gasto", clear_on_submit=True):
            fecha = st.date_input("Fecha del Gasto", hoy_cr)
            c1, c2 = st.columns(2)
            # Lista de conceptos para el selector
            tipo = c1.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Alimentación", "Otros"])
            monto = c2.number_input("Monto (CRC)", min_value=0, step=500, format="%d")
            
            foto = st.file_uploader("Subir Comprobante (Opcional)", type=['jpg', 'png', 'jpeg'])
            
            submit_gasto = st.form_submit_button("GUARDAR GASTO")
            
            if submit_gasto:
                if monto > 0:
                    try:
                        # Procesamiento de la imagen a base64
                        foto_b64 = procesar_foto(foto) if foto else None
                        
                        data_gasto = {
                            "fecha": str(fecha), 
                            "concepto": tipo, 
                            "monto": int(monto), 
                            "cliente_id": u, 
                            "foto_comprobante": foto_b64
                        }
                        
                        # Inserción en la tabla de gastos de Supabase
                        supabase.table("gastos").insert(data_gasto).execute()
                        
                        st.success(f"✅ Gasto de {tipo} por ₡{monto:,} guardado.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al conectar con la base de datos: {e}")
                else:
                    st.warning("⚠️ El monto debe ser mayor a 0 para registrar un gasto.")
                    
    elif opcion == "🛣️ Finalizar Viaje":
        st.markdown("### 🏁 Cierre de Viaje")
        with st.form("f_viaje", clear_on_submit=True):
            fecha = st.date_input("Fecha", hoy_cr)
            cli = st.text_input("Cliente / Empresa")
            
            c3, c4 = st.columns(2)
            orig = c3.text_input("Origen")
            dest = c4.text_input("Destino")
            
            c5, c6 = st.columns(2)
            cost = c5.number_input("Costo del Viaje", min_value=0, step=1000)
            # El kilometraje sugerido es el actual más 1
            km = c6.number_input("KM a la Llegada", min_value=km_actual, step=1, placeholder=f"Actual: {km_actual}")
            
            submit_viaje = st.form_submit_button("REGISTRAR VIAJE")
            
            if submit_viaje:
                if cli and orig and dest and km > 0:
                    try:
                        data_viaje = {
                            "fecha": str(fecha), 
                            "cliente": cli, 
                            "origen": orig, 
                            "destino": dest, 
                            "monto": int(cost) if cost else 0, 
                            "cliente_id": u, 
                            "km_actual": int(km)
                        }
                        
                        # Inserción en la tabla de viajes de Supabase
                        supabase.table("viajes").insert(data_viaje).execute()
                        
                        st.success("✅ Viaje finalizado y registrado.")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar el viaje: {e}")
                else:
                    st.warning("⚠️ Completa todos los campos (Cliente, Origen, Destino y KM) para finalizar.")

# --- TAB 2: GASTOS ---
with tabs[1]:
    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"<div class='gasto-card'><small>{row['fecha'].strftime('%d %b')}</small><br><b>{row['concepto']}</b><br><span style='color:#25D366; font-size:1.2rem;'>CRC {row['monto']:,.0f}</span></div>", unsafe_allow_html=True)
            if row.get('foto_comprobante'):
                with st.popover("📷 Ver Ticket"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            if st.button("🗑️ Borrar", key=f"d_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute(); st.rerun()
    else: st.info("Sin registros.")

# --- TAB 3: DATOS ---
with tabs[2]:
    st.metric("KILOMETRAJE ACTUAL", f"{km_actual:,} KM")
    st.divider()
    
    if not df_f.empty:
        st.metric(f"TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        
        # Gráfico redondo tipo Dona
        fig = px.pie(df_f.groupby('concepto')['monto'].sum().reset_index(), 
                     values='monto', names='concepto', hole=0.5, 
                     color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', legend_font_color="#25D366", margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Resumen de Gastos")
        df_tabla = df_f[['fecha', 'concepto', 'monto']].copy()
        df_tabla['fecha'] = df_tabla['fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_tabla, hide_index=True, use_container_width=True)
    
    # SELLO INFERIOR SIEMPRE VISIBLE
    st.markdown("""
    <div class='shield-box'>
        <span style='color: #25D366; font-weight: 900; letter-spacing: 1px;'>🛡️ AISAAC-SHIELD ACTIVATED</span><br>
        <small style='color: #A0A0A0;'>Sistema de Protección de Datos en Tiempo Real</small>
    </div>
    """, unsafe_allow_html=True)