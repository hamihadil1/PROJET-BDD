-- ================================================
-- إضافة مراقبات فورية لـ PROF-INF-011
-- ================================================

SET search_path TO gestion_examens;

-- 1. إيجاد امتحانات في قسم Informatique
SELECT '=== إضافة مراقبات لـ PROF-INF-011 ===' as message;

-- 2. إضافة 4 مراقبات لـ PROF-INF-011
INSERT INTO surveillances (examen_id, professeur_id, priorite, role, heures_creditees)
SELECT 
    e.id as examen_id,
    (SELECT id FROM professeurs WHERE matricule = 'PROF-INF-011') as professeur_id,
    1 as priorite,
    'surveillant' as role,
    2.0 as heures_creditees
FROM examens e
JOIN modules m ON e.module_id = m.id
JOIN formations f ON m.formation_id = f.id
WHERE e.statut = 'planifie'
AND f.dept_id = (SELECT dept_id FROM professeurs WHERE matricule = 'PROF-INF-011')
AND e.professeur_responsable_id != (SELECT id FROM professeurs WHERE matricule = 'PROF-INF-011')
ORDER BY e.date_heure
LIMIT 4
ON CONFLICT DO NOTHING;

-- 3. تحديث العداد
UPDATE professeurs 
SET total_surveillances = (
    SELECT COUNT(*) 
    FROM surveillances 
    WHERE professeur_id = (SELECT id FROM professeurs WHERE matricule = 'PROF-INF-011')
)
WHERE matricule = 'PROF-INF-011';

-- 4. التحقق
SELECT 
    '✅ تمت الإضافة' as résultat,
    (SELECT COUNT(*) FROM surveillances WHERE professeur_id = 
        (SELECT id FROM professeurs WHERE matricule = 'PROF-INF-011')) as nombre_surveillances,
    (SELECT total_surveillances FROM professeurs WHERE matricule = 'PROF-INF-011') as total_mis_à_jour;