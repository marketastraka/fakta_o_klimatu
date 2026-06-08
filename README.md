**KAYA DECOMPOSITION & WORLD BANK DATA ANALYSIS**

Tento projekt analyzuje vztahy mezi emisemi CO2, spotřebou energie, HDP a populací pomocí Kaya identity dekompozice. Data jsou kombinací World Bank API a EDGAR datasetu.

**CO PROJEKT DĚLÁ**
- stahuje makroekonomická data z World Bank API
- načítá emisní data CO2 z EDGAR datasetu
- přepočítává energetické a emisní ukazatele na celkové hodnoty
- počítá meziroční změny v procentech
- aplikuje Kaya dekompozici
- vytváří vizualizace časové změny faktorů pro jednotlivé země a cross-country dashboard

**POUŽITÁ DATA**

World Bank API:

- Population: SP.POP.TOTL
- GDP per capita: NY.GDP.PCAP.CD
- Energy use per capita: EG.USE.PCAP.KG.OE
- Energy use per GDP: EG.USE.COMM.GD.PP.KD
- GDP total: NY.GDP.MKTP.CD

EDGAR dataset:

- CO2 emise podle zemí (1970–2024) - https://edgar.jrc.ec.europa.eu/

**JAK SPUSTIT**

- pip install pandas numpy matplotlib requests openpyxl
- vytvořit podsložku EDGAR, do které se vloží stažený EDGAR dataset NEBO přímo upravit kód EDGAR_FILE = child_file("EDGAR", "IEA_EDGAR_CO2_1970_2024.xlsx") >> nahradit **EDGAR_FILE = r"C://umisteni_souboru/IEA_EDGAR_CO2_1970_2024.xlsx"**
- python data_glimpse.py

