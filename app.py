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
                            deg_content.append(f"{retirer_accents(nom)};{'OUI' if p_data['repas'] else 'NON'};{'OUI' if p_data['paye'] else 'NON'}")
                    
                    if dg_data["invites"]:
                        deg_content.append("")
                        deg_content.append("INVITES")
                        for inv in dg_data["invites"]:
                            deg_content.append(f"{retirer_accents(inv['nom'])};{'OUI' if inv['repas'] else 'NON'};{'OUI' if inv['paye'] else 'NON'}")
                    
                    zip_file.writestr(f"Degustation_{retirer_accents(mois_deg)}.csv", "\n".join(deg_content))
        
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
    
    # REMISE A ZERO
    st.subheader("⚠️ Zone Danger")
    
    # Bouton Report Solde
    if st.button("📅 Reporter Solde N+1", help="Copie la trésorerie actuelle comme solde de départ pour l'année suivante"):
        st.session_state.solde_depart = total_caisse
        sauvegarder_etat()
        st.success(f"✅ Solde de {total_caisse:.2f} € reporté !")
        st.rerun()
    
    if st.button("🧨 Nouvelle Année (Reset Total)"):
        st.session_state.mois_data = {} 
        for mois in ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", 
                     "Août", "Septembre", "Octobre", "Novembre", "Décembre"]:
            st.session_state.mois_data[mois] = {
                "nom_bouteille": "", "prix_achat": 0.0, "prix_sample": 0.0, "adherents": {}
            }
        st.session_state.adhesions = {}
        st.session_state.degustations = {
            "Mars": {"participants": {}, "invites": [], "prix_bouteilles": 0.0},
            "Juin": {"participants": {}, "invites": [], "prix_bouteilles": 0.0},
            "Septembre": {"participants": {}, "invites": [], "prix_bouteilles": 0.0},
            "Décembre": {"participants": {}, "invites": [], "prix_bouteilles": 0.0}
        }
        # NE PAS réinitialiser solde_depart ici (conservé volontairement)
        sauvegarder_etat()
        st.rerun()

# --- CORPS PRINCIPAL ---
st.title("🥃 Gestion Association Rhum")

# Création des onglets principaux
tab_adhesions, tab_degustations, *tabs_samples = st.tabs(
    ["💳 Adhésions", "🍽️ Dégustations"] + 
    ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
)

# ============================================
# ONGLET ADHESIONS
# ============================================
with tab_adhesions:
    st.header("💳 Adhésions Annuelles (35€)")
    
    if not st.session_state.adherents_noms:
        st.info("👈 Veuillez importer les adhérents dans le menu de gauche.")
    else:
        # Préparation données
        data_adhesions = []
        for nom in st.session_state.adherents_noms:
            # Vérifier si gratuit à vie
            nom_upper = nom.split()[0].upper()
            gratuit = nom_upper in GRATUITS_VIE
            
            paye = st.session_state.adhesions.get(nom, False)
            
            data_adhesions.append({
                "Nom": nom,
                "Statut": "🎁 GRATUIT" if gratuit else "Payant",
                "Payé": paye if not gratuit else True
            })
        
        df_adh = pd.DataFrame(data_adhesions)
        
        edited_adh = st.data_editor(
            df_adh,
            column_config={
                "Nom": st.column_config.TextColumn("Adhérent", disabled=True),
                "Statut": st.column_config.TextColumn("Statut", disabled=True),
                "Payé": st.column_config.CheckboxColumn("Cotisation Réglée ?")
            },
            hide_index=True,
            use_container_width=True,
            key="editor_adhesions",
            height=500
        )
        
        # Sauvegarde
        has_changes = False
        for index, row in edited_adh.iterrows():
            nom = row["Nom"]
            nom_upper = nom.split()[0].upper()
            
            # Ne pas modifier les gratuits
            if nom_upper in GRATUITS_VIE:
                continue
            
            old = st.session_state.adhesions.get(nom, False)
            if old != row["Payé"]:
                st.session_state.adhesions[nom] = bool(row["Payé"])
                has_changes = True
        
        if has_changes: sauvegarder_etat()
        
        # Bilan
        st.markdown("---")
        st.markdown("### 📊 Bilan Adhésions")
        
        total_adherents = len(st.session_state.adherents_noms)
        nb_gratuits = sum(1 for nom in st.session_state.adherents_noms if nom.split()[0].upper() in GRATUITS_VIE)
        nb_payants = total_adherents - nb_gratuits
        nb_payes = sum(1 for nom, paye in st.session_state.adhesions.items() if paye)
        
        ca_adhesions = nb_payes * 35
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Adhérents", total_adherents)
        c2.metric("Payants", f"{nb_payes} / {nb_payants}")
        c3.metric("Gratuits à Vie", nb_gratuits)
        c4.metric("Encaissé", f"{ca_adhesions} €")

# ============================================
# ONGLET DEGUSTATIONS
# ============================================
with tab_degustations:
    st.header("🍽️ Dégustations Annuelles (35€/pers)")
    
    if not st.session_state.adherents_noms:
        st.info("👈 Veuillez importer les adhérents dans le menu de gauche.")
    else:
        tabs_deg = st.tabs(["Mars", "Juin", "Septembre", "Décembre"])
        
        for idx_deg, mois_deg in enumerate(["Mars", "Juin", "Septembre", "Décembre"]):
            with tabs_deg[idx_deg]:
                st.subheader(f"📅 Dégustation {mois_deg}")
                
                # COÛTS DE LA DÉGUSTATION
                st.markdown("#### 💶 Coûts de la Dégustation")
                col_cout1, col_cout2 = st.columns(2)
                
                with col_cout1:
                    st.metric("Prix Repas Unitaire", "15 €", help="Coût fixe par personne qui mange")
                
                with col_cout2:
                    prix_bouteilles = st.number_input(
                        "Prix Total des 5 Bouteilles (€)",
                        value=st.session_state.degustations[mois_deg].get("prix_bouteilles", 0.0),
                        min_value=0.0,
                        step=5.0,
                        key=f"prix_bout_{mois_deg}"
                    )
                    st.session_state.degustations[mois_deg]["prix_bouteilles"] = prix_bouteilles
                    sauvegarder_etat()
                
                st.markdown("---")
                
                # Adhérents participants
                st.markdown("#### 👥 Adhérents")
                data_deg = []
                for nom in st.session_state.adherents_noms:
                    p_data = st.session_state.degustations[mois_deg]["participants"].get(nom, {"inscrit": False, "repas": False, "paye": False})
                    data_deg.append({
                        "Nom": nom,
                        "Inscrit": p_data.get("inscrit", False),
                        "Repas": p_data.get("repas", False),
                        "Payé": p_data.get("paye", False)
                    })
                
                df_deg = pd.DataFrame(data_deg)
                
                edited_deg = st.data_editor(
                    df_deg,
                    column_config={
                        "Nom": st.column_config.TextColumn("Adhérent", disabled=True),
                        "Inscrit": st.column_config.CheckboxColumn("Inscrit ?"),
                        "Repas": st.column_config.CheckboxColumn("Repas ?"),
                        "Payé": st.column_config.CheckboxColumn("Payé ?")
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_deg_{mois_deg}",
                    height=300
                )
                
                # Sauvegarde participants
                has_changes_deg = False
                for index, row in edited_deg.iterrows():
                    nom = row["Nom"]
                    old = st.session_state.degustations[mois_deg]["participants"].get(nom, {"inscrit": False, "repas": False, "paye": False})
                    
                    new_data = {
                        "inscrit": bool(row["Inscrit"]),
                        "repas": bool(row["Repas"]),
                        "paye": bool(row["Payé"])
                    }
                    
                    if old != new_data:
                        st.session_state.degustations[mois_deg]["participants"][nom] = new_data
                        has_changes_deg = True
                
                if has_changes_deg: sauvegarder_etat()
                
                st.markdown("---")
                
                # Invités
                st.markdown("#### 🎫 Invités Externes")
                
                # Ajout invité
                col_inv1, col_inv2 = st.columns([3, 1])
                with col_inv1:
                    new_invite = st.text_input("Nom de l'invité", key=f"new_inv_{mois_deg}")
                with col_inv2:
                    if st.button("➕ Ajouter", key=f"btn_inv_{mois_deg}"):
                        if new_invite.strip():
                            st.session_state.degustations[mois_deg]["invites"].append({
                                "nom": new_invite.strip(),
                                "repas": False,
                                "paye": False
                            })
                            sauvegarder_etat()
                            st.rerun()
                
                # Liste invités
                if st.session_state.degustations[mois_deg]["invites"]:
                    data_invites = []
                    for i, inv in enumerate(st.session_state.degustations[mois_deg]["invites"]):
                        data_invites.append({
                            "Index": i,
                            "Nom": inv["nom"],
                            "Repas": inv["repas"],
                            "Payé": inv["paye"]
                        })
                    
                    df_invites = pd.DataFrame(data_invites)
                    
                    edited_invites = st.data_editor(
                        df_invites,
                        column_config={
                            "Index": st.column_config.NumberColumn("ID", disabled=True),
                            "Nom": st.column_config.TextColumn("Nom Invité"),
                            "Repas": st.column_config.CheckboxColumn("Repas ?"),
                            "Payé": st.column_config.CheckboxColumn("Payé ?")
                        },
                        hide_index=True,
                        use_container_width=True,
                        key=f"editor_invites_{mois_deg}",
                        height=200
                    )
                    
                    # Sauvegarde invités
                    for index, row in edited_invites.iterrows():
                        i = int(row["Index"])
                        st.session_state.degustations[mois_deg]["invites"][i] = {
                            "nom": row["Nom"],
                            "repas": bool(row["Repas"]),
                            "paye": bool(row["Payé"])
                        }
                    
                    sauvegarder_etat()
                    
                    # Bouton supprimer invité
                    col_del1, col_del2 = st.columns([3, 1])
                    with col_del1:
                        idx_to_del = st.selectbox(
                            "Supprimer un invité",
                            options=range(len(st.session_state.degustations[mois_deg]["invites"])),
                            format_func=lambda x: st.session_state.degustations[mois_deg]["invites"][x]["nom"],
                            key=f"del_inv_{mois_deg}"
                        )
                    with col_del2:
                        if st.button("🗑️ Supprimer", key=f"btn_del_{mois_deg}"):
                            st.session_state.degustations[mois_deg]["invites"].pop(idx_to_del)
                            sauvegarder_etat()
                            st.rerun()
                
                st.markdown("---")
                
                # BILAN DÉTAILLÉ DE LA DÉGUSTATION
                st.markdown("### 📊 Bilan de la Dégustation")
                
                # Comptage participants
                nb_inscrits_adh = sum(1 for p in st.session_state.degustations[mois_deg]["participants"].values() if p.get("inscrit", False))
                nb_invites = len(st.session_state.degustations[mois_deg]["invites"])
                total_participants = nb_inscrits_adh + nb_invites
                
                # Comptage repas
                nb_repas_adh = sum(1 for p in st.session_state.degustations[mois_deg]["participants"].values() if p.get("inscrit", False) and p["repas"])
                nb_repas_inv = sum(1 for inv in st.session_state.degustations[mois_deg]["invites"] if inv["repas"])
                total_repas = nb_repas_adh + nb_repas_inv
                
                # Comptage paiements
                nb_payes_adh = sum(1 for p in st.session_state.degustations[mois_deg]["participants"].values() if p.get("inscrit", False) and p["paye"])
                nb_payes_inv = sum(1 for inv in st.session_state.degustations[mois_deg]["invites"] if inv["paye"])
                nb_payes_total = nb_payes_adh + nb_payes_inv
                
                # CALCULS FINANCIERS
                ca_theorique = total_participants * 35
                ca_reel = nb_payes_total * 35
                
                cout_repas_total = total_repas * 15
                cout_bouteilles = st.session_state.degustations[mois_deg].get("prix_bouteilles", 0.0)
                cout_total = cout_repas_total + cout_bouteilles
                
                marge_theorique = ca_theorique - cout_total
                marge_reelle = ca_reel - cout_total
                
                delta_marge_deg = marge_reelle - marge_theorique
                
                # AFFICHAGE MÉTRIQUES
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Participants", f"{total_participants}", help=f"Adhérents: {nb_inscrits_adh} | Invités: {nb_invites}")
                d2.metric("Repas", total_repas)
                d3.metric("Payés", f"{nb_payes_total} / {total_participants}")
                d4.metric("CA Encaissé", f"{ca_reel} €")
                
                st.markdown("---")
                
                # Détail des coûts et marges
                col_fin1, col_fin2, col_fin3 = st.columns(3)
                
                with col_fin1:
                    st.markdown("**💸 COÛTS**")
                    st.metric("Repas", f"{cout_repas_total} €", help=f"{total_repas} repas × 15€")
                    st.metric("Bouteilles", f"{cout_bouteilles} €", help="5 bouteilles à déguster")
                    st.metric("TOTAL Coûts", f"{cout_total} €")
                
                with col_fin2:
                    st.markdown("**💰 MARGES**")
                    st.metric(
                        "Marge Réelle",
                        f"{marge_reelle:.2f} €",
                        delta=f"{delta_marge_deg:.2f} € vs Théorique"
                    )
                    st.metric("Marge Potentielle", f"{marge_theorique:.2f} €")
                
                with col_fin3:
                    st.markdown("**📈 RENTABILITÉ**")
                    renta_reelle = (marge_reelle / ca_reel * 100) if ca_reel > 0 else 0
                    st.metric("Rentabilité", f"{renta_reelle:.1f} %")
                    
                    if marge_reelle < 0:
                        st.error("⚠️ DÉFICIT")
                    elif nb_payes_total < total_participants:
                        st.warning(f"⚠️ {total_participants - nb_payes_total} impayés")
                    else:
                        st.success("✅ OK")

# ============================================
# ONGLETS SAMPLES (Février à Décembre)
# ============================================
mois_list = ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

for idx, mois in enumerate(mois_list):
    with tabs_samples[idx]:
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
                pa = st.number_input("Prix Achat Bouteille (€)", 
                                   value=st.session_state.mois_data[mois]["prix_achat"],
                                   min_value=0.0, step=0.5, key=f"pa_{mois}")
                st.session_state.mois_data[mois]["prix_achat"] = pa
            
            with col3:
                ps = st.number_input("Prix Sample Unit. (€)", 
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

            # --- CALCULS DE TRÉSORERIE ---
            total_samples = sum(d["qte"] for d in st.session_state.mois_data[mois]["adherents"].values())
            total_payes = sum(d["qte"] for d in st.session_state.mois_data[mois]["adherents"].values() if d["paye"])
            
            # CA
            ca_theorique = total_samples * ps
            ca_reel = total_payes * ps
            
            # Marges
            marge_theorique = ca_theorique - pa
            marge_reelle = ca_reel - pa
            
            delta_marge = marge_reelle - marge_theorique
            
            st.markdown("### 📊 Trésorerie & Rentabilité")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric(
                label="📦 Samples Payés",
                value=f"{total_payes} / {total_samples}",
                delta=f"{total_samples - total_payes} en attente",
                delta_color="inverse"
            )
            
            col2.metric(
                label="💰 Caisse Réelle (Net)",
                value=f"{marge_reelle:.2f} €",
                delta=f"{delta_marge:.2f} € vs Potentiel",
                help="Bénéfice net actuel (CA perçu - Prix Bouteille)"
            )
            
            col3.metric(
                label="🏆 Bénéfice Potentiel",
                value=f"{marge_theorique:.2f} €"
            )
            
            pct_rembourse = (ca_reel / pa * 100) if pa > 0 else 0
            
            col4.metric(
                label="📉 Bouteille Remboursée",
                value=f"{pct_rembourse:.0f} %",
                delta="Déficitaire" if marge_reelle < 0 else "Rentable",
                delta_color="normal"
            )

            if marge_reelle < 0:
                st.error(f"⚠️ DÉFICIT : Il manque encore {-marge_reelle:.2f} € pour rembourser la bouteille !")
            elif marge_reelle >= 0 and total_payes < total_samples:
                st.warning(f"⚠️ Bouteille remboursée, mais {total_samples - total_payes} samples ne sont pas encore payés.")
            elif marge_reelle > 0 and total_payes == total_samples and total_samples > 0:
                st.success("✅ PARFAIT : Bouteille rentabilisée et tous les comptes sont à jour !")
            
            st.markdown("---")

            # EXPORT MOIS
            if st.button(f"📥 Exporter {mois} (CSV)", key=f"btn_{mois}"):
                lignes = []
                for nom, d in st.session_state.mois_data[mois]["adherents"].items():
                    if d["qte"] > 0:
                        lignes.append(f"{retirer_accents(nom)};{d['qte']};{'OUI' if d['paye'] else 'NON'}")
                
                if lignes:
                    csv_txt = f"Mois;{retirer_accents(mois)}\nBouteille;{retirer_accents(nom_b)}\n"
                    csv_txt += f"Marge;{marge_theorique:.2f};MargeReelle;{marge_reelle:.2f}\n\nNom;Samples;Paye\n"
                    csv_txt += "\n".join(lignes)
                    
                    st.download_button(
                        label="⬇️ Télécharger CSV",
                        data=csv_txt,
                        file_name=f"Rhum_{retirer_accents(mois)}.csv",
                        mime="text/csv"
                    )
