# app.py - Page d'accueil après connexion (version embellie)
import streamlit as st
from database import db
import time
from datetime import datetime
import pandas as pd
import plotly.express as px

# Configuration
st.set_page_config(
    page_title="Accueil - Plateforme Examens",
    page_icon="🎓",
    layout="wide"
)

# CSS personnalisé
st.markdown("""
<style>
    /* Style global */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px 30px;
        border-radius: 20px;
        margin-bottom: 40px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 200%;
        background: linear-gradient(45deg, transparent 20%, rgba(255,255,255,0.1) 50%, transparent 80%);
        transform: rotate(30deg);
    }
    
    .user-info-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 18px;
        padding: 25px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        margin-bottom: 25px;
        border-left: 6px solid #667eea;
        transition: transform 0.3s ease;
    }
    
    .user-info-card:hover {
        transform: translateY(-3px);
    }
    
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 25px 20px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        text-align: center;
        transition: all 0.3s ease;
        border-top: 5px solid;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .metric-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 30px rgba(0,0,0,0.18);
    }
    
    .role-card {
        background: linear-gradient(135deg, var(--role-color) 0%, var(--role-color-dark) 100%);
        color: white;
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }
    
    .role-card::after {
        content: '';
        position: absolute;
        top: -20px;
        right: -20px;
        width: 80px;
        height: 80px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
    }
    
    .nav-card {
        background: white;
        border-radius: 16px;
        padding: 30px 25px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        text-align: center;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .nav-card:hover {
        border-color: #667eea;
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.2);
    }
    
    .nav-icon {
        font-size: 48px;
        margin-bottom: 15px;
        color: #667eea;
    }
    
    .time-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 15px 25px;
        display: inline-block;
        font-weight: bold;
        color: white;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        margin: 10px 0;
    }
    
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

def check_authentication():
    """Vérifier si l'utilisateur est connecté"""
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown('<h1 style="margin: 0;">🔐 Accès non autorisé</h1>', unsafe_allow_html=True)
        st.markdown('<p style="opacity: 0.9; font-size: 1.2rem;">Veuillez vous connecter pour accéder au système</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔐 Aller à la page de connexion", 
                        use_container_width=True, 
                        type="primary",
                        help="Cliquez pour vous connecter au système"):
                st.switch_page("pages/Login.py")
        st.stop()

def get_user_stats():
    """Récupérer les statistiques pour l'utilisateur"""
    try:
        stats = {}
        
        # Statistiques générales
        queries = {
            'etudiants': "SELECT COUNT(*) as nb FROM gestion_examens.etudiants WHERE statut = 'actif'",
            'examens': "SELECT COUNT(*) as nb FROM gestion_examens.examens WHERE statut = 'planifie'",
            'conflits': "SELECT COUNT(*) as nb FROM gestion_examens.vue_conflits",
            'professeurs': "SELECT COUNT(*) as nb FROM gestion_examens.professeurs WHERE statut = 'actif'"
        }
        
        for key, query in queries.items():
            result = db.execute_query(query)
            if result is not None and not result.empty:
                stats[key] = int(result['nb'].iloc[0])
            else:
                stats[key] = 0
                
        return stats
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des statistiques: {str(e)}")
        return {'etudiants': 0, 'examens': 0, 'conflits': 0, 'professeurs': 0}

def main():
    """Page d'accueil après connexion"""
    
    # Vérification de l'authentification
    check_authentication()
    
    # Définir les variables CSS selon le rôle
    user_type = st.session_state.get('type_utilisateur', 'utilisateur')
    
    role_colors = {
        'administrateur': '--role-color: #10B981; --role-color-dark: #059669;',
        'vice_doyen': '--role-color: #8B5CF6; --role-color-dark: #7C3AED;',
        'chef_departement': '--role-color: #3B82F6; --role-color-dark: #2563EB;',
        'professeur': '--role-color: #F59E0B; --role-color-dark: #D97706;',
        'etudiant': '--role-color: #EF4444; --role-color-dark: #DC2626;',
        'utilisateur': '--role-color: #667eea; --role-color-dark: #764ba2;'
    }
    
    role_titles = {
        'administrateur': 'Administrateur Système',
        'vice_doyen': 'Vice-Doyen',
        'chef_departement': 'Chef de Département',
        'professeur': 'Professeur',
        'etudiant': 'Étudiant',
        'utilisateur': 'Utilisateur'
    }
    
    role_emojis = {
        'administrateur': '⚙️',
        'vice_doyen': '👑',
        'chef_departement': '👨‍💼',
        'professeur': '👨‍🏫',
        'etudiant': '🎓',
        'utilisateur': '👤'
    }
    
    # Sidebar améliorée
    with st.sidebar:
        # Carte d'information utilisateur
        st.markdown(f'''
        <style>
            .sidebar-role {{ {role_colors.get(user_type, role_colors['utilisateur'])} }}
        </style>
        <div class="user-info-card sidebar-role">
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <div style="font-size: 50px; margin-right: 15px;">
                    {role_emojis.get(user_type, '👤')}
                </div>
                <div>
                    <h3 style="margin: 0 0 5px 0; color: #333;">{st.session_state.get('nom_complet', 'Utilisateur')}</h3>
                    <p style="margin: 0; color: #666; font-size: 14px;">
                        {role_titles.get(user_type, 'Utilisateur')}
                    </p>
                    <p style="margin: 5px 0 0 0; color: #999; font-size: 12px;">
                        {st.session_state.get('matricule', 'N/A')}
                    </p>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Heure et date
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%A %d %B %Y")
        
        st.markdown(f'''
        <div style="text-align: center; margin: 25px 0;">
            <div class="time-display">
                <div style="font-size: 24px; margin-bottom: 5px;">🕐 {current_time}</div>
                <div style="font-size: 16px; opacity: 0.9;">📅 {current_date}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Bouton déconnexion
        col_logout1, col_logout2 = st.columns([1, 1])
        with col_logout1:
            if st.button("🔄 Actualiser", 
                        use_container_width=True,
                        help="Rafraîchir la page"):
                st.rerun()
        
        with col_logout2:
            if st.button("🚪 Déconnexion", 
                        use_container_width=True, 
                        type="secondary",
                        help="Se déconnecter du système"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("✅ Déconnexion réussie!")
                time.sleep(1)
                st.switch_page("app.py")
        
        # Informations système
        st.markdown("---")
        st.markdown("### 📊 Système")
        
        try:
            stats = get_user_stats()
            st.metric("👥 Étudiants actifs", f"{stats['etudiants']:,}")
            st.metric("📝 Examens planifiés", stats['examens'])
        except:
            st.info("ℹ️ Les statistiques ne sont pas disponibles")
    
    # En-tête principal
    st.markdown(f'''
    <div class="main-header">
        <h1 style="margin: 0 0 15px 0; font-size: 2.8rem;">
            {role_emojis.get(user_type, '🎓')} Bienvenue, {st.session_state.get('nom_complet', 'Cher utilisateur')}!
        </h1>
        <p style="opacity: 0.9; font-size: 1.3rem; margin: 0;">
            Plateforme d'Optimisation des EDT d'Examens Universitaires
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Section rôle avec style dynamique
    st.markdown(f'''
    <style>
        .dynamic-role-card {{ {role_colors.get(user_type, role_colors['utilisateur'])} }}
    </style>
    <div class="role-card dynamic-role-card">
        <div style="font-size: 60px; margin-bottom: 15px;">
            {role_emojis.get(user_type, '👤')}
        </div>
        <h2 style="margin: 10px 0;">{role_titles.get(user_type, 'Utilisateur')}</h2>
        <p style="opacity: 0.9; font-size: 1.1rem; margin: 0;">
            Vous avez accès aux fonctionnalités spécifiques à votre rôle
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Statistiques principales
    st.subheader("📈 Vue d'ensemble du système")
    
    stats = get_user_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        metric_color = "#10B981"
        st.markdown(f'''
        <div class="metric-card" style="border-top-color: {metric_color};">
            <div style="font-size: 36px; color: {metric_color}; margin-bottom: 10px;">👨‍🎓</div>
            <div style="font-size: 32px; font-weight: bold; color: #333; margin-bottom: 5px;">
                {stats['etudiants']:,}
            </div>
            <div style="font-size: 14px; color: #666;">Étudiants actifs</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        metric_color = "#3B82F6"
        st.markdown(f'''
        <div class="metric-card" style="border-top-color: {metric_color};">
            <div style="font-size: 36px; color: {metric_color}; margin-bottom: 10px;">📝</div>
            <div style="font-size: 32px; font-weight: bold; color: #333; margin-bottom: 5px;">
                {stats['examens']}
            </div>
            <div style="font-size: 14px; color: #666;">Examens planifiés</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        metric_color = "#EF4444"
        st.markdown(f'''
        <div class="metric-card" style="border-top-color: {metric_color};">
            <div style="font-size: 36px; color: {metric_color}; margin-bottom: 10px;">⚠️</div>
            <div style="font-size: 32px; font-weight: bold; color: #333; margin-bottom: 5px;">
                {stats['conflits']}
            </div>
            <div style="font-size: 14px; color: #666;">Conflits détectés</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        metric_color = "#8B5CF6"
        st.markdown(f'''
        <div class="metric-card" style="border-top-color: {metric_color};">
            <div style="font-size: 36px; color: {metric_color}; margin-bottom: 10px;">👨‍🏫</div>
            <div style="font-size: 32px; font-weight: bold; color: #333; margin-bottom: 5px;">
                {stats['professeurs']}
            </div>
            <div style="font-size: 14px; color: #666;">Professeurs actifs</div>
        </div>
        ''', unsafe_allow_html=True)
    
    # Navigation rapide selon le type d'utilisateur
    st.markdown("---")
    st.subheader("🚀 Navigation rapide")
    
    if user_type == 'vice_doyen':
        cols = st.columns(3)
        
        with cols[0]:
            st.markdown(f'''
            <div class="nav-card">
                <div class="nav-icon">📊</div>
                <h3>Tableau de Bord</h3>
                <p style="color: #666; font-size: 14px;">Vue stratégique globale et KPIs</p>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Accéder", key="vd_dash", use_container_width=True):
                st.switch_page("pages/Vice_Doyen.py")
        
        with cols[1]:
            st.markdown(f'''
            <div class="nav-card">
                <div class="nav-icon">📈</div>
                <h3>Statistiques</h3>
                <p style="color: #666; font-size: 14px;">Analyses détaillées par département</p>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Accéder", key="vd_stats", use_container_width=True):
                st.switch_page("pages/Vice_Doyen.py#statistiques")
        
        with cols[2]:
            st.markdown(f'''
            <div class="nav-card">
                <div class="nav-icon">⚠️</div>
                <h3>Conflits</h3>
                <p style="color: #666; font-size: 14px;">Détection et résolution des conflits</p>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Accéder", key="vd_conflicts", use_container_width=True):
                st.switch_page("pages/Vice_Doyen.py#conflits")
    
    elif user_type == 'administrateur':
        cols = st.columns(2)
        
        with cols[0]:
            st.markdown(f'''
            <div class="nav-card">
                <div class="nav-icon">📅</div>
                <h3>Planification</h3>
                <p style="color: #666; font-size: 14px;">Gérer la planification des examens</p>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Accéder", key="admin_plan", use_container_width=True):
                st.switch_page("pages/Administrateur.py")
        
        with cols[1]:
            st.markdown(f'''
            <div class="nav-card">
                <div class="nav-icon">⚙️</div>
                <h3>Optimisation</h3>
                <p style="color: #666; font-size: 14px;">Optimiser les ressources et EDT</p>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Accéder", key="admin_opt", use_container_width=True):
                st.switch_page("pages/Administrateur.py#optimisation")
    
    elif user_type == 'chef_departement':
        st.markdown(f'''
        <div class="nav-card">
            <div class="nav-icon">📊</div>
            <h3>Mon Département</h3>
            <p style="color: #666; font-size: 14px;">Statistiques et gestion du département</p>
        </div>
        ''', unsafe_allow_html=True)
        if st.button("📈 Accéder au tableau de bord", key="chef_dept", use_container_width=True):
            st.switch_page("pages/Chef_Departement.py")
    
    elif user_type == 'professeur':
        st.markdown(f'''
        <div class="nav-card">
            <div class="nav-icon">📅</div>
            <h3>Mon Emploi du Temps</h3>
            <p style="color: #666; font-size: 14px;">Consulter mes examens et surveillances</p>
        </div>
        ''', unsafe_allow_html=True)
        if st.button("📅 Voir mon EDT", key="prof_edt", use_container_width=True):
            st.switch_page("pages/Professeurs.py")
    
    elif user_type == 'etudiant':
        st.markdown(f'''
        <div class="nav-card">
            <div class="nav-icon">📚</div>
            <h3>Mes Examens</h3>
            <p style="color: #666; font-size: 14px;">Consulter mon planning d'examens</p>
        </div>
        ''', unsafe_allow_html=True)
        if st.button("📚 Voir mes examens", key="etu_exams", use_container_width=True):
            st.switch_page("pages/Etudiants.py")
    
    # Section activité récente (simulée)
    st.markdown("---")
    st.subheader("📋 Activité récente")
    
    col_act1, col_act2 = st.columns([2, 1])
    
    with col_act1:
        # Graphique d'activité simulé
        activity_data = pd.DataFrame({
            'Jour': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
            'Examens': [42, 48, 35, 52, 45, 20],
            'Utilisateurs': [120, 145, 110, 165, 130, 75]
        })
        
        fig = px.line(
            activity_data,
            x='Jour',
            y=['Examens', 'Utilisateurs'],
            title="Activité hebdomadaire",
            markers=True,
            color_discrete_sequence=['#667eea', '#10B981']
        )
        
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_act2:
        st.markdown("### 📊 Performance")
        
        performance_data = {
            "Temps réponse": "0.8s",
            "Disponibilité": "99.9%",
            "Satisfaction": "94%",
            "Conflits résolus": "92%"
        }
        
        for label, value in performance_data.items():
            st.metric(label, value)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px; font-size: 14px;">
        <p>🎓 <strong>Plateforme d'Optimisation des EDT d'Examens Universitaires</strong> | Version 2.0</p>
        <p>© 2024 - Système de gestion des emplois du temps | Tous droits réservés</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()