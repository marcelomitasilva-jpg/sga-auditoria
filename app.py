import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="SGA Pro v41.0 - Sistema Maestro", layout="wide")

# Inicializamos la memoria de la API Key para que no se pierda al cambiar de menú
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

with st.sidebar:
    st.title("🔐 SEGURIDAD")
    # Al usar type="password" ya no verás la clave escrita en la esquina de la pantalla
    clave_ingresada = st.text_input("Gemini API KEY", value=st.session_state.api_key, type="password")
    
    if clave_ingresada:
        st.session_state.api_key = clave_ingresada
        genai.configure(api_key=st.session_state.api_key)
        # Nano Banana (Gemini 1.5 Flash) es el motor de visión
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.warning("⚠️ Ingrese su API KEY para activar la Inteligencia de Visión.")

# --- 2. MOTOR DE BASE DE DATOS (CONSOLIDADO) ---
def conectar():
    return sqlite3.connect('sga_cooperativa.db')

def inicializar_db():
    conn = conectar()
    c = conn.cursor()
    # Módulo Personal
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE)')
    # Módulo Auditoría (Escáner)
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    # Módulo Vales
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio_id INTEGER, monto REAL, fecha TEXT)')
    # Módulo Activos
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, descripcion TEXT, valor REAL)')
    conn.commit()
    conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN MAESTRA ---
st.sidebar.title("🚀 MÓDULOS")
menu = st.sidebar.radio("IR A:", [
    "📊 1. Dashboard General",
    "👥 2. Registro de Personal",
    "⛏️ 3. Escáner IA (Auditoría)",
    "💰 4. Control de Vales",
    "🚜 5. Inventario de Activos",
    "📖 6. Libro Diario Central"
])

# --- LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen de la Cooperativa")
    st.write(f"Bienvenido, Marcelo. Sistema listo para procesar los cuadernos de 2019.")
    
    # Pequeño resumen de datos guardados
    c1, c2 = st.columns(2)
    with c1:
        total_socios = pd.read_sql_query("SELECT COUNT(*) as total FROM personal", conectar()).iloc[0]['total']
        st.metric("Socios Registrados", total_socios)
    with c2:
        total_bs = pd.read_sql_query("SELECT SUM(bs) as total FROM auditoria", conectar()).iloc[0]['total']
        st.metric("Total Bs Auditados", f"{total_bs if total_bs else 0:,.2f}")

elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Personal")
    with st.form("form_p"):
        nombre = st.text_input("Nombre Completo").upper()
        ci = st.text_input("CI / Documento")
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); c = conn.cursor()
                c.execute("INSERT INTO personal (nombre, ci) VALUES (?,?)", (nombre, ci))
                conn.commit(); conn.close()
                st.success("Socio registrado con éxito.")
            except:
                st.error("Error: Este CI ya existe en el sistema.")
    
    st.subheader("Socios Actuales")
    df_p = pd.read_sql_query("SELECT * FROM personal", conectar())
    st.dataframe(df_p, use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Extracción Inteligente de Cuadernos")
    
    if not st.session_state.api_key:
        st.error("❌ ERROR: Debes ingresar la API KEY en el menú de la izquierda.")
    else:
        archivo = st.file_uploader("Subir foto del cuaderno", type=['png', 'jpg', 'jpeg'])
        if archivo:
            img = Image.open(archivo)
            st.image(img, width=450, caption="Imagen cargada para análisis")
            
            if st.button("🚀 INICIAR ANÁLISIS IA"):
                with st.spinner("Analizando caligrafía y estructura..."):
                    # Preparación de imagen para la nube
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG')
                    
                    # Instrucción de experto para la IA
                    prompt = """Actúa como un experto contable. Analiza esta tabla de minería y extrae los datos. 
                    Responde ÚNICAMENTE con una lista en formato JSON con estas llaves: 
                    "fecha", "tujo", "mina", "bs", "obs". 
                    REGLAS:
                    1. Si el valor es ilegible o vacío en tujo, mina o bs, pon 0.
                    2. Los nombres o notas van en 'obs'.
                    3. No inventes datos, si no estás seguro pon 0."""
                    
                    try:
                        response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_byte_arr.getvalue()}])
                        # Extraer solo el texto que parece JSON
                        json_str = re.search(r'\[.*\]', response.text, re.DOTALL).group()
                        st.session_state.df_temp = pd.read_json(io.StringIO(json_str))
                        st.balloons()
                    except:
                        st.error("La IA no pudo formatear la tabla. Intente una foto con mejor luz.")

    if 'df_temp' in st.session_state:
        st.subheader("📋 Revisión de Auditoría")
        # El data_editor permite que tú corrijas cualquier error de la IA antes de guardar
        df_editado = st.data_editor(st.session_state.df_temp, use_container_width=True)
        
        if st.button("💾 GUARDAR DEFINITIVAMENTE EN LIBRO DIARIO"):
            conn = conectar()
            df_editado.to_sql('auditoria', conn, if_exists='append', index=False)
            conn.close()
            st.success("✅ Datos guardados y consolidados.")
            del st.session_state.df_temp

elif menu == "💰 4. Control de Vales":
    st.title("💰 Registro de Vales y Adelantos")
    st.info("Módulo de egresos en desarrollo.")

elif menu == "🚜 5. Inventario de Activos":
    st.title("🚜 Control de Activos")
    st.info("Módulo de maquinaria y equipos en desarrollo.")

elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario Central")
    st.write("Historial completo de registros auditados:")
    df_final = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df_final, use_container_width=True)
