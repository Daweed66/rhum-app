import streamlit as st
import pandas as pd
import csv
import json
import unicodedata
import zipfile
import io
from datetime import datetime
import os

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Gestion Samples Rhum",
    page_icon="🥃",
    layout="wide",
    initial_sidebar_state="expanded"
)

FICHIER_ETAT = "rhum_etat.json"

# --- THEME CSS LISIBLE (Chocolat & Bois Clair) ---
st.markdown("""
<style>
    /* Fond principal : Beige très clair */
    .stApp { background-color: #FAFAF5; }
    
    /* Sidebar : Beige un peu plus soutenu (Sable) */
    section[data-testid="stSidebar"] { background-color: #F0E6D2; border-right: 1px solid #D7CCC8; }
    
    /* Titres : Marron Chocolat Foncé */
    h1, h2, h3 { color: #3E2723 !important; font-family: 'Helvetica', 'Arial', sans-serif; font-weight: 700; }
    
    /* Texte normal : Noir doux */
    p, label, .stMarkdown { color: #2D241E !important; }
    
    /* Boutons : Marron Cuir */
    .stButton > button { background-color: #8D6E63; color: white !important; border: 1px solid #5D4037; border-radius: 6px; transition: all 0.2s; }
    .stButton > button:hover { background-color: #6D4C41; border-color: #3E2723; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    
    /* Métriques (Chiffres) : Couleur Cognac */
    [data-testid="stMetricValue"] { color: #A1887F !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #5D4037 !important; }
    
    /* Boîtes de succès/info/warning */
    .stSuccess { background-color: #E8F5E9; border-left: 5px solid #4CAF50; color: #1B5E20; }
    .stWarning { background-color: #FFF3E0; border-left: 5px solid #FF9800; color: #E65100; }
    .stError { background-color: #FFEBEE; border-left: 5px solid #F44336; color: #B71C1C; }
    
    /* Tableau (Data Editor) */
    [data-testid="stDataFrame"] { border: 1px solid #D7CCC8; border-radius: 5px; }

    /* Bilan Annuel Box */
    .bilan-box {
        background-color: #FFF8E1;
        border: 2px solid #FFECB3;
        border-radius: 10px;
        padding: 15px;
        margin-top: 20px;
        margin-bottom: 20px;
        text-align: center;
    }
    .bilan-title { color: #F57F17; font-weight: bold; font-size: 1.1em; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES ---
def retirer_accents(texte):
    if not isinstance(texte, str): return texte
    try:
        nfkd_form = unicodedata.normalize('NFKD', texte)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    except: return texte

def sauvegarder_etat():
    try:
        with open(FICHIER_ETAT, "w", encoding="utf-8") as f:
            json.dump({
                "adherents_noms": st.session_state.adherents_noms,
                "mois_data": st.session_state.mois_data
            }, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")

def charger_etat():
    if 'adherents_noms' not in st.session_state:
        st.session_state.adherents_noms = []
    
    if 'mois_data' not in st.session_state:
        st.session_state.mois_data = {}
        for mois in ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", 
                     "Août", "Septembre", "Octobre", "Novembre", "Décembre"]:
            st.session_state.mois_data[mois] = {
                "nom_bouteille": "",
                "prix_achat": 0.0,
                "prix_sample": 0.0,
                "adherents": {}
            }

    if os.path.exists(FICHIER_ETAT):
        try:
            with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.adherents_noms = data.get("adherents_noms", [])
                st.session_state.mois_data = data.get("mois_data", st.session_state.mois_data)
        except: pass

# --- INITIALISATION ---
charger_etat()

# --- HEADER & SIDEBAR ---
with st.sidebar:
    st.markdown("<div style='text-align: center; font-size: 80px;'>🥃</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Gestion Rhum</h2>", unsafe_allow_html=T
