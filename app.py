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
    .stApp {
        background-color: #FAFAF5;
    }
    
    /* Sidebar : Beige un peu plus soutenu (Sable) */
    section[data-testid="stSidebar"] {
        background-color: #F0E6D2;
        border-right: 1px solid #D7CCC8;
    }
    
    /* Titres : Marron Chocolat Foncé (Très lisible) */
    h1, h2, h3 {
        color: #3E2723 !important;
        font-family: 'Helvetica', 'Arial', sans-serif;
        font-weight: 700;
    }
    
    /* Texte normal : Noir doux */
    p, label, .stMarkdown {
        color: #2D241E !important;
    }
    
    /* Boutons : Marron Cuir */
    .stButton > button {
        background-color: #8D6E63;
        color: white !important;
        border: 1px solid #5D4037;
        border-radius: 6px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #6D4C41;
        border-color: #3E2723;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Métriques (Chiffres) : Couleur Cognac */
    [data-testid="stMetricValue"] {
        color: #A1887F !important;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #5D4037 !important;
    }
    
    /* Boîtes de succès/info */
    .stSuccess, .stInfo {
        background-color: #EFEBE9;
        border-left: 5px solid #8D6E63;
        color: #3E2723;
    }
    
    /* Tableau (Data Editor) */
    [data-testid="stDataFrame"] {
        border: 1px solid #D7CCC8;
        border-radius: 5px;
    }
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
    # Logo Rhum (emoji géant pour l'exemple, remplaçable par ton image)
    st.markdown("<div style='text-align: center; font-size: 80px;'>🥃</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Gestion Rhum</h2>", unsafe_allow_html=True)
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
    if st.button("📦 Exporter Année Complète (ZIP)"):
        zip_buffer = io.BytesIO()
        has_data = False
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for mois, data in st.session_state.mois_data.items():
                lignes_export = []
                # Calculs
                total_samples = 0
                total_payes = 0
                
                for nom, d in data["adherents"].items():
                    if d["qte"] > 0:
                        total_samples += d["qte"]
                        if d["paye"]: total_payes += d["qte"]
                        lignes_export.append([retirer_accents(nom), d["qte"], "OUI" if d["paye"] else "NON"])
                
                if lignes_export:
                    has_data = True
                    csv_content = []
                    csv_content.append(f"Mois;{retirer_accents(mois)}")
                    csv_content.append(f"Bouteille;{retirer_accents(data['nom_bouteille'])}")
                    
                    ca = total_samples * data["prix_sample"]
                    marge = ca - data["prix_achat"]
                    taux = (marge / ca * 100) if ca > 0 else 0
                    
                    csv_content.append(f"Prix Achat;{data['prix_achat']};Prix Sample;{data['prix_sample']}")
                    csv_content.append(f"Commandes;{total_samples};Payes;{total_payes}")
                    csv_content.append(f"Marge;{marge:.2f};Rentabilite;{taux:.1f}%")
                    csv_content.append("")
                    csv_content.append("Nom;Samples;Paye")
                    
                    for l in lignes_export:
                        csv_content.append(f"{l[0]};{l[1]};{l[2]}")
                    
                    # Correction ici: utilisation de \n pour le saut de ligne
                    zip_file.writestr(f"{retirer_accents(mois)}.csv", "\n".join(csv_content))
        
        if has_data:
            st.download_button(
                label="⬇️ Télécharger ZIP",
                data=zip_buffer.getvalue(),
                file_name=f"Rhum_Annee_{datetime.now().strftime('%Y')}.zip",
                mime="application/zip"
            )
        else:
            st.warning("Aucune donnée à exporter.")

    st.markdown("---")
    
    # REMISE A ZERO (DANGER ZONE)
    st.subheader("⚠️ Zone Danger")
    if st.button("🧨 Nouvelle Année (Reset Total)"):
        st.session_state.mois_data = {} # Reset data mois
        for mois in ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", 
                     "Août", "Septembre", "Octobre", "Novembre", "Décembre"]:
            st.session_state.mois_data[mois] = {
                "nom_bouteille": "", "prix_achat": 0.0, "prix_sample": 0.0, "adherents": {}
            }
        
        sauvegarder_etat()
        st.rerun()

# --- CORPS PRINCIPAL ---
st.title("🥃 Gestion Samples - Association Rhum")

mois_list = ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", 
             "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

tabs = st.tabs(mois_list)

for idx, mois in enumerate(mois_list):
    with tabs[idx]:
        st.header(f"📅 {mois}")
        
        # INFOS BOUTEILLE
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                nom_b = st.text_input("Nom Bouteille", 
                                    value=st.session_state.mois_data[mois]["nom_bouteille"],
                                    key=f"nom_{mois}")
                st.session_state.mois_data[mois]["nom_bouteille"] = nom_b
            
            with col2:
                pa = st.number_input("Prix Achat (€)", 
                                   value=st.session_state.mois_data[mois]["prix_achat"],
                                   min_value=0.0, step=0.5, key=f"pa_{mois}")
                st.session_state.mois_data[mois]["prix_achat"] = pa
            
            with col3:
                ps = st.number_input("Prix Sample (€)", 
                                   value=st.session_state.mois_data[mois]["prix_sample"],
                                   min_value=0.0, step=0.5, key=f"ps_{mois}")
                st.session_state.mois_data[mois]["prix_sample"] = ps

        st.markdown("---")

        # TABLEAU COMMANDES
        if not st.session_state.adherents_noms:
            st.info("👈 Veuillez importer les adhérents dans le menu de gauche.")
        else:
            # Préparation data
            data_list = []
            for nom in st.session_state.adherents_noms:
                d = st.session_state.mois_data[mois]["adherents"].get(nom, {"qte": 0, "paye": False})
                data_list.append({"Nom": nom, "Samples": d["qte"], "Payé": d["paye"]})
            
            df = pd.DataFrame(data_list)
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "Nom": st.column_config.TextColumn("Adhérent", disabled=True),
                    "Samples": st.column_config.NumberColumn("Quantité (3cl)", min_value=0, max_value=10, step=1),
                    "Payé": st.column_config.CheckboxColumn("Payé ?")
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_{mois}",
                height=400
            )
            
            # Sauvegarde changements
            has_changes = False
            for index, row in edited_df.iterrows():
                nom = row["Nom"]
                old = st.session_state.mois_data[mois]["adherents"].get(nom, {"qte": 0, "paye": False})
                if old["qte"] != row["Samples"] or old["paye"] != row["Payé"]:
                    st.session_state.mois_data[mois]["adherents"][nom] = {
                        "qte": int(row["Samples"]),
                        "paye": bool(row["Payé"])
                    }
                    has_changes = True
            
            if has_changes: sauvegarder_etat()

            # TOTAUX
            total_samples = sum(d["qte"] for d in st.session_state.mois_data[mois]["adherents"].values())
            total_payes = sum(d["qte"] for d in st.session_state.mois_data[mois]["adherents"].values() if d["paye"])
            
            ca = total_samples * ps
            marge = ca - pa
            taux = (marge / ca * 100) if ca > 0 else 0
            
            st.markdown("### 📊 Bilan du Mois")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Commandés", f"{total_samples} / 20")
            m2.metric("Payés", f"{total_payes} / {total_samples}")
            m3.metric("Marge", f"{marge:.2f} €")
            m4.metric("Rentabilité", f"{taux:.1f} %")
            
            # EXPORT MOIS
            if st.button(f"📥 Exporter {mois} (CSV)", key=f"btn_{mois}"):
                lignes = []
                for nom, d in st.session_state.mois_data[mois]["adherents"].items():
                    if d["qte"] > 0:
                        lignes.append(f"{retirer_accents(nom)};{d['qte']};{'OUI' if d['paye'] else 'NON'}")
                
                if lignes:
                    csv_txt = f"Mois;{retirer_accents(mois)}\nBouteille;{retirer_accents(nom_b)}\n"
                    csv_txt += f"Marge;{marge:.2f};Rentabilite;{taux:.1f}%\n\nNom;Samples;Paye\n"
                    csv_txt += "\n".join(lignes)
                    
                    st.download_button(
                        label="⬇️ Télécharger CSV",
                        data=csv_txt,
                        file_name=f"Rhum_{retirer_accents(mois)}.csv",
                        mime="text/csv"
                    )
