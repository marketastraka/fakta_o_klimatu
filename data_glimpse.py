from pathlib import Path
import re
import pandas as pd
import re
import numpy as np
import matplotlib.pyplot as plt
import requests
import zipfile
import io

BASE_DIR = Path(__file__).resolve().parent

# stažení dat z World Bank API - funkce pro načtení indikátoru a vrácení jako DataFrame
def load_worldbank_indicator(indicator_code):
    """
    Download a World Bank indicator and return it as a DataFrame.

    Example:
        population = load_worldbank_indicator("SP.POP.TOTL")
    """

    url = (
        f"https://api.worldbank.org/v2/en/indicator/"
        f"{indicator_code}?downloadformat=csv"
    )

    response = requests.get(url)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:

        # find the actual data file
        data_file = next(
            name
            for name in z.namelist()
            if name.startswith(f"API_{indicator_code}")
            and name.endswith(".csv")
        )

        with z.open(data_file) as f:
            df = pd.read_csv(f, skiprows=4)

    return df



def child_file(folder_name: str, file_name: str) -> Path:
    return BASE_DIR / folder_name / file_name


# stažení dat z World Bank API - pro každý indikátor vytvoříme samostatný DataFrame
population = load_worldbank_indicator("SP.POP.TOTL")
gdp_per_capita = load_worldbank_indicator("NY.GDP.PCAP.CD")
energy_capita = load_worldbank_indicator("EG.USE.PCAP.KG.OE")
energy_gdp = load_worldbank_indicator("EG.USE.COMM.GD.PP.KD")
gdp = load_worldbank_indicator("NY.GDP.MKTP.CD")

# edgar data - pro CO2 emise, ty nejsou dostupné přes World Bank API, takže je musíme stáhnout ručně a načíst z Excelu
EDGAR_FILE = child_file("EDGAR", "IEA_EDGAR_CO2_1970_2024.xlsx") # https://edgar.jrc.ec.europa.eu/dataset_ghg2025

# nastavení hraničních let pro analýzu
START_YEAR = 1989
END_YEAR = 2024

# funkce pro standardizaci názvů sloupců s roky (některé mají např. "2020 [YR2020]")
def standardize_year_columns(df, start_year=START_YEAR, end_year=END_YEAR):
    rename_dict = {}

    for col in df.columns:
        col_str = str(col)

        # find ANY 4-digit year in the name
        match = re.search(r"\d{4}", col_str)

        if match:
            year = int(match.group())

            if start_year <= year <= end_year:
                rename_dict[col] = str(year)

    df = df.rename(columns=rename_dict)

    # ensure all column names are strings
    df.columns = df.columns.astype(str)

    return df

# funkce pro výpočet roční změny v procentech
def get_yearly_change(
    df: pd.DataFrame,
    id_cols: list[str] = ["Country Name", "Country Code"],
) -> pd.DataFrame:
    df.columns = df.columns.astype(str)
    year_cols = [str(y) for y in range(START_YEAR, END_YEAR + 1) if str(y) in df.columns]
    subset = df[id_cols + year_cols].copy()
    result = subset[id_cols].copy()
    for i in range(1, len(year_cols)):
        prev, curr = year_cols[i - 1], year_cols[i]
        result[curr] = (subset[curr] - subset[prev]) / subset[prev] * 100
    return result


# 1 změna populace
print(population.head())

population_change = get_yearly_change(population)
print(population_change.head())

# 2 změna GDP/CAPITA
print(gdp_per_capita.head())

gdp_per_capita_change = get_yearly_change(gdp_per_capita)
print(gdp_per_capita_change.head())

# 3 změna ENERGIE/GDP

energy_gdp = load_worldbank_indicator("EG.USE.COMM.GD.PP.KD")
energy_gdp_change = get_yearly_change(energy_gdp)
print(energy_gdp_change.head())

# 4. změna CO2/energii > nejdřív musíme přepočítat energie z capita na celkovou GDP, pak spojit s CO2 a teprve pak spočítat změnu
energy_capita = load_worldbank_indicator("EG.USE.PCAP.KG.OE")
print(energy_capita.head()) # měřítko jsou kto/ob.rok

# vynásobit energy/capita počtem obyvatel = celková energie v kto/rok
energy_capita = energy_capita.merge(population[["Country Name", "Country Code"] + [str(y) for y in range(START_YEAR, END_YEAR + 1)]], on=["Country Name", "Country Code"], how="left", suffixes=("", "_population"))
for year in range(START_YEAR, END_YEAR + 1):
    energy_capita[str(year) + "_energy"] = energy_capita[str(year)] * energy_capita[str(year) + "_population"]
energy = energy_capita[["Country Name", "Country Code"] + [str(y) + "_energy" for y in range(START_YEAR, END_YEAR + 1)]].copy()
print(energy.head()) # měřítko jsou tuny oil equivalent/rok

# data ohledně CO2
edgar = pd.read_excel(
    EDGAR_FILE,
    sheet_name='TOTALS BY COUNTRY',
    skiprows=9
)
print(edgar.head()) # měřítko jsou ktuny CO2/rok
edgar = standardize_year_columns(edgar)

edgar = edgar.rename(columns={"Name": "Country Name", "Country_code_A3": "Country Code"})
co2 = edgar[["Country Name", "Country Code"] + [str(y) for y in range(START_YEAR, END_YEAR + 1)]].copy() # měřítko jsou ktuny CO2/rok
print(co2.head())
id_cols = ["Country Name", "Country Code"]

co2.loc[:, ~co2.columns.isin(id_cols)] = co2.loc[:, ~co2.columns.isin(id_cols)].apply(
    pd.to_numeric,
    errors="coerce"
)
energy_co2 = energy.merge(co2, on=["Country Code"], how="left", suffixes=("_energy", "_co2"))
print(energy_co2.head())

# vypočítat CO2/energie pro každý rok
for year in range(START_YEAR, END_YEAR + 1):
    energy_co2[str(year) + "_energy_co2"] = energy_co2[str(year)] / energy_co2[str(year) + "_energy"]
print(energy_co2.head())
energy_co2_final = energy_co2[["Country Code"] + [str(y) + "_energy_co2" for y in range(START_YEAR, END_YEAR + 1)]].copy()
print(energy_co2_final.head())
energy_co2_final = standardize_year_columns(energy_co2_final)

# výpočet změny CO2/energie
energy_co2_final_change = get_yearly_change(energy_co2_final, id_cols=["Country Code"])
print(energy_co2_final_change.head())



# PLOT = příprava dat pro vizualizaci - spojení všech 4 faktorů do jednoho dataframe pro konkrétní zemi a vykreslení změn v čase

def get_country_series(df, country_code, start_year=START_YEAR, end_year=END_YEAR):
    row = df[df["Country Code"] == country_code]

    year_cols = [str(y) for y in range(start_year, end_year + 1) if str(y) in df.columns]

    series = row[year_cols].T
    series.columns = ["value"]
    series.index = series.index.astype(int)

    return series

def build_combined_df(country_code):
    pop = get_country_series(population_change, country_code).rename(columns={"value": "population"})
    gdp = get_country_series(gdp_per_capita_change, country_code).rename(columns={"value": "gdp/capita"})
    eng_gdp = get_country_series(energy_gdp_change, country_code).rename(columns={"value": "energy/gdp"})
    co2 = get_country_series(energy_co2_final_change, country_code).rename(columns={"value": "co2/energy"})

    df = pop.join([gdp, eng_gdp, co2])

    # convert to %

    return df


# GRAF - 1
cmap = plt.get_cmap("tab20b")

colors = [
    cmap(2),
    cmap(6),
    cmap(10),
    cmap(14)
]

def plot_changes(country_code, set_title="Kaya decomposition"):
    df = build_combined_df(country_code)  # your existing function

    fig, ax = plt.subplots(figsize=(12, 6))  # 👈 wider plot

    df.plot(
        kind="bar",
        stacked=True,
        ax=ax,
        color=colors,  # 👈 custom colors
        width=0.8  # 👈 wider bars
    )

    ax.axhline(0, color="black", linewidth=1)

    ax.set_title(f"{set_title} - {country_code}")
    ax.set_xlabel("")
    ax.set_ylabel("% change")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    plt.xticks(rotation=45)
    plt.tight_layout()
    y_min, y_max = ax.get_ylim()
    ax.set_yticks(np.arange(np.floor(y_min), np.ceil(y_max) + 1, 2))

    plt.show()

plot_changes("USA")
plot_changes("CZE")
plot_changes("IND")
plot_changes("DEU")
plot_changes("CHN")
plot_changes("VNM")




## identifikace clusterů - Graf 2
def last_n_year_avg(df, n=5):
    df = df.copy()

    id_cols = ["Country Code", "Country Name"]

    year_cols = [
        c for c in df.columns
        if c not in id_cols and str(c).isdigit()
    ]

    year_cols = sorted(year_cols, key=int)

    last_cols = year_cols[-n:]

    s = df.set_index("Country Code")[last_cols].mean(axis=1)

    s.index = s.index.astype(str).str.strip().str.upper()

    return s

def build_dashboard(countries):

    gdp = last_n_year_avg(gdp_per_capita_change)
    pop = last_n_year_avg(population_change)
    co2 = last_n_year_avg(energy_co2_final_change)
    energy = last_n_year_avg(energy_gdp_change)

    df = pd.DataFrame({
        "gdp_growth": gdp,
        "population": pop,
        "co2": co2,
        "energy_eff": energy
    })

    df = df.loc[countries].copy()

    return df

def plot_dashboard(countries):

    df = build_dashboard(countries)

    fig, ax = plt.subplots(figsize=(10, 8))

    x = df["co2"]
    y = df["energy_eff"]

    sizes = (df["population"] - df["population"].min()) / (df["population"].max() - df["population"].min()) * 300 + 50

    scatter = ax.scatter(
        x, y,
        s=sizes,
        c=df["gdp_growth"],
        cmap="RdYlGn",
        alpha=0.8
    )

    # zero cross
    ax.axhline(0, color="black")
    ax.axvline(0, color="black")

    # labels
    for i in df.index:
        ax.text(df.loc[i, "co2"], df.loc[i, "energy_eff"], i)

    ax.set_xlabel("CO₂ / energy (last 5y avg)")
    ax.set_ylabel("Energy / GDP (last 5y avg)")
    ax.set_title("Kaya decomposition dashboard")

    plt.colorbar(scatter, label="GDP per capita growth (last 5y avg)")

    plt.show()

plot_dashboard(["CZE", "DEU", "IND", "NPL","USA", "CHN", "ITA", "ESP", "FRA", "RUS", "BRA", "ZAF", "MEX", "JPN", "KOR", "AUS", "CAN", "GBR", "TUR", "SAU", "ARG", "KAZ", "NOR", "VNM", "EGY", "IRN", "PAK", "IDN", "DZA", "MAR", "UKR", "ROU", "GRC", "HUN", "PRT", "CYP", "LTU", "LVA", "EST", "NER", "ETH", "PHL", "GHA", "SSD", "KEN"])