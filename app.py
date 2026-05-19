import os
import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN Y PROTOCOLO DE SEGURIDAD IA ---
# Forzamos al sistema a usar la ruta de conexión estable
os.environ["GOOGLE_API_USE_MTLS"] = "never" 

st.set_page_config(
    page_title="SGA Pro v56.0 - Sistema Integral", 
    layout="wide", 
    page_icon="⛏️"
)

# Recuperación de llave y configuración de modelo
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # Usamos la dirección física del modelo para evitar errores de versión beta
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={"temperature": 0.1, "top_p": 1}
        )
        ia_conectada = True
    except Exception:
        ia_conectada = False
else:
    ia_conectada = False

# --- 2. MOTOR DE BASE DE DATOS (7 MÓDULOS INTEGRADOS) ---
def conectar():
    # Base de datos persistente en el servidor de Streamlit
    return sqlite3.connect('sga_maestro_marcelo.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    # Módulo 2: Personal
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    # Módulo 3/6: Auditoría y Libro Diario
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    # Módulo 4: Vales
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    # Módulo 5: Activos
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. MENÚ DE NAVEGACIÓN (LOS 7 MÓDULOS) ---
with st.sidebar:
    st.title("🛡️ SGA CONTROL TOTAL")
    if ia_conectada:
        st.success("✅ IA Conectada (Modo Estable)")
    else:
        st.error("❌ Error: Revisa la API Key")
    
    menu = st.radio("SELECCIONE MÓDULO:", [
        "📊 1. Dashboard General",
        "👥 2. Registro de Personal",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "🚜 5. Inventario de Activos",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.markdown("---")
    st.caption("Usuario: Marcelo | Cooperativa 2026")

# --- 4. DESARROLLO DE MÓDULOS ---

# --- MÓDULO 1: DASHBOARD ---
if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    c1, c2, c3 = st.columns(3)
    with c1:
        tp = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
        st.metric("Total Socios", tp)
    with c2:
        tb = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
        st.metric("Producción Acumulada (Bs)", f"{tb if tb else 0:,.2f}")
    with c3:
        tv = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
        st.metric("Egresos Vales", f"{tv if tv else 0:,.2f}")
    
    st.markdown("---")
    st.write("### Estado de la Cooperativa")
    st.info("El sistema está procesando correctamente los datos de los cuadernos de 2019.")

# --- MÓDULO 2: PERSONAL ---
elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Socios y Personal")
    with st.form("personal_form"):
        n = st.text_input("Nombre Completo").upper()
        ci = st.text_input("Cédula de Identidad (CI)")
        cargo = st.selectbox("Cargo en la Cooperativa", ["Socio", "Administrador", "Seguridad", "Operario"])
        if st.form_submit_button("Guardar en Base de Datos"):
            if n and ci:
                try:
                    conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cargo))
                    conn.commit(); conn.close(); st.success("Registro exitoso.")
                except: st.error("Este CI ya está registrado.")
            else: st.warning("Por favor rellena todos los campos.")
    
    st.write("### Lista de Personal")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

# --- MÓDULO 3: ESCÁNER IA ---
elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Procesamiento de Cuadernos con IA")
    st.write("Sube la foto del cuaderno. La IA extraerá los datos y los guardará en el Libro Diario.")
    
    archivo = st.file_uploader("Cargar imagen del cuaderno", type=['png', 'jpg', 'jpeg'])
    if archivo:
        imagen = Image.open(archivo); st.image(imagen, width=700)
        
        if st.button("🚀 PROCESAR Y ARCHIVAR"):
            with st.spinner("La IA está leyendo el cuaderno..."):
                try:
                    img_bytes = io.BytesIO(); imagen.save(img_bytes, format='JPEG')
                    # Prompt optimizado para extracción pura
                    prompt = "Extrae los datos de la tabla. Formato JSON: [fecha, tujo, mina, bs, obs]. Si un valor es nulo pon 0. Solo responde el JSON."
                    
                    respuesta = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    
                    # Limpieza de la respuesta para evitar errores de formato
                    json_limpio = re.search(r'\[.*\]', respuesta.text, re.DOTALL).group()
                    df = pd.read_json(io.StringIO(json_limpio))
                    
                    # Guardado automático
                    conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                    st.success(f"✅ Se han guardado {len(df)} registros automáticamente.")
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Fallo técnico: {e}. Intenta refrescar o subir una foto más clara.")

# --- MÓDULO 4: VALES ---
elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales de Socios")
    with st.form("vales_form"):
        # Cargar lista de socios existentes
        socios_df = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        socio_sel = st.selectbox("Seleccionar Socio", socios_df['nombre'] if not socios_df.empty else ["No hay socios"])
        monto = st.number_input("Monto Adelantado (Bs)", min_value=0.0)
        fecha = st.date_input("Fecha de Entrega")
        concepto = st.text_input("Concepto (Ej: Adelanto fin de mes)")
        
        if st.form_submit_button("Registrar Vale"):
            conn = conectar()
            conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (socio_sel, monto, str(fecha), concepto))
            conn.commit(); conn.close(); st.success("Vale registrado correctamente.")

    st.write("### Historial de Vales")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

# --- MÓDULO 5: ACTIVOS ---
elif menu == "🚜 5. Inventario de Activos":
    st.title("🚜 Inventario de Maquinaria y Equipos")
    with st.form("activos_form"):
        item = st.text_input("Nombre del Activo / Herramienta")
        valor = st.number_input("Valor Estimado (Bs)", min_value=0.0)
        estado = st.selectbox("Estado de Conservación", ["Excelente", "Bueno", "Regular", "En Reparación"])
        if st.form_submit_button("Añadir al Inventario"):
            f_hoy = datetime.now().strftime("%Y-%m-%d")
            conn = conectar()
            conn.execute("INSERT INTO activos (item, valor, estado, fecha_reg) VALUES (?,?,?,?)", (item, valor, estado, f_hoy))
            conn.commit(); conn.close(); st.success("Activo registrado.")
            
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

# --- MÓDULO 6: LIBRO DIARIO ---
elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario (Registros Auditados)")
    st.write("Aquí se consolidan todos los datos extraídos por el Escáner IA.")
    df_final = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df_final, use_container_width=True)
    
    if not df_final.empty:
        st.download_button(
            label="📥 Descargar Libro Diario (Excel/CSV)",
            data=df_final.to_csv(index=False),
            file_name="libro_diario_2019.csv",
            mime="text/csv"
        )

# --- MÓDULO 7: CONFIGURACIÓN ---
elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Configuración del Sistema")
    st.write("**Versión del Software:** SGA Pro v56.0 - Master")
    st.write("**Base de Datos:** SQLite 3 (Persistente)")
    
    if st.button("🧹 Limpiar Memoria Temporal (Cache)"):
        st.cache_data.clear(); st.rerun()
    
    st.info("Para actualizar la clave de la IA, modifica los 'Secrets' en el panel de Streamlit.")
