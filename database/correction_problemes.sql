-- ================================================
-- CORRECTIONS DES PROBLÈMES DÉTECTÉS
-- ================================================

SET search_path TO gestion_examens;
SET client_encoding = 'UTF8';

-- 1. Corriger la vue emploi du temps
DROP VIEW IF EXISTS vue_emploi_temps_etudiant CASCADE;

CREATE OR REPLACE VIEW vue_emploi_temps_etudiant AS
SELECT 
    e.id as etudiant_id,
    e.matricule,
    e.prenom || ' ' || e.nom as etudiant_nom,
    ex.id as examen_id,
    m.nom as module_nom,
    f.nom as formation_nom,
    d.nom as departement_nom,
    pr.prenom || ' ' || pr.nom as professeur,
    s.nom as salle,
    s.type as type_salle,
    ex.date_heure,
    TO_CHAR(ex.date_heure, 'DD/MM/YYYY') as date_examen,
    TO_CHAR(ex.date_heure, 'HH24:MI') as heure_examen,
    ex.duree_minutes
FROM etudiants e
JOIN inscriptions i ON e.id = i.etudiant_id
JOIN modules m ON i.module_id = m.id
JOIN formations f ON m.formation_id = f.id
JOIN departements d ON f.dept_id = d.id
JOIN examens ex ON m.id = ex.module_id
JOIN professeurs pr ON ex.professeur_responsable_id = pr.id
JOIN salles_examen s ON ex.salle_id = s.id
WHERE e.statut = 'actif'
AND i.statut IN ('inscrit', 'en_cours', 'valide')
AND ex.statut IN ('planifie', 'confirme')
AND ex.date_heure IS NOT NULL
ORDER BY e.id, ex.date_heure;

-- 2. Vérifier et corriger les examens
UPDATE examens 
SET statut = 'planifie' 
WHERE statut IS NULL;

-- 3. Créer une vue simplifiée pour tests
CREATE OR REPLACE VIEW vue_emploi_simple AS
SELECT 
    e.matricule,
    e.prenom || ' ' || e.nom as etudiant,
    m.nom as module,
    TO_CHAR(ex.date_heure, 'DD/MM/YYYY HH24:MI') as date_heure,
    s.nom as salle,
    pr.prenom || ' ' || pr.nom as professeur
FROM etudiants e
JOIN inscriptions i ON e.id = i.etudiant_id
JOIN modules m ON i.module_id = m.id
JOIN examens ex ON m.id = ex.module_id
JOIN professeurs pr ON ex.professeur_responsable_id = pr.id
JOIN salles_examen s ON ex.salle_id = s.id
WHERE ex.statut = 'planifie'
ORDER BY ex.date_heure
LIMIT 50;

-- 4. Tester les vues corrigées
SELECT 'Test vue corrigée:' as test;
SELECT COUNT(*) as nb_lignes FROM vue_emploi_temps_etudiant;

SELECT 'Aperçu emploi du temps:' as test;
SELECT etudiant_nom, module_nom, date_examen, heure_examen, salle 
FROM vue_emploi_temps_etudiant 
LIMIT 10;

-- 5. Vérifier les surveillances
SELECT 'Surveillances attribuées:' as test;
SELECT COUNT(*) as total_surveillances FROM surveillances;

-- 6. Message de succès
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'CORRECTIONS APPLIQUÉES AVEC SUCCÈS!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Vues corrigées et prêtes pour la démonstration.';
    RAISE NOTICE 'Utilisez: SELECT * FROM vue_emploi_temps_etudiant LIMIT 10;';
    RAISE NOTICE '========================================';
END $$;

DO $$
DECLARE
    exam_rec RECORD;
    prof_rec RECORD;
    prof_count INTEGER;
    i INTEGER;
    total_added INTEGER := 0;
BEGIN
    -- لكل امتحان بدون مراقبين
    FOR exam_rec IN 
        SELECT e.*, f.dept_id 
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE e.statut = 'planifie'
        AND NOT EXISTS (SELECT 1 FROM surveillances s WHERE s.examen_id = e.id)
    LOOP
        -- إعادة تعيين العد
        prof_count := 0;
        
        -- إيجاد مراقبين من نفس القسم
        FOR prof_rec IN (
            SELECT p.id 
            FROM professeurs p
            WHERE p.dept_id = exam_rec.dept_id
            AND p.id != exam_rec.professeur_responsable_id
            AND p.statut = 'actif'
            ORDER BY p.total_surveillances ASC
            LIMIT 2
        ) LOOP
            INSERT INTO surveillances (examen_id, professeur_id, priorite, role)
            VALUES (exam_rec.id, prof_rec.id, 1, 'surveillant');
            
            UPDATE professeurs 
            SET total_surveillances = total_surveillances + 1
            WHERE id = prof_rec.id;
            
            prof_count := prof_count + 1;
            total_added := total_added + 1;
        END LOOP;
        
        -- إذا لم نجد مراقبين كافيين، ابحث في أقسام أخرى
        IF prof_count < 2 THEN
            FOR i IN 1..(2 - prof_count) LOOP
                SELECT p.id INTO prof_rec
                FROM professeurs p
                WHERE p.dept_id != exam_rec.dept_id
                AND p.statut = 'actif'
                AND p.id != exam_rec.professeur_responsable_id
                AND NOT EXISTS (
                    SELECT 1 FROM surveillances s 
                    WHERE s.examen_id = exam_rec.id AND s.professeur_id = p.id
                )
                ORDER BY p.total_surveillances ASC
                LIMIT 1;
                
                IF prof_rec.id IS NOT NULL THEN
                    INSERT INTO surveillances (examen_id, professeur_id, priorite, role)
                    VALUES (exam_rec.id, prof_rec.id, 2, 'surveillant');
                    
                    UPDATE professeurs 
                    SET total_surveillances = total_surveillances + 1
                    WHERE id = prof_rec.id;
                    
                    total_added := total_added + 1;
                END IF;
            END LOOP;
        END IF;
    END LOOP;
    
    RAISE NOTICE '% de moniteurs manuels ajoutés', total_added;
END $$;






-- Connectez-vous et exécutez ces commandes :

-- Ajouter des surveillants manuellement
SELECT '=== AJOUT DE SURVEILLANTS ===' as etape;

DO $$
DECLARE
    exam_rec RECORD;
    prof_rec RECORD;
    total_added INTEGER := 0;
    i INTEGER;
    j INTEGER;
BEGIN
    FOR exam_rec IN 
        SELECT e.*, f.dept_id 
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE e.statut = 'planifie'
        AND NOT EXISTS (SELECT 1 FROM surveillances s WHERE s.examen_id = e.id)
    LOOP
        i := 0;
        
        FOR prof_rec IN (
            SELECT p.id 
            FROM professeurs p
            WHERE p.dept_id = exam_rec.dept_id
            AND p.id != exam_rec.professeur_responsable_id
            AND p.statut = 'actif'
            ORDER BY p.total_surveillances ASC
            LIMIT 2
        ) LOOP
            INSERT INTO surveillances (examen_id, professeur_id, priorite, role, heures_creditees)
            VALUES (exam_rec.id, prof_rec.id, 1, 'surveillant', 1.5);
            
            UPDATE professeurs 
            SET total_surveillances = total_surveillances + 1
            WHERE id = prof_rec.id;
            
            i := i + 1;
            total_added := total_added + 1;
        END LOOP;
        
        IF i < 2 THEN
            FOR j IN 1..(2 - i) LOOP
                SELECT p.id INTO prof_rec
                FROM professeurs p
                WHERE p.dept_id != exam_rec.dept_id
                AND p.statut = 'actif'
                AND p.id != exam_rec.professeur_responsable_id
                AND NOT EXISTS (
                    SELECT 1 FROM surveillances s 
                    WHERE s.examen_id = exam_rec.id AND s.professeur_id = p.id
                )
                ORDER BY p.total_surveillances ASC
                LIMIT 1;
                
                IF prof_rec.id IS NOT NULL THEN
                    INSERT INTO surveillances (examen_id, professeur_id, priorite, role, heures_creditees)
                    VALUES (exam_rec.id, prof_rec.id, 2, 'surveillant', 1.5);
                    
                    UPDATE professeurs 
                    SET total_surveillances = total_surveillances + 1
                    WHERE id = prof_rec.id;
                    
                    total_added := total_added + 1;
                END IF;
            END LOOP;
        END IF;
    END LOOP;
    
    RAISE NOTICE '✅ % surveillants ajoutés manuellement', total_added;
END $$;