import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# CONFIGURACIÓN DE INFLUXDB
# ---------------------------------------------------------
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = st.secrets["INFLUXDB_TOKEN"]
INFLUXDB_ORG = "studio70751a@gmail.com"
INFLUXDB_BUCKET = "Studio"

# ---------------------------------------------------------
# FUNCIÓN PARA CONSULTAR INFLUXDB
# ---------------------------------------------------------
def query_influx(query):
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    tables = client.query_api().query(query)

    records = []
    for table in tables:
        for row in table.records:
            records.append({
                "_time": row.get_time(),
                "_field": row.get_field(),
                "_value": row.get_value()
            })
    return pd.DataFrame(records)

# ---------------------------------------------------------
# UI DE STREAMLIT
# ---------------------------------------------------------
st.title("Dashboard Sensores InfluxDB - Studio")

sensor = st.selectbox("Selecciona el sensor:", ["DHT22", "BH1750"])
start = st.number_input("Días hacia atrás (inicio):", min_value=1, max_value=60, value=7)
stop = st.number_input("Días hacia atrás (fin):", min_value=0, max_value=59, value=0)

# ---------------------------------------------------------
# CONSULTA SEGÚN SENSOR
# ---------------------------------------------------------
if sensor == "DHT22":

    # 🔍 PRIMERA CONSULTA: obtener TODOS LOS CAMPOS reales
    st.subheader("Campos detectados en el sensor DHT22")

    query_all = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -{start}d, stop: -{stop}d)
        |> filter(fn: (r) => r._measurement == "studio-dht22")
    '''

    df_all = query_influx(query_all)

    if df_all.empty:
        st.error("No hay datos del sensor DHT22 en el rango seleccionado.")
        st.stop()

    # Mostrar lista real de campos
    fields = sorted(df_all["_field"].unique().tolist())
    st.write("**Campos encontrados:**", fields)

    # 🔎 Verificamos si existe CO₂ usando varios nombres comunes
    co2_aliases = ["co2", "co2_ppm", "co2ppm", "co2_level", "co2_concentration"]
    co2_field = next((f for f in co2_aliases if f in fields), None)

    if co2_field:
        st.success(f"Campo CO₂ detectado como: **{co2_field}**")
    else:
        st.warning("⚠ No se detectó ningún campo de CO₂ en este sensor.")

    # ---------------------------------------------------------
    # Consulta final (solo los campos existentes)
    # ---------------------------------------------------------

    allowed_fields = ["temperature", "humidity"]
    if co2_field:
        allowed_fields.append(co2_field)

    query_fields = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -{start}d, stop: -{stop}d)
        |> filter(fn: (r) => r._measurement == "studio-dht22")
        |> filter(fn: (r) => contains(value: r._field, set: {allowed_fields}))
    '''

    df = query_influx(query_fields)

elif sensor == "BH1750":
    st.subheader("Campos detectados en el sensor BH1750")

    query_bh = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -{start}d, stop: -{stop}d)
        |> filter(fn: (r) => r._measurement == "studio-bh1750")
    '''

    df = query_influx(query_bh)

else:
    st.stop()

# ---------------------------------------------------------
# PROCESAR DATOS
# ---------------------------------------------------------
if df.empty:
    st.error("No se encontraron datos en este rango.")
    st.stop()

# Convertir a formato tabla pivoteada
df_pivot = df.pivot(index="_time", columns="_field", values="_value")

st.subheader("Tabla de datos")
st.dataframe(df_pivot)

# ---------------------------------------------------------
# GRAFICAR
# ---------------------------------------------------------
st.subheader("Gráficas")

for col in df_pivot.columns:
    fig = px.line(df_pivot, x=df_pivot.index, y=col, title=f"{col}")
    st.plotly_chart(fig, use_container_width=True)
