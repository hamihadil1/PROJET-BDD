-- testq_fixed.sql - ملف مصحح بترميز UTF-8
-- 1. حذف الامتحانات الحالية المنتهكة للقيود
DELETE FROM gestion_examens.examens 
WHERE statut = 'planifie' 
AND DATE(date_heure) IN ('2025-01-22', '2025-01-23', '2025-01-25', '2025-01-26');

-- 2. اعادة تعيين المراقبات
UPDATE gestion_examens.professeurs 
SET total_surveillances = 0;

DELETE FROM gestion_examens.surveillances;

-- 3. اعدادات الترميز
SET client_encoding = 'UTF8';
SET search_path TO gestion_examens;

-- 4. حذف الاجراءات القديمة ان وجدت
DROP PROCEDURE IF EXISTS generer_edt_optimal() CASCADE;
DROP FUNCTION IF EXISTS distribuer_surveillants_equilibres() CASCADE;

-- 5. اعادة تخطيط ذكي مع احترام القيود
CREATE OR REPLACE PROCEDURE generer_edt_optimal()
LANGUAGE plpgsql
AS $$
DECLARE
    v_module RECORD;
    v_date DATE := '2025-01-20';
    v_heure TIME;
    v_jours_disponibles INTEGER := 10;
    v_creneaux_par_jour INTEGER := 4;
    v_max_examens INTEGER := v_jours_disponibles * v_creneaux_par_jour;
    v_examens_planifies INTEGER := 0;
    v_prof_disponible INTEGER;
    v_salle_disponible INTEGER;
    v_heures TIME[] := ARRAY['08:30', '10:15', '13:30', '15:15'];
BEGIN
    -- تنظيف
    DELETE FROM examens WHERE statut = 'planifie';
    
    -- الحصول على قائمة الوحدات المرتبة حسب عدد الطلاب
    FOR v_module IN (
        SELECT 
            m.id as module_id,
            m.formation_id,
            f.dept_id,
            COUNT(DISTINCT i.etudiant_id) as nb_etudiants,
            ARRAY_AGG(DISTINCT i.etudiant_id) as liste_etudiants
        FROM modules m
        JOIN formations f ON m.formation_id = f.id
        JOIN inscriptions i ON m.id = i.module_id
        WHERE i.statut IN ('inscrit', 'en_cours')
        GROUP BY m.id, m.formation_id, f.dept_id
        ORDER BY nb_etudiants DESC
        LIMIT 30  -- فقط 30 امتحان لتجنب الاكتظاظ
    ) LOOP
        
        -- تخطيط كل وحدة
        FOR i IN 1..v_jours_disponibles LOOP
            FOR j IN 1..v_creneaux_par_jour LOOP
                
                -- حساب التاريخ والوقت
                v_date := '2025-01-20'::DATE + (i-1);
                
                -- تخطي عطلات نهاية الاسبوع
                CONTINUE WHEN EXTRACT(DOW FROM v_date) IN (0, 6);
                
                v_heure := v_heures[j];
                
                -- 1. التحقق من عدم وجود طلاب لديهم امتحان آخر في هذا اليوم
                IF EXISTS (
                    SELECT 1
                    FROM inscriptions i2
                    JOIN examens ex2 ON i2.module_id = ex2.module_id
                    WHERE i2.etudiant_id = ANY(v_module.liste_etudiants)
                    AND DATE(ex2.date_heure) = v_date
                    AND ex2.statut = 'planifie'
                ) THEN
                    CONTINUE;
                END IF;
                
                -- 2. ايجاد استاذ متاح (اقل من 3 امتحانات/يوم)
                SELECT p.id INTO v_prof_disponible
                FROM professeurs p
                WHERE p.dept_id = v_module.dept_id
                AND p.statut = 'actif'
                AND (
                    SELECT COUNT(*)
                    FROM examens ex
                    WHERE ex.professeur_responsable_id = p.id
                    AND DATE(ex.date_heure) = v_date
                    AND ex.statut = 'planifie'
                ) < p.charge_max_examens
                ORDER BY p.total_surveillances ASC
                LIMIT 1;
                
                IF v_prof_disponible IS NULL THEN
                    CONTINUE;
                END IF;
                
                -- 3. ايجاد قاعة متاحة
                SELECT s.id INTO v_salle_disponible
                FROM salles_examen s
                WHERE s.disponible = TRUE
                AND s.capacite >= v_module.nb_etudiants
                AND NOT EXISTS (
                    SELECT 1
                    FROM examens ex
                    WHERE ex.salle_id = s.id
                    AND ex.date_heure = (v_date + v_heure)
                )
                ORDER BY 
                    CASE 
                        WHEN s.type = 'amphi' AND v_module.nb_etudiants > 20 THEN 1
                        WHEN s.type != 'amphi' AND v_module.nb_etudiants <= 20 THEN 2
                        ELSE 3
                    END,
                    s.capacite - v_module.nb_etudiants
                LIMIT 1;
                
                IF v_salle_disponible IS NULL THEN
                    CONTINUE;
                END IF;
                
                -- 4. انشاء الامتحان
                INSERT INTO examens (
                    module_id,
                    formation_id,
                    professeur_responsable_id,
                    salle_id,
                    date_heure,
                    duree_minutes,
                    type_examen,
                    statut
                ) VALUES (
                    v_module.module_id,
                    v_module.formation_id,
                    v_prof_disponible,
                    v_salle_disponible,
                    v_date + v_heure,
                    90,
                    'normal',
                    'planifie'
                );
                
                v_examens_planifies := v_examens_planifies + 1;
                
                -- الخروج من الحلقتين بعد ادخال الامتحان
                EXIT WHEN TRUE;
                
            END LOOP;
            
            EXIT WHEN v_examens_planifies > v_max_examens;
        END LOOP;
        
    END LOOP;
    
    RAISE NOTICE '% examens planifies avec succes', v_examens_planifies;
    
    -- 5. توزيع المراقبين
    PERFORM distribuer_surveillants_equilibres();
    
END;
$$;

-- 6. توزيع المراقبين بشكل متوازن
CREATE OR REPLACE FUNCTION distribuer_surveillants_equilibres()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_examen RECORD;
    v_prof RECORD;
    v_dept_examen INTEGER;
    v_surveillants_ajoutes INTEGER := 0;
    v_nb_surveillants INTEGER := 2;
BEGIN
    FOR v_examen IN (
        SELECT e.*, f.dept_id
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE e.statut = 'planifie'
        AND NOT EXISTS (
            SELECT 1 FROM surveillances s 
            WHERE s.examen_id = e.id
        )
        ORDER BY e.date_heure
    ) LOOP
        
        v_dept_examen := v_examen.dept_id;
        
        -- مراقبون من نفس القسم
        FOR v_prof IN (
            SELECT p.id, p.nom, p.prenom, p.total_surveillances
            FROM professeurs p
            WHERE p.dept_id = v_dept_examen
            AND p.id != v_examen.professeur_responsable_id
            AND p.statut = 'actif'
            AND NOT EXISTS (
                SELECT 1 FROM examens ex
                WHERE ex.professeur_responsable_id = p.id
                AND DATE(ex.date_heure) = DATE(v_examen.date_heure)
                AND ex.statut = 'planifie'
            )
            ORDER BY p.total_surveillances ASC
            LIMIT v_nb_surveillants
        ) LOOP
            INSERT INTO surveillances (
                examen_id,
                professeur_id,
                priorite,
                role
            ) VALUES (
                v_examen.id,
                v_prof.id,
                1,
                'surveillant'
            );
            
            UPDATE professeurs 
            SET total_surveillances = total_surveillances + 1
            WHERE id = v_prof.id;
            
            v_surveillants_ajoutes := v_surveillants_ajoutes + 1;
        END LOOP;
        
    END LOOP;
    
    RETURN v_surveillants_ajoutes;
END;
$$;

-- 7. تشغيل الاجراء
CALL generer_edt_optimal();

-- 8. التحقق من النتائج
SELECT 'Resultats:' as message;
SELECT COUNT(*) as total_examens FROM examens WHERE statut = 'planifie';
SELECT COUNT(*) as total_conflits FROM vue_conflits;