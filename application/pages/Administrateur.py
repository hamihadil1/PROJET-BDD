# pages/Administrateur.py - النسخة الكاملة مع دعم PDF
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from database import db
import base64
from io import BytesIO
import numpy as np
from fpdf import FPDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import tempfile
import io
import json
import zipfile

st.set_page_config(page_title="Administrateur", layout="wide")

# =========================
# AUTHENTIFICATION - VERSION FINALE
# =========================

def verifier_acces_admin():
    """التحقق النهائي من صلاحية الإدارة"""
    
    # التحقق من تسجيل الدخول
    if 'logged_in' not in st.session_state:
        st.error("⛔ Veuillez vous connecter d'abord")
        time.sleep(2)
        st.switch_page("app.py")
        return False
    
    # إصلاح مشكلة encoding للنوع
    matricule = st.session_state.get('matricule', '')
    user_type = str(st.session_state.get('type_utilisateur', '')).lower()
    
    # إذا كان ADMIN-001، أجبر النوع على administrateur
    if matricule == 'ADMIN-001':
        st.session_state.type_utilisateur = 'administrateur'
        if 'administrateur system' in st.session_state.get('nom_complet', '').lower():
            st.session_state.nom_complet = 'Administrateur Systeme'
        return True
    
    # التحقق من أنواع أخرى
    if 'administrateur' in user_type:
        return True
    
    # إذا لم يكن مسؤولاً، أظهر رسالة مناسبة
    st.error(f"⛔ Accès réservé aux administrateurs")
    
    # تحديد الصفحة المناسبة حسب النوع
    pages = {
        'vice_doyen': ("Vice_Doyen.py", "👔 Panel Vice-Doyen"),
        'chef_departement': ("Chef_Departement.py", "👨‍💼 Panel Chef Département"),
        'professeur': ("Professeur.py", "👨‍🏫 Panel Professeur"),
        'etudiant': ("Etudiant.py", "🎓 Panel Étudiant")
    }
    
    target_page = "app.py"
    btn_text = "🔙 Retour à l'accueil"
    
    for key, (page, text) in pages.items():
        if key in user_type:
            target_page = f"pages/{page}"
            btn_text = f"Aller au {text}"
            break
    
    # زر التوجيه
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(btn_text, use_container_width=True):
            st.switch_page(target_page)
    
    return False

# التحقق من الوصول
if not verifier_acces_admin():
    st.stop()

# =========================
# FONCTIONS DE DONNÉES AMÉLIORÉES
# =========================

@st.cache_data(ttl=300)
def get_statistiques_globales():
    """إحصائيات عالمية مع تخزين مؤقت"""
    try:
        query = """
        WITH stats AS (
            -- Étudiants actifs
            SELECT '👨‍🎓 Étudiants actifs' as indicateur, 
                   COUNT(*) as valeur,
                   COUNT(*) * 100.0 / (SELECT COUNT(*) FROM gestion_examens.etudiants) as pourcentage
            FROM gestion_examens.etudiants 
            WHERE statut = 'actif'
            
            UNION ALL
            
            -- Professeurs actifs
            SELECT '👨‍🏫 Professeurs actifs',
                   COUNT(*),
                   COUNT(*) * 100.0 / (SELECT COUNT(*) FROM gestion_examens.professeurs)
            FROM gestion_examens.professeurs 
            WHERE statut = 'actif'
            
            UNION ALL
            
            -- Examens planifiés
            SELECT '📝 Examens planifiés',
                   COUNT(*),
                   COUNT(*) * 100.0 / GREATEST((SELECT COUNT(*) FROM gestion_examens.modules), 1)
            FROM gestion_examens.examens 
            WHERE statut = 'planifie'
            
            UNION ALL
            
            -- Salles occupées
            SELECT '🏢 Salles occupées',
                   COUNT(DISTINCT salle_id),
                   COUNT(DISTINCT salle_id) * 100.0 / 
                   GREATEST((SELECT COUNT(*) FROM gestion_examens.salles_examen), 1)
            FROM gestion_examens.examens 
            WHERE statut IN ('planifie', 'confirme')
            
            UNION ALL
            
            -- Conflits détectés
            SELECT '⚠️ Conflits détectés',
                   COALESCE((SELECT COUNT(*) FROM gestion_examens.vue_conflits), 0),
                   0
                   
            UNION ALL
            
            -- Utilisateurs connectés (24h)
            SELECT '🔗 Utilisateurs (24h)',
                   COUNT(*),
                   COUNT(*) * 100.0 / (SELECT COUNT(*) FROM gestion_examens.authentification)
            FROM gestion_examens.authentification 
            WHERE derniere_connexion > NOW() - INTERVAL '24 hours'
            
            UNION ALL
            
            -- Taux réussite
            SELECT '🎯 Taux réussite',
                   ROUND(AVG(CASE WHEN note >= 10 THEN 1 ELSE 0 END) * 100, 1),
                   AVG(CASE WHEN note >= 10 THEN 1 ELSE 0 END) * 100
            FROM gestion_examens.inscriptions 
            WHERE note IS NOT NULL
            
            UNION ALL
            
            -- Charge moyenne profs
            SELECT '⚖️ Charge moyenne',
                   ROUND(AVG(total_surveillances), 2),
                   AVG(total_surveillances) * 10
            FROM gestion_examens.professeurs 
            WHERE statut = 'actif'
        )
        SELECT indicateur, 
               valeur::TEXT, 
               ROUND(pourcentage, 1) as pourcentage
        FROM stats
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur stats: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_occupation_salles_detaille():
    """تفصيل احتلال القاعات"""
    try:
        query = """
        SELECT 
            s.type,
            s.nom,
            s.capacite,
            s.batiment,
            COUNT(e.id) as examens_planifies,
            COALESCE(SUM(e.duree_minutes), 0) as minutes_total,
            ROUND(
                COUNT(e.id) * 100.0 / 
                GREATEST((SELECT COUNT(*) FROM gestion_examens.examens WHERE statut = 'planifie'), 1),
                1
            ) as taux_utilisation,
            CASE 
                WHEN COUNT(e.id) = 0 THEN '🟢 Libre'
                WHEN COUNT(e.id) <= 2 THEN '🟡 Modéré'
                ELSE '🔴 Occupé'
            END as statut
        FROM gestion_examens.salles_examen s
        LEFT JOIN gestion_examens.examens e ON s.id = e.salle_id 
            AND e.statut IN ('planifie', 'confirme')
        GROUP BY s.id, s.type, s.nom, s.capacite, s.batiment
        ORDER BY s.type, examens_planifies DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur occupation: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_conflits_par_type():
    """تحليل النزاعات حسب النوع"""
    try:
        query = """
        SELECT 
            type_conflit,
            COUNT(*) as nombre_conflits,
            STRING_AGG(DISTINCT element, ', ' ORDER BY element LIMIT 5) as elements_concernees,
            MIN(date_conflit) as premiere_date,
            MAX(date_conflit) as derniere_date,
            CASE 
                WHEN type_conflit LIKE '%étudiant%' THEN 'Étudiant'
                WHEN type_conflit LIKE '%professeur%' THEN 'Professeur'
                ELSE 'Infrastructure'
            END as categorie,
            CASE 
                WHEN type_conflit LIKE '%étudiant%' THEN 3
                WHEN type_conflit LIKE '%professeur%' THEN 2
                ELSE 1
            END as priorite
        FROM gestion_examens.vue_conflits
        GROUP BY type_conflit
        ORDER BY priorite DESC, nombre_conflits DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur conflits: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def get_planification_recommandations():
    """توصيات التخطيط"""
    try:
        query = """
        WITH modules_sans_examen AS (
            SELECT 
                m.id as module_id,
                m.nom as module,
                f.nom as formation,
                d.nom as departement,
                COUNT(DISTINCT i.etudiant_id) as nb_etudiants,
                ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT i.etudiant_id) DESC) as rang
            FROM gestion_examens.modules m
            JOIN gestion_examens.formations f ON m.formation_id = f.id
            JOIN gestion_examens.departements d ON f.dept_id = d.id
            JOIN gestion_examens.inscriptions i ON m.id = i.module_id
                AND i.statut IN ('inscrit', 'en_cours')
            WHERE NOT EXISTS (
                SELECT 1 FROM gestion_examens.examens e 
                WHERE e.module_id = m.id 
                AND e.statut IN ('planifie', 'confirme')
            )
            GROUP BY m.id, m.nom, f.nom, d.nom
            HAVING COUNT(DISTINCT i.etudiant_id) > 0
        ),
        profs_surcharge AS (
            SELECT 
                p.id as prof_id,
                p.prenom || ' ' || p.nom as professeur,
                d.nom as departement,
                p.charge_max_examens,
                COUNT(DISTINCT e.id) as nb_examens_responsable,
                p.total_surveillances,
                CASE 
                    WHEN COUNT(DISTINCT e.id) > p.charge_max_examens THEN 'CRITIQUE'
                    WHEN p.total_surveillances > 5 THEN 'ALERTE'
                    ELSE 'NORMAL'
                END as niveau_alerte
            FROM gestion_examens.professeurs p
            JOIN gestion_examens.departements d ON p.dept_id = d.id
            LEFT JOIN gestion_examens.examens e ON p.id = e.professeur_responsable_id
                AND e.statut IN ('planifie', 'confirme')
            WHERE p.statut = 'actif'
            GROUP BY p.id, p.prenom, p.nom, d.nom, p.charge_max_examens, p.total_surveillances
        ),
        salles_sous_utilisees AS (
            SELECT 
                s.id as salle_id,
                s.nom as salle,
                s.type,
                s.capacite,
                COUNT(e.id) as nb_examens,
                ROUND(s.capacite * 0.3) as seuil_minimal
            FROM gestion_examens.salles_examen s
            LEFT JOIN gestion_examens.examens e ON s.id = e.salle_id 
                AND e.statut IN ('planifie', 'confirme')
            WHERE s.disponible = TRUE
            GROUP BY s.id, s.nom, s.type, s.capacite
            HAVING COUNT(e.id) < 2
        )
        SELECT 'Modules sans examen' as type_recommandation,
               COUNT(*) as nombre,
               STRING_AGG(module, ', ' ORDER BY rang LIMIT 3) as elements
        FROM modules_sans_examen
        WHERE rang <= 10
        
        UNION ALL
        
        SELECT 'Professeurs en surcharge',
               COUNT(*),
               STRING_AGG(professeur, ', ' LIMIT 3)
        FROM profs_surcharge
        WHERE niveau_alerte IN ('CRITIQUE', 'ALERTE')
        
        UNION ALL
        
        SELECT 'Salles sous-utilisées',
               COUNT(*),
               STRING_AGG(salle, ', ' LIMIT 3)
        FROM salles_sous_utilisees
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur recommandations: {str(e)}")
        return pd.DataFrame()


def execute_write(query, params=None):
    """تنفيذ INSERT / UPDATE / DELETE بدون المساس بـ database.py"""
    try:
        if not db.conn:
            db.connect()

        with db.conn.cursor() as cursor:
            cursor.execute(query, params)
            db.conn.commit()
            return True
    except Exception as e:
        db.conn.rollback()
        st.error(f"❌ Erreur SQL : {e}")
        return False


@st.cache_data(ttl=60)
def get_logs_activite_recente():
    """سجلات النشاط الحديثة"""
    try:
        query = """
        SELECT 
            a.matricule,
            a.type_utilisateur,
            a.derniere_connexion,
            TO_CHAR(a.derniere_connexion, 'DD/MM/YYYY HH24:MI:SS') as date_formattee,
            CASE 
                WHEN a.type_utilisateur = 'administrateur' THEN '👑'
                WHEN a.type_utilisateur = 'vice_doyen' THEN '👔'
                WHEN a.type_utilisateur = 'chef_departement' THEN '👨‍💼'
                WHEN a.type_utilisateur = 'professeur' THEN '👨‍🏫'
                WHEN a.type_utilisateur = 'etudiant' THEN '🎓'
                ELSE '👤'
            END as emoji,
            CASE 
                WHEN a.derniere_connexion > NOW() - INTERVAL '1 hour' THEN '🟢 Maintenant'
                WHEN a.derniere_connexion > NOW() - INTERVAL '4 hours' THEN '🟡 Récent'
                WHEN a.derniere_connexion > NOW() - INTERVAL '24 hours' THEN '🟠 Hier'
                ELSE '🔴 Ancien'
            END as fraicheur
        FROM gestion_examens.authentification a
        WHERE a.derniere_connexion IS NOT NULL
        ORDER BY a.derniere_connexion DESC
        LIMIT 15
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur logs: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_all_examens():
    """الحصول على جميع الامتحانات من قاعدة البيانات"""
    try:
        query = """
        SELECT 
            e.id,
            m.nom as module,
            f.nom as formation,
            d.nom as departement,
            p.prenom || ' ' || p.nom as professeur_responsable,
            s.nom as salle,
            e.date_heure,
            TO_CHAR(e.date_heure, 'DD/MM/YYYY HH24:MI') as date_formattee,
            e.duree_minutes,
            e.type_examen,
            e.statut,
            COUNT(DISTINCT i.etudiant_id) as nb_etudiants
        FROM gestion_examens.examens e
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.formations f ON e.formation_id = f.id
        JOIN gestion_examens.departements d ON f.dept_id = d.id
        LEFT JOIN gestion_examens.professeurs p ON e.professeur_responsable_id = p.id
        LEFT JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
        LEFT JOIN gestion_examens.inscriptions i ON e.module_id = i.module_id 
            AND i.statut IN ('inscrit', 'en_cours')
        GROUP BY e.id, m.nom, f.nom, d.nom, p.prenom, p.nom, s.nom, e.date_heure, 
                 e.duree_minutes, e.type_examen, e.statut
        ORDER BY e.date_heure DESC
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur examens: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_surveillants_examens():
    """الحصول على المراقبين لكل امتحان"""
    try:
        query = """
        SELECT 
            e.id as examen_id,
            m.nom as module,
            p.prenom || ' ' || p.nom as surveillant,
            s.role,
            s.priorite
        FROM gestion_examens.surveillances s
        JOIN gestion_examens.examens e ON s.examen_id = e.id
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.professeurs p ON s.professeur_id = p.id
        ORDER BY e.id, s.priorite
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur surveillants: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_etudiants_par_examen():
    """الحصول على الطلاب المسجلين في كل امتحان"""
    try:
        query = """
        SELECT 
            e.id as examen_id,
            m.nom as module,
            et.prenom || ' ' || et.nom as etudiant,
            et.matricule,
            i.statut as statut_inscription,
            i.note
        FROM gestion_examens.examens e
        JOIN gestion_examens.modules m ON e.module_id = m.id
        JOIN gestion_examens.inscriptions i ON m.id = i.module_id
        JOIN gestion_examens.etudiants et ON i.etudiant_id = et.id
        WHERE i.statut IN ('inscrit', 'en_cours', 'termine')
        ORDER BY e.id, et.nom
        """
        result = db.execute_query(query)
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur étudiants: {str(e)}")
        return pd.DataFrame()

def generer_edt_intelligent():
    """إنشاء جدول زمني ذكي"""
    try:
        with st.spinner("🔄 Génération de l'emploi du temps intelligent..."):
            start_time = time.time()
            
            # 1. تنظيف البيانات القديمة
            execute_write("""
                DELETE FROM gestion_examens.examens 
                WHERE statut = 'planifie' 
                AND date_heure < NOW()
            """)
            
            # 2. إعادة تعيين المراقبين
            execute_write("UPDATE gestion_examens.professeurs SET total_surveillances = 0")
            execute_write("DELETE FROM gestion_examens.surveillances")

            
            # 3. توليد امتحانات جديدة
            query_generation = """
            INSERT INTO gestion_examens.examens (
                module_id,
                formation_id,
                professeur_responsable_id,
                salle_id,
                date_heure,
                duree_minutes,
                type_examen,
                statut
            )
            SELECT 
                m.id as module_id,
                f.id as formation_id,
                (
                    SELECT p.id 
                    FROM gestion_examens.professeurs p
                    WHERE p.dept_id = f.dept_id
                    AND p.statut = 'actif'
                    AND (
                        SELECT COUNT(*)
                        FROM gestion_examens.examens e2
                        WHERE e2.professeur_responsable_id = p.id
                        AND DATE(e2.date_heure) = DATE(NOW() + INTERVAL '7 days')
                    ) < p.charge_max_examens
                    ORDER BY p.total_surveillances ASC
                    LIMIT 1
                ) as professeur_id,
                (
                    SELECT s.id 
                    FROM gestion_examens.salles_examen s
                    WHERE s.disponible = TRUE
                    AND s.capacite >= (
                        SELECT COUNT(DISTINCT i.etudiant_id)
                        FROM gestion_examens.inscriptions i
                        WHERE i.module_id = m.id
                        AND i.statut IN ('inscrit', 'en_cours')
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM gestion_examens.examens e3
                        WHERE e3.salle_id = s.id
                        AND e3.date_heure = (NOW() + INTERVAL '7 days' + INTERVAL '9 hours')
                    )
                    ORDER BY s.capacite - (
                        SELECT COUNT(DISTINCT i.etudiant_id)
                        FROM gestion_examens.inscriptions i
                        WHERE i.module_id = m.id
                    ) ASC
                    LIMIT 1
                ) as salle_id,
                NOW() + INTERVAL '7 days' + INTERVAL '9 hours' + 
                (INTERVAL '1 day' * (ROW_NUMBER() OVER () % 10)),
                90,
                'normal',
                'planifie'
            FROM gestion_examens.modules m
            JOIN gestion_examens.formations f ON m.formation_id = f.id
            WHERE EXISTS (
                SELECT 1 FROM gestion_examens.inscriptions i
                WHERE i.module_id = m.id
                AND i.statut IN ('inscrit', 'en_cours')
            )
            AND NOT EXISTS (
                SELECT 1 FROM gestion_examens.examens e
                WHERE e.module_id = m.id
                AND e.statut IN ('planifie', 'confirme')
            )
            ORDER BY (
                SELECT COUNT(DISTINCT i.etudiant_id)
                FROM gestion_examens.inscriptions i
                WHERE i.module_id = m.id
                AND i.statut IN ('inscrit', 'en_cours')
            ) DESC
            LIMIT 25;
            """
            
            success = execute_write(query_generation)
            
            if not success:
                return "❌ Erreur lors de la génération"
            
            # 4. توزيع المراقبين
            query_surveillance = """
            DO $$
            DECLARE
                exam_record RECORD;
                prof_record RECORD;
                surveillants_ajoutes INTEGER := 0;
            BEGIN
                FOR exam_record IN (
                    SELECT e.id as exam_id, f.dept_id
                    FROM gestion_examens.examens e
                    JOIN gestion_examens.modules m ON e.module_id = m.id
                    JOIN gestion_examens.formations f ON m.formation_id = f.id
                    WHERE e.statut = 'planifie'
                    AND NOT EXISTS (
                        SELECT 1 FROM gestion_examens.surveillances s 
                        WHERE s.examen_id = e.id
                    )
                ) LOOP
                    
                    -- Chercher 2 surveillants
                    FOR i IN 1..2 LOOP
                        SELECT p.id INTO prof_record
                        FROM gestion_examens.professeurs p
                        WHERE p.dept_id = exam_record.dept_id
                        AND p.id != (
                            SELECT professeur_responsable_id 
                            FROM gestion_examens.examens 
                            WHERE id = exam_record.exam_id
                        )
                        AND p.statut = 'actif'
                        AND NOT EXISTS (
                            SELECT 1 FROM gestion_examens.surveillances s
                            WHERE s.professeur_id = p.id
                            AND s.examen_id = exam_record.exam_id
                        )
                        ORDER BY p.total_surveillances ASC
                        LIMIT 1;
                        
                        IF prof_record.id IS NOT NULL THEN
                            INSERT INTO gestion_examens.surveillances 
                            (examen_id, professeur_id, priorite, role)
                            VALUES (exam_record.exam_id, prof_record.id, 1, 'surveillant');
                            
                            UPDATE gestion_examens.professeurs 
                            SET total_surveillances = total_surveillances + 1
                            WHERE id = prof_record.id;
                            
                            surveillants_ajoutes := surveillants_ajoutes + 1;
                        END IF;
                    END LOOP;
                END LOOP;
            END $$;
            """
            
            execute_write(query_surveillance)

            
            end_time = time.time()
            execution_time = round(end_time - start_time, 2)
            
            # الحصول على عدد الامتحانات المولدة
            count_query = "SELECT COUNT(*) FROM gestion_examens.examens WHERE statut = 'planifie'"
            count_result = db.execute_query(count_query)
            exam_count = count_result.iloc[0, 0] if count_result is not None else 0
            
            return f"✅ EDT généré avec succès! {exam_count} examens planifiés en {execution_time}s"
            
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def optimiser_ressources():
    """تحسين الموارد"""
    try:
        with st.spinner("⚡ Optimisation des ressources en cours..."):
            
            # 1. توازن المراقبين
            execute_write("""
                WITH prof_avg AS (
                    SELECT AVG(total_surveillances) as moyenne
                    FROM gestion_examens.professeurs 
                    WHERE statut = 'actif'
                )
                UPDATE gestion_examens.professeurs p
                SET total_surveillances = (
                    SELECT ROUND(moyenne)
                    FROM prof_avg
                )
                WHERE p.statut = 'actif'
                AND p.total_surveillances = 0
            """)
            
            # 2. تحرير القاعات غير المستخدمة
            execute_write("""
                UPDATE gestion_examens.salles_examen s
                SET disponible = TRUE
                WHERE NOT EXISTS (
                    SELECT 1 FROM gestion_examens.examens e
                    WHERE e.salle_id = s.id
                    AND e.statut IN ('planifie', 'confirme')
                    AND e.date_heure > NOW()
                )
                AND s.disponible = FALSE
            """)
            
            return "✅ Ressources optimisées avec succès!"
            
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

# =========================
# FONCTIONS PDF PROFESSIONNELS - FIXED
# =========================

def generer_pdf_avance():
    """إنشاء PDF متقدم باستخدام ReportLab"""
    try:
        # جمع البيانات
        stats = get_statistiques_globales()
        occupation = get_occupation_salles_detaille()
        conflits = get_conflits_par_type()
        recommandations = get_planification_recommandations()
        
        # إنشاء buffer للPDF
        buffer = BytesIO()
        
        # إنشاء مستند
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # تنسيق العنوان الرئيسي
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # العنوان - بدون إيموجي
        story.append(Paragraph("RAPPORT ADMINISTRATIF DU SYSTÈME", title_style))
        
        # معلومات التقرير
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        info_text = f"""
        <b>Date de génération:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>
        <b>Administrateur:</b> {st.session_state.get('nom_complet', 'Administrateur Système')}<br/>
        <b>Matricule:</b> {st.session_state.get('matricule', 'ADMIN-001')}<br/>
        <b>Environnement:</b> Production
        """
        
        story.append(Paragraph(info_text, info_style))
        story.append(Spacer(1, 20))
        
        # القسم 1: الإحصائيات - إزالة الإيموجي
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#059669'),
            spaceAfter=12
        )
        
        story.append(Paragraph("1. STATISTIQUES GLOBALES", section_title_style))
        
        if not stats.empty:
            # تحضير جدول الإحصائيات - إزالة الإيموجي
            stats_clean = stats.copy()
            # إزالة الإيموجي من العناوين
            emoji_mapping = {
                '👨‍🎓': 'Étudiants',
                '👨‍🏫': 'Professeurs', 
                '📝': 'Examens',
                '🏢': 'Salles',
                '⚠️': 'Conflits',
                '🔗': 'Utilisateurs',
                '🎯': 'Taux',
                '⚖️': 'Charge'
            }
            
            for emoji, text in emoji_mapping.items():
                stats_clean['indicateur'] = stats_clean['indicateur'].str.replace(emoji, text)
            
            stats_data = [['Indicateur', 'Valeur', '%']]
            for _, row in stats_clean.iterrows():
                stats_data.append([
                    row['indicateur'],
                    row['valeur'],
                    f"{row['pourcentage']}%"
                ])
            
            # إنشاء الجدول
            stats_table = Table(stats_data, colWidths=[3.5*cm, 2*cm, 2*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 20))
        
        # القسم 2: القاعات - إزالة الإيموجي من الحالة
        story.append(Paragraph("2. UTILISATION DES SALLES", section_title_style))
        
        if not occupation.empty:
            # تحضير جدول القاعات
            occupation_clean = occupation.copy()
            # إزالة الإيموجي من الحالة
            occupation_clean['statut'] = occupation_clean['statut'].str.replace('🟢', 'Libre')
            occupation_clean['statut'] = occupation_clean['statut'].str.replace('🟡', 'Modéré')
            occupation_clean['statut'] = occupation_clean['statut'].str.replace('🔴', 'Occupé')
            
            salle_data = [['Salle', 'Type', 'Capacité', 'Examens', 'Statut']]
            for _, row in occupation_clean.head(8).iterrows():
                salle_data.append([
                    row['nom'],
                    row['type'],
                    str(row['capacite']),
                    str(row['examens_planifies']),
                    row['statut']
                ])
            
            salle_table = Table(salle_data, colWidths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm])
            salle_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(salle_table)
            story.append(Spacer(1, 20))
        
        # القسم 3: النزاعات - إزالة الإيموجي
        story.append(Paragraph("3. CONFLITS DÉTECTÉS", section_title_style))
        
        if not conflits.empty:
            # تحضير جدول النزاعات
            conflit_data = [['Type de conflit', 'Nombre', 'Priorité']]
            for _, row in conflits.iterrows():
                priorite_text = {
                    1: 'Basse',
                    2: 'Moyenne', 
                    3: 'Haute'
                }.get(row['priorite'], 'Basse')
                
                conflit_data.append([
                    row['type_conflit'],
                    str(row['nombre_conflits']),
                    priorite_text
                ])
            
            conflit_table = Table(conflit_data, colWidths=[5*cm, 2*cm, 3*cm])
            conflit_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(conflit_table)
            story.append(Spacer(1, 20))
        
        # القسم 4: التوصيات
        story.append(Paragraph("4. RECOMMANDATIONS", section_title_style))
        
        if not recommandations.empty:
            recommand_text = "<ul>"
            for _, row in recommandations.iterrows():
                recommand_text += f"<li><b>{row['type_recommandation']}:</b> {row['nombre']} éléments</li>"
            recommand_text += "</ul>"
            
            story.append(Paragraph(recommand_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # خاتمة
        conclusion_style = ParagraphStyle(
            'Conclusion',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceBefore=20
        )
        
        story.append(Paragraph("Rapport généré automatiquement par le système de gestion des examens universitaires.", conclusion_style))
        story.append(Paragraph("© 2024 Université - Tous droits réservés", conclusion_style))
        
        # بناء الPDF
        doc.build(story)
        
        # الحصول على البايتات
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Erreur génération PDF avancé: {str(e)}")
        return None


   

def generer_pdf_avance():
    """إنشاء PDF متقدم باستخدام ReportLab"""
    try:
        # جمع البيانات
        stats = get_statistiques_globales()
        occupation = get_occupation_salles_detaille()
        conflits = get_conflits_par_type()
        recommandations = get_planification_recommandations()
        
        # إنشاء buffer للPDF
        buffer = BytesIO()
        
        # إنشاء مستند
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # تنسيق العنوان الرئيسي
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # العنوان
        story.append(Paragraph("RAPPORT ADMINISTRATIF DU SYSTÈME", title_style))
        
        # معلومات التقرير
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        info_text = f"""
        <b>Date de génération:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>
        <b>Administrateur:</b> {st.session_state.get('nom_complet', 'Administrateur Système')}<br/>
        <b>Matricule:</b> {st.session_state.get('matricule', 'ADMIN-001')}<br/>
        <b>Environnement:</b> Production
        """
        
        story.append(Paragraph(info_text, info_style))
        story.append(Spacer(1, 20))
        
        # القسم 1: الإحصائيات
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#059669'),
            spaceAfter=12
        )
        
        story.append(Paragraph("1. STATISTIQUES GLOBALES", section_title_style))
        
        if not stats.empty:
            # تحضير جدول الإحصائيات
            stats_data = [['Indicateur', 'Valeur', '%']]
            for _, row in stats.iterrows():
                stats_data.append([
                    row['indicateur'],
                    row['valeur'],
                    f"{row['pourcentage']}%"
                ])
            
            # إنشاء الجدول
            stats_table = Table(stats_data, colWidths=[3.5*cm, 2*cm, 2*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 20))
        
        # القسم 2: القاعات
        story.append(Paragraph("2. UTILISATION DES SALLES", section_title_style))
        
        if not occupation.empty:
            # تحضير جدول القاعات
            salle_data = [['Salle', 'Type', 'Capacité', 'Examens', 'Statut']]
            for _, row in occupation.head(8).iterrows():
                salle_data.append([
                    row['nom'],
                    row['type'],
                    str(row['capacite']),
                    str(row['examens_planifies']),
                    row['statut']
                ])
            
            salle_table = Table(salle_data, colWidths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm])
            salle_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(salle_table)
            story.append(Spacer(1, 20))
        
        # القسم 3: النزاعات
        story.append(Paragraph("3. CONFLITS DÉTECTÉS", section_title_style))
        
        if not conflits.empty:
            # تحضير جدول النزاعات
            conflit_data = [['Type de conflit', 'Nombre', 'Priorité']]
            for _, row in conflits.iterrows():
                priorite_text = {
                    1: '🟢 Basse',
                    2: '🟡 Moyenne',
                    3: '🔴 Haute'
                }.get(row['priorite'], '🟢 Basse')
                
                conflit_data.append([
                    row['type_conflit'],
                    str(row['nombre_conflits']),
                    priorite_text
                ])
            
            conflit_table = Table(conflit_data, colWidths=[5*cm, 2*cm, 3*cm])
            conflit_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(conflit_table)
            story.append(Spacer(1, 20))
        
        # القسم 4: التوصيات
        story.append(Paragraph("4. RECOMMANDATIONS", section_title_style))
        
        if not recommandations.empty:
            recommand_text = "<ul>"
            for _, row in recommandations.iterrows():
                recommand_text += f"<li><b>{row['type_recommandation']}:</b> {row['nombre']} éléments</li>"
            recommand_text += "</ul>"
            
            story.append(Paragraph(recommand_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # خاتمة
        conclusion_style = ParagraphStyle(
            'Conclusion',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceBefore=20
        )
        
        story.append(Paragraph("Rapport généré automatiquement par le système de gestion des examens universitaires.", conclusion_style))
        story.append(Paragraph("© 2024 Université - Tous droits réservés", conclusion_style))
        
        # بناء الPDF
        doc.build(story)
        
        # الحصول على البايتات
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Erreur génération PDF avancé: {str(e)}")
        return None

def generer_rapport_texte():
    """إنشاء تقرير نصي"""
    try:
        stats = get_statistiques_globales()
        occupation = get_occupation_salles_detaille()
        conflits = get_conflits_par_type()
        recommandations = get_planification_recommandations()
        
        rapport = f"""
{'='*60}
RAPPORT ADMINISTRATIF - SYSTÈME DE GESTION DES EXAMENS
{'='*60}
Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Administrateur: {st.session_state.get('nom_complet', 'Administrateur')}
Matricule: {st.session_state.get('matricule', 'ADMIN-001')}

{'='*60}
1. STATISTIQUES GLOBALES
{'='*60}
"""
        
        if not stats.empty:
            for _, row in stats.iterrows():
                rapport += f"- {row['indicateur']}: {row['valeur']} ({row['pourcentage']}%)\n"
        
        rapport += f"""
        
{'='*60}
2. OCCUPATION DES SALLES
{'='*60}
"""
        
        if not occupation.empty:
            for _, row in occupation.head(5).iterrows():
                rapport += f"- {row['nom']} ({row['type']}): {row['examens_planifies']} examens, Statut: {row['statut']}\n"
        
        rapport += f"""
        
{'='*60}
3. CONFLITS DÉTECTÉS
{'='*60}
"""
        
        if not conflits.empty:
            total_conflits = conflits['nombre_conflits'].sum()
            rapport += f"Total conflits: {total_conflits}\n"
            for _, row in conflits.iterrows():
                rapport += f"- {row['type_conflit']}: {row['nombre_conflits']} occurrences\n"
        
        rapport += f"""
        
{'='*60}
4. RECOMMANDATIONS
{'='*60}
"""
        
        if not recommandations.empty:
            for _, row in recommandations.iterrows():
                rapport += f"- {row['type_recommandation']}: {row['nombre']} éléments\n"
        
        rapport += f"""
        
{'='*60}
5. SYNTHÈSE ET ACTIONS PRIORITAIRES
{'='*60}
1. Résoudre les conflits de haute priorité
2. Optimiser l'utilisation des salles sous-utilisées
3. Planifier les modules sans examen
4. Équilibrer la charge de travail des professeurs
5. Mettre à jour régulièrement les statistiques

{'='*60}
FIN DU RAPPORT
{'='*60}
"""
        
        return rapport.encode('utf-8')
        
    except Exception as e:
        return f"❌ Erreur génération rapport: {str(e)}".encode('utf-8')

# =========================
# INTERFACE PRINCIPALE
# =========================

# عنوان الصفحة
st.markdown(f"""
    <div style='background: linear-gradient(135deg, #2C5282 0%, #1E3A8A 100%); 
                color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);'>
        <h1 style='margin: 0; text-align: center; font-size: 2.2em;'>
            ⚙️ PANEL ADMINISTRATEUR SYSTEME
        </h1>
        <div style='display: flex; justify-content: center; gap: 30px; margin-top: 15px;'>
            <div style='text-align: center;'>
                <div style='font-size: 0.9em; opacity: 0.9;'>Utilisateur</div>
                <div style='font-size: 1.1em; font-weight: bold;'>{st.session_state.get('nom_complet', 'Admin')}</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 0.9em; opacity: 0.9;'>Matricule</div>
                <div style='font-size: 1.1em; font-weight: bold;'>{st.session_state.get('matricule', 'ADMIN-001')}</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 0.9em; opacity: 0.9;'>Heure</div>
                <div style='font-size: 1.1em; font-weight: bold;'>{datetime.now().strftime('%H:%M:%S')}</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# =========================
# SECTION 1: DASHBOARD RAPIDE
# =========================
st.header("📊 Tableau de Bord en Temps Réel")

# KPIs الرئيسية
stats_data = get_statistiques_globales()
if not stats_data.empty:
    cols = st.columns(4)
    
    kpis_to_show = [
        ('👨‍🎓 Étudiants actifs', '#10B981'),
        ('👨‍🏫 Professeurs actifs', '#3B82F6'),
        ('📝 Examens planifiés', '#8B5CF6'),
        ('⚠️ Conflits détectés', '#EF4444')
    ]
    
    for idx, (kpi_name, color) in enumerate(kpis_to_show):
        with cols[idx]:
            kpi_data = stats_data[stats_data['indicateur'] == kpi_name]
            if not kpi_data.empty:
                row = kpi_data.iloc[0]
                st.markdown(f"""
                    <div style='background: white; padding: 15px; border-radius: 10px; 
                                border-left: 5px solid {color}; box-shadow: 0 2px 8px rgba(0,0,0,0.08);'>
                        <div style='font-size: 12px; color: #666; margin-bottom: 5px;'>{kpi_name}</div>
                        <div style='font-size: 26px; font-weight: bold; color: {color};'>{row['valeur']}</div>
                        <div style='font-size: 11px; color: #888; margin-top: 5px;'>
                            {row['pourcentage']}% du total
                        </div>
                    </div>
                """, unsafe_allow_html=True)

# =========================
# SECTION 2: GESTION DES EXAMENS
# =========================
st.header("📝 Gestion des Examens")

# عرض جميع الامتحانات
st.subheader("📋 Liste des Examens")

examens_data = get_all_examens()
if not examens_data.empty:
    # تصفية حسب الحالة
    statut_filter = st.selectbox(
        "Filtrer par statut:",
        ["Tous", "planifie", "confirme", "termine", "annule"]
    )
    
    if statut_filter != "Tous":
        examens_filtres = examens_data[examens_data['statut'] == statut_filter]
    else:
        examens_filtres = examens_data
    
    # عرض جدول الامتحانات
    st.dataframe(
        examens_filtres,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID"),
            "module": st.column_config.TextColumn("Module"),
            "formation": st.column_config.TextColumn("Formation"),
            "departement": st.column_config.TextColumn("Département"),
            "professeur_responsable": st.column_config.TextColumn("Professeur"),
            "salle": st.column_config.TextColumn("Salle"),
            "date_formattee": st.column_config.TextColumn("Date et Heure"),
            "duree_minutes": st.column_config.NumberColumn("Durée (min)"),
            "type_examen": st.column_config.TextColumn("Type"),
            "statut": st.column_config.TextColumn("Statut"),
            "nb_etudiants": st.column_config.NumberColumn("Étudiants")
        },
        hide_index=True
    )
    
    # إحصائيات الامتحانات
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        st.metric("Total Examens", len(examens_data))
    with col_e2:
        planifies = len(examens_data[examens_data['statut'] == 'planifie'])
        st.metric("Planifiés", planifies)
    with col_e3:
        confirmes = len(examens_data[examens_data['statut'] == 'confirme'])
        st.metric("Confirmés", confirmes)
    with col_e4:
        termines = len(examens_data[examens_data['statut'] == 'termine'])
        st.metric("Terminés", termines)
    
    # مخطط دائري لحالات الامتحانات
    fig = px.pie(
        examens_data,
        names='statut',
        title="Distribution des Examens par Statut",
        color='statut',
        color_discrete_map={
            'planifie': '#F59E0B',
            'confirme': '#3B82F6',
            'termine': '#10B981',
            'annule': '#EF4444'
        }
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # تفاصيل المراقبين
    st.subheader("👨‍🏫 Liste des Surveillants")
    surveillants_data = get_surveillants_examens()
    if not surveillants_data.empty:
        st.dataframe(
            surveillants_data,
            use_container_width=True,
            column_config={
                "examen_id": st.column_config.NumberColumn("ID Examen"),
                "module": st.column_config.TextColumn("Module"),
                "surveillant": st.column_config.TextColumn("Surveillant"),
                "role": st.column_config.TextColumn("Rôle"),
                "priorite": st.column_config.NumberColumn("Priorité")
            },
            hide_index=True
        )
    
    # تفاصيل الطلاب
    st.subheader("👨‍🎓 Étudiants par Examen")
    etudiants_data = get_etudiants_par_examen()
    if not etudiants_data.empty:
        st.dataframe(
            etudiants_data,
            use_container_width=True,
            column_config={
                "examen_id": st.column_config.NumberColumn("ID Examen"),
                "module": st.column_config.TextColumn("Module"),
                "etudiant": st.column_config.TextColumn("Étudiant"),
                "matricule": st.column_config.TextColumn("Matricule"),
                "statut_inscription": st.column_config.TextColumn("Statut"),
                "note": st.column_config.NumberColumn("Note", format="%.2f")
            },
            hide_index=True
        )
else:
    st.info("Aucun examen trouvé dans la base de données.")

# =========================
# SECTION 3: OUTILS PRINCIPAUX
# =========================
st.header("⚙️ Outils d'Administration")

col_t1, col_t2, col_t3 = st.columns(3)

with col_t1:
    st.markdown("### 🚀 Génération EDT")
    if st.button("Générer EDT Intelligent", key="gen_edt", use_container_width=True, type="primary"):
        result = generer_edt_intelligent()
        if "✅" in result:
            st.success(result)
        else:
            st.error(result)
        time.sleep(2)
        st.rerun()

with col_t2:
    st.markdown("### ⚡ Optimisation")
    if st.button("Optimiser Ressources", key="opt_ress", use_container_width=True):
        result = optimiser_ressources()
        st.success(result)
        st.rerun()

with col_t3:
    st.markdown("### 📈 Recommandations")
    recommandations = get_planification_recommandations()
    if not recommandations.empty:
        for _, row in recommandations.iterrows():
            st.info(f"**{row['type_recommandation']}**: {row['nombre']} éléments")
    else:
        st.success("✅ Aucune recommandation urgente")

# =========================
# SECTION 4: RAPPORTS ET EXPORT PDF
# =========================
st.header("📄 Rapports et Export")

col_r1, col_r2, col_r3 = st.columns(3)

with col_r1:
    st.markdown("### 📊 Rapports Complets")
    
    report_type = st.selectbox(
        "Type de rapport",
        ["📄 PDF Professionnel", "📝 Texte Simple", "📈 Statistiques CSV"]
    )
    
    if st.button("Générer Rapport", key="btn_rapport", use_container_width=True):
        if report_type == "📄 PDF Professionnel":
            with st.spinner("Création du PDF en cours..."):
                pdf_bytes = generer_pdf_avance()
                if pdf_bytes:
                    st.success("✅ PDF généré avec succès!")
                    
                    # معاينة PDF
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f"""
                    <div style='border: 1px solid #ddd; border-radius: 5px; padding: 10px;'>
                        <iframe 
                            src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0&scrollbar=0" 
                            width="100%" 
                            height="500" 
                            type="application/pdf"
                            style="border: none;">
                        </iframe>
                    </div>
                    """
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    
                    # زر التحميل
                    st.download_button(
                        label="📥 Télécharger PDF",
                        data=pdf_bytes,
                        file_name=f"rapport_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error("❌ Erreur lors de la génération du PDF")
        
        elif report_type == "📝 Texte Simple":
            txt_bytes = generer_rapport_texte()
            st.download_button(
                label="📥 Télécharger TXT",
                data=txt_bytes,
                file_name=f"rapport_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            # عرض محتوى النص
            st.text_area("Aperçu du rapport", txt_bytes.decode('utf-8'), height=200)

with col_r2:
    st.markdown("### 📈 Export des Données")
    
    export_options = st.multiselect(
        "Sélectionnez les données à exporter",
        ["Statistiques", "Salles", "Conflits", "Recommandations", "Examens", "Surveillants", "Étudiants"]
    )
    
    format_choice = st.selectbox("Format", ["CSV", "JSON"])
    
    if st.button("Exporter Données", key="btn_export", use_container_width=True):
        if not export_options:
            st.warning("Veuillez sélectionner au moins un type de données")
        else:
            with st.spinner("Export en cours..."):
                export_data = {}
                
                if "Statistiques" in export_options:
                    stats = get_statistiques_globales()
                    if not stats.empty:
                        export_data["statistiques"] = stats
                
                if "Salles" in export_options:
                    salles = get_occupation_salles_detaille()
                    if not salles.empty:
                        export_data["salles"] = salles
                
                if "Conflits" in export_options:
                    conflits = get_conflits_par_type()
                    if not conflits.empty:
                        export_data["conflits"] = conflits
                
                if "Recommandations" in export_options:
                    recommandations = get_planification_recommandations()
                    if not recommandations.empty:
                        export_data["recommandations"] = recommandations
                
                if "Examens" in export_options:
                    examens = get_all_examens()
                    if not examens.empty:
                        export_data["examens"] = examens
                
                if "Surveillants" in export_options:
                    surveillants = get_surveillants_examens()
                    if not surveillants.empty:
                        export_data["surveillants"] = surveillants
                
                if "Étudiants" in export_options:
                    etudiants = get_etudiants_par_examen()
                    if not etudiants.empty:
                        export_data["etudiants"] = etudiants
                
                if export_data:
                    if format_choice == "CSV":
                        # إنشاء ملف ZIP مع ملفات CSV متعددة
                        zip_buffer = BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                            for name, df in export_data.items():
                                csv_bytes = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                                zip_file.writestr(f"{name}.csv", csv_bytes)
                        
                        zip_bytes = zip_buffer.getvalue()
                        
                        st.download_button(
                            label="📥 Télécharger ZIP (CSV)",
                            data=zip_bytes,
                            file_name=f"export_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                    
                    elif format_choice == "JSON":
                        # تحويل البيانات إلى JSON
                        json_data = {}
                        for name, df in export_data.items():
                            json_data[name] = df.to_dict(orient='records')
                        
                        json_bytes = json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
                        
                        st.download_button(
                            label="📥 Télécharger JSON",
                            data=json_bytes,
                            file_name=f"export_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                else:
                    st.warning("Aucune donnée disponible pour l'export")

with col_r3:
    st.markdown("### 🔧 Maintenance")
    
    maintenance_option = st.selectbox(
        "Tâche de maintenance",
        ["Vérifier Intégrité", "Nettoyer Cache", "Vider Logs Anciens"]
    )
    
    if st.button("Exécuter Maintenance", key="btn_maintenance", use_container_width=True):
        if maintenance_option == "Vérifier Intégrité":
            with st.spinner("Vérification en cours..."):
                try:
                    checks = [
                        ("Étudiants sans formation", 
                         "SELECT COUNT(*) FROM gestion_examens.etudiants WHERE formation_id IS NULL"),
                        ("Examens sans salle", 
                         "SELECT COUNT(*) FROM gestion_examens.examens WHERE salle_id IS NULL"),
                        ("Professeurs sans département", 
                         "SELECT COUNT(*) FROM gestion_examens.professeurs WHERE dept_id IS NULL"),
                        ("Salles sans capacité", 
                         "SELECT COUNT(*) FROM gestion_examens.salles_examen WHERE capacite IS NULL OR capacite <= 0"),
                        ("Modules sans inscription", 
                         "SELECT COUNT(*) FROM gestion_examens.modules m WHERE NOT EXISTS (SELECT 1 FROM gestion_examens.inscriptions i WHERE i.module_id = m.id)")
                    ]
                    
                    results = []
                    errors = 0
                    
                    for check_name, query in checks:
                        result = db.execute_query(query)
                        if result is not None:
                            count = result.iloc[0, 0]
                            if count > 0:
                                results.append(f"❌ {check_name}: {count} erreurs")
                                errors += 1
                            else:
                                results.append(f"✅ {check_name}: OK")
                    
                    st.info("**Résultats de vérification:**")
                    for res in results:
                        st.write(res)
                    
                    if errors == 0:
                        st.success("🎉 Intégrité du système parfaite!")
                    else:
                        st.warning(f"⚠️ {errors} problèmes détectés")
                        
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")
        
        elif maintenance_option == "Nettoyer Cache":
            st.cache_data.clear()
            st.success("✅ Cache nettoyé avec succès!")
            st.rerun()
        
        elif maintenance_option == "Vider Logs Anciens":
            try:
                execute_write("""
                    DELETE FROM gestion_examens.authentification 
                    WHERE derniere_connexion < NOW() - INTERVAL '90 days'
                """)
                st.success("✅ Logs anciens nettoyés!")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")

# =========================
# SECTION 5: ANALYSE AVANCÉE
# =========================
st.header("📈 Analyse Avancée")

tab1, tab2, tab3, tab4 = st.tabs(["🏢 Salles", "⚠️ Conflits", "📊 Activité", "📅 Examens"])

with tab1:
    st.subheader("Analyse d'Occupation des Salles")
    occupation_data = get_occupation_salles_detaille()
    
    if not occupation_data.empty:
        col_o1, col_o2 = st.columns([2, 1])
        
        with col_o1:
            # جدول تفصيلي
            st.dataframe(
                occupation_data,
                use_container_width=True,
                column_config={
                    "type": st.column_config.TextColumn("Type"),
                    "nom": st.column_config.TextColumn("Salle"),
                    "capacite": st.column_config.NumberColumn("Capacité"),
                    "batiment": st.column_config.TextColumn("Bâtiment"),
                    "examens_planifies": st.column_config.NumberColumn("Examens"),
                    "minutes_total": st.column_config.NumberColumn("Minutes"),
                    "taux_utilisation": st.column_config.NumberColumn("Utilisation %", format="%.1f"),
                    "statut": st.column_config.TextColumn("Statut")
                },
                hide_index=True
            )
        
        with col_o2:
            # مخطط دائري
            occupation_summary = occupation_data.groupby('statut').size().reset_index(name='count')
            fig = px.pie(
                occupation_summary,
                values='count',
                names='statut',
                title="Statut des Salles",
                color='statut',
                color_discrete_map={
                    '🟢 Libre': '#10B981',
                    '🟡 Modéré': '#F59E0B',
                    '🔴 Occupé': '#EF4444'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Analyse des Conflits")
    conflits_data = get_conflits_par_type()
    
    if not conflits_data.empty:
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            # مخطط أعمدة
            fig = px.bar(
                conflits_data,
                x='type_conflit',
                y='nombre_conflits',
                color='priorite',
                title="Conflits par Type",
                labels={'type_conflit': 'Type', 'nombre_conflits': 'Nombre'},
                color_continuous_scale='reds'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col_c2:
            # تحليل النزاعات
            st.dataframe(
                conflits_data,
                use_container_width=True,
                column_config={
                    "type_conflit": "Type",
                    "nombre_conflits": "Nombre",
                    "elements_concernees": "Éléments concernés",
                    "categorie": "Catégorie",
                    "priorite": "Priorité"
                },
                hide_index=True
            )

with tab3:
    st.subheader("Activité Récente")
    logs_data = get_logs_activite_recente()
    
    if not logs_data.empty:
        st.dataframe(
            logs_data,
            use_container_width=True,
            column_config={
                "emoji": st.column_config.TextColumn(""),
                "matricule": st.column_config.TextColumn("Matricule"),
                "type_utilisateur": st.column_config.TextColumn("Type"),
                "date_formattee": st.column_config.TextColumn("Dernière Connexion"),
                "fraicheur": st.column_config.TextColumn("État")
            },
            hide_index=True
        )
        
        # رسم بياني للنشاط
        if 'derniere_connexion' in logs_data.columns:
            logs_data['heure'] = pd.to_datetime(logs_data['derniere_connexion']).dt.hour
            activity_by_hour = logs_data.groupby('heure').size().reset_index(name='connexions')
            
            fig = px.line(
                activity_by_hour,
                x='heure',
                y='connexions',
                title="Activité par Heure",
                labels={'heure': 'Heure', 'connexions': 'Connexions'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Analyse des Examens")
    
    if not examens_data.empty:
        # تحليل توزيع الامتحانات حسب التاريخ
        examens_data['date'] = pd.to_datetime(examens_data['date_heure']).dt.date
        examens_par_date = examens_data.groupby('date').size().reset_index(name='nb_examens')
        
        fig = px.line(
            examens_par_date,
            x='date',
            y='nb_examens',
            title="Examens par Date",
            labels={'date': 'Date', 'nb_examens': 'Nombre d\'examens'},
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # تحليل توزيع الامتحانات حسب القسم
        examens_par_departement = examens_data.groupby('departement').size().reset_index(name='nb_examens')
        
        fig2 = px.bar(
            examens_par_departement,
            x='departement',
            y='nb_examens',
            title="Examens par Département",
            color='nb_examens',
            color_continuous_scale='blues'
        )
        st.plotly_chart(fig2, use_container_width=True)

# =========================
# BARRE LATÉRALE
# =========================
with st.sidebar:
    # معلومات المستخدم
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #1E3A8A 0%, #2C5282 100%); 
                    padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;'>
            <div style='text-align: center;'>
                <div style='font-size: 24px; margin-bottom: 10px;'>👑</div>
                <h3 style='margin: 0 0 10px 0;'>Administrateur</h3>
                <p style='margin: 5px 0; font-size: 14px;'><b>{st.session_state.get('matricule', 'ADMIN-001')}</b></p>
                <p style='margin: 0; font-size: 12px; opacity: 0.9;'>{st.session_state.get('nom_complet', 'Système')}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # التنقل السريع
    st.markdown("### 🎯 Navigation")
    
    if st.button("📊 Tableau de bord", use_container_width=True):
        st.session_state.scroll_to = "dashboard"
    
    if st.button("📝 Examens", use_container_width=True):
        st.session_state.scroll_to = "examens"
    
    if st.button("⚙️ Outils admin", use_container_width=True):
        st.session_state.scroll_to = "outils"
    
    if st.button("📄 Rapports", use_container_width=True):
        st.session_state.scroll_to = "rapports"
    
    if st.button("📈 Analyse", use_container_width=True):
        st.session_state.scroll_to = "analyse"
    
    st.markdown("---")
    
    # PDF Express
    st.markdown("### 🚀 PDF Express")
    
    if st.button("📄 Générer PDF Rapide", use_container_width=True):
        with st.spinner("Génération PDF..."):
            pdf_bytes = generer_pdf_avance()
            if pdf_bytes:
                st.download_button(
                    label="📥 Télécharger",
                    data=pdf_bytes,
                    file_name=f"rapport_rapide_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    st.markdown("---")
    
    # إحصاءات سريعة
    st.markdown("### 📊 Statistiques Rapides")
    
    if not stats_data.empty:
        important_stats = {
            "Examens": stats_data[stats_data['indicateur'] == '📝 Examens planifiés']['valeur'].iloc[0] 
                if not stats_data[stats_data['indicateur'] == '📝 Examens planifiés'].empty else "0",
            "Conflits": stats_data[stats_data['indicateur'] == '⚠️ Conflits détectés']['valeur'].iloc[0] 
                if not stats_data[stats_data['indicateur'] == '⚠️ Conflits détectés'].empty else "0",
        }
        
        for key, value in important_stats.items():
            st.metric(key, value)
    
    st.markdown("---")
    
    # إجراءات النظام
    st.markdown("### ⚡ Actions Système")
    
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    if st.button("📱 Vue Mobile", use_container_width=True):
        st.info("Vue mobile activée")
    
    st.markdown("---")
    
    # معلومات الجلسة
    st.markdown("### 📋 Session")
    st.write(f"**Heure:** {datetime.now().strftime('%H:%M:%S')}")
    st.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    
    # زر الخروج
    if st.button("🚪 Déconnexion", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Déconnexion réussie")
        time.sleep(1)
        st.switch_page("app.py")

# =========================
# PIED DE PAGE
# =========================
st.markdown("---")

footer_cols = st.columns(3)

with footer_cols[0]:
    st.markdown(f"""
        <div style='font-size: 12px; color: #666;'>
            <p><b>🎓 Plateforme Examens Universitaires</b></p>
            <p>Version: 3.0 | Environnement: Production</p>
            <p>Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
    """, unsafe_allow_html=True)

with footer_cols[1]:
    # مؤشر الأداء
    try:
        start_time = time.time()
        test_query = "SELECT COUNT(*) FROM gestion_examens.examens WHERE statut = 'planifie'"
        db.execute_query(test_query)
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        if response_time < 100:
            status = "🟢 Excellente"
            color = "#10B981"
        elif response_time < 500:
            status = "🟡 Bonne"
            color = "#F59E0B"
        else:
            status = "🔴 Lente"
            color = "#EF4444"
        
        st.markdown(f"""
            <div style='text-align: center;'>
                <div style='font-size: 11px; color: #666;'>Performance BD</div>
                <div style='font-size: 14px; font-weight: bold; color: {color};'>{status}</div>
                <div style='font-size: 10px; color: #888;'>{response_time} ms</div>
            </div>
        """, unsafe_allow_html=True)
    except:
        pass

with footer_cols[2]:
    st.markdown(f"""
        <div style='text-align: right; font-size: 11px; color: #666;'>
            <p><b>Session Active</b></p>
            <p>Utilisateur: {st.session_state.get('matricule', 'ADMIN-001')}</p>
            <p>Début: {datetime.now().strftime('%H:%M:%S')}</p>
            <p>© 2024 Université - Tous droits réservés</p>
        </div>
    """, unsafe_allow_html=True)

# =========================
# SCRIPT POUR SCROLL
# =========================
if 'scroll_to' in st.session_state:
    target = st.session_state.scroll_to
    del st.session_state.scroll_to
    
    js_code = """
    <script>
        function scrollToTarget() {
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
        setTimeout(scrollToTarget, 100);
    </script>
    """
    
    st.components.v1.html(js_code, height=0)