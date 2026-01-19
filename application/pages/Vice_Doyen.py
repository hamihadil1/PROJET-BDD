# pages/Vice_Doyen.py - VERSION COMPLÈTE FINALE

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import db
import base64
from io import BytesIO
import tempfile
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, cm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import json
import psycopg2

# =========================
# CONFIGURATION
# =========================
st.set_page_config(
    page_title="Vice-Doyen - Vue Stratégique",
    page_icon="👑",
    layout="wide"
)

# =========================
# AUTHENTIFICATION
# =========================
def check_vice_doyen():
    if 'logged_in' not in st.session_state or st.session_state.get('user_type') != 'vice_doyen':
        st.error("⛔ Accès réservé au Vice-Doyen")
        if st.button("🔐 Page de connexion", key="btn_login_page_vicedoyen"):
            st.switch_page("app.py")
        st.stop()

check_vice_doyen()

# =========================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES
# =========================

def get_planning_complet():
    """Récupérer tout le planning"""
    try:
        query = """
        SELECT 
            d.nom as departement,
            f.nom as formation,
            g.nom as groupe,
            TO_CHAR(e.date_heure, 'DD/MM/YYYY') as date_examen,
            TO_CHAR(e.date_heure, 'Dy') as jour,
            TO_CHAR(e.date_heure, 'HH24:MI') as heure,
            m.nom as module,
            s.nom as salle,
            s.type as type_salle,
            s.capacite,
            pr.prenom || ' ' || pr.nom as professeur,
            e.duree_minutes,
            e.statut
        FROM gestion_examens.examens e
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.formations f ON e.formation_id = f.id
        JOIN gestion_examens.departements d ON f.dept_id = d.id
        LEFT JOIN gestion_examens.groupes g ON f.id = g.formation_id
        JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
        JOIN gestion_examens.professeurs pr ON e.professeur_responsable_id = pr.id
        WHERE e.statut IN ('planifie', 'confirme')
        ORDER BY e.date_heure, d.nom, f.nom
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur récupération planning: {str(e)}")
        return pd.DataFrame()

def get_detailed_salles():
    """Récupérer les détails des salles"""
    try:
        query = """
        SELECT 
            s.nom as salle,
            s.code,
            s.type,
            s.capacite,
            s.batiment,
            COUNT(e.id) as nb_examens,
            s.disponible,
            CASE 
                WHEN COUNT(e.id) > 0 THEN 'Occupée'
                ELSE 'Libre'
            END as etat
        FROM gestion_examens.salles_examen s
        LEFT JOIN gestion_examens.examens e ON s.id = e.salle_id AND e.statut IN ('planifie', 'confirme')
        GROUP BY s.id, s.nom, s.code, s.type, s.capacite, s.batiment, s.disponible
        ORDER BY s.type, s.nom
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_conflits_summary():
    """Récupérer le résumé des conflits"""
    try:
        query = """
        SELECT 
            type_conflit,
            COUNT(*) as nombre,
            STRING_AGG(DISTINCT element, ', ') as elements,
            TO_CHAR(MIN(date_conflit), 'DD/MM/YYYY') as premiere_date,
            TO_CHAR(MAX(date_conflit), 'DD/MM/YYYY') as derniere_date
        FROM gestion_examens.vue_conflits
        GROUP BY type_conflit
        ORDER BY nombre DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_detailed_conflits():
    """Récupérer les détails des conflits"""
    try:
        query = """
        SELECT 
            type_conflit,
            element,
            matricule,
            TO_CHAR(date_conflit, 'DD/MM/YYYY') as date_conflit,
            nombre_examens
        FROM gestion_examens.vue_conflits
        ORDER BY date_conflit DESC, type_conflit
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_heures_professeurs():
    """Récupérer les heures des professeurs"""
    try:
        query = """
        SELECT 
            p.prenom || ' ' || p.nom as professeur,
            d.nom as departement,
            ROUND(COALESCE(SUM(e.duree_minutes) / 60.0, 0), 1) as heures_examens,
            p.total_surveillances,
            p.email,
            p.specialite
        FROM gestion_examens.professeurs p
        JOIN gestion_examens.departements d ON p.dept_id = d.id
        LEFT JOIN gestion_examens.examens e ON p.id = e.professeur_responsable_id AND e.statut IN ('planifie', 'confirme')
        WHERE p.statut = 'actif'
        GROUP BY p.id, p.prenom, p.nom, d.nom, p.total_surveillances, p.email, p.specialite
        ORDER BY heures_examens DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_surveillances():
    """Récupérer les surveillances"""
    try:
        query = """
        SELECT 
            p.prenom || ' ' || p.nom as professeur,
            d.nom as departement,
            COUNT(s.id) as nb_surveillances,
            ROUND(COALESCE(SUM(s.heures_creditees), 0), 1) as total_heures,
            ROUND(AVG(s.priorite), 1) as priorite_moyenne
        FROM gestion_examens.professeurs p
        JOIN gestion_examens.departements d ON p.dept_id = d.id
        LEFT JOIN gestion_examens.surveillances s ON p.id = s.professeur_id
        WHERE p.statut = 'actif'
        GROUP BY p.id, p.prenom, p.nom, d.nom
        ORDER BY nb_surveillances DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_statistiques():
    """Récupérer les statistiques globales"""
    try:
        query = """
        SELECT 
            'Examens total' as categorie,
            COUNT(*)::TEXT as valeur
        FROM gestion_examens.examens 
        UNION ALL
        SELECT 
            'Examens planifiés',
            COUNT(*)::TEXT
        FROM gestion_examens.examens 
        WHERE statut = 'planifie'
        UNION ALL
        SELECT 
            'Examens confirmés',
            COUNT(*)::TEXT
        FROM gestion_examens.examens 
        WHERE statut = 'confirme'
        UNION ALL
        SELECT 
            'Étudiants actifs',
            COUNT(*)::TEXT
        FROM gestion_examens.etudiants 
        WHERE statut = 'actif'
        UNION ALL
        SELECT 
            'Professeurs actifs',
            COUNT(*)::TEXT
        FROM gestion_examens.professeurs 
        WHERE statut = 'actif'
        UNION ALL
        SELECT 
            'Salles disponibles',
            COUNT(*)::TEXT
        FROM gestion_examens.salles_examen 
        WHERE disponible = TRUE
        UNION ALL
        SELECT 
            'Conflits détectés',
            COUNT(*)::TEXT
        FROM gestion_examens.vue_conflits
        UNION ALL
        SELECT 
            'Taux occupation (%)',
            ROUND(
                COUNT(DISTINCT e.salle_id) * 100.0 / 
                GREATEST((SELECT COUNT(*) FROM gestion_examens.salles_examen), 1),
            2)::TEXT
        FROM gestion_examens.examens e
        WHERE e.statut IN ('planifie', 'confirme')
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# =========================
# FONCTIONS D'EXPORT
# =========================

def download_csv(df, filename):
    """Générer un lien de téléchargement CSV"""
    if df.empty:
        return ""
    
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'''
    <a href="data:file/csv;base64,{b64}" 
       download="{filename}.csv" 
       style="background-color: #4CAF50; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 14px; margin: 2px;">
       📥 CSV
    </a>
    '''
    return href

def download_excel(df, filename):
    """Générer un lien de téléchargement Excel"""
    if df.empty:
        return ""
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Donnees')
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'''
    <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" 
       download="{filename}.xlsx" 
       style="background-color: #2196F3; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 14px; margin: 2px;">
       📥 Excel
    </a>
    '''
    return href

def create_pdf_from_dataframe_safe(df, title, filename):
    """Créer un PDF sans fichiers temporaires (solution plus sûre)"""
    if df.empty:
        return None
    
    try:
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
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        normal_style = ParagraphStyle(
            'NormalCustom',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=5
        )
        
        elements = []
        elements.append(Paragraph(f"<b>{title}</b>", title_style))
        current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Généré le: {current_date}", normal_style))
        elements.append(Paragraph(f"Nombre d'enregistrements: {len(df)}", normal_style))
        elements.append(Spacer(1, 15))
        
        if len(df) > 100:
            df_display = df.head(100)
            elements.append(Paragraph(f"<i>Affichage limité aux 100 premiers enregistrements sur {len(df)}</i>", normal_style))
        else:
            df_display = df
        
        if len(df_display.columns) > 8:
            important_cols = df_display.columns[:8].tolist()
            df_display = df_display[important_cols]
            elements.append(Paragraph(f"<i>Affichage limité aux 8 premières colonnes</i>", normal_style))
        
        data = [df_display.columns.tolist()] + df_display.values.tolist()
        col_widths = []
        for col in df_display.columns:
            max_len = max(df_display[col].astype(str).apply(len).max(), len(col))
            col_widths.append(min(max_len * 3, 100))
        
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Vice-Doyen - Plateforme Examens Universitaires", normal_style))
        doc.build(elements)
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Erreur PDF: {str(e)}")
        return None

def download_pdf(df, filename, title):
    """Créer un bouton de téléchargement PDF"""
    pdf_bytes = create_pdf_from_dataframe_safe(df, title, filename)
    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'''
        <a href="data:application/pdf;base64,{b64}" 
           download="{filename}.pdf" 
           style="background-color: #FF5733; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 14px; margin: 2px;">
           📄 PDF
        </a>
        '''
        return href
    return ""

# =========================
# FONCTIONS D'AFFICHAGE
# =========================

def display_metrics_section(df, title):
    """Afficher une section avec des métriques"""
    if df is not None and not df.empty:
        st.subheader(title)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", len(df))
        
        current_date = datetime.now().strftime("%Y%m%d_%H%M")
        base_filename = f"{title.lower().replace(' ', '_')}_{current_date}"
        
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            st.markdown(download_csv(df, base_filename), unsafe_allow_html=True)
        with col_dl2:
            st.markdown(download_excel(df, base_filename), unsafe_allow_html=True)
        with col_dl3:
            st.markdown(download_pdf(df, base_filename, title), unsafe_allow_html=True)
        
        return True
    return False

# =========================
# INTERFACE PRINCIPALE
# =========================

st.markdown("""
    <div style='background: linear-gradient(135deg, #1E3A8A 0%, #2C5282 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h1 style='margin: 0; text-align: center; font-size: 2.5em;'>👑 VICE-DOYEN - VUE STRATÉGIQUE</h1>
        <p style='text-align: center; margin: 10px 0 0 0; opacity: 0.9; font-size: 1.1em;'>Tableau de bord complet avec export des données</p>
    </div>
""", unsafe_allow_html=True)

tab_planning, tab_salles, tab_conflits, tab_professeurs, tab_surveillances, tab_stats = st.tabs([
    "📊 Planning Examens", 
    "🏢 Salles", 
    "⚠️ Conflits", 
    "👨‍🏫 Professeurs", 
    "👥 Surveillances",
    "📈 Statistiques"
])

# =========================
# ONGLET 1: PLANNING DES EXAMENS
# =========================
with tab_planning:
    st.header("📊 Planning des Examens")
    
    df_planning = get_planning_complet()
    
    if display_metrics_section(df_planning, "Planning des Examens"):
        with st.expander("🔍 Filtres de recherche", expanded=True):
           col1, col2, col3, col4 = st.columns(4)
    
           with col1:
               departements = ['Tous'] + sorted(df_planning['departement'].unique().tolist()) if not df_planning.empty else ['Tous']
               selected_departement = st.selectbox("Département", departements, key="dept_filter_planning")
    
           with col2:
              formations = ['Toutes'] + sorted(df_planning['formation'].unique().tolist()) if not df_planning.empty else ['Toutes']
              selected_formation = st.selectbox("Formation", formations, key="formation_filter_planning")
    
           with col3:
               dates = ['Toutes'] + sorted(df_planning['date_examen'].unique().tolist()) if not df_planning.empty else ['Toutes']
               selected_date = st.selectbox("Date", dates, key="date_filter_planning")
    
           with col4:
              salles = ['Toutes'] + sorted(df_planning['salle'].unique().tolist()) if not df_planning.empty else ['Toutes']
              selected_salle = st.selectbox("Salle", salles, key="salle_filter_planning")

        if not df_planning.empty:
            df_filtered = df_planning.copy()
            
            if selected_departement != 'Tous':
                df_filtered = df_filtered[df_filtered['departement'] == selected_departement]

            if selected_formation != 'Toutes':
                df_filtered = df_filtered[df_filtered['formation'] == selected_formation]
            
            if selected_date != 'Toutes':
                df_filtered = df_filtered[df_filtered['date_examen'] == selected_date]
            
            if selected_salle != 'Toutes':
                df_filtered = df_filtered[df_filtered['salle'] == selected_salle]
            
            st.dataframe(
                df_filtered,
                column_config={
                    "departement": "Département",
                    "formation": "Formation",
                    "groupe": "Groupe",
                    "date_examen": "Date",
                    "jour": "Jour",
                    "heure": "Heure",
                    "module": "Module",
                    "salle": "Salle",
                    "type_salle": "Type",
                    "capacite": "Capacité",
                    "professeur": "Professeur",
                    "duree_minutes": "Durée (min)",
                    "statut": "Statut"
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            with st.expander("📈 Visualisations"):
                if not df_filtered.empty:
                    col_viz1, col_viz2 = st.columns(2)
                    
                    with col_viz1:
                        if 'date_examen' in df_filtered.columns:
                            date_counts = df_filtered.groupby('date_examen').size().reset_index(name='count')
                            if not date_counts.empty:
                                fig1 = px.bar(
                                    date_counts,
                                    x='date_examen',
                                    y='count',
                                    title="Examens par date",
                                    labels={'count': 'Nombre d\'examens', 'date_examen': 'Date'},
                                    color='count'
                                )
                                st.plotly_chart(fig1, use_container_width=True)
                    
                    with col_viz2:
                        if 'departement' in df_filtered.columns:
                            dept_counts = df_filtered.groupby('departement').size().reset_index(name='count')
                            if not dept_counts.empty:
                                fig2 = px.pie(
                                    dept_counts,
                                    names='departement',
                                    values='count',
                                    title="Répartition par département",
                                    hole=0.3
                                )
                                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Aucun examen disponible pour le moment")

# =========================
# ONGLET 2: SALLES
# =========================
with tab_salles:
    st.header("🏢 Gestion des Salles")
    
    df_salles = get_detailed_salles()
    
    if display_metrics_section(df_salles, "État des Salles"):
        st.dataframe(
            df_salles,
            column_config={
                "salle": "Salle",
                "code": "Code",
                "type": "Type",
                "capacite": "Capacité",
                "batiment": "Bâtiment",
                "nb_examens": "Examens",
                "disponible": "Disponible",
                "etat": "État"
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        with st.expander("📊 Statistiques des salles"):
            if not df_salles.empty:
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                with col_stat1:
                    salles_occupees = df_salles[df_salles['etat'] == 'Occupée'].shape[0]
                    st.metric("Salles occupées", salles_occupees)
                
                with col_stat2:
                    salles_libres = df_salles[df_salles['etat'] == 'Libre'].shape[0]
                    st.metric("Salles libres", salles_libres)
                
                with col_stat3:
                    taux_occupation = (salles_occupees / len(df_salles)) * 100 if len(df_salles) > 0 else 0
                    st.metric("Taux d'occupation", f"{taux_occupation:.1f}%")
                
                col_viz1, col_viz2 = st.columns(2)
                
                with col_viz1:
                    type_counts = df_salles.groupby('type').size().reset_index(name='count')
                    if not type_counts.empty:
                        fig1 = px.bar(
                            type_counts,
                            x='type',
                            y='count',
                            title="Salles par type",
                            labels={'count': 'Nombre', 'type': 'Type'},
                            color='type'
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col_viz2:
                    etat_counts = df_salles.groupby('etat').size().reset_index(name='count')
                    if not etat_counts.empty:
                        fig2 = px.pie(
                            etat_counts,
                            names='etat',
                            values='count',
                            title="État des salles",
                            color='etat',
                            color_discrete_map={'Occupée': '#FF6B6B', 'Libre': '#4ECDC4'}
                        )
                        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Aucune donnée sur les salles disponibles")

# =========================
# ONGLET 3: CONFLITS
# =========================
with tab_conflits:
    st.header("⚠️ Conflits Détectés")
    
    df_conflits_summary = get_conflits_summary()
    df_conflits_detail = get_detailed_conflits()
    
    if df_conflits_summary is not None and not df_conflits_summary.empty:
        st.subheader("Résumé des conflits")
        
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        
        with col_sum1:
            total_conflits = df_conflits_summary['nombre'].sum()
            st.metric("Total conflits", total_conflits)
        
        with col_sum2:
            types_conflits = len(df_conflits_summary)
            st.metric("Types de conflits", types_conflits)
        
        with col_sum3:
            if df_conflits_detail is not None and not df_conflits_detail.empty and 'date_conflit' in df_conflits_detail.columns:
                dates_unique = df_conflits_detail['date_conflit'].nunique()
                st.metric("Jours avec conflits", dates_unique)
            else:
                st.metric("Jours avec conflits", 0)
        
        st.markdown("### 📋 Résumé par type")
        current_date = datetime.now().strftime("%Y%m%d_%H%M")
        base_filename_summary = f"conflits_resume_{current_date}"
        
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            st.markdown(download_csv(df_conflits_summary, base_filename_summary), unsafe_allow_html=True)
        with col_dl2:
            st.markdown(download_excel(df_conflits_summary, base_filename_summary), unsafe_allow_html=True)
        with col_dl3:
            st.markdown(download_pdf(df_conflits_summary, base_filename_summary, "Résumé des Conflits"), unsafe_allow_html=True)
        
        st.dataframe(
            df_conflits_summary,
            column_config={
                "type_conflit": "Type de conflit",
                "nombre": "Nombre",
                "elements": "Éléments concernés",
                "premiere_date": "Première occurrence",
                "derniere_date": "Dernière occurrence"
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("### 🔍 Détails des conflits")
        if df_conflits_detail is not None and not df_conflits_detail.empty:
            base_filename_detail = f"conflits_detail_{current_date}"
            
            col_dld1, col_dld2, col_dld3 = st.columns(3)
            with col_dld1:
                st.markdown(download_csv(df_conflits_detail, base_filename_detail), unsafe_allow_html=True)
            with col_dld2:
                st.markdown(download_excel(df_conflits_detail, base_filename_detail), unsafe_allow_html=True)
            with col_dld3:
                st.markdown(download_pdf(df_conflits_detail, base_filename_detail, "Détails des Conflits"), unsafe_allow_html=True)
            
            st.dataframe(
                df_conflits_detail,
                column_config={
                    "type_conflit": "Type",
                    "element": "Élément",
                    "matricule": "Matricule",
                    "date_conflit": "Date",
                    "nombre_examens": "Nombre examens"
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            with st.expander("📈 Analyse des conflits"):
                if not df_conflits_summary.empty:
                    fig = px.bar(
                        df_conflits_summary,
                        x='type_conflit',
                        y='nombre',
                        title="Répartition des conflits par type",
                        labels={'nombre': 'Nombre de conflits', 'type_conflit': 'Type de conflit'},
                        color='nombre',
                        text='nombre'
                    )
                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📭 Aucun détail de conflit disponible")
    else:
        st.success("✅ Aucun conflit détecté !")

# =========================
# ONGLET 4: PROFESSEURS
# =========================
with tab_professeurs:
    st.header("👨‍🏫 Charge des Professeurs")
    
    df_professeurs = get_heures_professeurs()
    
    if display_metrics_section(df_professeurs, "Charge des Professeurs"):
        st.dataframe(
            df_professeurs,
            column_config={
                "professeur": "Professeur",
                "departement": "Département",
                "heures_examens": "Heures examens",
                "total_surveillances": "Surveillances",
                "email": "Email",
                "specialite": "Spécialité"
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        with st.expander("📊 Analyse de la charge"):
            if not df_professeurs.empty:
                col_ana1, col_ana2 = st.columns(2)
                
                with col_ana1:
                    top_10 = df_professeurs.nlargest(10, 'heures_examens')
                    if not top_10.empty:
                        fig1 = px.bar(
                            top_10,
                            x='professeur',
                            y='heures_examens',
                            title="Top 10 - Charge en heures",
                            labels={'heures_examens': 'Heures', 'professeur': 'Professeur'},
                            color='departement',
                            text='heures_examens'
                        )
                        fig1.update_traces(texttemplate='%{text:.1f}h', textposition='outside')
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col_ana2:
                    dept_avg = df_professeurs.groupby('departement').agg({
                        'heures_examens': 'mean',
                        'professeur': 'count'
                    }).reset_index()
                    dept_avg = dept_avg.rename(columns={'professeur': 'nb_professeurs', 'heures_examens': 'moyenne_heures'})
                    dept_avg['moyenne_heures'] = dept_avg['moyenne_heures'].round(1)
                    
                    if not dept_avg.empty:
                        fig2 = px.bar(
                            dept_avg,
                            x='departement',
                            y='moyenne_heures',
                            title="Moyenne d'heures par département",
                            labels={'moyenne_heures': 'Heures moyennes', 'departement': 'Département'},
                            text='moyenne_heures',
                            color='nb_professeurs'
                        )
                        fig2.update_traces(texttemplate='%{text:.1f}h', textposition='outside')
                        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Aucune donnée sur les professeurs")

# =========================
# ONGLET 5: SURVEILLANCES
# =========================
with tab_surveillances:
    st.header("👥 Surveillance des Examens")
    
    df_surveillances = get_surveillances()
    
    if display_metrics_section(df_surveillances, "Surveillances"):
        st.dataframe(
            df_surveillances,
            column_config={
                "professeur": "Professeur",
                "departement": "Département",
                "nb_surveillances": "Nombre surveillances",
                "total_heures": "Heures créditées",
                "priorite_moyenne": "Priorité moyenne"
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        with st.expander("📈 Analyse des surveillances"):
            if not df_surveillances.empty:
                col_surv1, col_surv2 = st.columns(2)
                
                with col_surv1:
                    top_surveillants = df_surveillances.nlargest(10, 'nb_surveillances')
                    if not top_surveillants.empty:
                        fig1 = px.bar(
                            top_surveillants,
                            x='professeur',
                            y='nb_surveillances',
                            title="Top 10 surveillants",
                            labels={'nb_surveillances': 'Nombre de surveillances', 'professeur': 'Professeur'},
                            color='departement',
                            text='nb_surveillances'
                        )
                        fig1.update_traces(texttemplate='%{text}', textposition='outside')
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col_surv2:
                    dept_surveillances = df_surveillances.groupby('departement')['nb_surveillances'].sum().reset_index()
                    if not dept_surveillances.empty:
                        fig2 = px.pie(
                            dept_surveillances,
                            names='departement',
                            values='nb_surveillances',
                            title="Surveillances par département",
                            hole=0.3
                        )
                        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Aucune donnée de surveillances")

# =========================
# ONGLET 6: STATISTIQUES
# =========================
with tab_stats:
    st.header("📈 Statistiques Globales")
    
    df_stats = get_statistiques()
    
    if df_stats is not None and not df_stats.empty:
        st.subheader("Statistiques Globales")
        
        cols = st.columns(3)
        for idx, row in df_stats.iterrows():
            with cols[idx % 3]:
                if '%' in row['categorie']:
                    st.metric(row['categorie'], row['valeur'])
                else:
                    try:
                        value = int(float(row['valeur'])) if '.' in row['valeur'] else int(row['valeur'])
                        st.metric(row['categorie'], value)
                    except:
                        st.metric(row['categorie'], row['valeur'])
        
        current_date = datetime.now().strftime("%Y%m%d_%H%M")
        base_filename = f"statistiques_globales_{current_date}"
        
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            st.markdown(download_csv(df_stats, base_filename), unsafe_allow_html=True)
        with col_dl2:
            st.markdown(download_excel(df_stats, base_filename), unsafe_allow_html=True)
        with col_dl3:
            st.markdown(download_pdf(df_stats, base_filename, "Statistiques Globales"), unsafe_allow_html=True)
        
        st.dataframe(
            df_stats,
            column_config={
                "categorie": "Catégorie",
                "valeur": "Valeur"
            },
            hide_index=True,
            use_container_width=True
        )
        
        with st.expander("📊 Visualisation des indicateurs"):
            if not df_stats.empty:
                df_graph = df_stats.copy()
                df_graph['valeur_num'] = df_graph['valeur'].apply(
                    lambda x: float(x.replace('%', '')) if '%' in x else (float(x) if x.replace('.', '').replace('-', '').isdigit() else 0)
                )
                df_graph['type'] = df_graph['categorie'].apply(lambda x: 'Pourcentage' if '%' in x else 'Nombre')
                
                fig = px.bar(
                    df_graph,
                    x='categorie',
                    y='valeur_num',
                    title="Indicateurs clés de performance",
                    labels={'valeur_num': 'Valeur', 'categorie': 'Indicateur'},
                    color='type',
                    text='valeur'
                )
                st.plotly_chart(fig, use_container_width=True)
                
        with st.expander("ℹ️ Informations système"):
            st.info("""
            **Plateforme d'Optimisation des Emplois du Temps d'Examens Universitaires**
            
            Cette interface permet au Vice-Doyen de:
            - Visualiser l'ensemble du planning des examens
            - Surveiller l'occupation des salles
            - Détecter et analyser les conflits
            - Évaluer la charge de travail des professeurs
            - Exporter les données dans différents formats
            
            **Fonctionnalités d'export:**
            - CSV: Format simple pour traitement de données
            - Excel: Format complet avec mise en forme
            - PDF: Rapport professionnel pour documentation
            """)
    else:
        st.warning("⚠️ Impossible de récupérer les statistiques")

# =========================
# BARRE LATÉRALE - ACTIONS RAPIDES
# =========================
with st.sidebar:
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #1E3A8A 0%, #2C5282 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;'>
            <h3 style='margin: 0; text-align: center;'>👑 {st.session_state.get('nom_complet', 'Vice-Doyen')}</h3>
            <p style='text-align: center; margin: 5px 0 0 0; font-size: 0.9em;'>Matricule: <code>{st.session_state.get('matricule', 'VD-001')}</code></p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # SECTION 1: EXPORT COMPLET
    st.markdown("### 📤 Export Complet")
    
    if st.button("📊 Générer rapport global", type="primary", use_container_width=True, key="btn_rapport_global_vicedoyen"):
        with st.spinner("Préparation du rapport global..."):
            try:
                all_data = {
                    "Planning_Examens": get_planning_complet(),
                    "Salles": get_detailed_salles(),
                    "Conflits_Resume": get_conflits_summary(),
                    "Conflits_Detail": get_detailed_conflits(),
                    "Professeurs": get_heures_professeurs(),
                    "Surveillances": get_surveillances(),
                    "Statistiques": get_statistiques()
                }
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for sheet_name, df in all_data.items():
                        if df is not None and not df.empty:
                            safe_sheet_name = sheet_name[:31]
                            df.to_excel(writer, index=False, sheet_name=safe_sheet_name)
                
                excel_data = output.getvalue()
                b64 = base64.b64encode(excel_data).decode()
                
                current_date = datetime.now().strftime('%Y%m%d_%H%M')
                href = f'''
                <div style="text-align: center; margin: 20px 0;">
                    <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" 
                       download="rapport_global_{current_date}.xlsx" 
                       style="background-color: #1E3A8A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-size: 14px; font-weight: bold;">
                       📥 Télécharger rapport complet Excel
                    </a>
                </div>
                '''
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ Rapport global généré avec succès!")
                
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du rapport: {str(e)}")
    
    st.markdown("---")
    
    # SECTION 2: ACTIONS RAPIDES
    st.markdown("### ⚡ Actions Rapides")
    
    col_rapide1, col_rapide2 = st.columns(2)
    
    with col_rapide1:
        if st.button("🔄 Actualiser", use_container_width=True, key="btn_actualiser_vicedoyen"):
            st.rerun()
    
    with col_rapide2:
        if st.button("📋 Vue d'ensemble", use_container_width=True, key="btn_vue_ensemble_vicedoyen"):
            with st.expander("📊 Vue d'ensemble rapide", expanded=True):
                df_stats_rapide = get_statistiques()
                if df_stats_rapide is not None and not df_stats_rapide.empty:
                    for _, row in df_stats_rapide.iterrows():
                        if row['categorie'] in ['Examens total', 'Examens planifiés', 'Examens confirmés', 'Conflits détectés']:
                            st.metric(row['categorie'], row['valeur'])
    
    st.markdown("---")
    
    # SECTION 3: VALIDATION FINALE - VERSION SIMPLIFIÉE
    st.markdown("### ✅ Validation Finale")
    
    if st.button("✅ Valider EDT Final", type="primary", use_container_width=True, key="btn_valider_edt_vicedoyen"):
        with st.spinner("Validation en cours..."):
            try:
                # Test direct avec psycopg2
                conn = psycopg2.connect(
                    dbname="unuversity",
                    user="postgres",
                    password="0000",
                    host="localhost",
                    port="5433"
                )
                cursor = conn.cursor()
                
                # Exécuter la fonction
                cursor.execute("SELECT valider_edt_final(1)")
                result = cursor.fetchone()
                
                if result:
                    result_json = result[0]
                    
                    # Parser le JSON
                    if isinstance(result_json, str):
                        try:
                            result_data = json.loads(result_json)
                        except:
                            result_data = {"success": False, "message": "Erreur parsing JSON"}
                    else:
                        result_data = result_json
                    
                    # Afficher le résultat
                    if result_data.get('success'):
                        if result_data.get('statut') == 'deja_valide':
                            st.success(f"✅ {result_data.get('message')}")
                            st.info(f"📊 {result_data.get('examens_confirmes')} examens déjà confirmés")
                        else:
                            st.success(f"🎉 {result_data.get('message')}")
                            st.balloons()
                            st.info(f"📈 {result_data.get('examens_confirmes')} examens confirmés")
                    else:
                        st.error(f"❌ {result_data.get('message')}")
                        
                    if 'conflits' in result_data and result_data['conflits'] > 0:
                        st.warning(f"⚠️ {result_data['conflits']} conflits détectés")
                else:
                    st.warning("⚠️ La fonction n'a retourné aucun résultat")
                
                cursor.close()
                conn.close()
                    
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")
                st.info("ℹ️ Assurez-vous que la fonction 'valider_edt_final' existe dans la base 'unuversity'")
    
    st.markdown("---")
    
    # SECTION 4: KPIs ACADÉMIQUES
    st.markdown("### 📊 KPIs Académiques")
    
    if st.button("📈 Afficher KPIs", use_container_width=True, key="btn_afficher_kpis_vicedoyen"):
        with st.expander("📊 Indicateurs de Performance", expanded=True):
            # Créer les vues KPI si elles n'existent pas
            try:
                # Vue KPI heures professeurs
                query_kpi1 = """
                SELECT 
                    d.nom as departement,
                    p.prenom || ' ' || p.nom as professeur,
                    COUNT(DISTINCT e.id) as nb_examens_responsable,
                    ROUND(COALESCE(SUM(e.duree_minutes) / 60.0, 0), 2) as heures_responsable
                FROM gestion_examens.professeurs p
                JOIN gestion_examens.departements d ON p.dept_id = d.id
                LEFT JOIN gestion_examens.examens e ON p.id = e.professeur_responsable_id 
                    AND e.statut IN ('planifie', 'confirme')
                GROUP BY d.id, d.nom, p.id, p.prenom, p.nom
                ORDER BY heures_responsable DESC 
                LIMIT 10
                """
                df_kpi1 = db.execute_query(query_kpi1)
                if df_kpi1 is not None and not df_kpi1.empty:
                    st.subheader("🏆 Top 10 - Charge des professeurs")
                    st.dataframe(df_kpi1, use_container_width=True)
                else:
                    st.info("ℹ️ Aucune donnée KPI pour les professeurs")
                
                # Vue KPI utilisation salles
                query_kpi2 = """
                SELECT 
                    'Taux occupation global' as indicateur,
                    ROUND(
                        COUNT(DISTINCT e.salle_id) * 100.0 /
                        GREATEST((SELECT COUNT(*) FROM gestion_examens.salles_examen), 1),
                    2) as valeur,
                    '%' as unite
                FROM gestion_examens.examens e
                WHERE e.statut IN ('planifie', 'confirme')
                """
                df_kpi2 = db.execute_query(query_kpi2)
                if df_kpi2 is not None and not df_kpi2.empty:
                    st.subheader("🏢 Utilisation des salles")
                    for _, row in df_kpi2.iterrows():
                        st.metric(row['indicateur'], f"{row['valeur']}{row['unite']}")
                else:
                    st.info("ℹ️ Aucune donnée KPI pour les salles")
                    
            except Exception as e:
                st.error(f"❌ Erreur KPIs: {str(e)}")
    
    st.markdown("---")
    
    # SECTION 5: DÉCONNEXION
    if st.button("🚪 Déconnexion", type="secondary", use_container_width=True, key="btn_deconnexion_vicedoyen"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# =========================
# PIED DE PAGE
# =========================
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; color: #666; font-size: 12px; padding: 20px;'>
        <p>🎓 <b>Plateforme d'Optimisation des Emplois du Temps d'Examens Universitaires</b> | Vue Vice-Doyen</p>
        <p>📅 Généré le: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | 🔄 Données actualisées en temps réel</p>
    </div>
""", unsafe_allow_html=True)