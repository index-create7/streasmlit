import pandas as pd
import streamlit as st
from pathlib import Path
Base_DIR = Path().parent
DATA_DIR = Base_DIR / "data"
CSV_DIR = DATA_DIR / "record.csv"
DATA_DIR.mkdir(parents=True, exist_ok=True)
COLUMNS = ""
if CSV_DIR.exists():
    df=pd.read_csv(CSV_DIR)
else:
    df=pd.DataFrame(columns=COLUMNS)

