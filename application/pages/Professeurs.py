# pages/Professeur.py - Page complète avec connexion DB
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# =========================
# IMPORT DE LA BASE DE DONNÉES
# =========================
try:
    from database import db
    DB_CONNECTED = True
except ImportError as e:
    st.error(f"❌ Erreur d'import de la base de données: {e}")
    DB_CONNECTED = False

# =========================
# CONFIGURATION
# =========================
st.set_page_config(
    page_title="Professeur - Plateforme Examens",
    page_icon="👨‍🏫",
    layout="wide"
)

# =========================
# FONCTIONS UTILITAIRES
# =========================

def test_db_connection():
    """Tester la connexion à la base de données"""
    if not DB_CONNECTED:
        return False, "Base de données non connectée"
    
    try:
        # Test simple de connexion
        query = "SELECT 1 as test"
        result = db.execute_query(query)
        if result is not None:
            return True, "✅ Connexion réussie"
        else:
            return False, "❌ Aucun résultat"
    except Exception as e:
        return False, f"❌ Erreur: {str(e)}"

def create_demo_examens():
    """Créer des données de démonstration pour les examens"""
    data = {
        'examen_id': [1, 2, 3],
        'module': [
            'Programmation Python',
            'Base de Données',
            'Réseaux Informatiques'
        ],
        'formation': [
            'Licence Informatique L3',
            'Master Informatique M1',
            'Licence Informatique L2'
        ],
        'salle': ['Amphi A', 'Salle 101', 'Labo Info 1'],
        'date_examen': [
            (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y'),
            (datetime.now() + timedelta(days=2)).strftime('%d/%m/%Y'),
            (datetime.now() + timedelta(days=3)).strftime('%d/%m/%Y')
        ],
        'heure_examen': ['09:00', '14:00', '10:30'],
        'duree_minutes': [120, 90, 120],
        'statut': ['planifie', 'planifie', 'planifie'],
        'nb_etudiants': [45, 32, 28]
    }
    return pd.DataFrame(data)

def create_demo_surveillances():
    """Créer des données de démonstration pour les surveillances"""
    data = {
        'surveillance_id': [1, 2, 3],
        'module': [
            'Algorithmique Avancée',
            'Base de Données',
            'Réseaux Informatiques'
        ],
        'formation': [
            'Licence Informatique L3',
            'Master Informatique M1',
            'Licence Informatique L2'
        ],
        'date_examen': [
            (datetime.now() + timedelta(days=2)).strftime('%d/%m/%Y'),
            (datetime.now() + timedelta(days=3)).strftime('%d/%m/%Y'),
            (datetime.now() + timedelta(days=5)).strftime('%d/%m/%Y')
        ],
        'heure_examen': ['08:30', '10:15', '13:30'],
        'duree_minutes': [120, 90, 120],
        'role': ['surveillant', 'surveillant', 'surveillant'],
        'priorite': [1, 1, 2],
        'heures_creditees': [2.0, 1.5, 2.0],
        'salle': ['Amphi A', 'Salle 101', 'Labo Info 1'],
        'professeur_responsable': [
            'Jean Martin',
            'Marie Dubois',
            'Pierre Lefevre'
        ],
        'statut': ['planifie', 'planifie', 'planifie']
    }
    return pd.DataFrame(data)

# =========================
# FONCTIONS DE DONNÉES - CONNEXION DB
# =========================

def get_professeur_info():
    """Récupérer les informations du professeur depuis la DB"""
    try:
        if not DB_CONNECTED:
            # Données de démo si DB non connectée
            return pd.Series({
                'id': 5,
                'matricule': 'PROF-INF-011',
                'nom': 'Martin',
                'prenom': 'Jean-Paul',
                'email': 'jeanpaul.martin@univ.fr',
                'specialite': 'Algorithmique',
                'charge_max_examens': 3,
                'total_surveillances': 0,
                'dept_id': 1,
                'departement': 'Informatique'
            })
        
        user_id = st.session_state.get('user_id')
        matricule = st.session_state.get('matricule')
        
        if not user_id and not matricule:
            st.error("❌ Aucune information d'utilisateur trouvée")
            return None
        
        # Essayer d'abord par user_id
        if user_id:
            query = """
            SELECT p.id, p.matricule, p.nom, p.prenom, p.email, p.specialite, 
                   p.charge_max_examens, p.total_surveillances, p.dept_id,
                   d.nom as departement
            FROM gestion_examens.professeurs p
            LEFT JOIN gestion_examens.departements d ON p.dept_id = d.id
            WHERE p.id = %s AND p.statut = 'actif'
            LIMIT 1
            """
            result = db.execute_query(query, (user_id,))
            if result is not None and not result.empty:
                return result.iloc[0]
        
        # Essayer par matricule
        if matricule:
            query = """
            SELECT p.id, p.matricule, p.nom, p.prenom, p.email, p.specialite, 
                   p.charge_max_examens, p.total_surveillances, p.dept_id,
                   d.nom as departement
            FROM gestion_examens.professeurs p
            LEFT JOIN gestion_examens.departements d ON p.dept_id = d.id
            WHERE p.matricule = %s AND p.statut = 'actif'
            LIMIT 1
            """
            result = db.execute_query(query, (matricule,))
            if result is not None and not result.empty:
                return result.iloc[0]
        
        return None
        
    except Exception as e:
        st.error(f"❌ Erreur de récupération: {str(e)}")
        return None

def get_examens_professeur(professeur_id):
    """Récupérer les examens du professeur depuis la DB"""
    try:
        if not DB_CONNECTED:
            st.warning("⚠️ Mode démo - Base de données non connectée")
            return create_demo_examens()
        
        query = f"""
        SELECT 
            e.id as examen_id,
            m.nom as module,
            f.nom as formation,
            s.nom as salle,
            TO_CHAR(e.date_heure, 'DD/MM/YYYY') as date_examen,
            TO_CHAR(e.date_heure, 'HH24:MI') as heure_examen,
            e.duree_minutes,
            e.statut,
            DATE(e.date_heure) as date_only,
            (
                SELECT COUNT(DISTINCT i.etudiant_id)
                FROM gestion_examens.inscriptions i
                WHERE i.module_id = e.module_id
                AND i.statut IN ('inscrit', 'en_cours')
            ) as nb_etudiants,
            (
                SELECT STRING_AGG(p2.prenom || ' ' || p2.nom, ', ')
                FROM gestion_examens.surveillances s2
                JOIN gestion_examens.professeurs p2 ON s2.professeur_id = p2.id
                WHERE s2.examen_id = e.id
                AND s2.role = 'surveillant'
            ) as co_surveillants
        FROM gestion_examens.examens e
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.formations f ON e.formation_id = f.id
        JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
        WHERE e.professeur_responsable_id = {professeur_id}
        AND e.statut IN ('planifie', 'confirme')
        ORDER BY e.date_heure
        """
        
        result = db.execute_query(query)
        if result is not None:
            return result
        else:
            return pd.DataFrame()
        
    except Exception as e:
        st.error(f"❌ Erreur DB examens: {str(e)}")
        return pd.DataFrame()

def get_surveillances_professeur(professeur_id):
    """Récupérer les surveillances du professeur depuis la DB"""
    try:
        if not DB_CONNECTED:
            st.warning("⚠️ Mode démo - Base de données non connectée")
            return create_demo_surveillances()
        
        query = f"""
        SELECT 
            s.id as surveillance_id,
            m.nom as module,
            f.nom as formation,
            TO_CHAR(e.date_heure, 'DD/MM/YYYY') as date_examen,
            TO_CHAR(e.date_heure, 'HH24:MI') as heure_examen,
            e.duree_minutes,
            s.role,
            s.priorite,
            s.heures_creditees,
            sa.nom as salle,
            pr.prenom || ' ' || pr.nom as professeur_responsable,
            e.statut
        FROM gestion_examens.surveillances s
        JOIN gestion_examens.examens e ON s.examen_id = e.id
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.formations f ON m.formation_id = f.id
        JOIN gestion_examens.salles_examen sa ON e.salle_id = sa.id
        JOIN gestion_examens.professeurs pr ON e.professeur_responsable_id = pr.id
        WHERE s.professeur_id = {professeur_id}
        AND e.statut IN ('planifie', 'confirme')
        ORDER BY e.date_heure
        """
        
        result = db.execute_query(query)
        if result is not None and not result.empty:
            st.success(f"✅ {len(result)} surveillance(s) trouvée(s)")
            return result
        else:
            # Vérifier si c'est PROF-INF-011 pour afficher données démo
            check_query = f"SELECT matricule FROM gestion_examens.professeurs WHERE id = {professeur_id}"
            prof_check = db.execute_query(check_query)
            if prof_check is not None and not prof_check.empty:
                matricule = prof_check.iloc[0]['matricule']
                if matricule == 'PROF-INF-011':
                    st.warning("⚠️ Aucune surveillance trouvée - Affichage données de démonstration")
                    return create_demo_surveillances()
            
            return pd.DataFrame()
        
    except Exception as e:
        st.error(f"❌ Erreur DB surveillances: {str(e)}")
        return pd.DataFrame()

def check_constraints(examens_df, professeur_info):
    """Vérifier les contraintes pour le professeur"""
    violations = []
    
    if examens_df.empty:
        return violations
    
    # Vérifier le maximum d'examens par jour
    if 'date_only' in examens_df.columns:
        examens_par_jour = examens_df.groupby('date_only').size()
        jours_depasses = examens_par_jour[examens_par_jour > professeur_info['charge_max_examens']]
        
        for date, count in jours_depasses.items():
            violations.append({
                'type': 'Dépassement limite examens/jour',
                'message': f"{count} examens le {date} (maximum: {professeur_info['charge_max_examens']})"
            })
    
    return violations

# =========================
# FONCTIONS D'EXPORT
# =========================

def export_to_csv(data, filename):
    """Exporter les données en CSV"""
    return data.to_csv(index=False).encode('utf-8')

def export_to_excel(data, filename):
    """Exporter les données en Excel"""
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        data.to_excel(writer, index=False, sheet_name='Données')
    return output.getvalue()

def export_to_pdf(data, title):
    """Exporter les données en PDF simple"""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    import io
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          rightMargin=2*cm, leftMargin=2*cm,
                          topMargin=2*cm, bottomMargin=2*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Titre
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 1*cm))
    
    # Informations
    story.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 1*cm))
    
    # Tableau
    if not data.empty:
        # Préparer les données
        table_data = [list(data.columns)]
        for _, row in data.iterrows():
            table_data.append([str(val) for val in row])
        
        # Créer le tableau
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# =========================
# AUTHENTIFICATION
# =========================
def check_professeur_auth():
    """Vérifier si l'utilisateur est un professeur connecté"""
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("⛔ Accès non autorisé. Veuillez vous connecter.")
        if st.button("🔐 Page de connexion"):
            st.switch_page("pages/Login.py")
        st.stop()
    
    if st.session_state.get('user_type') != 'professeur':
        st.error("⛔ Cette page est réservée aux professeurs")
        st.stop()

# =========================
# INTERFACE PRINCIPALE
# =========================

# Vérifier l'authentification
check_professeur_auth()

# Vérifier la connexion DB
connection_status, message = test_db_connection()
if not connection_status:
    st.warning(f"⚠️ {message} - Mode démonstration activé")

# Titre principal
st.title("👨‍🏫 Espace Professeur - Planning des Examens")

# Récupérer les informations du professeur
with st.spinner("Chargement de vos informations..."):
    prof_info = get_professeur_info()

if prof_info is None:
    st.error("❌ Impossible de charger vos informations de professeur.")
    st.stop()

# En-tête avec informations
st.markdown(f"""
<div style='background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    <h3 style='margin: 0;'>👋 Bienvenue, {prof_info['prenom']} {prof_info['nom']}</h3>
    <p style='margin: 5px 0; opacity: 0.9;'>
        <strong>Département:</strong> {prof_info['departement']} | 
        <strong>Spécialité:</strong> {prof_info['specialite']} |
        <strong>Limite examens/jour:</strong> {prof_info['charge_max_examens']} |
        <strong>Surveillances totales:</strong> {prof_info['total_surveillances']}
    </p>
</div>
""", unsafe_allow_html=True)

# Récupérer les données
with st.spinner("Chargement de vos données..."):
    examens_df = get_examens_professeur(prof_info['id'])
    surveillances_df = get_surveillances_professeur(prof_info['id'])
    violations = check_constraints(examens_df, prof_info)

# Onglets
tab1, tab2, tab3 = st.tabs(["📅 Mes Examens", "👥 Mes Surveillances", "⚠️ Vérifications"])

# TAB 1: MES EXAMENS
with tab1:
    st.header("Mes Examens Responsables")
    
    if not examens_df.empty:
        # Statistiques rapides
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total examens", len(examens_df))
        with col2:
            jours = examens_df['date_examen'].nunique() if 'date_examen' in examens_df.columns else 0
            st.metric("Jours d'examens", jours)
        with col3:
            heures_total = examens_df['duree_minutes'].sum() / 60 if 'duree_minutes' in examens_df.columns else 0
            st.metric("Heures totales", f"{heures_total:.1f}h")
        
        # Options d'export
        col_export1, col_export2 = st.columns([3, 1])
        with col_export2:
            export_format = st.selectbox(
                "Format d'export:",
                ["CSV", "Excel", "PDF"],
                key="export_examens"
            )
            
            if st.button("📥 Exporter", key="btn_export_examens", use_container_width=True):
                if export_format == "CSV":
                    csv_data = export_to_csv(examens_df, "mes_examens.csv")
                    st.download_button(
                        label="⬇️ Télécharger CSV",
                        data=csv_data,
                        file_name="mes_examens.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                elif export_format == "Excel":
                    excel_data = export_to_excel(examens_df, "mes_examens.xlsx")
                    st.download_button(
                        label="⬇️ Télécharger Excel",
                        data=excel_data,
                        file_name="mes_examens.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:  # PDF
                    pdf_data = export_to_pdf(examens_df, "Mes Examens")
                    st.download_button(
                        label="⬇️ Télécharger PDF",
                        data=pdf_data,
                        file_name="mes_examens.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        
        # Tableau des examens
        st.dataframe(
            examens_df[[
                'date_examen', 'heure_examen', 'module', 'formation', 
                'salle', 'nb_etudiants', 'duree_minutes'
            ]],
            use_container_width=True,
            height=400
        )
        
        # Graphique si plusieurs examens
        if len(examens_df) > 1 and 'date_examen' in examens_df.columns:
            exams_par_jour = examens_df.groupby('date_examen').size().reset_index(name='nb_examens')
            fig = px.bar(
                exams_par_jour,
                x='date_examen',
                y='nb_examens',
                title="Nombre d'examens par jour",
                labels={'date_examen': 'Date', 'nb_examens': 'Nombre d\'examens'}
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Aucun examen planifié")

# TAB 2: MES SURVEILLANCES
with tab2:
    st.header("Mes Surveillances")
    
    if not surveillances_df.empty:
        # Statistiques rapides
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total surveillances", len(surveillances_df))
        with col2:
            total_heures = surveillances_df['heures_creditees'].sum() if 'heures_creditees' in surveillances_df.columns else 0
            st.metric("Heures créditées", f"{total_heures:.1f}h")
        with col3:
            jours = surveillances_df['date_examen'].nunique() if 'date_examen' in surveillances_df.columns else 0
            st.metric("Jours concernés", jours)
        
        # Options d'export
        col_export1, col_export2 = st.columns([3, 1])
        with col_export2:
            export_format = st.selectbox(
                "Format d'export:",
                ["CSV", "Excel", "PDF"],
                key="export_surveillances"
            )
            
            if st.button("📥 Exporter", key="btn_export_surveillances", use_container_width=True):
                if export_format == "CSV":
                    csv_data = export_to_csv(surveillances_df, "mes_surveillances.csv")
                    st.download_button(
                        label="⬇️ Télécharger CSV",
                        data=csv_data,
                        file_name="mes_surveillances.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                elif export_format == "Excel":
                    excel_data = export_to_excel(surveillances_df, "mes_surveillances.xlsx")
                    st.download_button(
                        label="⬇️ Télécharger Excel",
                        data=excel_data,
                        file_name="mes_surveillances.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:  # PDF
                    pdf_data = export_to_pdf(surveillances_df, "Mes Surveillances")
                    st.download_button(
                        label="⬇️ Télécharger PDF",
                        data=pdf_data,
                        file_name="mes_surveillances.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        
        # Tableau des surveillances
        st.dataframe(
            surveillances_df[[
                'date_examen', 'heure_examen', 'module', 'formation',
                'salle', 'role', 'heures_creditees', 'professeur_responsable'
            ]],
            use_container_width=True,
            height=400
        )
        
        # Note pour données de démonstration
        if prof_info['matricule'] == 'PROF-INF-011' and prof_info['total_surveillances'] == 0:
            st.warning("""
            ⚠️ **Mode démonstration**  
            Les surveillances réelles apparaîtront après la mise à jour de la base de données.
            """)
    else:
        st.info("📭 Aucune surveillance attribuée")

# TAB 3: VÉRIFICATIONS
with tab3:
    st.header("Vérifications des Contraintes")
    
    if violations:
        st.error(f"**{len(violations)} problème(s) détecté(s)**")
        
        for violation in violations:
            with st.expander(f"❌ {violation['type']}", expanded=True):
                st.write(violation['message'])
        
        # Export des problèmes
        if st.button("📥 Exporter le rapport", key="btn_export_violations", use_container_width=True):
            violations_df = pd.DataFrame(violations)
            csv_data = export_to_csv(violations_df, "rapport_problemes.csv")
            st.download_button(
                label="⬇️ Télécharger CSV",
                data=csv_data,
                file_name="rapport_problemes.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.success("✅ Toutes les contraintes sont respectées !")

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(f"""
    <div style='text-align: center; padding: 15px; background: #1E40AF; border-radius: 10px; color: white; margin-bottom: 20px;'>
        <h5>{prof_info['prenom']} {prof_info['nom']}</h5>
        <p style='font-size: 0.8em;'>{prof_info['matricule']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Informations de connexion
    if not connection_status:
        st.error("❌ Base de données non connectée")
    else:
        st.success("✅ Base de données connectée")
    
    st.markdown("---")
    
    # Actions rapides
    if st.button("🔄 Actualiser les données", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    if st.button("🚪 Déconnexion", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# =========================
# FOOTER
# =========================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #6b7280; font-size: 0.8em; padding: 10px;'>
    🎓 Plateforme de Gestion des Examens | {datetime.now().strftime("%d/%m/%Y %H:%M")}
</div>
""", unsafe_allow_html=True)