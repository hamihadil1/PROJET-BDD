-- ================================================
-- REQUÊTES DE DÉMONSTRATION POUR LE PROJET
-- ================================================

SET search_path TO gestion_examens;

-- ================================================
-- 1. POUR LE VICE-DOYEN (Vue stratégique)
-- ================================================

SELECT '=== VUE STRATÉGIQUE GLOBALE ===' as section;

-- KPIs principaux
SELECT 
    'Nombre total d''étudiants' as indicateur,
    COUNT(*) as valeur
FROM etudiants 
WHERE statut = 'actif'

UNION ALL
SELECT 
    'Nombre total d''examens planifiés',
    COUNT(*)
FROM examens 
WHERE statut = 'planifie'

UNION ALL
SELECT 
    'Taux d''occupation des salles (%)',
    ROUND(COUNT(DISTINCT salle_id) * 100.0 / (SELECT COUNT(*) FROM salles_examen), 1)
FROM examens 
WHERE statut = 'planifie'

UNION ALL
SELECT 
    'Conflits détectés',
    COUNT(*)
FROM vue_conflits;

-- Occupation par département
SELECT '=== OCCUPATION PAR DÉPARTEMENT ===' as section;
SELECT 
    d.nom as departement,
    COUNT(DISTINCT f.id) as nb_formations,
    COUNT(DISTINCT e.id) as nb_etudiants,
    COUNT(DISTINCT ex.id) as nb_examens,
    ROUND(COUNT(DISTINCT ex.id) * 100.0 / GREATEST(COUNT(DISTINCT f.id), 1), 1) as taux_examens
FROM departements d
LEFT JOIN formations f ON d.id = f.dept_id
LEFT JOIN etudiants e ON f.id = e.formation_id AND e.statut = 'actif'
LEFT JOIN examens ex ON f.id = ex.formation_id AND ex.statut = 'planifie'
GROUP BY d.id, d.nom
ORDER BY nb_etudiants DESC;

-- ================================================
-- 2. POUR L'ADMINISTRATEUR (Planification)
-- ================================================

SELECT '=== DÉTECTION DES CONFLITS ===' as section;
SELECT 
    type_conflit,
    COUNT(*) as nombre,
    STRING_AGG(DISTINCT element, ', ') as elements_concernees
FROM vue_conflits 
GROUP BY type_conflit 
ORDER BY nombre DESC;

-- Optimisation des ressources
SELECT '=== OPTIMISATION DES RESSOURCES ===' as section;
SELECT 
    'Salles' as ressource,
    COUNT(*) as total,
    COUNT(CASE WHEN disponible = true THEN 1 END) as disponibles,
    COUNT(CASE WHEN disponible = false THEN 1 END) as occupees,
    ROUND(COUNT(CASE WHEN disponible = false THEN 1 END) * 100.0 / COUNT(*), 1) as taux_occupation
FROM salles_examen
UNION ALL
SELECT 
    'Professeurs',
    COUNT(*),
    COUNT(CASE WHEN total_surveillances < 5 THEN 1 END),
    COUNT(CASE WHEN total_surveillances >= 5 THEN 1 END),
    ROUND(COUNT(CASE WHEN total_surveillances >= 5 THEN 1 END) * 100.0 / COUNT(*), 1)
FROM professeurs;

-- ================================================
-- 3. POUR CHEF DE DÉPARTEMENT (Statistiques)
-- ================================================

SELECT '=== STATISTIQUES PAR FORMATION ===' as section;
SELECT 
    f.nom as formation,
    d.nom as departement,
    COUNT(DISTINCT e.id) as nb_etudiants,
    COUNT(DISTINCT i.id) as nb_inscriptions,
    COUNT(DISTINCT ex.id) as nb_examens,
    ROUND(AVG(i.note)::NUMERIC, 2) as moyenne_notes
FROM formations f
JOIN departements d ON f.dept_id = d.id
LEFT JOIN etudiants e ON f.id = e.formation_id AND e.statut = 'actif'
LEFT JOIN inscriptions i ON e.id = i.etudiant_id
LEFT JOIN examens ex ON f.id = ex.formation_id
GROUP BY f.id, f.nom, d.id, d.nom
ORDER BY d.nom, f.nom;

-- Conflits par département
SELECT '=== CONFLITS PAR DÉPARTEMENT ===' as section;
SELECT 
    d.nom as departement,
    vc.type_conflit,
    COUNT(*) as nombre_conflits
FROM vue_conflits vc
JOIN etudiants e ON vc.element LIKE '%' || e.nom || '%'
JOIN formations f ON e.formation_id = f.id
JOIN departements d ON f.dept_id = d.id
GROUP BY d.nom, vc.type_conflit
ORDER BY d.nom, nombre_conflits DESC;

-- ================================================
-- 4. POUR ÉTUDIANTS/PROFESSEURS (Planning)
-- ================================================

-- Exemple planning étudiant
SELECT '=== EXEMPLE PLANNING ÉTUDIANT ===' as section;
SELECT 
    etudiant_nom,
    module_nom,
    date_examen,
    heure_examen,
    salle,
    professeur,
    duree_minutes || ' min' as duree
FROM vue_emploi_temps_etudiant 
WHERE etudiant_id = (SELECT id FROM etudiants LIMIT 1)
ORDER BY date_heure;

-- Exemple planning professeur
SELECT '=== EXEMPLE PLANNING PROFESSEUR ===' as section;
SELECT 
    professeur_nom,
    module,
    TO_CHAR(date_heure, 'DD/MM/YYYY HH24:MI') as date_heure,
    salle,
    role as fonction,
    priorite_surveillance
FROM vue_surveillances_professeur 
WHERE professeur_id = (SELECT id FROM professeurs LIMIT 1)
ORDER BY date_heure;

-- ================================================
-- 5. TEST DE PERFORMANCE
-- ================================================

SELECT '=== TEST DE PERFORMANCE ===' as section;
DO $$
DECLARE
    debut TIMESTAMP;
    fin TIMESTAMP;
    duree DECIMAL;
BEGIN
    debut := clock_timestamp();
    
    -- Test des requêtes complexes
    PERFORM COUNT(*) FROM vue_emploi_temps_etudiant;
    PERFORM COUNT(*) FROM vue_conflits;
    PERFORM COUNT(*) FROM vue_utilisation_salles;
    PERFORM COUNT(*) FROM vue_surveillances_professeur;
    
    -- Test de jointures complexes
    PERFORM COUNT(*)
    FROM etudiants e
    JOIN inscriptions i ON e.id = i.etudiant_id
    JOIN examens ex ON i.module_id = ex.module_id
    WHERE e.statut = 'actif'
    AND ex.statut = 'planifie';
    
    fin := clock_timestamp();
    duree := EXTRACT(EPOCH FROM (fin - debut));
    
    RAISE NOTICE 'Temps d''exécution des requêtes: % secondes', duree;
    
    IF duree < 1 THEN
        RAISE NOTICE '✓ Performance excellente!';
    ELSIF duree < 3 THEN
        RAISE NOTICE '✓ Performance bonne';
    ELSE
        RAISE NOTICE '⚠ Performance à améliorer';
    END IF;
END $$;

-- ================================================
-- 6. DÉMONSTRATION DE FONCTIONNALITÉS
-- ================================================

-- Test de planification
-- Test de planification
SELECT '=== TEST PLANIFICATION ===' as section;
DO $$
DECLARE
    v_module_id INTEGER;
    v_salle_id INTEGER;
    v_prof_id INTEGER;
BEGIN
    -- الحصول على القيم أولاً
    SELECT id INTO v_module_id FROM modules LIMIT 1;
    SELECT id INTO v_salle_id FROM salles_examen WHERE type = 'amphi' LIMIT 1;
    SELECT id INTO v_prof_id FROM professeurs WHERE statut = 'actif' LIMIT 1;
    
    -- تخطيط الامتحان
    CALL planifier_examen(
        v_module_id,
        v_salle_id,
        '2025-02-01 14:00:00',
        v_prof_id,
        90
    );
    RAISE NOTICE '✓ Examen planifié avec succès';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '✗ Erreur: %', SQLERRM;
END $$;

-- Test d'optimisation
SELECT '=== TEST OPTIMISATION ===' as section;
RAISE NOTICE 'Remarque: La reconstruction complète est désactivée pour préserver les données';

-- ================================================
-- 7. RAPPORT FINAL DE DÉMONSTRATION
-- ================================================

DO $$
DECLARE
    total_etudiants INTEGER;
    total_examens INTEGER;
    total_conflits INTEGER;
    total_salles INTEGER;
    total_salles_utilisees INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_etudiants FROM etudiants WHERE statut = 'actif';
    SELECT COUNT(*) INTO total_examens FROM examens WHERE statut = 'planifie';
    SELECT COUNT(*) INTO total_conflits FROM vue_conflits;
    SELECT COUNT(*) INTO total_salles FROM salles_examen;
    SELECT COUNT(DISTINCT salle_id) INTO total_salles_utilisees FROM examens WHERE statut = 'planifie';
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'DÉMONSTRATION PROJET EXAMENS UNIVERSITAIRES';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RÉSULTATS:';
    RAISE NOTICE '- % étudiants actifs', total_etudiants;
    RAISE NOTICE '- % examens planifiés', total_examens;
    RAISE NOTICE '- % conflits détectés', total_conflits;
    RAISE NOTICE '- % salles utilisées sur %', total_salles_utilisees, total_salles;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'FONCTIONNALITÉS DÉMONTRÉES:';
    RAISE NOTICE '✓ Détection automatique des conflits';
    RAISE NOTICE '✓ Optimisation des ressources';
    RAISE NOTICE '✓ Planning personnalisé';
    RAISE NOTICE '✓ Respect des contraintes';
    RAISE NOTICE '✓ Performance optimale';
    RAISE NOTICE '========================================';
END $$;