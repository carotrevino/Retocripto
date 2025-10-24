# streamlit_app.py
from datetime import date
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, date
from app_core import (
    USERS, verify_password, make_user,
    lista_estudios, list_folios, get_order_summary,
    save_order, save_results, read_csv, decrypt_view, filter_df, export_excel
)

st.set_page_config(
    page_title="Consultorio | Criptografía segura", page_icon="🔐", layout="wide")


# --- Auth (simple en memoria) ---
if "user" not in st.session_state:
    st.session_state.user = None


def login_view():
    st.subheader("Iniciar sesión")
    email = st.text_input("Correo", value="recep@lab.local")
    pwd = st.text_input("Contraseña", type="password", value="recep123")
    if st.button("Entrar", type="primary"):
        rec = USERS.get(email)
        if rec and verify_password(pwd, rec["salt"], rec["hash"]):
            st.session_state.user = {"email": email, "role": rec["role"]}
            st.success(f"Bienvenida/o: {email} — rol: {rec['role']}")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")


def logout_button():
    st.sidebar.button(
        "Cerrar sesión", on_click=lambda: st.session_state.update(user=None))
    if st.session_state.user:
        st.sidebar.success(
            f"👋 {st.session_state.user['email']} ({st.session_state.user['role']})")


# --- Layout principal ---
st.title("🔐 Consultorio | Gestión segura")

if not st.session_state.user:
    login_view()
    st.stop()
else:
    logout_button()

# Tabs por rol
tabs = st.tabs(["Recepción", "Laboratorio", "Consultas/Reportes", "Admin"])

# ========== Recepción ==========
with tabs[0]:
    if st.session_state.user["role"] not in ("recepcion", "admin"):
        st.info("No tienes permisos para esta sección.")
    else:
        st.subheader("➕ Alta de paciente / solicitud")
        with st.form("form_recepcion", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                folio = st.text_input("Folio (opcional)", placeholder="auto")
                fecha_prog = st.date_input(
                    "Fecha programada", value=date.today())
                costo = st.number_input(
                    "Costo (MXN)", min_value=0.0, step=50.0)
            with col2:
                nombre = st.text_input("Nombre del paciente")
                edad = st.number_input(
                    "Edad", min_value=0, max_value=120, step=1)
                genero = st.selectbox(
                    "Género", ["F", "M", "Otro", "No especifica"])
            with col3:
                telefono = st.text_input("Teléfono")
                direccion = st.text_input("Dirección")
                tipo = st.multiselect(
                    "Estudios", lista_estudios(), defauwhlt=[])
            auto_cost = st.checkbox("Calcular costo automático desde catálogo")
            observaciones = st.text_area("Observaciones", height=90)
            submitted = st.form_submit_button("Guardar paciente + solicitud")
        if submitted:
            try:
                # Si el checkbox está activo, ignoramos costo manual
                if auto_cost:
                    from app_core import costo_total_desde_catalogo
                    costo = costo_total_desde_catalogo(tipo)
                folio_final = save_order(
                    folio, str(
                        fecha_prog), costo, nombre, edad, genero, telefono, direccion, tipo, observaciones
                )
                st.success(f"Guardado folio: {folio_final}")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ========== Laboratorio ==========
with tabs[1]:
    if st.session_state.user["role"] not in ("lab", "medico", "admin"):
        st.info("No tienes permisos para esta sección.")
    else:
        st.subheader("🧪 Captura de resultados")
        cols = st.columns([2, 1])
        with cols[0]:
            folios = list_folios()  # puedes filtrar por estado si deseas
            folio_sel = st.selectbox("Selecciona folio", [
                                     "—"] + folios, index=0)
            if st.button("Cargar orden"):
                st.session_state["folio_loaded"] = folio_sel if folio_sel != "—" else None

            folio_loaded = st.session_state.get("folio_loaded")
            if folio_loaded:
                info = get_order_summary(folio_loaded)
                if info:
                    st.markdown(
                        f"**Paciente:** {info['Nombre']} — **Estado:** {info['Estado']}")
                    st.markdown(f"**Estudios:** {info['Tipo_Estudio']}")
                else:
                    st.warning("Folio no encontrado")
        with cols[1]:
            st.write(" ")

        resultados = st.text_area(
            "Resultados (texto o JSON)", height=200, placeholder='{"glucosa": 90, "obs":"ayuno 8h"}')
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Guardar resultados"):
                try:
                    ok = save_results(st.session_state.get(
                        "folio_loaded", ""), resultados, liberar=False)
                    if ok:
                        st.success("Resultados guardados (estado: capturado)")
                except Exception as e:
                    st.error(f"Error: {e}")
        with c2:
            F
        if st.button("Firmar y liberar"):
            try:
                ok = save_results(st.session_state.get(
                    "folio_loaded", ""), resultados, liberar=True)
                if ok:
                    st.success("Orden firmada (estado: firmado)")
            except Exception as e:
                st.error(f"Error: {e}")

        # ======== Formato LABZA (PDF) ========
st.markdown("### 🧾 Formato LABZA (PDF)")

# Solo si hay folio cargado y ya se cargó el resumen
folio_loaded = st.session_state.get("folio_loaded")
if folio_loaded:
    info = get_order_summary(folio_loaded)
    if info:
        # Arma el diccionario de datos para el PDF
        # (ajusta las llaves a las que uses realmente en tu Excel / JSON)
        data = {
            "paciente": info.get("Nombre", ""),
            "edad": info.get("Edad", ""),
            "sexo": info.get("Género", info.get("Genero", "")),
            "fecha": date.today().strftime("%d/%m/%Y"),
            "folio": folio_loaded,
            "medico": info.get("Medico", ""),
            "analisis": ", ".join(info.get("Tipo_Estudio", [])) if isinstance(info.get("Tipo_Estudio"), list) else info.get("Tipo_Estudio", ""),
        }

        # Si el área de texto 'resultados' contiene JSON válido, úsalo para rellenar analitos
        _raw = st.session_state.get("resultados", "") or ""
        try:
            parsed = json.loads(_raw) if _raw else {}
        except Exception:
            parsed = {}

        # Mapea nombres del JSON a campos del formato (ajusta a tus claves reales)
        mapping = {
            "glucosa": "GLUC",
            "bun": "BUN",
            "creatinina": "CREAT",
            "urea": "UREA",
            "acido_urico": "AC_URICO",
            "sodio": "Na",
            "potasio": "K",
            "cloro": "Cl",
            "calcio": "Ca",
            # ... añade todos los que necesites
        }
        for k_json, k_pdf in mapping.items():
            if k_json in parsed and parsed[k_json] not in (None, ""):
                data[k_pdf] = parsed[k_json]

        # Botón para generar y descargar
        if st.button("Generar PDF LABZA", key="btn_pdf"):
            pdf_path = generate_labza_pdf(data)  # crea el PDF en disco
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Descargar PDF",
                    data=f.read(),
                    file_name=Path(pdf_path).name,
                    mime="application/pdf",
                    key="dl_pdf",
                )
            st.success("PDF creado. Al imprimir usa **Tamaño real / 100%**.")
    else:
        st.info("Carga un folio válido para generar el PDF.")
else:
    st.info("Primero selecciona y carga un folio.")

resultados = st.text_area(
    "Resultados (texto o JSON)", height=200,
    placeholder='{"glucosa": 90, "obs":"ayuno 8h"}',
    key="resultados"   # <-- añade esto
)


# ========== Consultas / Reportes ==========
with tabs[2]:
    st.subheader("🔎 Búsqueda y exportación")
    q = st.text_input("Buscar (cualquier campo)")
    df = decrypt_view(read_csv())
    df_f = filter_df(df, q) if q else df
    st.dataframe(df_f, use_container_width=True, height=300)
    if st.button("Exportar a Excel"):
        path, msg = export_excel(df_f)
        st.success(f"{msg}. Archivo: {path}")

# ========== Admin ==========
with tabs[3]:
    if st.session_state.user["role"] != "admin":
        st.info("Solo admin puede gestionar usuarios.")
    else:
        st.subheader("👤 Gestión de usuarios (demo en memoria)")
        with st.form("form_new_user"):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Nombre (solo referencia local)")
            with col2:
                email = st.text_input("Correo")
            with col3:
                role = st.selectbox(
                    "Rol", ["recepcion", "lab", "medico", "admin"])
            pwd = st.text_input("Contraseña", type="password")
            submitted_u = st.form_submit_button("Crear/Actualizar usuario")
        if submitted_u:
            if email and pwd and role:
                USERS[email] = make_user(pwd, role)
                st.success(f"Usuario {email} ({role}) creado/actualizado")
            else:
                st.error("Completa correo, rol y contraseña")

        # Tabla simple
        st.markdown("**Usuarios actuales (solo memoria de ejecución):**")
        data = [{"email": e, "role": USERS[e]["role"]}
                for e in sorted(USERS.keys())]
        st.dataframe(pd.DataFrame(data), use_container_width=True, height=200)
