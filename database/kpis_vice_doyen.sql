-- ================================================
-- 1. KPIs ACADÉMIQUES COMPLETS POUR VICE-DOYEN
-- ================================================

-- KPI 1: Occupation globale des amphis et salles
SELECT 
    'Salles totales' as indicateur,
    COUNT(*) as valeur
FROM gestion_examens.salles_examen

UNION ALL
SELECT 
    'Salles utilisées',
    COUNT(DISTINCT e.salle_id)
FROM gestion_examens.examens e
WHERE e.statut = 'planifie'

UNION ALL
SELECT 
    'Taux occupation salles (%)',
    ROUND(
        COUNT(DISTINCT e.salle_id) * 100.0 / 
        (SELECT COUNT(*) FROM gestion_examens.salles_examen),
    2)
FROM gestion_examens.examens e
WHERE e.statut = 'planifie'

UNION ALL
SELECT 
    'Amphithéâtres utilisés',
    COUNT(DISTINCT CASE WHEN s.type = 'amphi' THEN e.salle_id END)
FROM gestion_examens.examens e
JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
WHERE e.statut = 'planifie'

UNION ALL
SELECT 
    'Taux occupation amphis (%)',
    ROUND(
        COUNT(DISTINCT CASE WHEN s.type = 'amphi' THEN e.salle_id END) * 100.0 /
        (SELECT COUNT(*) FROM gestion_examens.salles_examen WHERE type = 'amphi'),
    2)
FROM gestion_examens.examens e
JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
WHERE e.statut = 'planifie';

-- ================================================
-- 2. TAUX CONFLITS PAR DÉPARTEMENT
-- ================================================

SELECT 
    d.nom as departement,
    COUNT(DISTINCT vc.element) as nb_conflits,
    ROUND(
        COUNT(DISTINCT vc.element) * 100.0 / 
        GREATEST(
            (SELECT COUNT(DISTINCT element) FROM gestion_examens.vue_conflits),
            1
        ),
    2) as taux_conflits_departement
FROM gestion_examens.departements d
LEFT JOIN gestion_examens.formations f ON d.id = f.dept_id
LEFT JOIN gestion_examens.etudiants e ON f.id = e.formation_id
LEFT JOIN gestion_examens.vue_conflits vc ON vc.element LIKE '%' || e.nom || '%'
GROUP BY d.id, d.nom
ORDER BY nb_conflits DESC;

-- ================================================
-- 3. HEURES PROFESSEURS (Charge de travail)
-- ================================================

-- Heures totales des professeurs (responsables + surveillants)
SELECT 
    p.nom_complet,
    p.departement,
    p.heures_responsable,
    p.heures_surveillant,
    (p.heures_responsable + p.heures_surveillant) as heures_totales
FROM (
    -- Professeurs responsables d'examens
    SELECT 
        pr.prenom || ' ' || pr.nom as nom_complet,
        d.nom as departement,
        COALESCE(SUM(ex.duree_minutes) / 60.0, 0) as heures_responsable,
        0 as heures_surveillant
    FROM gestion_examens.professeurs pr
    JOIN gestion_examens.departements d ON pr.dept_id = d.id
    LEFT JOIN gestion_examens.examens ex ON pr.id = ex.professeur_responsable_id
        AND ex.statut = 'planifie'
    WHERE pr.statut = 'actif'
    GROUP BY pr.id, pr.prenom, pr.nom, d.nom
    
    UNION ALL
    
    -- Professeurs surveillants
    SELECT 
        pr.prenom || ' ' || pr.nom as nom_complet,
        d.nom as departement,
        0 as heures_responsable,
        COALESCE(SUM(ex.duree_minutes) / 60.0, 0) as heures_surveillant
    FROM gestion_examens.professeurs pr
    JOIN gestion_examens.departements d ON pr.dept_id = d.id
    JOIN gestion_examens.surveillances s ON pr.id = s.professeur_id
    JOIN gestion_examens.examens ex ON s.examen_id = ex.id
        AND ex.statut = 'planifie'
    WHERE pr.statut = 'actif'
    GROUP BY pr.id, pr.prenom, pr.nom, d.nom
) p
ORDER BY heures_totales DESC;

-- ================================================
-- 4. VALIDATION FINALE EDT (Emploi du Temps)
-- ================================================

-- Vue complète pour validation finale
SELECT 
    -- Date et heure
    TO_CHAR(e.date_heure, 'DD/MM/YYYY') as date_examen,
    TO_CHAR(e.date_heure, 'HH24:MI') as heure_examen,
    
    -- Informations salle
    s.nom as salle,
    s.type as type_salle,
    s.capacite,
    
    -- Informations module et formation
    m.nom as module,
    f.nom as formation,
    d.nom as departement,
    
    -- Professeur responsable
    pr.prenom || ' ' || pr.nom as professeur_responsable,
    
    -- Nombre d'étudiants
    (SELECT COUNT(DISTINCT i.etudiant_id)
     FROM gestion_examens.inscriptions i
     WHERE i.module_id = e.module_id
     AND i.statut IN ('inscrit', 'en_cours')) as nb_etudiants,
    
    -- Surveillants
    (SELECT STRING_AGG(p2.prenom || ' ' || p2.nom, ', ')
     FROM gestion_examens.surveillances s2
     JOIN gestion_examens.professeurs p2 ON s2.professeur_id = p2.id
     WHERE s2.examen_id = e.id) as surveillants,
    
    -- Statut
    e.statut
    
FROM gestion_examens.examens e
JOIN gestion_examens.salles_examen s ON e.salle_id = s.id
JOIN gestion_examens.modules m ON e.module_id = m.id
JOIN gestion_examens.formations f ON e.formation_id = f.id
JOIN gestion_examens.departements d ON f.dept_id = d.id
JOIN gestion_examens.professeurs pr ON e.professeur_responsable_id = pr.id
WHERE e.statut IN ('planifie', 'confirme')
ORDER BY e.date_heure, s.nom;

-- ================================================
-- 5. ANALYSE DÉTAILLÉE DES CONFLITS
-- ================================================

-- Conflits par type et département
SELECT 
    vc.type_conflit,
    d.nom as departement,
    COUNT(*) as nombre_conflits,
    STRING_AGG(DISTINCT vc.element, ' | ') as elements_concernees
FROM gestion_examens.vue_conflits vc
LEFT JOIN (
    -- Relier les conflits aux départements
    SELECT DISTINCT e.id as etudiant_id, d.nom
    FROM gestion_examens.etudiants e
    JOIN gestion_examens.formations f ON e.formation_id = f.id
    JOIN gestion_examens.departements d ON f.dept_id = d.id
    
    UNION ALL
    
    SELECT DISTINCT p.id as professeur_id, d.nom
    FROM gestion_examens.professeurs p
    JOIN gestion_examens.departements d ON p.dept_id = d.id
) dept_info ON vc.element LIKE '%' || (
    CASE 
        WHEN vc.type_conflit LIKE '%étudiant%' THEN (SELECT nom FROM gestion_examens.etudiants WHERE id = dept_info.etudiant_id)
        WHEN vc.type_conflit LIKE '%professeur%' THEN (SELECT nom FROM gestion_examens.professeurs WHERE id = dept_info.professeur_id)
        ELSE vc.element
    END
) || '%'
GROUP BY vc.type_conflit, d.nom
ORDER BY nombre_conflits DESC;

-- ================================================
-- 6. TABLEAU DE BORD GLOBAL (Tous les KPIs)
-- ================================================

-- Vue globale pour tableau de bord
WITH stats_globales AS (
    SELECT 
        -- Étudiants
        (SELECT COUNT(*) FROM gestion_examens.etudiants WHERE statut = 'actif') as total_etudiants,
        
        -- Professeurs
        (SELECT COUNT(*) FROM gestion_examens.professeurs WHERE statut = 'actif') as total_professeurs,
        
        -- Examens
        (SELECT COUNT(*) FROM gestion_examens.examens WHERE statut = 'planifie') as examens_planifies,
        (SELECT COUNT(*) FROM gestion_examens.examens WHERE statut = 'confirme') as examens_confirmees,
        
        -- Salles
        (SELECT COUNT(*) FROM gestion_examens.salles_examen) as total_salles,
        (SELECT COUNT(DISTINCT salle_id) FROM gestion_examens.examens WHERE statut = 'planifie') as salles_utilisees,
        
        -- Conflits
        (SELECT COUNT(*) FROM gestion_examens.vue_conflits) as total_conflits,
        
        -- Heures
        (SELECT COALESCE(SUM(duree_minutes) / 60.0, 0) FROM gestion_examens.examens WHERE statut = 'planifie') as heures_examens_total
)
SELECT 
    '👨‍🎓 Étudiants actifs' as kpi,
    total_etudiants::text as valeur
FROM stats_globales

UNION ALL
SELECT 
    '👨‍🏫 Professeurs actifs',
    total_professeurs::text

UNION ALL
SELECT 
    '📝 Examens planifiés',
    examens_planifies::text

UNION ALL
SELECT 
    '✅ Examens confirmés',
    examens_confirmees::text

UNION ALL
SELECT 
    '🏢 Salles utilisées',
    salles_utilisees::text || ' / ' || total_salles::text

UNION ALL
SELECT 
    '📊 Taux occupation salles (%)',
    ROUND(salles_utilisees * 100.0 / total_salles, 2)::text || ' %'

UNION ALL
SELECT 
    '⚠️ Conflits détectés',
    total_conflits::text

UNION ALL
SELECT 
    '⏰ Heures examens totales',
    ROUND(heures_examens_total, 1)::text || ' h'

UNION ALL
SELECT 
    '📈 Taux validation EDT (%)',
    ROUND(examens_confirmees * 100.0 / GREATEST(examens_planifies + examens_confirmees, 1), 2)::text || ' %';

-- ================================================
-- 7. RAPPORT PAR DÉPARTEMENT (Détail)
-- ================================================

SELECT 
    d.nom as departement,
    
    -- Statistiques étudiants
    COUNT(DISTINCT e.id) as nb_etudiants,
    
    -- Statistiques examens
    COUNT(DISTINCT ex.id) as nb_examens,
    ROUND(
        COUNT(DISTINCT ex.id) * 100.0 / 
        GREATEST(COUNT(DISTINCT f.id), 1),
    2) as taux_examens_par_formation,
    
    -- Utilisation salles
    COUNT(DISTINCT CASE WHEN ex.statut = 'planifie' THEN s.id END) as salles_utilisees,
    (SELECT COUNT(*) FROM gestion_examens.salles_examen) as total_salles_departement,
    
    -- Heures professeurs
    COALESCE(SUM(ex.duree_minutes) / 60.0, 0) as heures_examens_total,
    
    -- Conflits
    COUNT(DISTINCT vc.element) as nb_conflits,
    
    -- Taux occupation
    ROUND(
        COUNT(DISTINCT CASE WHEN ex.statut = 'planifie' THEN s.id END) * 100.0 /
        GREATEST(
            (SELECT COUNT(*) FROM gestion_examens.salles_examen),
            1
        ),
    2) as taux_occupation_salles
    
FROM gestion_examens.departements d
LEFT JOIN gestion_examens.formations f ON d.id = f.dept_id
LEFT JOIN gestion_examens.etudiants e ON f.id = e.formation_id AND e.statut = 'actif'
LEFT JOIN gestion_examens.examens ex ON f.id = ex.formation_id
LEFT JOIN gestion_examens.salles_examen s ON ex.salle_id = s.id
LEFT JOIN gestion_examens.vue_conflits vc ON (
    vc.element LIKE '%' || e.nom || '%' OR
    vc.element LIKE '%' || (SELECT nom FROM gestion_examens.professeurs WHERE dept_id = d.id LIMIT 1) || '%'
)
GROUP BY d.id, d.nom
ORDER BY nb_etudiants DESC;

-- ================================================
-- 8. VUE SYNTHÈSE POUR VALIDATION FINALE
-- ================================================

-- Vue qui résume tout pour la validation finale
SELECT 
    'SYNTHÈSE VALIDATION' as section,
    
    -- Occupation
    (SELECT COUNT(DISTINCT salle_id) FROM gestion_examens.examens WHERE statut = 'planifie') || '/' ||
    (SELECT COUNT(*) FROM gestion_examens.salles_examen) as occupation_salles,
    
    -- Conflits
    (SELECT COUNT(*) FROM gestion_examens.vue_conflits) as conflits_detectes,
    
    -- Équilibre
    ROUND(
        (SELECT COUNT(*) FROM gestion_examens.examens WHERE statut = 'planifie') * 100.0 /
        GREATEST((SELECT COUNT(*) FROM gestion_examens.modules), 1),
    2) || ' %' as taux_examens_planifies,
    
    -- Professeurs
    (SELECT ROUND(AVG(total_surveillances), 2) FROM gestion_examens.professeurs WHERE statut = 'actif') as moyenne_surveillances_par_prof,
    
    -- Recommandation
    CASE 
        WHEN (SELECT COUNT(*) FROM gestion_examens.vue_conflits) = 0 THEN '✅ VALIDATION RECOMMANDÉE'
        WHEN (SELECT COUNT(*) FROM gestion_examens.vue_conflits) < 5 THEN '⚠️ VALIDATION AVEC RÉSERVES'
        ELSE '❌ REVOIR LA PLANIFICATION'
    END as recommandation_validation;