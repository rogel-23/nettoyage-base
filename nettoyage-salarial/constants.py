abbreviation_mapping = {
    "TECH": "TECHNICIEN",
    "EMP": "EMPLOYÉ",
    "AGT": "AGENT",
    "AG DE MAI": "AGENT DE MAINTENANCE",
    "CAD": "CADRE",
    "ING": "INGÉNIEUR",
    "RESP": "RESPONSABLE",
    "DIR": "DIRECTEUR",
}

# Dictionnaires de reconnaissance automatique
id_columns = [
    "Identifiant du collaborateur", "ID employé", "Employee ID", "Matricule",
    "Numéro de collaborateur", "ID personnel", "UID", "User ID", "ID RH",
    "Numéro d'identification", "Identifiant collaborateur", "Code Emploi"
]
nplus1_columns = [
    "Matricule du N+1", "ID du manager", "Manager ID", "Identifiant du N+1", "N+1", "UID N+1"
]
date_columns = [
    "Date de naissance", "Birth Date", "Naissance", "Date_Naissance",
    "DOB", "Date de naissance complète"
]
entry_date_columns = [
    "Date d'entrée", "Date d’embauche", "Hire Date", "Start Date", "Date_Entree", "Année/Date d'entrée société"
]
date_exceptions = [
    "Année de naissance", "Année_Naissance", "Birth Year", "Age", "Âge", "Âge actuel"
]
entry_year_exceptions = [
    "Année d'entrée société", "Année d'entrée", "Year of Entry", "Entry Year", "Ancienneté année"
]
seniority_date_columns = [
    "Date d'ancienneté", "Ancienneté date", "Seniority Date", "Date de début d'ancienneté"
]
seniority_exceptions = [
    "Ancienneté société", "Ancienneté en années", "Seniority (years)", "Years of Service"
]
position_entry_date_columns = [
    "Date d'entrée poste", "Date prise de poste", "Position Start Date", "Date début poste"
]
exit_date_columns = [
    "Date de sortie", "Date de départ", "End Date", "Date fin contrat"
]
gender_columns = [
    "Genre", "Sexe", "Gender", "Sex", "Civilité"
]
hours_columns = [
    "Horaires", "Temps de travail", "Heures", "Heures hebdomadaires", "Durée du travail",
    "Working Hours", "Weekly Hours", "Work Time", "Work Hours"
]
workload_columns = [
    "Taux d'activité", "Temps de travail (en %)", "Temps partiel", "Working Rate", "Workload", "Activity Rate"
]
workingtime_columns = [
    "Horaires", "Temps de travail", "Heures", "Heures hebdomadaires", "Durée du travail",
    "Working Hours", "Weekly Hours", "Work Time", "Work Hours",
    "Taux d'activité", "Temps de travail (en %)", "Temps partiel", "Working Rate", "Workload", "Activity Rate",
    "Forfait jours", "Forfait", "Nombre de jours", "Forfait J"
]
contract_columns = ["Contrat", "Type de contrat", "Nature du contrat", "Type contrat"]
status_columns = ["Statut", "Niveau", "Fonction", "Catégorie", "Statut (2)", "Statut2"]
region_columns = ["Région", "Region", "Zone géographique", "Région administrative", "Localisation géographique"]
postal_code_columns = ["Code postal", "Postal Code", "CP", "ZIP", "ZIP Code", "Code ZIP", "Code_postal"]
city_columns = ["Ville", "ville", "Ville collaborateur", "Localisation", "Ville de travail"]
segmentation_columns = [
    "Nom Segmentation",
    "Nom Segmentation Famille",
    "Nom Segmentation Emploi",
    "Nom Segmentation Secteur",
    "Nom Segmentation Métier",
    "Famille Emploi",
    "Famille métier",
    "Secteur emploi",
    "Secteur métier",
    "Domaine métier",
    "Catégorie métier",
    "Nom segment métier",
    "Nom segment RH",
    "Libellé métier",
    "Nom segmentation RH",
    "Nom de la famille d’emplois",
    "Famille RH",
    "Nom emploi type",
    "Famille professionnelle"
]
job_title_columns = [
    "Poste", "Emploi repère", "Nom du poste", "Nom emploi repère",
    "Intitulé du poste", "Titre de poste", "Libellé emploi",
    "Intitulé emploi", "Fonction RH", "Nom de l'emploi", "Emploi type"
]
job_columns = ["Poste", "Emploi repère", "Intitulé de poste", "Libellé poste", "Nom du poste", "Job title"]
convention_columns = ["Convention", "Convention collective", "Convention applicable", "Libellé convention", "Nom de la convention"]
idcc_columns = ["IDCC", "Code IDCC", "Identifiant IDCC"]
coefficient_columns = ["Coefficient", "Niveau hiérarchique", "Code coefficient", "Niveau conventionnel"]
base_salary_columns = [
    "Salaire de base (hors toutes primes)",
    "Salaire de base",
    "Base salary",
    "Fixed salary",
    "FIXSAL",
    "Salaire fixe"
]

financial_keywords = [
    "prime", "primes", "montant", "heure", "participation", "intéress", "astrei", "stock", "action", "cash",
    "abondement", "retraite", "forfait repas", "voiture", "avantage", "actionnariat", "commission", "commissions",
    "avance", "avances", "véhicule", "vehicule", "véhicules", "vehicules", "nature", "logement", "indemn", "bonus",
    "compl", "variable", "salaire", "epargne", "épargne", "lti","rémunération", "remuneration"
]


contrat_mapping = {
    "cdi": "CDI",
    "contrat à durée indéterminée": "CDI",
    "contrat durée indéterminée": "CDI",

    "cdd": "CDD",
    "contrat à durée déterminée": "CDD",
    "contrat durée déterminée": "CDD",

    "stage": "Stage",
    "stagiaire": "Stage",

    "apprentissage": "Contrat d'apprentissage",
    "alternance": "Contrat d'apprentissage",
    "contrat d'apprentissage": "Contrat d'apprentissage",
    "apprenti": "Contrat d'apprentissage",
}