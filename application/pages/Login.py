# pages/Login.py - النسخة المعدلة
import streamlit as st
from database import db

# Configuration de la page
st.set_page_config(
    page_title="Connexion - Plateforme Examens",
    page_icon="🔐",
    layout="centered"
)

# Titre
st.markdown('<h1 style="text-align: center; color: #1E3A8A;">🔐 Connexion au Système</h1>', 
            unsafe_allow_html=True)

# Formulaire de connexion simplifié
with st.form("login_form"):
    st.subheader("Identifiants de connexion")
    
    # إزالة اختيار نوع المستخدم - النظام يكتشف النوع تلقائياً
    matricule = st.text_input("Matricule", placeholder="Ex: VD-001, ADMIN-001, etc.")
    mot_de_passe = st.text_input("Mot de passe", type="password")
    
    submit = st.form_submit_button("Se Connecter")
    
    if submit:
        if not matricule or not mot_de_passe:
            st.error("Veuillez remplir tous les champs")
        else:
            with st.spinner("Vérification en cours..."):
                try:
                    # Appel de la fonction de vérification dans la base de données
                    query = """
                        SELECT * FROM gestion_examens.verifier_authentification(%s, %s)
                    """
                    
                    df = db.execute_query(query, (matricule, mot_de_passe))
                    
                    if not df.empty:
                        # Sauvegarde des informations dans la session
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = df['id'].iloc[0]
                        st.session_state['matricule'] = df['matricule'].iloc[0]
                        st.session_state['user_type'] = df['type_utilisateur'].iloc[0]
                        st.session_state['nom_complet'] = df['nom_complet'].iloc[0]
                        st.session_state['statut'] = df['statut'].iloc[0]
                        
                        # Mise à jour de la dernière connexion
                        try:
                            db.execute_procedure("gestion_examens.mettre_a_jour_connexion", 
                                               [st.session_state['user_id']])
                        except:
                            pass  # Ignore si la procédure n'existe pas
                        
                        st.success(f"✅ Connexion réussie! Bienvenue {st.session_state['nom_complet']}")
                        
                        # Redirection automatique selon le type d'utilisateur
                        st.rerun()
                    else:
                        st.error("❌ Matricule ou mot de passe incorrect")
                        
                except Exception as e:
                    st.error(f"Erreur système: {str(e)}")

# Comptes de test pour la démonstration
with st.expander("🔑 Comptes de test"):
    st.markdown("""
    **Comptes disponibles pour le test :**
    
    | Rôle | Matricule | Mot de passe |
    |------|-----------|--------------|
    | 👑 Vice-Doyen | `VD-001` | `vicedoyen123` |
    | ⚙️ Administrateur | `ADMIN-001` | `admin123` |
    | 📊 Chef Département (Info) | `CHEF-INF-001` | `chef123` |
    | 👨‍🏫 Professeur | `PROF-INF-011` | `011` |
    | 👨‍🎓 Étudiant | `ETU-2024-00001` | `00001` |
    
    **Note :** Le système détecte automatiquement votre rôle.
    """)

# Redirection automatique après connexion réussie
if 'logged_in' in st.session_state and st.session_state['logged_in']:
    user_type = st.session_state['user_type']
    
    # Mapping des types vers les pages
    page_map = {
        'vice_doyen': 'Vice_Doyen',
        'administrateur': 'Administrateur',
        'chef_departement': 'Chef_Departement',
        'professeur': 'Professeurs',
        'etudiant': 'Etudiants'
    }
    
    if user_type in page_map:
        # Redirection automatique
        target_page = page_map[user_type]
        st.switch_page(f"pages/{target_page}.py")
    else:
        st.error(f"Type d'utilisateur non reconnu: {user_type}")