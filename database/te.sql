-- ================================================
-- SOLUTION FINALE - CORRECTION DES SURVEILLANCES
-- ================================================

SET search_path TO gestion_examens;
SET client_encoding = 'UTF8';

-- 1. SUPPRIMER ET RECRÉER LES SURVEILLANCES AVEC UN ALGORITHME SIMPLE
DELETE FROM surveillances;
UPDATE professeurs SET total_surveillances = 0;

-- 2. CRÉER UNE PROCÉDURE SIMPLIFIÉE
CREATE OR REPLACE PROCEDURE attribuer_surveillances_simples()
LANGUAGE plpgsql
AS $$
DECLARE
    exam_rec RECORD;
    prof_rec RECORD;
    prof_counter INTEGER;
    surveillants_ajoutes INTEGER := 0;
    examens_traites INTEGER := 0;
BEGIN
    RAISE NOTICE '=== DÉBUT ATTRIBUTION SIMPLIFIÉE ===';
    
    -- Pour chaque examen
    FOR exam_rec IN (
        SELECT 
            e.id as examen_id,
            e.professeur_responsable_id,
            f.dept_id,
            DATE(e.date_heure) as date_examen
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE e.statut = 'planifie'
        ORDER BY e.date_heure
    ) LOOP
    
        examens_traites := examens_traites + 1;
        prof_counter := 0;
        
        RAISE NOTICE 'Examen %: Département %', 
            exam_rec.examen_id, exam_rec.dept_id;
        
        -- Étape 1: Trouver 2 professeurs du même département
        FOR prof_rec IN (
            SELECT p.id, p.matricule, p.prenom, p.nom
            FROM professeurs p
            WHERE p.dept_id = exam_rec.dept_id
            AND p.statut = 'actif'
            AND p.id != exam_rec.professeur_responsable_id
            AND NOT EXISTS (
                SELECT 1 FROM surveillances s
                WHERE s.professeur_id = p.id
                AND s.examen_id = exam_rec.examen_id
            )
            ORDER BY p.total_surveillances ASC
            LIMIT 2
        ) LOOP
            
            INSERT INTO surveillances (
                examen_id,
                professeur_id,
                priorite,
                role,
                heures_creditees
            ) VALUES (
                exam_rec.examen_id,
                prof_rec.id,
                1,
                'surveillant',
                1.5
            );
            
            prof_counter := prof_counter + 1;
            surveillants_ajoutes := surveillants_ajoutes + 1;
            
            RAISE NOTICE '  + % %', prof_rec.prenom, prof_rec.nom;
        END LOOP;
        
        -- Étape 2: Si besoin, compléter avec d'autres départements
        IF prof_counter < 2 THEN
            FOR i IN 1..(2 - prof_counter) LOOP
                SELECT p.id, p.matricule, p.prenom, p.nom INTO prof_rec
                FROM professeurs p
                WHERE p.dept_id != exam_rec.dept_id
                AND p.statut = 'actif'
                AND p.id != exam_rec.professeur_responsable_id
                AND NOT EXISTS (
                    SELECT 1 FROM surveillances s
                    WHERE s.professeur_id = p.id
                    AND s.examen_id = exam_rec.examen_id
                )
                ORDER BY p.total_surveillances ASC
                LIMIT 1;
                
                IF prof_rec.id IS NOT NULL THEN
                    INSERT INTO surveillances (
                        examen_id,
                        professeur_id,
                        priorite,
                        role,
                        heures_creditees
                    ) VALUES (
                        exam_rec.examen_id,
                        prof_rec.id,
                        2,
                        'surveillant',
                        1.5
                    );
                    
                    surveillants_ajoutes := surveillants_ajoutes + 1;
                    RAISE NOTICE '  + % % (autre département)', 
                        prof_rec.prenom, prof_rec.nom;
                END IF;
            END LOOP;
        END IF;
        
    END LOOP;
    
    RAISE NOTICE '=== FIN ATTRIBUTION ===';
    RAISE NOTICE 'Examens traités: %', examens_traites;
    RAISE NOTICE 'Surveillants ajoutés: %', surveillants_ajoutes;
    
    -- Mettre à jour les compteurs
    UPDATE professeurs p
    SET total_surveillances = (
        SELECT COUNT(*) 
        FROM surveillances s 
        WHERE s.professeur_id = p.id
    );
    
END;
$$;

-- 3. EXÉCUTER LA PROCÉDURE
CALL attribuer_surveillances_simples();

-- 4. VÉRIFICATION DES RÉSULTATS
SELECT '=== VÉRIFICATION DES SURVEILLANCES ===' as etape;

-- 4.1 Statistiques générales
SELECT 
    'Examens planifiés:' as indicateur,
    COUNT(*) as valeur
FROM examens 
WHERE statut = 'planifie'
UNION ALL
SELECT 
    'Examens avec surveillance:',
    COUNT(DISTINCT s.examen_id)
FROM surveillances s
JOIN examens e ON s.examen_id = e.id
WHERE e.statut = 'planifie'
UNION ALL
SELECT 
    'Total surveillances:',
    COUNT(*)
FROM surveillances
UNION ALL
SELECT 
    'Professeurs avec surveillance:',
    COUNT(DISTINCT professeur_id)
FROM surveillances
UNION ALL
SELECT 
    'Surveillances moyennes par prof:',
    ROUND(AVG(total_surveillances), 2)
FROM professeurs 
WHERE statut = 'actif';

-- 4.2 Détail pour chaque professeur
SELECT '=== RÉPARTITION PAR PROFESSEUR ===' as etape;

SELECT 
    p.matricule,
    p.prenom || ' ' || p.nom as professeur,
    d.nom as departement,
    p.total_surveillances,
    CASE 
        WHEN p.total_surveillances = 0 THEN '❌ Aucune'
        WHEN p.total_surveillances <= 2 THEN '✅ Correct'
        WHEN p.total_surveillances <= 4 THEN '⚠️ Élevé'
        ELSE '🚨 Très élevé'
    END as statut
FROM professeurs p
JOIN departements d ON p.dept_id = d.id
WHERE p.statut = 'actif'
ORDER BY p.total_surveillances DESC, p.nom;

-- 5. VÉRIFICATION SPÉCIFIQUE POUR PROF-INF-011
SELECT '=== SURVEILLANCES DE PROF-INF-011 ===' as etape;

-- 5.1 Statistiques du professeur
SELECT 
    p.matricule,
    p.prenom || ' ' || p.nom as professeur,
    p.total_surveillances,
    d.nom as departement,
    COALESCE(SUM(s.heures_creditees), 0) as total_heures
FROM professeurs p
JOIN departements d ON p.dept_id = d.id
LEFT JOIN surveillances s ON p.id = s.professeur_id
WHERE p.matricule = 'PROF-INF-011'
GROUP BY p.id, p.matricule, p.prenom, p.nom, d.nom, p.total_surveillances;

-- 5.2 Détail des surveillances (méthode directe)
SELECT '=== DÉTAIL DES SURVEILLANCES ===' as etape;

SELECT 
    p.matricule,
    p.prenom || ' ' || p.nom as professeur,
    m.nom as module,
    TO_CHAR(e.date_heure, 'DD/MM/YYYY') as date_examen,
    TO_CHAR(e.date_heure, 'HH24:MI') as heure_examen,
    s.role,
    s.priorite,
    s.heures_creditees,
    sa.nom as salle,
    pr.prenom || ' ' || pr.nom as professeur_responsable,
    e.statut
FROM surveillances s
JOIN professeurs p ON s.professeur_id = p.id
JOIN examens e ON s.examen_id = e.id
JOIN modules m ON e.module_id = m.id
JOIN salles_examen sa ON e.salle_id = sa.id
JOIN professeurs pr ON e.professeur_responsable_id = pr.id
WHERE p.matricule = 'PROF-INF-011'
AND e.statut IN ('planifie', 'confirme')
ORDER BY e.date_heure;

-- 6. CRÉER UNE VUE SIMPLIFIÉE POUR L'APPLICATION
CREATE OR REPLACE VIEW vue_surveillances_simple AS
SELECT 
    s.id as surveillance_id,
    p.id as professeur_id,
    p.matricule as matricule_prof,
    p.prenom || ' ' || p.nom as nom_professeur,
    e.id as examen_id,
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
    e.statut as statut_examen
FROM surveillances s
JOIN professeurs p ON s.professeur_id = p.id
JOIN examens e ON s.examen_id = e.id
JOIN modules m ON e.module_id = m.id
JOIN formations f ON m.formation_id = f.id
JOIN salles_examen sa ON e.salle_id = sa.id
JOIN professeurs pr ON e.professeur_responsable_id = pr.id
WHERE e.statut IN ('planifie', 'confirme')
ORDER BY e.date_heure, p.nom;

SELECT '=== VUE SIMPLIFIÉE CRÉÉE ===' as etape;
SELECT COUNT(*) as nb_lignes FROM vue_surveillances_simple;

-- 7. TESTER LA VUE POUR PROF-INF-011
SELECT '=== TEST AVEC LA VUE ===' as etape;

SELECT 
    matricule_prof,
    nom_professeur,
    date_examen,
    heure_examen,
    module,
    formation,
    role,
    heures_creditees,
    salle,
    professeur_responsable
FROM vue_surveillances_simple
WHERE matricule_prof = 'PROF-INF-011'
ORDER BY 
    TO_DATE(date_examen, 'DD/MM/YYYY'),
    heure_examen;

-- 8. AJOUTER DES SURVEILLANCES MANQUELLES SI NÉCESSAIRE
DO $$
DECLARE
    prof_sans_surveillance RECORD;
    examen_disponible INTEGER;
    corrections_appliquees INTEGER := 0;
BEGIN
    
    -- Identifier les professeurs sans surveillance
    FOR prof_sans_surveillance IN (
        SELECT p.id, p.matricule, p.prenom, p.nom, p.dept_id
        FROM professeurs p
        WHERE p.statut = 'actif'
        AND p.total_surveillances = 0
        ORDER BY p.dept_id
    ) LOOP
        
        RAISE NOTICE 'Professeur sans surveillance: % %', 
            prof_sans_surveillance.prenom, prof_sans_surveillance.nom;
        
        -- Trouver un examen du même département
        SELECT e.id INTO examen_disponible
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE e.statut = 'planifie'
        AND f.dept_id = prof_sans_surveillance.dept_id
        AND e.professeur_responsable_id != prof_sans_surveillance.id
        AND EXISTS (
            SELECT 1 FROM surveillances s
            WHERE s.examen_id = e.id
            HAVING COUNT(*) < 2
        )
        LIMIT 1;
        
        IF examen_disponible IS NOT NULL THEN
            INSERT INTO surveillances (
                examen_id,
                professeur_id,
                priorite,
                role,
                heures_creditees
            ) VALUES (
                examen_disponible,
                prof_sans_surveillance.id,
                1,
                'surveillant',
                1.5
            ) ON CONFLICT DO NOTHING;
            
            corrections_appliquees := corrections_appliquees + 1;
            RAISE NOTICE '  ✓ Ajouté surveillance pour examen %', examen_disponible;
        END IF;
        
    END LOOP;
    
    IF corrections_appliquees > 0 THEN
        -- Mettre à jour les compteurs
        UPDATE professeurs p
        SET total_surveillances = (
            SELECT COUNT(*) 
            FROM surveillances s 
            WHERE s.professeur_id = p.id
        );
        
        RAISE NOTICE '✅ % corrections appliquées', corrections_appliquees;
    ELSE
        RAISE NOTICE 'ℹ️ Aucune correction nécessaire';
    END IF;
    
END $$;

-- 9. RÉSULTATS FINAUX
SELECT '=== RÉSULTATS FINAUX ===' as etape;

SELECT 
    'Professeurs actifs:' as type,
    COUNT(*) as valeur
FROM professeurs 
WHERE statut = 'actif'
UNION ALL
SELECT 
    'Professeurs avec surveillance:',
    COUNT(*)
FROM professeurs 
WHERE statut = 'actif' AND total_surveillances > 0
UNION ALL
SELECT 
    'Professeurs sans surveillance:',
    COUNT(*)
FROM professeurs 
WHERE statut = 'actif' AND total_surveillances = 0
UNION ALL
SELECT 
    'Total surveillances:',
    COUNT(*)
FROM surveillances
UNION ALL
SELECT 
    'Examens couverts:',
    COUNT(DISTINCT examen_id)
FROM surveillances;

-- 10. SUPPRIMER LA PROCÉDURE TEMPORAIRE
DROP PROCEDURE IF EXISTS attribuer_surveillances_simples();

SELECT '=== CORRECTIONS TERMINÉES ===' as etape;