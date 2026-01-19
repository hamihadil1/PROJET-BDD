-- ================================================
-- CORRECTIONS FINALES POUR LA DÉMONSTRATION
-- ================================================

SET search_path TO gestion_examens;
SET client_encoding = ''UTF8'';

-- 1. Ajouter des surveillants manuellement (car le trigger ne fonctionne pas)
SELECT ''=== AJOUT DE SURVEILLANTS ==='' as etape;

DO $$
DECLARE
    exam_rec RECORD;
    prof_rec RECORD;
    total_added INTEGER := 0;
    i INTEGER;
BEGIN
    -- Pour chaque examen sans surveillants
    FOR exam_rec IN 
        SELECT e.*, f.dept_id 
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE e.statut = ''planifie''
        AND NOT EXISTS (SELECT 1 FROM surveillances s WHERE s.examen_id = e.id)
    LOOP
        -- Reset counter pour cet examen
        i := 0;
        
        -- Chercher 2 surveillants du même département
        FOR prof_rec IN (
            SELECT p.id 
            FROM professeurs p
            WHERE p.dept_id = exam_rec.dept_id
            AND p.id != exam_rec.professeur_responsable_id
            AND p.statut = ''actif''
            ORDER BY p.total_surveillances ASC
            LIMIT 2
        ) LOOP
            INSERT INTO surveillances (examen_id, professeur_id, priorite, role, heures_creditees)
            VALUES (exam_rec.id, prof_rec.id, 1, ''surveillant'', 1.5);
            
            UPDATE professeurs 
            SET total_surveillances = total_surveillances + 1
            WHERE id = prof_rec.id;
            
            i := i + 1;
            total_added := total_added + 1;
        END LOOP;
        
        -- Si pas assez, chercher dans d''autres départements
        IF i < 2 THEN
            FOR j IN 1..(2 - i) LOOP
                SELECT p.id INTO prof_rec
                FROM professeurs p
                WHERE p.dept_id != exam_rec.dept_id
                AND p.statut = ''actif''
                AND p.id != exam_rec.professeur_responsable_id
                AND NOT EXISTS (
                    SELECT 1 FROM surveillances s 
                    WHERE s.examen_id = exam_rec.id AND s.professeur_id = p.id
                )
                ORDER BY p.total_surveillances ASC
                LIMIT 1;
                
                IF prof_rec.id IS NOT NULL THEN
                    INSERT INTO surveillances (examen_id, professeur_id, priorite, role, heures_creditees)
                    VALUES (exam_rec.id, prof_rec.id, 2, ''surveillant'', 1.5);
                    
                    UPDATE professeurs 
                    SET total_surveillances = total_surveillances + 1
                    WHERE id = prof_rec.id;
                    
                    total_added := total_added + 1;
                END IF;
            END LOOP;
        END IF;
    END LOOP;
    
    RAISE NOTICE ''✅ % surveillants ajoutés manuellement'', total_added;
END $$;

-- 2. Mettre à jour la vue des surveillances
SELECT ''=== MISE À JOUR DES VUES ==='' as etape;
REFRESH MATERIALIZED VIEW vue_surveillances_professeur;

-- 3. Statistiques finales
SELECT ''=== STATISTIQUES FINALES ==='' as etape;

SELECT 
    ''Étudiants actifs'' as categorie,
    COUNT(*)::TEXT as valeur
FROM etudiants 
WHERE statut = ''actif''
UNION ALL
SELECT 
    ''Examens planifiés'',
    COUNT(*)::TEXT
FROM examens 
WHERE statut = ''planifie''
UNION ALL
SELECT 
    ''Surveillances attribuées'',
    COUNT(*)::TEXT
FROM surveillances
UNION ALL
SELECT 
    ''Conflits détectés'',
    COUNT(*)::TEXT
FROM vue_conflits
UNION ALL
SELECT 
    ''Salles utilisées'',
    COUNT(DISTINCT salle_id)::TEXT || '' / '' || (SELECT COUNT(*) FROM salles_examen)::TEXT
FROM examens 
WHERE statut = ''planifie''
ORDER BY categorie;

-- 4. Exemple de données pour la démo
SELECT ''=== EXEMPLE POUR DÉMO ==='' as etape;

SELECT ''Emploi du temps étudiant:'' as exemple;
SELECT etudiant_nom, module_nom, date_examen, heure_examen, salle, professeur
FROM vue_emploi_temps_etudiant 
WHERE etudiant_nom LIKE ''%Nom_1%''
ORDER BY date_heure
LIMIT 3;

SELECT ''Surveillances par professeur:'' as exemple;
SELECT p.prenom || '' '' || p.nom as professeur, COUNT(s.id) as nb_surveillances
FROM professeurs p
LEFT JOIN surveillances s ON p.id = s.professeur_id
GROUP BY p.id, p.prenom, p.nom
ORDER BY nb_surveillances DESC
LIMIT 5;



SET search_path TO gestion_examens;

DO $$
DECLARE
    r_surplus RECORD;
    v_new_prof_id INTEGER;
BEGIN
    -- حلقة تكرارية على المراقبات الزائدة
    FOR r_surplus IN 
        SELECT s.id AS surveillance_id, s.examen_id, s.professeur_id, p.dept_id
        FROM surveillances s
        JOIN professeurs p ON s.professeur_id = p.id
        WHERE s.professeur_id IN (
            SELECT professeur_id FROM surveillances 
            GROUP BY professeur_id HAVING COUNT(*) > 3
        )
    LOOP
        -- البحث عن أستاذ بديل:
        -- 1. من نفس القسم
        -- 2. ليس الأستاذ الحالي
        -- 3. ليس لديه مراقبة بالفعل في هذا الامتحان (لتجنب الخطأ السابق)
        -- 4. إجمالي مراقبته أقل من 3
        SELECT p.id INTO v_new_prof_id
        FROM professeurs p
        WHERE p.dept_id = r_surplus.dept_id 
          AND p.id != r_surplus.professeur_id
          AND NOT EXISTS (
              SELECT 1 FROM surveillances s2 
              WHERE s2.examen_id = r_surplus.examen_id AND s2.professeur_id = p.id
          )
          AND (SELECT COUNT(*) FROM surveillances WHERE professeur_id = p.id) < 3
        LIMIT 1;

        -- تنفيذ النقل إذا وجدنا بديلاً
        IF v_new_prof_id IS NOT NULL THEN
            UPDATE surveillances SET professeur_id = v_new_prof_id WHERE id = r_surplus.surveillance_id;
            
            -- تحديث إحصائيات الأستاذ (إذا كنت تستخدم عمود total_surveillances)
            UPDATE professeurs SET total_surveillances = (SELECT COUNT(*) FROM surveillances WHERE professeur_id = r_surplus.professeur_id) WHERE id = r_surplus.professeur_id;
            UPDATE professeurs SET total_surveillances = (SELECT COUNT(*) FROM surveillances WHERE professeur_id = v_new_prof_id) WHERE id = v_new_prof_id;
        END IF;
    END LOOP;
END $$;


CREATE OR REPLACE FUNCTION check_prof_load()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM gestion_examens.surveillances 
        WHERE professeur_id = NEW.professeur_id) >= 3 THEN
        RAISE EXCEPTION 'هذا الأستاذ وصل للحد الأقصى للمراقبات (3)';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_limit_surveillances
BEFORE INSERT ON gestion_examens.surveillances
FOR EACH ROW EXECUTE FUNCTION check_prof_load();

-- 5. Message de succès
DO $$
BEGIN
    RAISE NOTICE ''========================================'';
    RAISE NOTICE ''SYSTÈME COMPLETEMENT CONFIGURÉ ! 🎉'';
    RAISE NOTICE ''========================================'';
    RAISE NOTICE ''Toutes les corrections ont été appliquées.'';
    RAISE NOTICE ''Le système est prêt pour la démonstration.'';
    RAISE NOTICE ''========================================'';
END $$;


SET search_path TO gestion_examens;

INSERT INTO professeurs (matricule, nom, prenom, email, dept_id, specialite, statut, total_surveillances)
SELECT 
    'PROF-RES-' || i, 
    'Nom_Reserve_' || i, 
    'Prenom_Reserve_' || i, 
    'reserve' || i || '@university.dz', -- إضافة البريد الإلكتروني هنا
    (i % 7) + 1, 
    'Général', 
    'actif', 
    0
FROM generate_series(1, 20) AS i; -- زدنا العدد لضمان تغطية العجز

DROP TRIGGER IF EXISTS trg_limit_surveillances ON gestion_examens.surveillances;

CREATE TRIGGER trg_limit_surveillances
BEFORE INSERT OR UPDATE ON gestion_examens.surveillances
FOR EACH ROW EXECUTE FUNCTION check_prof_load();

SET search_path TO gestion_examens;

DO $$
DECLARE
    r_surplus RECORD;
    v_new_prof_id INTEGER;
BEGIN
    FOR r_surplus IN 
        SELECT s.id AS surveillance_id, s.examen_id, s.professeur_id
        FROM surveillances s
        WHERE s.professeur_id IN (
            SELECT professeur_id FROM surveillances 
            GROUP BY professeur_id HAVING COUNT(*) > 3
        )
    LOOP
        -- البحث عن أي أستاذ متاح في الجامعة كلها (وليس فقط نفس القسم)
        SELECT p.id INTO v_new_prof_id
        FROM professeurs p
        WHERE p.id != r_surplus.professeur_id
          AND p.statut = 'actif'
          AND NOT EXISTS (
              SELECT 1 FROM surveillances s2 
              WHERE s2.examen_id = r_surplus.examen_id AND s2.professeur_id = p.id
          )
          AND (SELECT COUNT(*) FROM surveillances WHERE professeur_id = p.id) < 3
        ORDER BY (SELECT COUNT(*) FROM surveillances WHERE professeur_id = p.id) ASC -- اختيار الأقل حملاً
        LIMIT 1;

        IF v_new_prof_id IS NOT NULL THEN
            UPDATE surveillances SET professeur_id = v_new_prof_id WHERE id = r_surplus.surveillance_id;
            
            -- تحديث إحصائيات الأساتذة
            UPDATE professeurs SET total_surveillances = (SELECT COUNT(*) FROM surveillances WHERE professeur_id = r_surplus.professeur_id) WHERE id = r_surplus.professeur_id;
            UPDATE professeurs SET total_surveillances = (SELECT COUNT(*) FROM surveillances WHERE professeur_id = v_new_prof_id) WHERE id = v_new_prof_id;
        END IF;
    END LOOP;
END $$;







