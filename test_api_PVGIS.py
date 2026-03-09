# Este código consulta la API de PVGIS para obtener la radiación solar mensual en Bogotá durante el año 2023 y luego crea un gráfico de columnas para visualizar los datos. La barra con el valor mínimo se resalta en rojo, mientras que las demás barras se muestran en naranja. Además, se agregan los valores numéricos sobre cada barra para facilitar la lectura.
# https: // joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis_en

import requests
import matplotlib.pyplot as plt

year = 2023

# Entry point con PVGIS 5.3
url = "https://re.jrc.ec.europa.eu/api/v5_3/MRcalc"
params = {
    "lat": 4.7110,          # Bogotá
    "lon": -74.0721,
    "startyear": year,
    "endyear": year,
    "horirrad": 1,
    "outputformat": "json"
}

response = requests.get(url, params=params)
data = response.json()

months = []
radiation = []

# La estructura correcta está en data["outputs"]["monthly"]
if "outputs" in data and "monthly" in data["outputs"]:
    for month in data["outputs"]["monthly"]:
        months.append(month["month"])
        radiation.append(month["H(h)_m"])
else:
    print("No se encontraron datos:", data)

# Crear gráfico de columnas
plt.figure(figsize=(10, 6))

# Determinar el índice del valor mínimo
min_index = radiation.index(min(radiation))

# Colores: rojo para el mínimo, naranja para el resto
colors = ["#FF6B6B" if i ==
          min_index else "orange" for i in range(len(radiation))]

bars = plt.bar(range(len(months)), radiation, color=colors, edgecolor="black")

# Agregar valores sobre cada barra
for bar, value in zip(bars, radiation):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f'{value:.1f}', ha='center', va='bottom', fontsize=9)

plt.title(f"Radiación mensual en Bogotá ({year})", fontsize=14)
plt.xlabel("Mes", fontsize=12)
plt.ylabel("Radiación [kWh/m²]", fontsize=12)

# Etiquetas de meses
plt.xticks(range(len(months)), ["Ene", "Feb", "Mar", "Abr",
           "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"])

plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()
