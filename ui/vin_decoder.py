from database import get_connection

# ================================
# VALIDARE VIN
# ================================
def is_valid_vin(vin: str) -> bool:
    if not vin or len(vin) != 17:
        return False
    for c in vin:
        if c in "IOQ":
            return False
    return True


# ================================
# EXTRAGERE WMI (primele 3 caractere)
# ================================
def get_wmi(vin: str) -> str:
    return vin[:3].upper()


# ================================
# EXTRAGERE PREFIX MODEL (primele 5 caractere)
# ================================
def get_family_prefix(vin: str) -> str:
    return vin[:5].upper()


# ================================
# EXTRAGERE AN FABRICATIE
# ================================
VIN_YEAR_MAP = {
    "Y": 2000,
    "1": 2001, "2": 2002, "3": 2003, "4": 2004, "5": 2005,
    "6": 2006, "7": 2007, "8": 2008, "9": 2009,
    "A": 2010, "B": 2011, "C": 2012, "D": 2013, "E": 2014,
    "F": 2015, "G": 2016, "H": 2017, "J": 2018, "K": 2019,
    "L": 2020, "M": 2021, "N": 2022, "P": 2023, "R": 2024,
    "S": 2025, "T": 2026, "V": 2027, "W": 2028, "X": 2029,
}

def get_year_from_vin(vin: str):
    code = vin[9].upper()
    return VIN_YEAR_MAP.get(code)


# ================================
# CAUTARE WMI
# ================================
def lookup_wmi(wmi: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT marca FROM vin_wmi WHERE wmi=?", (wmi,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None


# ================================
# CAUTARE PREFIX VIN
# ================================
def lookup_family(prefix: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT marca, model, descriere, cc, year
        FROM vin_family
        WHERE prefix=?
    """, (prefix,))
    row = cur.fetchone()
    con.close()
    if row:
        return {
            "marca": row[0],
            "model": row[1],
            "descriere": row[2],
            "cc": row[3],
            "year": row[4]
        }
    return None


# ================================
# DECODARE COMPLETA VIN
# ================================
def decode_vin(vin: str):
    vin = vin.strip().upper()
    if not is_valid_vin(vin):
        return {"valid": False}

    wmi = get_wmi(vin)
    prefix = get_family_prefix(vin)
    year = get_year_from_vin(vin)

    marca = lookup_wmi(wmi)
    family = lookup_family(prefix)

    result = {
        "valid": True,
        "vin": vin,
        "wmi": wmi,
        "prefix": prefix,
        "year": year,
        "marca": marca,
        "model": None,
        "descriere": None,
        "cc": None
    }

    if family:
        result["model"] = family["model"]
        result["descriere"] = family["descriere"]
        result["cc"] = family["cc"]
        if family["year"] and not result["year"]:
            result["year"] = family["year"]
        if not marca:
            result["marca"] = family["marca"]

    return result
