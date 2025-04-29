import streamlit as st
import pandas as pd
from docx import Document
import numpy as np
import openpyxl
from openpyxl.styles import PatternFill
import re
from datetime import datetime
import unidecode
import re
from constants import (
    abbreviation_mapping, id_columns, date_columns, entry_date_columns, date_exceptions,
    entry_year_exceptions, seniority_date_columns, seniority_exceptions, position_entry_date_columns,
    exit_date_columns, gender_columns, hours_columns, workload_columns, workingtime_columns,
    contract_columns, status_columns, region_columns, postal_code_columns, city_columns, contrat_mapping,
    segmentation_columns, job_title_columns, job_columns, nplus1_columns, convention_columns, idcc_columns,
    coefficient_columns, base_salary_columns, financial_keywords
)
from cleaning_logic import (
    generate_word_report, is_valid_postal, harmonize_text, harmonize_if_known, is_invalid_contract, clean_workload, 
    is_invalid_workload, extract_hour, normalize_job_title,
    save_cleaned_excel, apply_fusions, harmonize_financial_values
)

# Initialisation des états
if "ready_to_download" not in st.session_state:
    st.session_state.ready_to_download = False
    st.session_state.excel_bytes = None
    st.session_state.error_doc = None
    st.session_state.modif_doc = None

if "columns_to_check_dupes" not in st.session_state:
    st.session_state.columns_to_check_dupes = []

if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None

# Fonction de chargement
def load_file():
    uploaded_file = st.file_uploader("Téléchargez un fichier Excel", type=["xls", "xlsx", "xlsm"])
    if uploaded_file is not None:
        # Lire une première fois pour détecter les colonnes
        temp_df = pd.read_excel(uploaded_file, nrows=0)

        # Identifier les colonnes "code postal"
        postal_cols = [col for col in temp_df.columns if col in postal_code_columns]

        # Créer un dictionnaire de types : les codes postaux en string
        dtype_dict = {col: str for col in postal_cols}

        return pd.read_excel(uploaded_file, dtype=dtype_dict)
    return None

# Interface Streamlit
st.set_page_config(page_title="Outil de Nettoyage Salarial", page_icon="🧹", layout="wide")

st.markdown("## 🔒 Accès sécurisé")

password = st.text_input("Veuillez entrer le mot de passe :", type="password")

correct_password = "salaires2025"

if password != correct_password:
    st.warning("⛔ Mot de passe incorrect ou vide.")
    st.stop()
else:
    st.success("🔓 Accès autorisé.")


# --- Titre principal ---
st.title("🧹 Outil de nettoyage de bases de données salariales")

st.markdown("""
Bienvenue dans votre outil de nettoyage des bases salariales.

Suivez les étapes ci-dessous pour charger vos données, appliquer les transformations nécessaires, harmoniser les intitulés et télécharger votre fichier corrigé.
""")

# Valeur du SMIC à personnaliser
st.sidebar.markdown("### Paramètres globaux")
smic_threshold = st.sidebar.number_input(
    "💶 Montant du SMIC (net ou brut selon vos données)", 
    min_value=0.0, 
    value=1766.92, 
    step=1.0,
    help="Utilisé pour vérifier les salaires de base. Valeur par défaut : 1766,92 € (SMIC brut 2024)."
)
st.sidebar.markdown("### 🔎 Étapes")
st.sidebar.markdown("""
1. 📥 Charger votre fichier Excel
2. 🔧 Sélectionner les actions de nettoyage
3. 🔗 Appliquer les fusions
4. 📥 Télécharger les résultats
""")


with st.container():
    st.header("📥 Chargez votre fichier")
    st.markdown("---")
    df = load_file()


if df is not None:
    # Réinitialiser les groupes de similarité (emploi, convention, etc.)
    keys_to_clear = [key for key in st.session_state if key.startswith("similar_groups_") or key.startswith("group_select_")]
    for key in keys_to_clear:
        del st.session_state[key]

errors = []
modifications = []
modified_cells = set()
incoherent_entry_dates = {}

if df is not None:
    st.subheader("📊 Aperçu des données")
    st.dataframe(df.head())

    with st.container():
        st.header("🔧 Sélection des colonnes à nettoyer")
        st.markdown("---")
        st.markdown(
            """
            <div style="background-color:#F9F9F9;padding:10px;border-radius:10px">
            <b>🔎 Sélectionnez une action pour chaque colonne :</b><br>
            - Choisissez parmi plusieurs types de nettoyage<br>
            - Vous pouvez cocher pour signaler les cellules vides comme erreur
            </div>
            """,
            unsafe_allow_html=True
        )
        # tout ton bloc de sélection de colonnes ici
        column_menus = {}
        entry_date_checks = {}  # Pour activer ou désactiver la vérification d’antériorité

        for col in df.columns: 
            options = [
                "🚫 Aucune action", "📑 Gestion des doublons", "📆 Harmoniser les dates", "🚻 Harmoniser le genre",
                "⏱️ Harmoniser les horaires", "📊 Harmoniser le taux d'activité", "📃 Harmoniser le contrat",
                "🔤 Harmoniser les textes", "📮 Vérification code postal", "👔 Harmoniser les intitulés d'emploi",
                "👥 Vérifier N+1 ≠ collaborateur", "🤝 Harmoniser la convention collective", "📄 Vérification IDCC",
                "🧮 Vérification du format des coefficients", "💶 Vérification salaire de base", "💰 Harmonisation des valeurs financières"
            ]
            if col in id_columns:
                default = "📑 Gestion des doublons"
            elif any(keyword in col.lower() for keyword in ["salaire de base", "fixe", "rémunération fixe"]):
                default = "💶 Vérification salaire de base"
            elif col in date_columns and col not in date_exceptions:
                default = "📆 Harmoniser les dates"
            elif col in entry_date_columns and col not in entry_year_exceptions:
                default = "📆 Harmoniser les dates"
            elif col in entry_year_exceptions:
                default = "🚫 Aucune action"
            elif col in seniority_date_columns:
                default = "📆 Harmoniser les dates"
            elif col in seniority_exceptions:
                default = "🚫 Aucune action"
            elif col in position_entry_date_columns:
                default = "📆 Harmoniser les dates"
            elif any(word in col.lower() for word in financial_keywords) and col not in base_salary_columns:
                default = "💰 Harmonisation des valeurs financières"
            elif col in exit_date_columns:
                default = "📆 Harmoniser les dates"
            elif col in gender_columns:
                default = "🚻 Harmoniser le genre"
            elif col in hours_columns:
                default = "⏱️ Harmoniser les horaires"
            elif col in workload_columns:
                default = "📊 Harmoniser le taux d'activité"
            elif col in contract_columns:
                default = "📃 Harmoniser le contrat"
            elif col in status_columns:
                default = "🔤 Harmoniser les textes"
            elif col in region_columns:
                default = "🔤 Harmoniser les textes"
            elif col in postal_code_columns:
                default = "📮 Vérification code postal"
            elif col in segmentation_columns or col.startswith("Nom Segmentation"):
                default = "🔤 Harmoniser les textes"
            elif col in job_title_columns:
                default = "👔 Harmoniser les intitulés d'emploi"
            elif col in job_columns:
                default = "👔 Harmoniser les intitulés d'emploi"
            elif col in nplus1_columns:
                default = "👥 Vérifier N+1 ≠ collaborateur"
            elif col in convention_columns:
                default = "🤝 Harmoniser la convention collective"
            elif col in idcc_columns:
                default = "📄 Vérification IDCC"
            elif col in coefficient_columns:
                default = "🧮 Vérification du format des coefficients"
            elif col in base_salary_columns:
                default = "💶 Vérification salaire de base"
            else:
                default = "🚫 Aucune action"

            action = st.selectbox(f"{col}", options, index=options.index(default), key=col)
            column_menus[col] = action  # si tu veux garder l’info

            # Définir une valeur par défaut selon le type de colonne
            default_empty_check = False if col in idcc_columns else True
            checkbox_key = f"check_empty_{col}"
            checkbox_value = st.session_state.get(checkbox_key, default_empty_check)

            st.checkbox(
                f"📭 Remonter les cases vides comme erreurs pour {col}",
                value=checkbox_value,
                key=checkbox_key,
                help="Si activé, les cellules vides dans cette colonne seront considérées comme des erreurs.",
            )


        

            # Pour la colonne "Date d'entrée poste" → vérifications supplémentaires
            if col in position_entry_date_columns:
                st.session_state[f"check_poste_vs_societe_{col}"] = st.checkbox(
                    f"🏢 Vérifier que {col} est postérieure à la date d'entrée société",
                    value=True,
                    help="Si activé, les dates d'entrée poste antérieures à l'entrée société seront remontées en erreur.",
                    key=f"check_poste_societe_{col}"
                )
                st.session_state[f"check_poste_vs_naissance_{col}"] = st.checkbox(
                    f"🍼 Vérifier que {col} est postérieure à la date de naissance",
                    value=True,
                    help="Si activé, les dates d'entrée poste antérieures à la naissance seront remontées en erreur.",
                    key=f"check_poste_naissance_{col}"
                )

            columns_to_check_dupes = []
            columns_to_check_dates = []
            birth_date_column = next((col for col in df.columns if "naissance" in col.lower()), None)


            # Identifier les colonnes N+1 et ID collaborateur
            nplus1_col = next((col for col in df.columns if "n+1" in col.lower()), None)
            id_col = next((col for col in df.columns if col in id_columns), None)

            if action == "👥 Vérifier N+1 ≠ collaborateur":
                id_col = next((c for c in df.columns if c in id_columns), None)
                if id_col:
                    conflit_mask = (
                        df[col].notna() &
                        df[col].astype(str).str.strip().ne("") &
                        (df[col].astype(str) == df[id_col].astype(str))
                    )
                    nb_conflits = conflit_mask.sum()

                    if nb_conflits > 0:
                        st.warning(f"{nb_conflits} ligne(s) ont un identifiant de N+1 identique à celui du collaborateur ({id_col}).")
                        st.dataframe(df[conflit_mask])
                        errors.append(f"{col} : {nb_conflits} ligne(s) avec un identifiant N+1 identique à celui du collaborateur ({id_col}).")

                    # Pour mise en couleur rouge dans l'Excel
                    df["_nplus1_conflit_"] = conflit_mask
                    st.session_state["_nplus1_conflit_"] = conflit_mask.copy()  # ✅ pour le conserver jusqu’au bout
                    modifications.append(f"Vérification N+1 ≠ collaborateur appliquée sur {col}")

                st.session_state.cleaned_df = df.copy()

                # ✅ Ajout visuel :
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())


            if action in ["👔 Harmoniser les intitulés d'emploi", "🤝 Harmoniser la convention collective"]:
                st.markdown(f"#### ⛵ Harmonisation automatique des textes ({col})")
                df[col] = df[col].fillna("").apply(normalize_job_title)
                group_key = f"similar_groups_{col}"

                threshold = 0.85 if action == "👔 Harmoniser les intitulés d'emploi" else 0.75

                if group_key not in st.session_state:
                    _, similar_groups = get_similar_job_title_groups(df[col], threshold=threshold)
                    st.session_state[group_key] = similar_groups
                else:
                    similar_groups = st.session_state[group_key]

                st.markdown("#### 🤝 Suggestions de regroupements similaires")

                confirmed_mapping = {}
                selected_titles_per_group = {}

                for i, group in enumerate(similar_groups):
                    if len(group) < 2:
                        continue

                    label = f"🔗 Groupe similaire détecté : {group}"
                    st.write(label)

                    # --- NOUVEAU : Cases à cocher par intitulé
                    selected_titles = []
                    for title in group:
                        checkbox_key = f"select_title_{col}_{i}_{title}"
                        selected = st.checkbox(
                            f"✅ Harmoniser {title} ?",
                            value=True,  # coché par défaut
                            key=checkbox_key
                        )
                        if selected:
                            selected_titles.append(title)

                    # --- EXISTANT : menu déroulant pour choisir la valeur de référence
                    options = ["Aucune fusion"] + sorted(group, key=len)
                    select_key = f"group_select_{col}_{i}_{action.replace(' ', '_')}"

                    def update_fusion_selection(key):
                        st.session_state[f"confirmed_selection_{key}"] = st.session_state[key]

                    selected_value = st.selectbox(
                        f"👉 Choisissez la version de référence à conserver pour ce groupe",
                        options=options,
                        key=select_key,
                        on_change=update_fusion_selection,
                        args=(select_key,)
                    )

                    # --- NOUVEAU : Enregistrer la sélection
                    selected_titles_per_group[select_key] = selected_titles

                # Sauvegarder tout dans st.session_state
                if selected_titles_per_group:
                    st.session_state[f"selected_titles_per_group_{col}"] = selected_titles_per_group

                # selected_value = st.session_state.get(f"confirmed_selection_{select_key}", "Aucune fusion")

                # ❗ Ne pas appliquer ici, on ne fait que stocker les sélections utilisateur
                for i, group in enumerate(similar_groups):
                    if len(group) < 2:
                        continue

                    select_key = f"group_select_{col}_{i}_{action.replace(' ', '_')}"
                    selected_value = st.session_state.get(f"confirmed_selection_{select_key}", "Aucune fusion")

                    if selected_value == "Aucune fusion":
                        continue  # pas de fusion pour ce groupe

                    # On lit les cases correctes
                    for val in group:
                        checkbox_key = f"select_title_{col}_{i}_{val}"
                        if st.session_state.get(checkbox_key, False):  # uniquement si coché
                            confirmed_mapping[val] = selected_value


                # ✅ On sauvegarde seulement le mapping, sans modifier les données pour l’instant
                if confirmed_mapping:
                    fusion_key = f"fusion_mapping_{col}"
                    st.session_state[fusion_key] = confirmed_mapping
                    st.info("📝 Vos choix de fusion ont été enregistrés. Cliquez sur « Appliquer les fusions » pour les activer.")



                    if action == "📮 Vérification code postal":
                        empty_check = st.session_state.get(f"check_empty_{col}", True)
                        original = df[col].copy()

                        empty_check = st.session_state.get(f"check_empty_{col}", True)
                        invalid_mask = ~df[col].apply(lambda val: is_valid_postal(val, empty_check))
                        nb_errors = invalid_mask.sum()

                        if nb_errors > 0:
                            st.warning(f"{nb_errors} valeur(s) incorrecte(s) détectée(s) dans {col}.")
                            errors.append(f"{col} : {nb_errors} valeur(s) incorrecte(s) détectée(s) (doivent être 5 chiffres).")
                            st.dataframe(df[invalid_mask])

                        # Ajouter comme cellules "modifiées" pour les colorer en jaune
                        # modified_cells.update([(idx, col) for idx in df[invalid_mask].index])
                        modifications.append(f"Vérification du format de code postal appliquée sur {col}")

                        st.session_state.cleaned_df = df.copy()

                        # ✅ Ajout visuel :
                        st.success(f"✅ Transformation appliquée sur {col}")
                        st.dataframe(df[[col]].head())



            if action == "🔤 Harmoniser les textes": 
                
                original = df[col].copy()
                df[col] = df[col].apply(lambda x: harmonize_text(x, abbreviation_mapping))

                # Gestion spécifique des régions : vides à remonter ?
                empty_check = st.session_state.get(f"check_empty_{col}", True)
                empty_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
                if empty_check and empty_mask.any():
                    nb_empty = empty_mask.sum()
                    st.warning(f"{nb_empty} case(s) vide(s) détectée(s) dans {col}.")
                    errors.append(f"{col} : {nb_empty} case(s) vide(s) détectée(s).")


                elif col in segmentation_columns or col.startswith("Nom Segmentation"):
                    empty_check = st.session_state.get(f"check_empty_{col}", True)
                    if empty_check:
                        empty_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
                        nb_empty = empty_mask.sum()
                        if nb_empty > 0:
                            st.warning(f"{nb_empty} case(s) vide(s) détectée(s) dans {col}.")
                            errors.append(f"{col} : {nb_empty} case(s) vide(s) détectée(s).")

                changed = ~df[col].fillna("").eq(original.fillna(""))
                if changed.any():
                    modifications.append(f"Harmonisation des textes appliquée sur {col}")
                    modified_cells.update([(idx, col) for idx in df[changed].index])
                
                st.session_state.cleaned_df = df.copy()

                # ✅ Ajout visuel :
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())

            if action == "📃 Harmoniser le contrat":

                original = df[col].copy()
                empty_check = st.session_state.get(f"check_empty_{col}", True)

                # Appliquer harmonisation seulement si la valeur est reconnue
                df[col] = df[col].apply(lambda val: harmonize_if_known(val, contrat_mapping))

                invalid_mask = df[col].apply(lambda val: is_invalid_contract(val, contrat_mapping, empty_check))
                nb_invalid = invalid_mask.sum()

                if nb_invalid > 0:
                    st.warning(f"{nb_invalid} valeur(s) non reconnue(s) ou vide(s) détectée(s) dans {col}.")
                    errors.append(f"{col} : {nb_invalid} valeur(s) non reconnue(s) ou vide(s).")

                # Marquer comme modifiées les cellules harmonisées
                changed = df[col] != original
                if changed.any():
                    modifications.append(f"Harmonisation du contrat appliquée sur {col}")
                    modified_cells.update([(idx, col) for idx in df[changed].index])



                non_reconnu_mask = df[col] == "Non reconnu"
                non_reconnu_count = non_reconnu_mask.sum()
                if non_reconnu_count > 0:
                    st.warning(f"{non_reconnu_count} valeur(s) non reconnue(s) ou vide(s) détectée(s) dans {col}.")
                    errors.append(f"{col} : {non_reconnu_count} valeur(s) non reconnue(s) ou vide(s).")

                changed = df[col] != original
                if changed.any():
                    modifications.append(f"Harmonisation du contrat appliquée sur {col}")
                    modified_cells.update([(idx, col) for idx in df[changed].index])

                st.session_state.cleaned_df = df.copy()

                # ✅ Ajout visuel :
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())


            if action == "📊 Harmoniser le taux d'activité":
                empty_check = st.session_state.get(f"check_empty_{col}", True)
                original = df[col].copy()
                new_values = []
                invalid_indices = []

                for i, val in enumerate(df[col]):
                    if pd.isna(val) or str(val).strip() == "":
                        new_values.append(val)
                        if empty_check:
                            invalid_indices.append(i)
                        continue

                    try:
                        val_str = str(val).replace(",", ".").replace("%", "").strip()
                        val_float = float(val_str)

                        if 0 < val_float <= 1:
                            val_float *= 100

                        val_float = round(val_float, 1)

                        if val_float < 0 or val_float > 100:
                            invalid_indices.append(i)

                        if val_float.is_integer():
                            new_values.append(f"{int(val_float)}%")
                        else:
                            new_values.append(f"{val_float:.1f}%")

                    except:
                        new_values.append(val)
                        invalid_indices.append(i)

                df[col] = new_values

                # Enregistrement des erreurs pour la mise en rouge
                if "invalid_workload" not in st.session_state:
                    st.session_state["invalid_workload"] = {}
                st.session_state["invalid_workload"][col] = invalid_indices

                if invalid_indices:
                    st.warning(f"{len(invalid_indices)} valeur(s) incorrecte(s) ou vide(s) détectée(s) dans {col}.")
                    errors.append(f"{col} : {len(invalid_indices)} valeur(s) incorrecte(s) ou vide(s).")

                changed = df[col] != original
                if changed.any():
                    modifications.append(f"Harmonisation du taux d'activité appliquée sur {col}")
                    modified_cells.update([(idx, col) for idx in df[changed].index])
                
                st.session_state.cleaned_df = df.copy()

                # ✅ Ajout visuel
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())


            if action == "⏱️ Harmoniser les horaires":
                original = df[col].copy()
                empty_check = st.session_state.get(f"check_empty_{col}", True)

                new_values = []
                invalid_indices = []

                for i, val in enumerate(df[col]):
                    if pd.isna(val) or str(val).strip() == "":
                        new_values.append("")
                        if empty_check:
                            invalid_indices.append(i)
                    else:
                        try:
                            val_str = str(val).lower().replace(",", ".")
                            match = re.search(r"(\d+(?:\.\d+)?)", val_str)
                            if match:
                                heure = round(float(match.group(1)), 1)
                                new_values.append(str(heure))  # toujours une chaîne
                            else:
                                new_values.append(str(val))  # conserver en texte brut
                                invalid_indices.append(i)
                        except:
                            new_values.append(str(val))
                            invalid_indices.append(i)

                df[col] = pd.Series(new_values, dtype="object")

                if "invalid_hours" not in st.session_state:
                    st.session_state["invalid_hours"] = {}
                st.session_state["invalid_hours"][col] = invalid_indices

                if invalid_indices:
                    st.warning(f"{len(invalid_indices)} valeur(s) non reconnue(s) ou vide(s) détectée(s) dans {col}.")
                    errors.append(f"{col} : {len(invalid_indices)} valeur(s) non reconnue(s) ou vide(s).")

                changed = df[col] != original
                if changed.any():
                    modifications.append(f"Harmonisation des horaires appliquée sur {col}")
                    modified_cells.update([(idx, col) for idx in df[changed].index])

                st.session_state.cleaned_df = df.copy()

                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].fillna(""))


            if action == "🧮 Vérification du format des coefficients":
                # Convention collective associée
                related_convention_col = next((c for c in df.columns if c in convention_columns), None)
                
                if related_convention_col:
                    inconsistent_format_rows = []

                    # Fonction pour extraire le "format" d’un coefficient (ex. A1B2 → LCLD)
                    def get_format(val):
                        val = str(val)
                        return "".join(["L" if c.isalpha() else "D" if c.isdigit() else "S" for c in val if c.strip() != ""])

                    # Groupe par convention
                    grouped = df[[related_convention_col, col]].dropna().groupby(related_convention_col)

                    for convention, group_df in grouped:
                        formats = group_df[col].dropna().astype(str).apply(get_format)
                        unique_formats = formats.unique()

                        if len(unique_formats) > 1:
                            st.warning(f"Convention « {convention} » : plusieurs formats de coefficient détectés → {list(unique_formats)}")
                            st.dataframe(group_df)
                            errors.append(f"Convention « {convention} » : plusieurs formats de coefficient détectés → {list(unique_formats)}")
                            inconsistent_rows.extend(group_df.index.tolist())

                        # Enregistrer les index à colorer
                        if "coeff_format_errors" not in st.session_state:
                            st.session_state["coeff_format_errors"] = {}
                        st.session_state["coeff_format_errors"][col] = inconsistent_rows
                
                modifications.append(f"🧮 Vérification du format des coefficients appliquée sur {col}")

                # ✅ Ajout visuel :
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())


            if action == "🚻 Harmoniser le genre":
                genre_mapping = {
                    "h": "Hommes", "homme": "Hommes", "m": "Hommes",
                    "f": "Femmes", "femme": "Femmes"
                }

                original = df[col].copy()
                new_values = []
                invalid_indices = []
                empty_check = st.session_state.get(f"check_empty_{col}", True)

                for i, val in enumerate(df[col]):
                    val_str = str(val).strip().lower() if pd.notna(val) else ""
                    if val_str in genre_mapping:
                        new_values.append(genre_mapping[val_str])
                    elif val_str == "":
                        new_values.append(val)
                        if empty_check:
                            invalid_indices.append(i)
                    else:
                        new_values.append(val)
                        invalid_indices.append(i)

                df[col] = new_values

                # Enregistrement des erreurs pour la mise en rouge
                if "invalid_gender" not in st.session_state:
                    st.session_state["invalid_gender"] = {}
                st.session_state["invalid_gender"][col] = invalid_indices

                if invalid_indices:
                    st.warning(f"{len(invalid_indices)} valeur(s) non reconnue(s) ou vide(s) détectée(s) dans {col}.")
                    errors.append(f"{col} : {len(invalid_indices)} valeur(s) non reconnue(s) ou vide(s).")

                # Marquer les modifications valides
                changed = df[col] != original
                if changed.any():
                    modifications.append(f"Harmonisation du genre appliquée sur {col}")
                    modified_cells.update([(idx, col) for idx in df[changed].index])
                
                st.session_state.cleaned_df = df.copy()

                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())


            if action == "💰 Harmonisation des valeurs financières":
                empty_check = st.session_state.get(f"check_empty_{col}", True)
                df, errors_fin, modifs_fin = harmonize_financial_values(df, col, empty_check)

                if errors_fin:
                    st.warning(errors_fin[0])
                    error_df = pd.DataFrame(modifs_fin, columns=["Index", col])
                    st.dataframe(error_df)
                    errors.extend(errors_fin)

                modifications.append(f"💰 Harmonisation des valeurs financières appliquée sur {col}")
                modified_cells.update(modifs_fin)

                st.session_state.cleaned_df = df.copy()

                # ✅ Affichage sans bug
                safe_display = df[[col]].copy()
                safe_display[col] = safe_display[col].astype(str)
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(safe_display.head())


            if action == "📆 Harmoniser les dates":
                columns_to_check_dates.append(col)
                empty_check = st.session_state.get(f"check_empty_{col}", True)
                
                original_values = df[col].copy()
                col_datetime = pd.to_datetime(original_values, errors='coerce')

                # On distingue les dates vides à remonter uniquement si la case est cochée
                empty_check_key = f"check_empty_{col}"
                empty_check = st.session_state.get(empty_check_key, True)

                invalid_date_indices = []
                for i, val in enumerate(original_values):
                    if pd.isna(val) or str(val).strip() == "":
                        if empty_check:
                            invalid_date_indices.append(i)
                    else:
                        try:
                            pd.to_datetime(val, errors='raise')  # force une erreur si invalide
                        except:
                            invalid_date_indices.append(i)

                if "invalid_dates" not in st.session_state:
                    st.session_state["invalid_dates"] = {}
                st.session_state["invalid_dates"][col] = invalid_date_indices


                # Remplacement uniquement des dates valides
                df[col] = original_values.copy()  # on garde les chaînes
                df.loc[col_datetime.notna(), col] = col_datetime[col_datetime.notna()].dt.strftime("%d/%m/%Y")

                # Détection des erreurs (vides ou "01/01/1900")
                errors_found = df[
                    ((df[col].isna()) & empty_check) |
                    (col_datetime.dt.strftime("%d/%m/%Y") == "01/01/1900")
                ]


                try:
                    col_datetime = pd.to_datetime(df[col], errors='coerce')

                    if not errors_found.empty:
                        errors.append(f"{col}: {len(errors_found)} valeurs incorrectes ou absentes.")
                        st.write(f"Erreurs dans {col} :")
                        st.dataframe(errors_found)

                    # Vérification spécifique Date d'entrée > Date de naissance
                    if col in entry_date_columns and entry_date_checks.get(col, True) and birth_date_column in df.columns:
                        entry_datetime = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                        birth_date_datetime = pd.to_datetime(df[birth_date_column], errors="coerce", dayfirst=True)
                        incoherent_rows = df[entry_datetime.dt.date < birth_date_datetime.dt.date]


                        if "incoherent_entry_dates" not in st.session_state:
                            st.session_state["incoherent_entry_dates"] = {}
                        if col not in st.session_state["incoherent_entry_dates"]:
                            st.session_state["incoherent_entry_dates"][col] = []
                        st.session_state["incoherent_entry_dates"][col].extend(incoherent_rows.index.tolist())

                        if "incoherent_entry_dates" not in st.session_state:
                            st.session_state["incoherent_entry_dates"] = {}

                        if not incoherent_rows.empty: 
                            errors.append(f"Incohérences détectées : {len(incoherent_rows)} lignes avec date d'entrée antérieure à la naissance.")
                            for i, row in incoherent_rows.iterrows():
                                errors.append(f"Ligne {i+2} : Date d'entrée ({row[col]}) antérieure à la date de naissance ({row[birth_date_column]})")
                            st.write(f"⚠️ Lignes incohérentes (entrée < naissance) dans {col} :")
                            st.dataframe(incoherent_rows)

                    # Vérification : Date d'entrée poste < Date d'entrée société
                    if col in position_entry_date_columns:
                        check_vs_soc = st.session_state.get(f"check_poste_vs_societe_{col}", True)
                        check_vs_birth = st.session_state.get(f"check_poste_vs_naissance_{col}", True)

                        col_datetime = pd.to_datetime(df[col], errors='coerce')  # base de travail "sûre"

                        if check_vs_soc:
                            entry_soc_col = next((c for c in df.columns if c in entry_date_columns), None)
                            if entry_soc_col:
                                entry_soc_datetime = pd.to_datetime(df[entry_soc_col], errors='coerce')
                                incoh_soc = df[col_datetime.dt.date < entry_soc_datetime.dt.date]
                                if col not in incoherent_entry_dates:
                                    incoherent_entry_dates[col] = set()
                                incoherent_entry_dates[col].update(incoh_soc.index)
                                if not incoh_soc.empty:
                                    errors.append(f"Incohérences : {len(incoh_soc)} lignes où {col} est antérieure à l'entrée société.")
                                    for i, row in incoh_soc.iterrows():
                                        errors.append(f"Ligne {i+2} : {col} = {row[col]}, Entrée société = {row[entry_soc_col]}")

                        if check_vs_birth and birth_date_column:
                            birth_date_datetime = pd.to_datetime(df[birth_date_column], errors='coerce')
                            incoh_birth = df[col_datetime.dt.date < birth_date_datetime.dt.date]
                            if col not in incoherent_entry_dates:
                                incoherent_entry_dates[col] = set()
                            incoherent_entry_dates[col].update(incoh_birth.index)
                            if not incoh_birth.empty:
                                errors.append(f"Incohérences : {len(incoh_birth)} lignes où {col} est antérieure à la naissance.")
                                for i, row in incoh_birth.iterrows():
                                    errors.append(f"Ligne {i+2} : {col} = {row[col]}, Naissance = {row[birth_date_column]}")

                    # Harmonisation des dates seulement après toutes les vérifications
                    df.loc[col_datetime.notna(), col] = col_datetime[col_datetime.notna()].dt.strftime("%d/%m/%Y")
                    modified_cells.update([(idx, col) for idx in df[df[col].notna()].index])
                    modifications.append(f"Harmonisation des dates appliquée sur {col}")

                except Exception as e:
                    st.warning(f"Erreur sur {col}: {e}")
                
                st.session_state.cleaned_df = df.copy()

                # ✅ Ajout visuel :
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())
            
            if action == "💶 Vérification salaire de base":
                from cleaning_logic import verify_base_salary
                empty_check = st.session_state.get(f"check_empty_{col}", True)
                df, errors_found, modified = verify_base_salary(df, col, smic_threshold, empty_check)
                modified_cells.update(modified)

                if errors_found:
                    st.warning(errors_found[0])
                    error_df = pd.DataFrame(modified, columns=["Index", col])
                    st.dataframe(error_df)
                    errors.extend(errors_found)

                modifications.append(f"💶 Vérification salaire de base appliquée sur {col}")
                st.session_state.cleaned_df = df.copy()

                # ✅ Ajout visuel :
                st.success(f"✅ Transformation appliquée sur {col}")
                safe_display = df[[col]].copy()
                safe_display[col] = safe_display[col].astype(str)
                st.dataframe(safe_display.head())


            # Appliquer la fusion si elle existe déjà pour la colonne de convention
            if col in idcc_columns:
                related_convention_col = next((c for c in df.columns if c in convention_columns), None)
                fusion_key = f"fusion_mapping_{related_convention_col}"
                if related_convention_col and fusion_key in st.session_state:
                    df[related_convention_col] = df[related_convention_col].replace(st.session_state[fusion_key])


            if action == "📄 Vérification IDCC":
                empty_check = st.session_state.get(f"check_empty_{col}", False)
                original = df[col].copy()
                
                # Identifier la colonne de convention associée
                related_convention_col = next((c for c in df.columns if c in convention_columns), None)

                if related_convention_col:
                    inconsistent_rows = []
                    convention_idcc_map = df.groupby(related_convention_col)[col].apply(lambda x: x.dropna().unique())

                    for convention, idcc_values in convention_idcc_map.items():
                        if len(idcc_values) > 1:
                            # Incohérence détectée
                            rows = df[df[related_convention_col] == convention]
                            inconsistent_rows.append((convention, idcc_values, rows))

                    if inconsistent_rows:
                        for convention, ids, rows in inconsistent_rows:
                            st.warning(f"Convention « {convention} » a plusieurs IDCC : {ids.tolist()}")
                            st.dataframe(rows)
                            errors.append(f"Incohérence IDCC : « {convention} » a plusieurs IDCC : {ids.tolist()}")
                    
                    if "invalid_idcc" not in st.session_state:
                        st.session_state["invalid_idcc"] = {}

                    # Stocke les index des lignes incohérentes
                    for convention, ids, rows in inconsistent_rows:
                        indices = rows.index.tolist()
                        st.session_state["invalid_idcc"].setdefault(col, []).extend(indices)


                    if empty_check:
                        empty_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
                        if empty_mask.any():
                            nb_empty = empty_mask.sum()
                            st.warning(f"{nb_empty} case(s) vide(s) détectée(s) dans {col}.")
                            errors.append(f"{col} : {nb_empty} case(s) vide(s).")
                            st.dataframe(df[empty_mask])
                            indices_vides = df[empty_mask].index.tolist()
                            st.session_state["invalid_idcc"].setdefault(col, []).extend(indices_vides)


                modifications.append(f"📄 Vérification IDCC appliquée sur {col}")


            if action == "📑 Gestion des doublons":
                if col not in st.session_state.columns_to_check_dupes:
                    st.session_state.columns_to_check_dupes.append(col)
                st.session_state.cleaned_df = df.copy()
                st.success(f"✅ Transformation appliquée sur {col}")
                st.dataframe(df[[col]].head())


            # 🔎 Vérification de cohérence des colonnes de temps de travail
            if col in hours_columns or col in workload_columns or "forfait" in col.lower():
                working_columns_found = {
                    "horaires": next((c for c in df.columns if c in hours_columns), None),
                    "taux": next((c for c in df.columns if c in workload_columns), None),
                    "forfait": next((c for c in df.columns if "forfait" in c.lower()), None)
                }

            # Si les trois colonnes sont présentes...
                if all(working_columns_found.values()):
                    col1 = df[working_columns_found["horaires"]]
                    col2 = df[working_columns_found["taux"]]
                    col3 = df[working_columns_found["forfait"]]

                    all_empty = col1.isna().all() and col2.isna().all() and col3.isna().all()
                    none_full = not col1.notna().all() and not col2.notna().all() and not col3.notna().all()

                    if all_empty:
                        st.error("❌ Les colonnes Horaires, Taux d'activité et Forfait jours sont toutes vides. Une des trois doit être renseignée.")
                        errors.append("Colonnes temps de travail : toutes vides.")
                        
                    elif none_full:
                        fill_rates = {
                            "Horaires": col1.notna().mean(),
                            "Taux d'activité": col2.notna().mean(),
                            "Forfait jours": col3.notna().mean()
                        }

                        sorted_fill = sorted(fill_rates.items(), key=lambda x: x[1], reverse=True)

                        message_lines = [
                            "⚠️ Aucune des colonnes Horaires, Taux d'activité ou Forfait jours n'est remplie à 100%.",
                            "Niveau de remplissage détecté :"
                        ]
                        for col, rate in sorted_fill:
                            message_lines.append(f"• {col} : {rate:.1%}")

                        # Une seule fois dans Streamlit
                        st.warning("\n".join(message_lines))

                        # Et une seule fois dans le rapport d'erreurs
                        errors.append("\n".join(message_lines))
    


        with st.container():
            st.subheader("🔄 Appliquer les fusions")
            st.markdown("---")

        if st.button("Appliquer les fusions maintenant"):
            # ✅ Utiliser la version à jour dans la session
            df_current = st.session_state.get("cleaned_df", df.copy())


            # ✅ Appliquer les fusions sur cette base
            df_with_fusion, modifs_fusion, modif_cells_fusion = apply_fusions(
                df_current.copy(),
                column_menus,
                fusion_mode=True
            )

            # ✅ Mettre à jour le DataFrame nettoyé avec les fusions
            st.session_state.cleaned_df = df_with_fusion.copy()
            df = df_with_fusion.copy()  # <-- pour que les fusions soient bien visibles dans le reste du script

            # ✅ Enregistrer les modifications
            modified_cells.update(modif_cells_fusion)
            st.session_state.modified_cells = modified_cells
            modifications.extend(modifs_fusion)

            # ✅ Générer rapports Word (modifications / erreurs)
            if modifications:
                mod_file = generate_word_report("Modifications effectuées", modifications)
                with open(mod_file, "rb") as f:
                    st.session_state.modif_doc = f.read()
            else:
                st.session_state.modif_doc = None

            if errors:
                err_file = generate_word_report("Erreurs détectées", errors)
                with open(err_file, "rb") as f:
                    st.session_state.error_doc = f.read()
            else:
                st.session_state.error_doc = None

            save_cleaned_excel(
                st.session_state.cleaned_df.copy(),
                modified_cells,
                st.session_state.columns_to_check_dupes,
                incoherent_entry_dates,
                column_menus,
                smic_threshold
            )

            st.success("✅ Fusions appliquées avec succès. Le fichier Excel inclura les regroupements sélectionnés.")


# Boutons de téléchargement
with st.container():
    st.subheader("📥 Téléchargements disponibles")
    st.markdown("---")
    if st.session_state.ready_to_download:
        if st.session_state.error_doc:
            st.download_button("📄 Télécharger le rapport des erreurs", st.session_state.error_doc, file_name="rapport_erreurs.docx")
        if st.session_state.modif_doc:
            st.download_button("📄 Télécharger le rapport des modifications", st.session_state.modif_doc, file_name="rapport_modifications.docx")
        if st.session_state.excel_bytes:
            st.download_button("📊 Télécharger le fichier nettoyé (Excel)", st.session_state.excel_bytes, file_name="données_nettoyées.xlsx")
