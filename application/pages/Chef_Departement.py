# pages/Chef_Departement.py - Version complète avec tables
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from database import db
import base64
from io import BytesIO
import tempfile
import os
import atexit
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch

st.set_page_config(page_title="Chef Département", layout="wide")

# =========================
# AUTHENTIFICATION
# =========================
if 'logged_in' not in st.session_state:
    st.error("Veuillez vous connecter")
    st.switch_page("app.py")
    st.stop()

# =========================
# GESTION DES FICHIERS TEMPORAIRES
# =========================

class TempFileManager:
    """Gestionnaire de fichiers temporaires"""
    
    def __init__(self):
        self.temp_files = []
        atexit.register(self.cleanup)
    
    def create_temp_file(self, suffix='.pdf'):
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=suffix,
            dir=tempfile.gettempdir()
        )
        self.temp_files.append(temp_file.name)
        return temp_file
    
    def cleanup(self):
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
        self.temp_files = []
    
    def cleanup_file(self, file_path):
        try:
            if file_path in self.temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                self.temp_files.remove(file_path)
        except:
            pass

# Initialiser le gestionnaire
temp_manager = TempFileManager()

# =========================
# FONCTIONS DE GÉNÉRATION PDF
# =========================

def generate_pdf_report_safe(dept_name, dept_id, examens_data, formations_data, professeurs_data, conflits_data):
    pdf_bytes = None
    temp_file = None
    
    try:
        temp_file = temp_manager.create_temp_file(suffix='.pdf')
        pdf_path = temp_file.name
        temp_file.close()
        
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#2C5282'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=10
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=5
        )
        
        elements = []
        
        # Titre
        elements.append(Paragraph(f"RAPPORT DU DÉPARTEMENT {dept_name}", title_style))
        elements.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 20))
        
        # Informations générales
        elements.append(Paragraph("INFORMATIONS GÉNÉRALES", subtitle_style))
        
        info_data = [
            ['Département:', dept_name],
            ['ID Département:', str(dept_id)],
            ['Date génération:', datetime.now().strftime('%d/%m/%Y')],
            ['Responsable:', st.session_state.get('nom_complet', 'Chef Département')]
        ]
        
        info_table = Table(info_data, colWidths=[100, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F8FF')),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Statistiques
        elements.append(Paragraph("STATISTIQUES PRINCIPALES", subtitle_style))
        
        stats_data = [
            ['Indicateur', 'Valeur'],
            ['Nombre d\'examens', str(len(examens_data) if not examens_data.empty else 0)],
            ['Nombre de formations', str(len(formations_data) if not formations_data.empty else 0)],
            ['Nombre de professeurs', str(len(professeurs_data) if not professeurs_data.empty else 0)],
            ['Nombre de conflits', str(len(conflits_data) if not conflits_data.empty else 0)]
        ]
        
        if not formations_data.empty:
            total_etudiants = formations_data['etudiants'].sum()
            stats_data.append(['Total étudiants', str(int(total_etudiants))])
        
        if not professeurs_data.empty:
            total_surveillances = professeurs_data['total_surveillances'].sum()
            stats_data.append(['Total surveillances', str(int(total_surveillances))])
        
        stats_table = Table(stats_data, colWidths=[150, 100])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 20))
        
        # Examens
        if not examens_data.empty:
            elements.append(Paragraph("EXAMENS PLANIFIÉS", subtitle_style))
            
            examens_pdf = examens_data.head(10)
            
            examens_header = [['Module', 'Formation', 'Date', 'Heure', 'Salle', 'Professeur']]
            examens_rows = []
            
            for _, row in examens_pdf.iterrows():
                examens_rows.append([
                    str(row.get('module', ''))[:25],
                    str(row.get('formation', ''))[:20],
                    str(row.get('date_examen', '')),
                    str(row.get('heure_examen', '')),
                    str(row.get('salle', ''))[:15],
                    str(row.get('professeur', ''))[:20]
                ])
            
            examens_table_data = examens_header + examens_rows
            
            examens_table = Table(examens_table_data, colWidths=[80, 70, 50, 40, 50, 70])
            examens_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ]))
            
            elements.append(examens_table)
            if len(examens_data) > 10:
                elements.append(Paragraph(f"... et {len(examens_data) - 10} autres examens", normal_style))
            elements.append(Spacer(1, 20))
        
        # Formations
        if not formations_data.empty:
            elements.append(Paragraph("FORMATIONS DU DÉPARTEMENT", subtitle_style))
            
            formations_header = [['Formation', 'Étudiants', 'Examens']]
            formations_rows = []
            
            for _, row in formations_data.iterrows():
                formations_rows.append([
                    str(row.get('formation', ''))[:30],
                    str(int(row.get('etudiants', 0))),
                    str(int(row.get('examens', 0)))
                ])
            
            formations_table_data = formations_header + formations_rows
            
            formations_table = Table(formations_table_data, colWidths=[200, 60, 60])
            formations_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ]))
            
            elements.append(formations_table)
            elements.append(Spacer(1, 20))
        
        # Professeurs
        if not professeurs_data.empty:
            elements.append(Paragraph("PROFESSEURS ACTIFS", subtitle_style))
            
            prof_pdf = professeurs_data.head(8)
            
            prof_header = [['Nom', 'Prénom', 'Surveillances', 'Examens responsables']]
            prof_rows = []
            
            for _, row in prof_pdf.iterrows():
                prof_rows.append([
                    str(row.get('nom', ''))[:15],
                    str(row.get('prenom', ''))[:10],
                    str(int(row.get('total_surveillances', 0))),
                    str(int(row.get('nb_examens_responsable', 0)))
                ])
            
            prof_table_data = prof_header + prof_rows
            
            prof_table = Table(prof_table_data, colWidths=[70, 60, 60, 70])
            prof_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF9800')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ]))
            
            elements.append(prof_table)
            if len(professeurs_data) > 8:
                elements.append(Paragraph(f"... et {len(professeurs_data) - 8} autres professeurs", normal_style))
            elements.append(Spacer(1, 20))
        
        # Recommandations
        elements.append(Paragraph("RECOMMANDATIONS", subtitle_style))
        
        recommandations = [
            "1. Vérifier régulièrement les conflits d'horaires",
            "2. Équilibrer la charge des surveillances entre professeurs",
            "3. Valider les salles selon leur capacité",
            "4. Planifier les rattrapages en avance",
            "5. Communiquer les emplois du temps aux étudiants"
        ]
        
        for rec in recommandations:
            elements.append(Paragraph(rec, normal_style))
        
        elements.append(Spacer(1, 20))
        
        # Signature
        elements.append(Paragraph("Signature:", normal_style))
        elements.append(Paragraph("_________________________", normal_style))
        elements.append(Paragraph(f"Chef du Département {dept_name}", normal_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Plateforme d'Optimisation des Examens Universitaires", 
                                 ParagraphStyle('Footer', parent=normal_style, fontSize=8, alignment=TA_CENTER)))
        
        # Générer
        doc.build(elements)
        
        # Lire
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                break
            except PermissionError:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.1)
                else:
                    raise
        
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Erreur génération PDF: {str(e)}")
        return None
    
    finally:
        if 'pdf_path' in locals():
            temp_manager.cleanup_file(pdf_path)

def generate_simple_pdf(dept_name, data, data_type="examens"):
    try:
        if data.empty:
            return None
        
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=14,
            textColor=colors.HexColor('#2C5282'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        elements = []
        
        titles = {
            "examens": f"LISTE DES EXAMENS - {dept_name}",
            "formations": f"FORMATIONS - {dept_name}",
            "professeurs": f"PROFESSEURS - {dept_name}",
            "conflits": f"CONFLITS DÉTECTÉS"
        }
        
        elements.append(Paragraph(titles.get(data_type, "RAPPORT"), title_style))
        elements.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 
                                 styles['Normal']))
        elements.append(Spacer(1, 20))
        
        if data_type == "examens" and not data.empty:
            headers = ['Module', 'Formation', 'Date', 'Heure', 'Salle']
            table_data = [headers]
            
            for _, row in data.head(20).iterrows():
                table_data.append([
                    str(row.get('module', ''))[:25],
                    str(row.get('formation', ''))[:20],
                    str(row.get('date_examen', '')),
                    str(row.get('heure_examen', '')),
                    str(row.get('salle', ''))[:15]
                ])
        
        elif data_type == "formations" and not data.empty:
            headers = ['Formation', 'Étudiants', 'Examens']
            table_data = [headers]
            
            for _, row in data.iterrows():
                table_data.append([
                    str(row.get('formation', ''))[:30],
                    str(int(row.get('etudiants', 0))),
                    str(int(row.get('examens', 0)))
                ])
        
        elif data_type == "professeurs" and not data.empty:
            headers = ['Nom', 'Prénom', 'Surveillances']
            table_data = [headers]
            
            for _, row in data.head(15).iterrows():
                table_data.append([
                    str(row.get('nom', ''))[:20],
                    str(row.get('prenom', ''))[:15],
                    str(int(row.get('total_surveillances', 0)))
                ])
        
        else:
            return None
        
        if len(table_data) > 1:
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(table)
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Erreur PDF simple: {str(e)}")
        return None

def download_pdf_button(pdf_bytes, filename):
    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'''
        <a href="data:application/pdf;base64,{b64}" 
           download="{filename}" 
           style="background-color: #FF5733; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; font-size: 13px; font-weight: bold; margin: 3px;">
           📄 PDF
        </a>
        '''
        return href
    return ""

# =========================
# FONCTIONS DE DONNÉES
# =========================

def get_departement_info():
    try:
        query = """
        SELECT d.id as dept_id, d.nom as departement_nom
        FROM gestion_examens.professeurs p
        JOIN gestion_examens.departements d ON p.dept_id = d.id
        WHERE p.id = (
            SELECT user_id 
            FROM gestion_examens.authentification 
            WHERE matricule = 'CHEF-INF-001'
        )
        """
        result = db.execute_query(query)
        if result is not None:
            return result.iloc[0]
    except:
        pass
    
    return {'dept_id': 1, 'departement_nom': 'Informatique'}

def get_statistiques_globales():
    try:
        query = """
        SELECT 'Etudiants actifs' as indicateur, 
               (SELECT COUNT(*)::TEXT FROM gestion_examens.etudiants WHERE statut = 'actif') as valeur
        UNION ALL
        SELECT 'Professeurs actifs',
               (SELECT COUNT(*)::TEXT FROM gestion_examens.professeurs WHERE statut = 'actif')
        UNION ALL
        SELECT 'Examens planifies',
               (SELECT COUNT(*)::TEXT FROM gestion_examens.examens WHERE statut = 'planifie')
        UNION ALL
        SELECT 'Formations',
               (SELECT COUNT(*)::TEXT FROM gestion_examens.formations)
        UNION ALL
        SELECT 'Salles disponibles',
               (SELECT COUNT(*)::TEXT FROM gestion_examens.salles_examen WHERE disponible = TRUE)
        UNION ALL
        SELECT 'Conflits detectes',
               COALESCE((SELECT COUNT(*)::TEXT FROM gestion_examens.vue_conflits), '0')
        """
        return db.execute_query(query)
    except Exception as e:
        return pd.DataFrame({'indicateur': ['Erreur'], 'valeur': [str(e)]})

def get_examens_par_departement(dept_id):
    try:
        query = f"""
        SELECT 
            m.nom as module,
            f.nom as formation,
            TO_CHAR(e.date_heure, 'DD/MM/YYYY') as date_examen,
            TO_CHAR(e.date_heure, 'HH24:MI') as heure_examen,
            s.nom as salle,
            s.type as type_salle,
            pr.prenom || ' ' || pr.nom as professeur,
            e.duree_minutes,
            e.statut
        FROM gestion_examens.examens e
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.formations f ON m.formation_id = f.id
        JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
        JOIN gestion_examens.professeurs pr ON e.professeur_responsable_id = pr.id
        WHERE f.dept_id = {dept_id}
        AND e.statut = 'planifie'
        ORDER BY e.date_heure
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_formations_par_departement(dept_id):
    try:
        query = f"""
        SELECT 
            f.nom as formation,
            COUNT(DISTINCT e.id) as etudiants,
            COUNT(DISTINCT m.id) as modules,
            COUNT(DISTINCT ex.id) as examens
        FROM gestion_examens.formations f
        LEFT JOIN gestion_examens.etudiants e ON f.id = e.formation_id AND e.statut = 'actif'
        LEFT JOIN gestion_examens.modules m ON f.id = m.formation_id
        LEFT JOIN gestion_examens.examens ex ON f.id = ex.formation_id AND ex.statut = 'planifie'
        WHERE f.dept_id = {dept_id}
        GROUP BY f.id, f.nom
        ORDER BY f.nom
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_professeurs_par_departement(dept_id):
    try:
        query = f"""
        SELECT 
            p.matricule,
            p.nom,
            p.prenom,
            p.specialite,
            p.total_surveillances,
            COUNT(DISTINCT e.id) as nb_examens_responsable
        FROM gestion_examens.professeurs p
        LEFT JOIN gestion_examens.examens e ON p.id = e.professeur_responsable_id AND e.statut = 'planifie'
        WHERE p.dept_id = {dept_id} AND p.statut = 'actif'
        GROUP BY p.id, p.matricule, p.nom, p.prenom, p.specialite, p.total_surveillances
        ORDER BY p.nom, p.prenom
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_conflits_tous():
    try:
        query = """
        SELECT 
            type_conflit,
            element,
            TO_CHAR(date_conflit, 'DD/MM/YYYY') as date_conflit,
            nombre_examens
        FROM gestion_examens.vue_conflits
        ORDER BY date_conflit DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def download_csv(df, filename):
    if df.empty:
        return ""
    
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'''
    <a href="data:file/csv;base64,{b64}" 
       download="{filename}" 
       style="background-color: #4CAF50; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 12px; margin: 2px;">
       📥 CSV
    </a>
    '''
    return href

def download_excel(df, filename):
    if df.empty:
        return ""
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Donnees')
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'''
    <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" 
       download="{filename}" 
       style="background-color: #2196F3; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 12px; margin: 2px;">
       📊 Excel
    </a>
    '''
    return href

# =========================
# INTERFACE PRINCIPALE
# =========================

# Récupérer le département
dept_info = get_departement_info()
dept_id = dept_info['dept_id']
dept_name = dept_info['departement_nom']

# Titre principal
st.markdown(f"""
    <div style='background: linear-gradient(135deg, #2C5282 0%, #1E3A8A 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h1 style='margin: 0; text-align: center; font-size: 2em;'>👔 CHEF DE DÉPARTEMENT</h1>
        <h2 style='margin: 10px 0 0 0; text-align: center; font-size: 1.3em; opacity: 0.9;'>{dept_name}</h2>
    </div>
""", unsafe_allow_html=True)

# Récupérer les données
stats_data = get_statistiques_globales()
examens_data = get_examens_par_departement(dept_id)
formations_data = get_formations_par_departement(dept_id)
professeurs_data = get_professeurs_par_departement(dept_id)
conflits_data = get_conflits_tous()

# =========================
# TABLEAU DE BORD PRINCIPAL
# =========================

# Section 1: Tableau des KPIs
st.header("📊 Tableau de Bord - Indicateurs Clés")

if not stats_data.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(stats_data.iterrows()):
        col_idx = idx % 3
        with cols[col_idx]:
            st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #2C5282; margin-bottom: 10px;'>
                    <div style='font-size: 14px; color: #666;'>{row['indicateur']}</div>
                    <div style='font-size: 24px; font-weight: bold; color: #2C5282;'>{row['valeur']}</div>
                </div>
            """, unsafe_allow_html=True)

# Section 2: Onglets pour différentes tables
st.header("📋 Données Détaillées")

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Examens Planifiés", 
    "🎓 Formations", 
    "👨‍🏫 Professeurs", 
    "⚠️ Conflits"
])

# Tab 1: Examens
with tab1:
    st.subheader(f"Examens Planifiés - {dept_name}")
    
    if not examens_data.empty:
        st.dataframe(
            examens_data,
            use_container_width=True,
            column_config={
                "module": "Module",
                "formation": "Formation",
                "date_examen": "Date",
                "heure_examen": "Heure",
                "salle": "Salle",
                "type_salle": "Type",
                "professeur": "Professeur",
                "duree_minutes": "Durée (min)",
                "statut": "Statut"
            },
            hide_index=True
        )
        
        # Graphique des examens par date
        if 'date_examen' in examens_data.columns:
            examens_par_date = examens_data.groupby('date_examen').size().reset_index(name='nombre_examens')
            fig = px.bar(
                examens_par_date,
                x='date_examen',
                y='nombre_examens',
                title=f"Nombre d'examens par date - {dept_name}",
                labels={'date_examen': 'Date', 'nombre_examens': 'Nombre d\'examens'},
                color='nombre_examens',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun examen planifié pour ce département")

# Tab 2: Formations
with tab2:
    st.subheader(f"Formations - {dept_name}")
    
    if not formations_data.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(
                formations_data,
                use_container_width=True,
                column_config={
                    "formation": "Formation",
                    "etudiants": "Étudiants",
                    "modules": "Modules",
                    "examens": "Examens"
                },
                hide_index=True
            )
        
        with col2:
            # Graphique circulaire
            fig = px.pie(
                formations_data,
                values='etudiants',
                names='formation',
                title=f"Répartition des étudiants par formation",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune formation trouvée")

# Tab 3: Professeurs
with tab3:
    st.subheader(f"Professeurs - {dept_name}")
    
    if not professeurs_data.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(
                professeurs_data,
                use_container_width=True,
                column_config={
                    "matricule": "Matricule",
                    "nom": "Nom",
                    "prenom": "Prénom",
                    "specialite": "Spécialité",
                    "total_surveillances": "Surveillances",
                    "nb_examens_responsable": "Examens responsables"
                },
                hide_index=True
            )
        
        with col2:
            # Graphique des surveillances
            fig = px.bar(
                professeurs_data,
                x='prenom',
                y='total_surveillances',
                title="Nombre de surveillances par professeur",
                labels={'prenom': 'Prénom', 'total_surveillances': 'Surveillances'},
                color='total_surveillances',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun professeur trouvé")

# Tab 4: Conflits
with tab4:
    st.subheader("Conflits Détectés")
    
    if not conflits_data.empty:
        st.dataframe(
            conflits_data,
            use_container_width=True,
            column_config={
                "type_conflit": "Type de conflit",
                "element": "Élément concerné",
                "date_conflit": "Date",
                "nombre_examens": "Nombre d'examens"
            },
            hide_index=True
        )
        
        # Graphique des conflits par type
        conflits_par_type = conflits_data.groupby('type_conflit').size().reset_index(name='nombre')
        fig = px.pie(
            conflits_par_type,
            values='nombre',
            names='type_conflit',
            title="Répartition des conflits par type",
            color_discrete_sequence=px.colors.sequential.Reds
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ Aucun conflit détecté !")

# =========================
# SECTION EXPORT
# =========================
st.header("📤 Export des Données")

# Export PDF principal
if st.button("📄 Générer Rapport PDF Complet", type="primary", use_container_width=True):
    with st.spinner("Génération du rapport PDF en cours..."):
        pdf_bytes = generate_pdf_report_safe(
            dept_name, 
            dept_id, 
            examens_data, 
            formations_data, 
            professeurs_data, 
            conflits_data
        )
        
        if pdf_bytes:
            st.success("✅ Rapport PDF généré avec succès!")
            
            filename = f"Rapport_{dept_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'''
            <div style="text-align: center; margin: 15px 0;">
                <a href="data:application/pdf;base64,{b64}" 
                   download="{filename}" 
                   style="background-color: #FF5733; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-size: 14px; font-weight: bold;">
                   📥 Télécharger le PDF
                </a>
            </div>
            '''
            st.markdown(href, unsafe_allow_html=True)

# Export par type
st.subheader("Export par type de données")

col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)

with col_exp1:
    st.markdown("**Examens**")
    if not examens_data.empty:
        filename = f"examens_{dept_name}.csv"
        st.markdown(download_csv(examens_data, filename), unsafe_allow_html=True)
        
        filename = f"examens_{dept_name}.xlsx"
        st.markdown(download_excel(examens_data, filename), unsafe_allow_html=True)
        
        if st.button("PDF", key="pdf_examens", use_container_width=True):
            pdf_bytes = generate_simple_pdf(dept_name, examens_data, "examens")
            if pdf_bytes:
                filename = f"Examens_{dept_name}.pdf"
                st.markdown(download_pdf_button(pdf_bytes, filename), unsafe_allow_html=True)

with col_exp2:
    st.markdown("**Formations**")
    if not formations_data.empty:
        filename = f"formations_{dept_name}.csv"
        st.markdown(download_csv(formations_data, filename), unsafe_allow_html=True)
        
        filename = f"formations_{dept_name}.xlsx"
        st.markdown(download_excel(formations_data, filename), unsafe_allow_html=True)
        
        if st.button("PDF", key="pdf_formations", use_container_width=True):
            pdf_bytes = generate_simple_pdf(dept_name, formations_data, "formations")
            if pdf_bytes:
                filename = f"Formations_{dept_name}.pdf"
                st.markdown(download_pdf_button(pdf_bytes, filename), unsafe_allow_html=True)

with col_exp3:
    st.markdown("**Professeurs**")
    if not professeurs_data.empty:
        filename = f"professeurs_{dept_name}.csv"
        st.markdown(download_csv(professeurs_data, filename), unsafe_allow_html=True)
        
        filename = f"professeurs_{dept_name}.xlsx"
        st.markdown(download_excel(professeurs_data, filename), unsafe_allow_html=True)
        
        if st.button("PDF", key="pdf_professeurs", use_container_width=True):
            pdf_bytes = generate_simple_pdf(dept_name, professeurs_data, "professeurs")
            if pdf_bytes:
                filename = f"Professeurs_{dept_name}.pdf"
                st.markdown(download_pdf_button(pdf_bytes, filename), unsafe_allow_html=True)

with col_exp4:
    st.markdown("**Conflits**")
    if not conflits_data.empty:
        filename = f"conflits.csv"
        st.markdown(download_csv(conflits_data, filename), unsafe_allow_html=True)
        
        filename = f"conflits.xlsx"
        st.markdown(download_excel(conflits_data, filename), unsafe_allow_html=True)
        
        if st.button("PDF", key="pdf_conflits", use_container_width=True):
            pdf_bytes = generate_simple_pdf(dept_name, conflits_data, "conflits")
            if pdf_bytes:
                filename = f"Conflits.pdf"
                st.markdown(download_pdf_button(pdf_bytes, filename), unsafe_allow_html=True)

# =========================
# BARRE LATÉRALE
# =========================
with st.sidebar:
    st.markdown(f"""
        <div style='background: #2C5282; padding: 15px; border-radius: 8px; color: white; margin-bottom: 15px;'>
            <h4 style='margin: 0;'>👔 Chef de Département</h4>
            <p style='margin: 5px 0;'><b>{dept_name}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    # Nettoyage
    if st.button("🧹 Nettoyer fichiers temporaires", use_container_width=True):
        temp_manager.cleanup()
        st.success("Fichiers temporaires nettoyés!")
    
    st.markdown("---")
    
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    if st.button("🚪 Déconnexion", type="secondary", use_container_width=True):
        temp_manager.cleanup()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# =========================
# PIED DE PAGE
# =========================
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; color: #666; font-size: 11px; padding: 15px;'>
        <p>🎓 Plateforme Examens Universitaires | Département {dept_name}</p>
        <p>📅 {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
    </div>
""", unsafe_allow_html=True)