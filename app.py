import streamlit as st
import pandas as pd
import csv
import json
import unicodedata
from datetime import datetime
import os

# Configuration de la page
st.set_page_config(
    page_title="Gestion Samples Rhum",
    page_icon="🥃",
    layout="wide"
)

FICHIER_ETAT = "rhum_etat.json"

# Fonction pour retirer les accents
def retirer_accents(texte):
    if not isinstance(texte, str):
        return texte
    try:
        nfkd_form = unicodedata.normalize('NFKD', texte)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    except:
        return texte

# Initialisation du state
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

# Charger l'état sauvegardé
def charger_etat():
    if os.path.exists(FICHIER_ETAT):
        try:
            with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.adherents_noms = data.get("adherents_noms", [])
                st.session_state.mois_data = data.get("mois_data", st.session_state.mois_data)
        except:
            pass

# Sauvegarder l'état
def sauvegarder_etat():
    try:
        with open(FICHIER_ETAT, "w", encoding="utf-8") as f:
            json.dump({
                "adherents_noms": st.session_state.adherents_noms,
                "mois_data": st.session_state.mois_data
            }, f, ensure_ascii=False, indent=4)
    except:
        pass

# Charger au démarrage
charger_etat()

# En-tête
st.title("🥃 Gestion Samples Rhum - Association")
st.markdown("---")

# Zone d'import des adhérents
col1, col2 = st.columns([3, 1])
with col1:
    uploaded_file = st.file_uploader(
        "📥 Importer la liste des adhérents (CSV avec colonnes Nom;Prénom)",
        type=['csv'],
        help="Format : Nom;Prénom (première ligne = en-tête à ignorer)"
    )
    
    if uploaded_file is not None:
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
            st.success(f"✅ {len(st.session_state.adherents_noms)} adhérents importés avec succès !")
            sauvegarder_etat()
        except Exception as e:
            st.error(f"❌ Erreur lors de l'import : {e}")

with col2:
    st.metric("👥 Adhérents chargés", len(st.session_state.adherents_noms))

st.markdown("---")

# Onglets par mois
mois_list = ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", 
             "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

tabs = st.tabs(mois_list)

for idx, mois in enumerate(mois_list):
    with tabs[idx]:
        st.header(f"📅 {mois}")
        
        # Infos bouteille
        col1, col2, col3 = st.columns(3)
        with col1:
            nom_b = st.text_input(
                "Nom de la bouteille",
                value=st.session_state.mois_data[mois]["nom_bouteille"],
                key=f"nom_{mois}"
            )
            st.session_state.mois_data[mois]["nom_bouteille"] = nom_b
        
        with col2:
            prix_achat = st.number_input(
                "Prix achat (€)",
                value=st.session_state.mois_data[mois]["prix_achat"],
                min_value=0.0,
                step=0.5,
                key=f"prix_achat_{mois}"
            )
            st.session_state.mois_data[mois]["prix_achat"] = prix_achat
        
        with col3:
            prix_sample = st.number_input(
                "Prix sample (€)",
                value=st.session_state.mois_data[mois]["prix_sample"],
                min_value=0.0,
                step=0.5,
                key=f"prix_sample_{mois}"
            )
            st.session_state.mois_data[mois]["prix_sample"] = prix_sample
        
        st.markdown("---")
        
        # Liste des adhérents
        if not st.session_state.adherents_noms:
            st.warning("⚠️ Aucun adhérent chargé. Importez d'abord le fichier CSV.")
        else:
            st.subheader("🍹 Commandes de samples (3cl)")
            
            # Affichage sous forme de tableau éditable
            data_rows = []
            for nom in st.session_state.adherents_noms:
                current_data = st.session_state.mois_data[mois]["adherents"].get(nom, {"qte": 0, "paye": False})
                data_rows.append({
                    "Nom": nom,
                    "Samples": current_data["qte"],
                    "Payé": current_data["paye"]
                })
            
            df = pd.DataFrame(data_rows)
            
            # Utiliser st.data_editor pour l'édition
            edited_df = st.data_editor(
                df,
                column_config={
                    "Nom": st.column_config.TextColumn("Nom", disabled=True, width="large"),
                    "Samples": st.column_config.NumberColumn(
                        "Samples (3cl)",
                        min_value=0,
                        max_value=5,
                        step=1,
                        width="small"
                    ),
                    "Payé": st.column_config.CheckboxColumn("Payé", width="small")
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_{mois}"
            )
            
            # Mettre à jour session_state
            for _, row in edited_df.iterrows():
                nom = row["Nom"]
                st.session_state.mois_data[mois]["adherents"][nom] = {
                    "qte": int(row["Samples"]),
                    "paye": bool(row["Payé"])
                }
            
            # Calculs
            total_samples = sum([d["qte"] for d in st.session_state.mois_data[mois]["adherents"].values()])
            total_payes = sum([d["qte"] for d in st.session_state.mois_data[mois]["adherents"].values() if d["paye"]])
            ca = total_samples * prix_sample
            marge = ca - prix_achat
            taux = (marge / ca * 100) if ca > 0 else 0
            
            # Affichage des totaux
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📦 Commandés", f"{total_samples} / 20")
            col2.metric("💰 Payés", f"{total_payes} / {total_samples}", delta=None)
            col3.metric("💵 Marge", f"{marge:.2f} €")
            col4.metric("📈 Rentabilité", f"{taux:.1f} %")
            
            # Bouton export
            st.markdown("---")
            if st.button(f"📥 Exporter {mois} en CSV", key=f"export_{mois}"):
                # Préparer les données
                lignes_export = []
                for nom, data in st.session_state.mois_data[mois]["adherents"].items():
                    if data["qte"] > 0:
                        lignes_export.append({
                            "Nom": retirer_accents(nom),
                            "Samples": data["qte"],
                            "Paye": "OUI" if data["paye"] else "NON"
                        })
                
                if lignes_export:
                    # Créer CSV
                    mois_clean = retirer_accents(mois)
                    nom_b_clean = retirer_accents(nom_b)
                    
                    csv_content = []
                    csv_content.append(f"Mois;{mois_clean}")
                    csv_content.append(f"Bouteille;{nom_b_clean}")
                    csv_content.append(f"Prix Achat;{prix_achat};Prix Sample;{prix_sample}")
                    csv_content.append(f"Samples Commandes;{total_samples};Samples Payes;{total_payes}")
                    csv_content.append(f"Marge;{marge:.2f};Rentabilite;{taux:.1f}%")
                    csv_content.append("")
                    csv_content.append("Nom;Samples (3cl);Paye")
                    
                    for ligne in lignes_export:
                        csv_content.append(f"{ligne['Nom']};{ligne['Samples']};{ligne['Paye']}")
                    
                    csv_string = "\n".join(csv_content)
                    
                    st.download_button(
                        label=f"💾 Télécharger Rhum_{mois_clean}_{datetime.now().strftime('%Y%m%d')}.csv",
                        data=csv_string.encode('utf-8'),
                        file_name=f"Rhum_{mois_clean}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("Aucune commande à exporter pour ce mois.")

# Bouton de sauvegarde globale
st.markdown("---")
if st.button("💾 Sauvegarder toutes les données", type="primary"):
    sauvegarder_etat()
    st.success("✅ Données sauvegardées avec succès !")
