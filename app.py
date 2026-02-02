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
    .stApp { background-color: #FAFAF5; }
    section[data-testid="stSidebar"] { background-color: #F0E6D2; border-right: 1px solid #D7CCC8; }
    h1, h2, h3 { color: #3E2723 !important; font-family: 'Helvetica', 'Arial', sans-serif; font-weight: 700; }
    p, label, .stMarkdown { color: #2D241E !important; }
    .stButton > button { background-color: #8D6E63; color: white !important; border: 1px solid #5D4037; border-radius: 6px; transition: all 0.2s; }
    .stButton > button:hover { background-color: #6D4C41; border-color: #3E2723; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    [data-testid="stMetricValue"] { color: #A1887F !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #5D4037 !important; }
    .stSuccess { background-color: #E8F5E9; border-left: 5px solid #4CAF50; color: #1B5E20; }
    .stWarning { background-color: #FFF3E0; border-left: 5px solid #FF9800; color: #E65100; }
    .stError { background-color: #FFEBEE; border-left: 5px solid #F44336; color: #B71C1C; }
    [data-testid="stDataFrame"] { border: 1px solid #D7CCC8; border-radius: 5px; }
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
    .solde-box {
        background-color: #E1F5FE;
        border: 2px solid #81D4FA;
        border-radius: 10px;
        padding: 15px;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .solde-title { color: #0277BD; font-weight: bold; font-size: 0.95em; margin-bottom: 8px; }
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
                "mois_data": st.session_state.mois_data,
                "adhesions": st.session_state.adhesions,
                "degustations": st.session_state.degustations,
                "solde_depart": st.session_state.solde_depart
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
    
    # Adhésions
    if 'adhesions' not in st.session_state:
        st.session_state.adhesions = {}
    
    # Dégustations
    if 'degustations' not in st.session_state:
        st.session_state.degustations = {
            "Mars": {"participants": {}, "invites": [], "prix_bouteilles": 0.0},
            "Juin": {"participants": {}, "invites": [], "prix_bouteilles": 0.0},
            "Septembre": {"participants": {}, "invites": [], "prix_bouteilles": 0.0},
            "Décembre": {"participants": {}, "invites": [], "prix_bouteilles": 0.0}
        }
    
    # Solde de départ
    if 'solde_depart' not in st.session_state:
        st.session_state.solde_depart = 0.0

    if os.path.exists(FICHIER_ETAT):
        try:
            with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.adherents_noms = data.get("adherents_noms", [])
                st.session_state.mois_data = data.get("mois_data", st.session_state.mois_data)
                st.session_state.adhesions = data.get("adhesions", {})
                st.session_state.solde_depart = data.get("solde_depart", 0.0)
                
                # Migration ancienne structure dégustations (si pas de prix_bouteilles)
                loaded_deg = data.get("degustations", st.session_state.degustations)
                for mois in ["Mars", "Juin", "Septembre", "Décembre"]:
                    if mois in loaded_deg:
                        if "prix_bouteilles" not in loaded_deg[mois]:
                            loaded_deg[mois]["prix_bouteilles"] = 0.0
                st.session_state.degustations = loaded_deg
        except: pass

# --- INITIALISATION ---
charger_etat()

# Liste des adhérents gratuits à vie
GRATUITS_VIE = ["BORDES", "JAUBERT"]

# --- HEADER & SIDEBAR ---
with st.sidebar:
    st.markdown("<div style='text-align: center; font-size: 80px;'>🥃</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Gestion Rhum</h2>", unsafe_allow_html=True)
    
    # --- SOLDE DE DÉPART ---
    st.markdown("""<div class="solde-box">
        <div class="solde-title">💰 SOLDE ANNÉE PRÉCÉDENTE</div>
    """, unsafe_allow_html=True)
    
    solde_depart = st.number_input(
        "Trésorerie Décembre N-1 (€)",
        value=st.session_state.solde_depart,
        min_value=0.0,
        step=10.0,
        help="Solde de clôture de l'année précédente",
        key="input_solde_depart"
    )
    
    if solde_depart != st.session_state.solde_depart:
        st.session_state.solde_depart = solde_depart
        sauvegarder_etat()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # --- BILAN ANNUEL DYNAMIQUE ---
    total_annuel_samples = 0
    total_annuel_marge_reelle = 0.0
    
    # Samples
    for m_data in st.session_state.mois_data.values():
        nb_s_total = sum(d["qte"] for d in m_data["adherents"].values())
        nb_s_payes = sum(d["qte"] for d in m_data["adherents"].values() if d["paye"])
        
        if nb_s_total > 0:
            ca_reel = nb_s_payes * m_data["prix_sample"]
            marge_mois = ca_reel - m_data["prix_achat"]
            total_annuel_samples += nb_s_total
            total_annuel_marge_reelle += marge_mois

    # Adhésions
    adhesions_encaissees = sum(35 for nom, paye in st.session_state.adhesions.items() if paye)
    
    # Dégustations (avec coûts repas et bouteilles)
    degust_encaissees = 0
    for dg_data in st.session_state.degustations.values():
        # CA
        ca_deg = sum(35 for p_data in dg_data["participants"].values() if p_data.get("inscrit", False) and p_data["paye"])
        ca_deg += sum(35 for inv_data in dg_data["invites"] if inv_data["paye"])
        
        # Coûts
        nb_repas = sum(1 for p in dg_data["participants"].values() if p.get("inscrit", False) and p["repas"])
        nb_repas += sum(1 for inv in dg_data["invites"] if inv["repas"])
        cout_repas = nb_repas * 15
        cout_bouteilles = dg_data.get("prix_bouteilles", 0.0)
        
        marge_deg = ca_deg - cout_repas - cout_bouteilles
        degust_encaissees += marge_deg

    # TRÉSORERIE TOTALE = Solde Départ + Activité Année
    activite_annee = total_annuel_marge_reelle + adhesions_encaissees + degust_encaissees
    total_caisse = st.session_state.solde_depart + activite_annee

    st.markdown(f"""<div class="bilan-box">
        <div class="bilan-title">💰 TRÉSORERIE TOTALE</div>
    """, unsafe_allow_html=True)
    
    col_b1, col_b2 = st.columns(2)
    col_b1.metric("Samples", f"{total_annuel_samples}")
    col_b2.metric("Caisse", f"{total_caisse:.0f} €", 
                  delta=f"+{activite_annee:.0f} € cette année" if activite_annee >= 0 else f"{activite_annee:.0f} € cette année",
                  help=f"Solde départ: {st.session_state.solde_depart:.0f} € + Activité: {activite_annee:.0f} €")
    
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # IMPORT
    uploaded_file = st.file_uploader("📥 Importer CSV Adhérents", type=['csv'])
    if uploaded_file:
        try:
            noms_importes = []
            content = uploaded_file.read().decode('utf-8').splitlines()
            reader = csv.reader(content, delimiter=';')
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    nom, prenom = row[0].strip(), row[1].strip()
                    if nom or prenom:
                        nom_fmt = f"{nom.upper()} {prenom.title()}"
                        noms_importes.append(nom_fmt)
            
            st.session_state.adherents_noms = sorted(list(set(noms_importes)))
            st.success(f"✅ {len(st.session_state.adherents_noms)} chargés")
            sauvegarder_etat()
        except Exception as e:
            st.error(f"Erreur: {e}")

    st.markdown("---")
    
    # EXPORT TOTAL (ZIP)
    if st.button("📦 Exporter Année (ZIP)"):
        zip_buffer = io.BytesIO()
        has_data = False
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # Export BILAN GÉNÉRAL
            bilan_content = [
                f"BILAN ANNUEL - Année {datetime.now().year}",
                "",
                f"Solde Départ (Décembre N-1);{st.session_state.solde_depart:.2f}",
                "",
                "=== ACTIVITÉ DE L'ANNÉE ===",
                f"Samples - Marge;{total_annuel_marge_reelle:.2f}",
                f"Adhésions;{adhesions_encaissees:.2f}",
                f"Dégustations - Marge;{degust_encaissees:.2f}",
                f"TOTAL Activité;{activite_annee:.2f}",
                "",
                f"=== TRÉSORERIE FINALE ===",
                f"Caisse Totale;{total_caisse:.2f}"
            ]
            zip_file.writestr("00_Bilan_Annuel.csv", "\n".join(bilan_content))
            has_data = True
            
            # Export samples
            for mois, data in st.session_state.mois_data.items():
                lignes_export = []
                total_samples = 0
                total_payes = 0
                
                for nom, d in data["adherents"].items():
                    if d["qte"] > 0:
                        total_samples += d["qte"]
                        if d["paye"]: total_payes += d["qte"]
                        lignes_export.append([retirer_accents(nom), d["qte"], "OUI" if d["paye"] else "NON"])
                
                if lignes_export:
                    csv_content = []
                    csv_content.append(f"Mois;{retirer_accents(mois)}")
                    csv_content.append(f"Bouteille;{retirer_accents(data['nom_bouteille'])}")
                    
                    ca = total_samples * data["prix_sample"]
                    marge = ca - data["prix_achat"]
                    
                    csv_content.append(f"Prix Achat;{data['prix_achat']};Prix Sample;{data['prix_sample']}")
                    csv_content.append(f"Commandes;{total_samples};Payes;{total_payes}")
                    csv_content.append(f"Marge;{marge:.2f}")
                    csv_content.append("")
                    csv_content.append("Nom;Samples;Paye")
                    
                    for l in lignes_export:
                        csv_content.append(f"{l[0]};{l[1]};{l[2]}")
                    
                    zip_file.writestr(f"Samples_{retirer_accents(mois)}.csv", "\n".join(csv_content))
            
            # Export adhésions
            if st.session_state.adhesions:
                adh_content = ["Nom;Paye"]
                for nom, paye in st.session_state.adhesions.items():
                    adh_content.append(f"{retirer_accents(nom)};{'OUI' if paye else 'NON'}")
                zip_file.writestr("Adhesions.csv", "\n".join(adh_content))
            
            # Export dégustations
            for mois_deg, dg_data in st.session_state.degustations.items():
                if dg_data["participants"] or dg_data["invites"]:
                    deg_content = [f"Degustation;{retirer_accents(mois_deg)}", ""]
                    deg_content.append(f"Prix Bouteilles;{dg_data.get('prix_bouteilles', 0.0)}")
                    deg_content.append("")
                    deg_content.append("Nom;Repas;Paye")
                    
                    for nom, p_data in dg_data["participants"].items():
                        if p_data.get("inscrit", False):
                            deg_content.append(f"
