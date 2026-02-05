# 2. DÉGUSTATIONS
with tab2:
    st.header("🍽️ Dégustations")
    # On définit la liste des mois explicitement
    liste_mois_deg = ["Mars", "Juin", "Septembre", "Décembre"]
    # On crée les onglets visuels
    onglets_visuels = st.tabs(liste_mois_deg)
    
    # On boucle sur les deux listes en parallèle (index, nom du mois)
    for i, mois_nom in enumerate(liste_mois_deg):
        with onglets_visuels[i]:
            # On utilise le NOM du mois (ex: "Mars") pour chercher les données
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
