import streamlit as st
import pandas as pd
import csv
import json
import unicodedata
import zipfile
import io
from datetime import datetime
import os
import hashlib

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Gestion Samples Rhum",
    page_icon="🥃",
    layout="wide",
    initial_sidebar_state="expanded"
)

FICHIER_ETAT = "rhum_etat.json"
FICHIER_MDP = "rhum_mdp.json"
CAPACITE_BOUTEILLE = 20  # Capacité théorique (20 samples de 3cl + marge)
RHUMOTHEQUE_PRELEVEMENT = 2  # Nombre de samples prélevés pour la rhumothèque (2x3cl)

# --- GESTION MOT DE PASSE ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def charger_mdp():
    if os.path.exists(FICHIER_MDP):
        try:
            with open(FICHIER_MDP, "r") as f:
                data = json.load(f)
                return data.get("password_hash", None)
        except: return None
    return None

def sauvegarder_mdp(password_hash):
    try:
        with open(FICHIER_MDP, "w") as f:
            json.dump({"password_hash": password_hash}, f)
    except Exception as e: st.error(f"Erreur sauvegarde MDP : {e}")

def verifier_authentification():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    mdp_hash = charger_mdp()
    
    if mdp_hash is None:
        st.info("⚠️ Aucun mot de passe. Veuillez en créer un.")
        with st.form("init_pwd"):
            p1 = st.text_input("Nouveau mot de passe", type="password")
            p2 = st.text_input("Confirmer", type="password")
            if st.form_submit_button("Créer"):
                if len(p1) < 4: st.error("Trop court (min 4 caractères)")
                elif p1 != p2: st.error("Les mots de passe ne correspondent pas")
                else:
                    sauvegarder_mdp(hash_password(p1))
                    st.success("✅ Créé ! Rechargez la page.")
                    st.rerun()
        return False

    if st.session_state.authenticated: return True

    st.markdown("## 🥃 Connexion Gestion Rhum")
    with st.form("login"):
        pwd = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("🔓 Connexion"):
            if hash_password(pwd) == mdp_hash:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("❌ Incorrect")
    
    with st.expander("⚠️ Réinitialiser le mot de passe"):
        if st.button("🗑️ Supprimer le mot de passe actuel"):
            try: os.remove(FICHIER_MDP)
            except: pass
            st.warning("Mot de passe supprimé. Rechargez la page.")
    return False

# --- THEME CSS ---
st.markdown("""
<style>
    .stApp { background-color: #FAFAF5; }
    section[data-testid="stSidebar"] { background-color: #F0E6D2; border-right: 1px solid #D7CCC8; }
    h1, h2, h3 { color: #3E2723 !important; font-family: 'Helvetica', 'Arial', sans-serif; font-weight: 700; }
    p, label, .stMarkdown { color: #2D241E !important; }
    .stButton > button { background-color: #8D6E63; color: white !important; border: 1px solid #5D4037; border-radius: 6px; }
    [data-testid="stMetricValue"] { color: #A1887F !important; font-weight: bold; }
    .bilan-box { background-color: #FFF8E1; border: 2px solid #FFECB3; border-radius: 10px; padding: 15px; margin: 20px 0; text-align: center; }
    .solde-box { background-color: #E1F5FE; border: 2px solid #81D4FA; border-radius: 10px; padding: 15px; margin: 10px 0 20px 0; }
    .rhumo-tag { background-color: #795548; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

if not verifier_authentification(): st.stop()

# --- FONCTIONS METIER ---
def retirer_accents(texte):
    if not isinstance(texte, str): return texte
    try: return "".join([c for c in unicodedata.normalize('NFKD', texte) if not unicodedata.combining(c)])
    except: return texte

def sauvegarder_etat():
    try:
        with open(FICHIER_ETAT, "w", encoding="utf-8") as f:
            json.dump({
                "adherents_noms": st.session_state.adherents_noms,
                "mois_data": st.session_state.mois_data,
                "adhesions": st.session_state.adhesions,
                "degustations": st.session_state.degustations,
                "solde_depart": st.session_state.solde_depart,
                "rhumotheque": st.session_state.rhumotheque
            }, f, ensure_ascii=False, indent=4)
    except Exception as e: st.error(f"Erreur sauvegarde : {e}")

def charger_etat():
    # Init par défaut
    if 'adherents_noms' not in st.session_state: st.session_state.adherents_noms = []
    if 'mois_data' not in st.session_state:
        st.session_state.mois_data = {m: {"nom_bouteille": "", "prix_achat": 0.0, "prix_sample": 0.0, "adherents": {}} 
                                      for m in ["Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]}
    if 'adhesions' not in st.session_state: st.session_state.adhesions = {}
    if 'degustations' not in st.session_state:
        st.session_state.degustations = {m: {"participants": {}, "invites": [], "prix_bouteilles": 0.0} 
                                         for m in ["Mars", "Juin", "Septembre", "Décembre"]}
    if 'solde_depart' not in st.session_state: st.session_state.solde_depart = 0.0
    if 'rhumotheque' not in st.session_state: st.session_state.rhumotheque = {}

    if os.path.exists(FICHIER_ETAT):
        try:
            with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.adherents_noms = data.get("adherents_noms", [])
                st.session_state.mois_data = data.get("mois_data", st.session_state.mois_data)
                st.session_state.adhesions = data.get("adhesions", {})
                st.session_state.solde_depart = data.get("solde_depart", 0.0)
                st.session_state.rhumotheque = data.get("rhumotheque", {})
                
                # Migration dégustations
                loaded_deg = data.get("degustations", st.session_state.degustations)
                for m in ["Mars", "Juin", "Septembre", "Décembre"]:
                    if m in loaded_deg and "prix_bouteilles" not in loaded_deg[m]:
                        loaded_deg[m]["prix_bouteilles"] = 0.0
                st.session_state.degustations = loaded_deg
        except: pass

charger_etat()
GRATUITS_VIE = ["BORDES", "JAUBERT"]

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<div style='text-align: center; font-size: 80px;'>🥃</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Gestion Rhum</h2>", unsafe_allow_html=True)
    if st.button("🚪 Déconnexion"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.markdown("---")
    
    # SOLDE DÉPART
    st.markdown('<div class="solde-box"><div class="solde-title">💰 SOLDE N-1</div>', unsafe_allow_html=True)
    solde = st.number_input("Trésorerie Décembre N-1 (€)", value=st.session_state.solde_depart, step=10.0, key="inp_solde")
    if solde != st.session_state.solde_depart:
        st.session_state.solde_depart = solde
        sauvegarder_etat()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # CALCUL BILAN GLOBAL
    tot_samples_marge = 0
    tot_samples_qty = 0
    for m_data in st.session_state.mois_data.values():
        qty = sum(d["qte"] for d in m_data["adherents"].values())
        payes = sum(d["qte"] for d in m_data["adherents"].values() if d["paye"])
        if qty > 0:
            ca_reel = payes * m_data["prix_sample"]
            tot_samples_marge += (ca_reel - m_data["prix_achat"])
            tot_samples_qty += qty

    tot_adh_encaisse = sum(35 for p in st.session_state.adhesions.values() if p)
    
    tot_deg_marge = 0
    for dg in st.session_state.degustations.values():
        ca = sum(35 for p in dg["participants"].values() if p.get("inscrit") and p.get("paye"))
        ca += sum(35 for i in dg["invites"] if i.get("paye"))
        cout_repas = 15 * (sum(1 for p in dg["participants"].values() if p.get("inscrit") and p.get("repas")) + sum(1 for i in dg["invites"] if i.get("repas")))
        tot_deg_marge += (ca - cout_repas - dg.get("prix_bouteilles", 0))

    activite = tot_samples_marge + tot_adh_encaisse + tot_deg_marge
    caisse_finale = st.session_state.solde_depart + activite

    st.markdown('<div class="bilan-box"><div class="bilan-title">💰 TRÉSORERIE TOTALE</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Samples", tot_samples_qty)
    c2.metric("Caisse", f"{caisse_finale:.0f} €", delta=f"{activite:+.0f} € (Activité)", help="Solde départ + Activité année")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # IMPORT
    up = st.file_uploader("📥 Import Adhérents (CSV)", type=['csv'])
    if up:
        try:
            lignes = up.read().decode('utf-8').splitlines()
            reader = csv.reader(lignes, delimiter=';')
            next(reader, None)
            noms = []
            for r in reader:
                if len(r) >= 2 and (r[0] or r[1]):
                    noms.append(f"{r[0].strip().upper()} {r[1].strip().title()}")
            st.session_state.adherents_noms = sorted(list(set(noms)))
            st.success(f"✅ {len(st.session_state.adherents_noms)} chargés")
            sauvegarder_etat()
        except Exception as e: st.error(f"Erreur: {e}")

    st.markdown("---")
    
    # EXPORT
    if st.button("📦 Exporter Année (ZIP)"):
        buf = io.BytesIO()
        has_data = False
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as z:
            # Bilan
            z.writestr("00_Bilan.csv", f"Solde Depart;{st.session_state.solde_depart}\nActivite;{activite}\nCaisse Finale;{caisse_finale}")
            has_data = True
            
            # Samples
            for m, d in st.session_state.mois_data.items():
                lines = [f"{retirer_accents(n)};{v['qte']};{'OUI' if v['paye'] else 'NON'}" for n, v in d["adherents"].items() if v['qte']>0]
                if lines:
                    content = f"Mois;{retirer_accents(m)}\nBouteille;{retirer_accents(d['nom_bouteille'])}\n\nNom;Samples;Paye\n" + "\n".join(lines)
                    z.writestr(f"Samples_{retirer_accents(m)}.csv", content)
            
            # Rhumotheque
            if st.session_state.rhumotheque:
                r_lines = ["Mois;Bouteille;En Stock;Valeur;Notes"]
                for m, rd in st.session_state.rhumotheque.items():
                    if rd.get("en_stock", False):
                        r_lines.append(f"{retirer_accents(m)};{retirer_accents(rd['nom'])};OUI;{rd['valeur']};{retirer_accents(rd.get('notes',''))}")
                z.writestr("Rhumotheque.csv", "\n".join(r_lines))

        st.download_button("⬇️ Télécharger ZIP", buf.getvalue(), f"Rhum_{datetime.now().year}.zip", "application/zip")

    st.markdown("---")
    if st.button("📅 Reporter Solde N+1"):
        st.session_state.solde_depart = caisse_finale
        sauvegarder_etat()
        st.success("✅ Solde reporté !")
        st.rerun()

    if st.button("🧨 Reset Année"):
        st.session_state.mois_data = {m: {"nom_bouteille": "", "prix_achat": 0.0, "prix_sample": 0.0, "adherents": {}} for m in st.session_state.mois_data}
        st.session_state.adhesions = {}
        st.session_state.degustations = {m: {"participants": {}, "invites": [], "prix_bouteilles": 0.0} for m in st.session_state.degustations}
        st.session_state.rhumotheque = {}
        sauvegarder_etat()
        st.rerun()

# --- CORPS PRINCIPAL ---
st.title("🥃 Gestion Association Rhum")

# Création des onglets
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💳 Adhésions", "🍽️ Dégustations", "🥃 Samples Mensuels", "📦 Stock Restant", "🏛️ Rhumothèque"])

# 1. ADHÉSIONS
with tab1:
    st.header("💳 Adhésions (35€)")
    if not st.session_state.adherents_noms: st.info("Importez des adhérents.")
    else:
        data = [{"Nom": n, "Gratuit": (n.split()[0].upper() in GRATUITS_VIE), "Payé": st.session_state.adhesions.get(n, False)} for n in st.session_state.adherents_noms]
        df = pd.DataFrame(data)
        edf = st.data_editor(df, column_config={"Nom": st.column_config.TextColumn(disabled=True), "Gratuit": st.column_config.CheckboxColumn(disabled=True), "Payé": st.column_config.CheckboxColumn("Réglé ?")}, hide_index=True, use_container_width=True, height=500)
        
        chg = False
        for _, r in edf.iterrows():
            if not r["Gratuit"] and st.session_state.adhesions.get(r["Nom"], False) != r["Payé"]:
                st.session_state.adhesions[r["Nom"]] = r["Payé"]
                chg = True
        if chg: sauvegarder_etat()

# 2. DÉGUSTATIONS
with tab2:
    st.header("🍽️ Dégustations")
    liste_mois_deg = ["Mars", "Juin", "Septembre", "Décembre"]
    onglets_visuels = st.tabs(liste_mois_deg)
    
    for i, mois_nom in enumerate(liste_mois_deg):
        with onglets_visuels[i]:
            d = st.session_state.degustations[mois_nom]
            c1, c2 = st.columns(2)
            c1.metric("Prix Repas", "15 €")
            pb = c2.number_input(f"Prix 5 Bouteilles ({mois_nom})", value=d.get("prix_bouteilles", 0.0), step=5.0, key=f"pb_{mois_nom}")
            if pb != d.get("prix_bouteilles", 0.0):
                d["prix_bouteilles"] = pb
                sauvegarder_etat()
            
            # Adhérents
            data_adh = [{"Nom": n, "Inscrit": d["participants"].get(n, {}).get("inscrit", False), "Repas": d["participants"].get(n, {}).get("repas", False), "Payé": d["participants"].get(n, {}).get("paye", False)} for n in st.session_state.adherents_noms]
            edf = st.data_editor(pd.DataFrame(data_adh), column_config={"Nom": st.column_config.TextColumn(disabled=True)}, hide_index=True, use_container_width=True, key=f"deg_adh_{mois_nom}", height=300)
            
            chg = False
            for _, r in edf.iterrows():
                old = d["participants"].get(r["Nom"], {})
                if old.get("inscrit") != r["Inscrit"] or old.get("repas") != r["Repas"] or old.get("paye") != r["Payé"]:
                    d["participants"][r["Nom"]] = {"inscrit": r["Inscrit"], "repas": r["Repas"], "paye": r["Payé"]}
                    chg = True
            if chg: sauvegarder_etat()

            # Invités
            c1, c2 = st.columns([3, 1])
            new_inv = c1.text_input("Invité", key=f"ni_{mois_nom}")
            if c2.button("Ajouter", key=f"bi_{mois_nom}") and new_inv:
                d["invites"].append({"nom": new_inv, "repas": False, "paye": False})
                sauvegarder_etat()
                st.rerun()
            
            if d["invites"]:
                inv_df = pd.DataFrame(d["invites"])
                inv_ed = st.data_editor(inv_df, hide_index=True, key=f"deg_inv_{mois_nom}")
                d["invites"] = inv_ed.to_dict('records')
                sauvegarder_etat()

# 3. SAMPLES
with tab3:
    st.header("🥃 Samples Mensuels")
    tms = st.tabs(list(st.session_state.mois_data.keys()))
    for i, (mois, data) in enumerate(st.session_state.mois_data.items()):
        with tms[i]:
            c1, c2, c3 = st.columns([2, 1, 1])
            nom_b = c1.text_input("Nom Bouteille", value=data["nom_bouteille"], key=f"nb_{mois}")
            pa = c2.number_input("Prix Achat", value=data["prix_achat"], step=1.0, key=f"pa_{mois}")
            ps = c3.number_input("Prix Sample", value=data["prix_sample"], step=0.5, key=f"ps_{mois}")
            
            if nom_b != data["nom_bouteille"] or pa != data["prix_achat"] or ps != data["prix_sample"]:
                data["nom_bouteille"] = nom_b
                data["prix_achat"] = pa
                data["prix_sample"] = ps
                
                # Mise à jour auto Rhumothèque
                if nom_b and mois not in st.session_state.rhumotheque:
                    st.session_state.rhumotheque[mois] = {
                        "nom": nom_b,
                        "en_stock": True,
                        "valeur": ps * RHUMOTHEQUE_PRELEVEMENT, 
                        "notes": ""
                    }
                elif nom_b and mois in st.session_state.rhumotheque:
                    st.session_state.rhumotheque[mois]["nom"] = nom_b
                    st.session_state.rhumotheque[mois]["valeur"] = ps * RHUMOTHEQUE_PRELEVEMENT
                
                sauvegarder_etat()
                st.rerun()

            # Tableau
            if st.session_state.adherents_noms:
                rows = [{"Nom": n, "Qté": data["adherents"].get(n, {"qte":0})["qte"], "Payé": data["adherents"].get(n, {"paye":False})["paye"]} for n in st.session_state.adherents_noms]
                edf = st.data_editor(pd.DataFrame(rows), column_config={"Nom": st.column_config.TextColumn(disabled=True), "Qté": st.column_config.NumberColumn(min_value=0, max_value=10), "Payé": st.column_config.CheckboxColumn()}, hide_index=True, use_container_width=True, key=f"s_{mois}", height=400)
                
                chg = False
                for _, r in edf.iterrows():
                    d = data["adherents"].get(r["Nom"], {"qte":0, "paye":False})
                    if d["qte"] != r["Qté"] or d["paye"] != r["Payé"]:
                        data["adherents"][r["Nom"]] = {"qte": r["Qté"], "paye": r["Payé"]}
                        chg = True
                if chg: sauvegarder_etat()
            
            # KPI du mois
            total_samples = sum(d["qte"] for d in data["adherents"].values())
            total_payes = sum(d["qte"] for d in data["adherents"].values() if d["paye"])
            ca_reel = total_payes * ps
            marge_reelle = ca_reel - pa
            c1, c2, c3 = st.columns(3)
            c1.metric("Payés / Commandés", f"{total_payes} / {total_samples}")
            c2.metric("Marge Réelle", f"{marge_reelle:.2f} €")
            c3.metric("Bouteille payée ?", "OUI" if marge_reelle >= 0 else "NON", delta_color="normal")

# 4. STOCK RESTANT
with tab4:
    st.header("📦 Stock Invendu (Samples)")
    rows = []
    tot_val = 0
    for m, d in st.session_state.mois_data.items():
        if d["nom_bouteille"]:
            vendus = sum(ad["qte"] for ad in d["adherents"].values())
            preleves = RHUMOTHEQUE_PRELEVEMENT if m in st.session_state.rhumotheque and st.session_state.rhumotheque[m]["en_stock"] else 0
            capa = max(CAPACITE_BOUTEILLE, vendus + preleves)
            restant = capa - vendus - preleves
            if restant > 0:
                val = restant * d["prix_sample"]
                tot_val += val
                rows.append({"Mois": m, "Bouteille": d["nom_bouteille"], "Vendus": vendus, "Rhumothèque": preleves, "Restant": restant, "Valeur": f"{val:.2f} €"})
    
    st.metric("Valeur Latente (Stock)", f"{tot_val:.2f} €")
    if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else: st.info("Aucun stock dormant.")

# 5. RHUMOTHÈQUE
with tab5:
    st.header("🏛️ Rhumothèque (Archives)")
    st.info(f"ℹ️ {RHUMOTHEQUE_PRELEVEMENT} samples (6cl) réservés automatiquement par bouteille.")
    
    rhumo_list = []
    tot_val_rhumo = 0
    
    cols = st.columns(3)
    for i, (mois, data) in enumerate(st.session_state.rhumotheque.items()):
        if not data.get("nom"): continue
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{mois}** : {data['nom']}")
                st.caption(f"Valeur : {data['valeur']:.2f} €")
                en_stock = st.checkbox("En Stock", value=data["en_stock"], key=f"rh_st_{mois}")
                notes = st.text_area("Notes", value=data.get("notes", ""), height=60, key=f"rh_nt_{mois}")
                if en_stock != data["en_stock"] or notes != data.get("notes", ""):
                    data["en_stock"] = en_stock
                    data["notes"] = notes
                    sauvegarder_etat()
                    st.rerun()
                if data["en_stock"]:
                    rhumo_list.append(data)
                    tot_val_rhumo += data["valeur"]

    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.metric("Bouteilles en Archive", len(rhumo_list))
    c2.metric("Valeur Totale", f"{tot_val_rhumo:.2f} €")
