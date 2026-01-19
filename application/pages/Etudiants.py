import streamlit as st
import pandas as pd
from datetime import datetime
from database import db

# Import pour génération PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
import io

# =========================
# CONFIGURATION
# =========================
st.set_page_config(
    page_title="Étudiant - Plateforme Examens",
    page_icon="👨‍🎓",
    layout="wide"
)

# =========================
# FONCTIONS POUR GÉNÉRER PDF
# =========================

def generer_pdf_etudiant(student_info, planning_df, violations):
    """Générer un PDF personnalisé pour l'étudiant"""
    # Créer le buffer
    buffer = io.BytesIO()
    
    # Créer le document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Style personnalisé
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor('#1e40af')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=10,
        textColor=colors.HexColor('#374151')
    )
    
    # En-tête du document
    story.append(Paragraph("EMPLOI DU TEMPS D'EXAMENS", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informations étudiant
    story.append(Paragraph(f"Étudiant: {student_info['prenom']} {student_info['nom']}", header_style))
    story.append(Paragraph(f"Matricule: {student_info['matricule']}", styles['Normal']))
    story.append(Paragraph(f"Formation: {student_info['formation']}", styles['Normal']))
    story.append(Paragraph(f"Département: {student_info['departement']}", styles['Normal']))
    story.append(Paragraph(f"Groupe: {student_info['groupe']}", styles['Normal']))
    story.append(Paragraph(f"Promotion: {student_info['promo']}", styles['Normal']))
    story.append(Paragraph(f"Date de génération: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    
    story.append(Spacer(1, 1*cm))
    
    # Section des examens si disponibles
    if not planning_df.empty:
        story.append(Paragraph("📅 PLANNING DES EXAMENS", header_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Préparer les données pour le tableau
        table_data = []
        
        # En-tête du tableau
        headers = ['Date', 'Heure', 'Matière', 'Salle', 'Professeur', 'Durée']
        table_data.append(headers)
        
        # Données des examens
        for _, row in planning_df.iterrows():
            table_data.append([
                row.get('date_examen', ''),
                row.get('heure_examen', ''),
                str(row.get('module_nom', ''))[:30],
                row.get('salle', ''),
                str(row.get('professeur', ''))[:20],
                f"{row.get('duree_minutes', '')} min" if pd.notna(row.get('duree_minutes')) else ''
            ])
        
        # Créer le tableau
        table = Table(table_data, colWidths=[3*cm, 2*cm, 5*cm, 3*cm, 4*cm, 2*cm])
        
        # Style du tableau
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
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
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 1*cm))
        
        # Statistiques
        story.append(Paragraph("📊 STATISTIQUES", header_style))
        stats_text = f"""
        • Nombre total d'examens: {len(planning_df)}<br/>
        • Nombre de jours d'examens: {planning_df['date_only'].nunique() if 'date_only' in planning_df.columns else 'N/A'}<br/>
        • Premier examen: {planning_df['date_examen'].min() if not planning_df.empty else 'N/A'}<br/>
        • Dernier examen: {planning_df['date_examen'].max() if not planning_df.empty else 'N/A'}<br/>
        """
        story.append(Paragraph(stats_text, styles['Normal']))
    
    # Section des problèmes si existants
    if violations:
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("⚠️ PROBLÈMES DÉTECTÉS", header_style))
        
        for violation in violations:
            severity_color = colors.red if violation['severity'] == 'high' else colors.orange
            story.append(Paragraph(
                f"• {violation['type']}: {violation['message']}",
                ParagraphStyle(
                    'ProblemStyle',
                    parent=styles['Normal'],
                    textColor=severity_color,
                    fontSize=9,
                    leftIndent=20
                )
            ))
    
    # Pied de page
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        "Ce document a été généré automatiquement par le système de gestion des examens.",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
    ))
    
    # Générer le PDF
    doc.build(story)
    
    # Retourner le buffer
    buffer.seek(0)
    return buffer

# =========================
# VÉRIFICATION AUTHENTIFICATION
# =========================
def check_student_auth():
    """Vérifier si l'utilisateur est un étudiant connecté"""
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("⛔ Accès non autorisé. Veuillez vous connecter.")
        if st.button("🔐 Page de connexion"):
            st.switch_page("pages/Login.py")
        st.stop()
    
    if st.session_state.get('user_type') != 'etudiant':
        st.error("⛔ Cette page est réservée aux étudiants")
        st.stop()

check_student_auth()

# =========================
# FONCTIONS DE VÉRIFICATION DES CONTRRAINTES
# =========================

def get_student_info_from_session():
    """Récupérer les informations de l'étudiant"""
    try:
        matricule = st.session_state.get('matricule')
        
        if not matricule:
            return None
        
        query = """
        SELECT 
            e.id, e.matricule, e.nom, e.prenom, e.email,
            e.promo, e.annee_inscription, e.statut,
            f.nom as formation, d.nom as departement,
            COALESCE(g.nom, 'Non assigné') as groupe,
            e.formation_id
        FROM gestion_examens.etudiants e
        JOIN gestion_examens.formations f ON e.formation_id = f.id
        JOIN gestion_examens.departements d ON f.dept_id = d.id
        LEFT JOIN gestion_examens.groupes g ON e.groupe_id = g.id
        WHERE e.matricule = %s
        LIMIT 1
        """
        
        result = db.execute_query(query, (matricule,))
        
        if result is None or result.empty:
            return None
        
        return result.iloc[0]
        
    except Exception as e:
        st.error(f"Erreur récupération info étudiant: {str(e)}")
        return None

def get_planning_etudiant_with_constraints(matricule):
    """Récupérer les examens avec vérification des contraintes"""
    try:
        query = """
        WITH etudiant_info AS (
            SELECT 
                e.id as etudiant_id,
                e.formation_id
            FROM gestion_examens.etudiants e
            WHERE e.matricule = %s
            LIMIT 1
        ),
        modules_etudiant AS (
            SELECT DISTINCT i.module_id
            FROM gestion_examens.inscriptions i
            WHERE i.etudiant_id = (SELECT etudiant_id FROM etudiant_info)
        )
        SELECT DISTINCT
            m.nom as module_nom,
            f.nom as formation,
            d.nom as departement,
            p.prenom || ' ' || p.nom as professeur,
            p.id as professeur_id,
            s.nom as salle,
            s.type as type_salle,
            TO_CHAR(ex.date_heure, 'DD/MM/YYYY') as date_examen,
            TO_CHAR(ex.date_heure, 'HH24:MI') as heure_examen,
            ex.duree_minutes,
            ex.date_heure,
            ex.statut,
            ex.id as examen_id,
            DATE(ex.date_heure) as date_only
        FROM modules_etudiant me
        JOIN gestion_examens.examens ex ON me.module_id = ex.module_id
        JOIN gestion_examens.modules m ON ex.module_id = m.id
        JOIN gestion_examens.formations f ON ex.formation_id = f.id
        JOIN gestion_examens.departements d ON f.dept_id = d.id
        JOIN gestion_examens.professeurs p ON ex.professeur_responsable_id = p.id
        JOIN gestion_examens.salles_examen s ON ex.salle_id = s.id
        WHERE ex.statut IN ('planifie', 'confirme')
        AND f.id = (SELECT formation_id FROM etudiant_info)
        ORDER BY ex.date_heure
        """
        
        result = db.execute_query(query, (matricule,))
        
        if result is None:
            return pd.DataFrame()
        
        return result if not result.empty else pd.DataFrame()
        
    except Exception as e:
        st.error(f"Erreur récupération planning: {str(e)}")
        return pd.DataFrame()

def check_constraints(planning_df, student_info):
    """Vérifier les contraintes d'emploi du temps"""
    violations = []
    
    if planning_df.empty:
        return violations
    
    # 1. Vérifier les examens dupliqués
    duplicates = planning_df.duplicated(subset=['module_nom', 'date_only', 'heure_examen'], keep=False)
    if duplicates.any():
        dup_exams = planning_df[duplicates]
        for date in dup_exams['date_only'].unique():
            date_exams = dup_exams[dup_exams['date_only'] == date]
            violations.append({
                'type': 'Examen dupliqué',
                'message': f"Plusieurs examens du même module le {date}",
                'details': f"{len(date_exams)} examens identiques trouvés",
                'severity': 'high'
            })
    
    # 2. Vérifier les examens multiples le même jour pour l'étudiant
    exams_per_day = planning_df.groupby('date_only').size()
    multiple_exams_days = exams_per_day[exams_per_day > 1]
    
    for date, count in multiple_exams_days.items():
        day_exams = planning_df[planning_df['date_only'] == date]
        violations.append({
            'type': 'Étudiant - Multiples examens/jour',
            'message': f"{count} examens le {date} (max: 1)",
            'details': f"Modules: {', '.join(day_exams['module_nom'].unique())}",
            'severity': 'high'
        })
    
    # 3. Vérifier les professeurs surchargés
    if 'professeur_id' in planning_df.columns:
        prof_exams_per_day = planning_df.groupby(['professeur', 'date_only']).size()
        overloaded_profs = prof_exams_per_day[prof_exams_per_day > 3]
        
        for (prof, date), count in overloaded_profs.items():
            violations.append({
                'type': 'Professeur surchargé',
                'message': f"{prof} a {count} examens le {date} (max: 3)",
                'details': f"Limite dépassée de {count - 3} examens",
                'severity': 'medium'
            })
    
    return violations


def get_upcoming_exam_alerts(planning_df, days_ahead=3):
    """الحصول على تنبيهات للامتحانات القريبة"""
    alerts = []
    today = datetime.now().date()
    
    for _, exam in planning_df.iterrows():
        exam_date = exam.get('date_only')
        if exam_date:
            days_diff = (exam_date - today).days
            if 0 <= days_diff <= days_ahead:
                alerts.append({
                    'module': exam.get('module_nom'),
                    'date': exam.get('date_examen'),
                    'heure': exam.get('heure_examen'),
                    'days_left': days_diff,
                    'urgence': 'haut' if days_diff == 0 else 'moyen'
                })
    
    return alerts

# في قسم التحليلات
def display_calendar_view(planning_df):
    """عرض التقويم الشهري"""
    import calendar
    
    st.subheader("📅 Vue Calendrier")
    
    # تحويل التواريخ
    planning_df['date_obj'] = pd.to_datetime(planning_df['date_examen'], format='%d/%m/%Y')
    
    # إنشاء تقويم
    month = planning_df['date_obj'].dt.month.iloc[0] if not planning_df.empty else datetime.now().month
    year = planning_df['date_obj'].dt.year.iloc[0] if not planning_df.empty else datetime.now().year
    
    cal = calendar.monthcalendar(year, month)
    
    # عرض التقويم
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    day_exams = planning_df[planning_df['date_obj'].dt.day == day]
                    if not day_exams.empty:
                        st.markdown(f"<div style='background:#3b82f6;color:white;border-radius:5px;padding:5px;'>{day}</div>", unsafe_allow_html=True)
                        st.caption(f"{len(day_exams)} exam")
                    else:
                        st.write(day)

def analyze_exam_schedule(planning_df):
    """Analyser la répartition des examens"""
    analysis = {}
    
    if planning_df.empty:
        return analysis
    
    # Répartition par date
    analysis['par_date'] = planning_df.groupby('date_examen').agg({
        'module_nom': 'count',
        'heure_examen': lambda x: ', '.join(sorted(set(x)))
    }).rename(columns={'module_nom': 'nb_examens', 'heure_examen': 'heures'})
    
    # Répartition par professeur
    if 'professeur' in planning_df.columns:
        analysis['par_professeur'] = planning_df.groupby('professeur').agg({
            'examen_id': 'count',
            'date_examen': lambda x: len(set(x))
        }).rename(columns={'examen_id': 'nb_examens', 'date_examen': 'nb_jours'})
    
    # Répartition par salle
    if 'salle' in planning_df.columns:
        analysis['par_salle'] = planning_df.groupby('salle').agg({
            'examen_id': 'count',
            'date_examen': lambda x: len(set(x))
        }).rename(columns={'examen_id': 'nb_examens', 'date_examen': 'nb_jours'})
    
    return analysis

# =========================
# INTERFACE PRINCIPALE
# =========================

# Titre
st.title("👨‍🎓 Espace Étudiant - Emploi du Temps Intelligent")

# Récupérer le matricule de la session
matricule = st.session_state.get('matricule', 'ETU-2024-00001')

# Récupérer les informations de l'étudiant
student_info = get_student_info_from_session()

if student_info is None:
    st.error("❌ Impossible de charger vos informations.")
    st.stop()

# Récupérer le planning avec contraintes
planning = get_planning_etudiant_with_constraints(matricule)

# Vérifier les contraintes
violations = check_constraints(planning, student_info)

# Analyser l'emploi du temps
analysis = analyze_exam_schedule(planning)

# En-tête
st.markdown(f"""
<div style='background: #f0f9ff; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    <h3 style='margin: 0; color: #1e40af;'>👋 Bienvenue, {student_info['prenom']} {student_info['nom']}</h3>
    <p style='margin: 5px 0; color: #4b5563;'>
        <strong>Matricule:</strong> {student_info['matricule']} | 
        <strong>Formation:</strong> {student_info['formation']}
    </p>
</div>
""", unsafe_allow_html=True)

# Onglets
tab1, tab2, tab3, tab4 = st.tabs(["📅 Emploi du Temps", "⚠️ Vérifications", "📊 Analyse", "📄 Télécharger PDF"])

# TAB 1: EMPLOI DU TEMPS
with tab1:
    st.header("📅 Mon Emploi du Temps d'Examens")
    
    if not planning.empty:
        # Filtrer par formation
        if 'formation' in planning.columns:
            planning = planning[planning['formation'] == student_info['formation']]
        
        if not planning.empty:
            # Afficher un résumé
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total examens", len(planning))
            
            with col2:
                dates_uniques = planning['date_only'].nunique()
                st.metric("Jours d'examens", dates_uniques)
            
            with col3:
                if 'professeur' in planning.columns:
                    profs_uniques = planning['professeur'].nunique()
                    st.metric("Professeurs", profs_uniques)
            
            with col4:
                if violations:
                    st.metric("⚠️ Problèmes", len(violations), delta_color="inverse")
                else:
                    st.metric("✅ Conformité", "OK")
            
            st.markdown("---")
            
            # Afficher les examens par date
            dates_uniques = sorted(planning['date_only'].unique())
            
            for date in dates_uniques:
                examens_du_jour = planning[planning['date_only'] == date]
                
                # Vérifier si l'étudiant a plus d'un examen ce jour-là
                nb_examens_jour = len(examens_du_jour)
                jour_problematique = nb_examens_jour > 1
                
                st.subheader(f"📅 {date} {'⚠️' if jour_problematique else ''}")
                
                if jour_problematique:
                    st.warning(f"**ATTENTION :** Vous avez {nb_examens_jour} examens ce jour (maximum autorisé : 1)")
                
                for idx, exam in examens_du_jour.iterrows():
                    module_nom = exam.get('module_nom', 'Module non spécifié')
                    heure_examen = exam.get('heure_examen', 'Heure non spécifiée')
                    salle = exam.get('salle', 'Salle non spécifiée')
                    professeur = exam.get('professeur', 'Professeur non spécifié')
                    duree = exam.get('duree_minutes', 'N/A')
                    statut = exam.get('statut', 'N/A')
                    
                    with st.container():
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            st.markdown(f"**{module_nom}**")
                            st.markdown(f"👨‍🏫 {professeur}")
                            st.markdown(f"🏢 {salle} ({exam.get('type_salle', '')})")
                            if duree and duree != 'N/A':
                                st.markdown(f"⏱️ {duree} minutes")
                        
                        with col_b:
                            st.markdown(f"**{heure_examen}**")
                            if statut and statut != 'N/A':
                                badge_color = "#10b981" if statut == 'planifie' else "#f59e0b"
                                st.markdown(f"<span style='background: {badge_color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;'>{statut}</span>", unsafe_allow_html=True)
                        
                        st.markdown("---")
            
            # Section Téléchargement PDF
            st.markdown("---")
            st.markdown("### 📄 Télécharger mon planning en PDF")
            
            col_pdf1, col_pdf2 = st.columns([2, 1])
            
            with col_pdf1:
                st.markdown("""
                **Générez un PDF personnalisé contenant:**
                • Vos informations personnelles
                • Votre emploi du temps complet
                • Les problèmes détectés (le cas échéant)
                • Les statistiques de vos examens
                """)
            
            with col_pdf2:
                if st.button("🖨️ Générer mon PDF", type="primary", use_container_width=True):
                    with st.spinner("Génération du PDF en cours..."):
                        try:
                            # Générer le PDF
                            pdf_buffer = generer_pdf_etudiant(student_info, planning, violations)
                            
                            # Afficher le bouton de téléchargement
                            st.download_button(
                                label="📥 Cliquez pour télécharger",
                                data=pdf_buffer,
                                file_name=f"Planning_Examens_{matricule}_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                type="secondary",
                                use_container_width=True
                            )
                            
                            st.success("✅ PDF généré avec succès!")
                            
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
        else:
            st.info("📭 Aucun examen dans votre formation spécifique")
    else:
        st.info("📭 Aucun examen planifié trouvé")

# TAB 2: VÉRIFICATIONS
with tab2:
    st.header("⚠️ Vérification des Contraintes")
    
    st.markdown("""
    ### 📋 Règles à respecter:
    
    1. **Étudiants :** Maximum 1 examen par jour
    2. **Professeurs :** Maximum 3 examens par jour  
    3. **Modules :** Pas d'examen dupliqué (même module, même date, même heure)
    """)
    
    if violations:
        st.error(f"❌ **{len(violations)} problème(s) détecté(s)**")
        
        # Grouper par sévérité
        high_severity = [v for v in violations if v['severity'] == 'high']
        medium_severity = [v for v in violations if v['severity'] == 'medium']
        
        if high_severity:
            st.subheader("🚨 Problèmes critiques")
            for v in high_severity:
                with st.expander(f"❌ {v['type']}: {v['message']}", expanded=True):
                    st.write(f"**Détails:** {v['details']}")
        
        if medium_severity:
            st.subheader("⚠️ Avertissements")
            for v in medium_severity:
                with st.expander(f"⚠️ {v['type']}: {v['message']}"):
                    st.write(f"**Détails:** {v['details']}")
        
        # Recommandations
        st.markdown("---")
        st.subheader("💡 Recommandations")
        
        if any("Examen dupliqué" in v['type'] for v in violations):
            st.info("""
            **Pour les examens dupliqués:**
            - Contactez l'administration pour supprimer les doublons
            - Vérifiez que chaque module n'a qu'un seul examen
            """)
        
        if any("Étudiant - Multiples examens/jour" in v['type'] for v in violations):
            st.warning("""
            **Pour les examens multiples le même jour:**
            - Vous devez avoir maximum 1 examen par jour
            - Contactez votre responsable de formation
            - Demandez une réorganisation des dates
            """)
        
        if any("Professeur surchargé" in v['type'] for v in violations):
            st.info("""
            **Pour les professeurs surchargés:**
            - L'administration doit répartir les examens
            - Ajouter des surveillants supplémentaires
            """)
    else:
        st.success("✅ **Toutes les contraintes sont respectées !**")
        
        # Afficher un résumé positif
        if not planning.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                exams_per_day = planning.groupby('date_only').size().max()
                st.metric("Max examens/jour", exams_per_day, 
                         delta="OK" if exams_per_day <= 1 else "Problème")
            
            with col2:
                if 'professeur' in planning.columns:
                    prof_stats = planning.groupby(['professeur', 'date_only']).size().max()
                    st.metric("Max examens/prof/jour", prof_stats,
                             delta="OK" if prof_stats <= 3 else "Problème")
            
            with col3:
                duplicates = planning.duplicated(subset=['module_nom', 'date_only', 'heure_examen']).sum()
                st.metric("Examens dupliqués", duplicates,
                         delta="OK" if duplicates == 0 else "Problème")

# TAB 3: ANALYSE
with tab3:
    st.header("📊 Analyse de l'Emploi du Temps")
    
    if not planning.empty:
        # Répartition par date
        st.subheader("📅 Répartition par date")
        if 'par_date' in analysis:
            st.dataframe(
                analysis['par_date'],
                use_container_width=True
            )
        
        # Graphique des examens par jour
        if 'par_date' in analysis:
            st.bar_chart(analysis['par_date']['nb_examens'])
        
        # Répartition par professeur
        if 'par_professeur' in analysis:
            st.subheader("👨‍🏫 Répartition par professeur")
            st.dataframe(
                analysis['par_professeur'],
                use_container_width=True
            )
        
        # Répartition par salle
        if 'par_salle' in analysis:
            st.subheader("🏢 Répartition par salle")
            st.dataframe(
                analysis['par_salle'],
                use_container_width=True
            )
        
        # Statistiques détaillées
        st.subheader("📈 Statistiques détaillées")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Durée moyenne", f"{planning['duree_minutes'].mean():.0f} min")
            st.metric("Heure la plus tôt", planning['heure_examen'].min())
            st.metric("Heure la plus tard", planning['heure_examen'].max())
        
        with col2:
            st.metric("Premier examen", planning['date_examen'].min())
            st.metric("Dernier examen", planning['date_examen'].max())
            if 'date_only' in planning.columns:
                st.metric("Période couverte", f"{planning['date_only'].nunique()} jours")
    
    else:
        st.info("📭 Aucune donnée à analyser")

# TAB 4: TÉLÉCHARGER PDF
with tab4:
    st.header("📄 Générer et Télécharger PDF")
    
    st.markdown("""
    ### 📋 Votre document PDF personnalisé
    
    Générez un PDF contenant toutes vos informations d'examens:
    """)
    
    # Options de personnalisation
    col_opt1, col_opt2 = st.columns(2)
    
    with col_opt1:
        inclure_statistiques = st.checkbox("Inclure les statistiques", value=True)
        inclure_problemes = st.checkbox("Inclure les problèmes détectés", value=True)
    
    with col_opt2:
        format_pdf = st.selectbox(
            "Format du PDF:",
            ["Standard", "Compact", "Détaillé"]
        )
    
    
    # Bouton de génération principal
    st.markdown("---")
    
    col_gen1, col_gen2, col_gen3 = st.columns([2, 1, 2])
    
    with col_gen2:
        if st.button("🖨️ GÉNÉRER LE PDF", type="primary", use_container_width=True):
            with st.spinner("Création de votre document PDF..."):
                try:
                    # Générer le PDF
                    pdf_buffer = generer_pdf_etudiant(student_info, planning, violations)
                    
                    # Téléchargement
                    file_name = f"Planning_Examens_{student_info['matricule']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    
                    st.download_button(
                        label="📥 TÉLÉCHARGER LE PDF",
                        data=pdf_buffer,
                        file_name=file_name,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                    
                    st.success("✅ Document PDF prêt au téléchargement!")
                    
                    # Aperçu des informations incluses
                    with st.expander("📋 Aperçu du contenu"):
                        st.markdown(f"""
                        **Votre PDF contient:**
                        
                        **1. Informations personnelles:**
                        - Nom: {student_info['prenom']} {student_info['nom']}
                        - Matricule: {student_info['matricule']}
                        - Formation: {student_info['formation']}
                        
                        **2. Emploi du temps:**
                        - {len(planning)} examen(s) planifié(s)
                        - {planning['date_only'].nunique() if not planning.empty else 0} jour(s) d'examens
                        
                        **3. Vérifications:**
                        - {len(violations)} problème(s) détecté(s)
                        
                        **Fichier:** {file_name}
                        """)
                        
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération: {str(e)}")

   # في الشريط الجانبي
with st.sidebar:
    if not planning.empty:
        next_exam = planning.sort_values('date_heure').iloc[0]
        exam_date = next_exam.get('date_examen', '')
        exam_time = next_exam.get('heure_examen', '')
        
        days_left = (pd.to_datetime(exam_date, format='%d/%m/%Y') - datetime.now()).days
        
        st.markdown("### ⏰ Prochain examen")
        st.markdown(f"""
        **{next_exam.get('module_nom', '')}**
        
        📅 {exam_date}
        🕐 {exam_time}
        
        **Jours restants: {days_left}**
        """)
        
        if days_left <= 7:
            st.warning(f"⚠️ {days_left} jour(s) restant(s)")
    
    # Informations supplémentaires
    st.markdown("---")
    st.markdown("""
    ### 💡 Conseils d'utilisation:
    
    1. **Sauvegardez votre PDF** sur votre ordinateur et téléphone
    2. **Imprimez une copie** pour l'avoir toujours avec vous
    3. **Partagez avec vos parents** pour les informer de vos dates d'examens
    4. **Vérifiez régulièrement** les mises à jour de votre planning
    """)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(f"""
    <div style='text-align: center; padding: 15px; background: #f8fafc; border-radius: 10px;'>
        <h4>👨‍🎓 {student_info['prenom']} {student_info['nom']}</h4>
        <p style='font-size: 0.9em; color: #6b7280;'>{student_info['matricule']}</p>
        <p style='font-size: 0.8em; color: #9ca3af;'>{student_info['formation']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Statut des contraintes
    if violations:
        st.error(f"⚠️ {len(violations)} problème(s)")
    else:
        st.success("✅ Conforme")
    
    st.markdown("---")
    
    # Section Téléchargement PDF rapide
    st.markdown("### 📄 Téléchargement rapide")
    
    if st.button("📥 Télécharger mon PDF", use_container_width=True, type="primary"):
        with st.spinner("Préparation du PDF..."):
            try:
                pdf_buffer = generer_pdf_etudiant(student_info, planning, violations)
                
                # Afficher le bouton de téléchargement
                st.download_button(
                    label="⬇️ Cliquez ici pour télécharger",
                    data=pdf_buffer,
                    file_name=f"Planning_{matricule}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error("Erreur de génération PDF")
    
    st.markdown("---")
    
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()
    
    # Option pour signaler un problème
    with st.expander("🚨 Signaler un problème"):
        problem_type = st.selectbox(
            "Type de problème",
            ["Examens dupliqués", "Trop d'examens/jour", "Professeur surchargé", "Autre"]
        )
        
        description = st.text_area("Description du problème")
        
        if st.button("Envoyer le signalement"):
            st.success("Signalement envoyé à l'administration")
    
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
<div style='text-align: center; color: #6b7280; font-size: 0.9em; padding: 20px;'>
    🎓 Système Intelligent de Gestion des Examens | 
    {datetime.now().strftime("%d/%m/%Y %H:%M")}
</div>
""", unsafe_allow_html=True)