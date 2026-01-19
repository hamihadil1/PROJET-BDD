SET search_path TO gestion_examens;

CREATE OR REPLACE VIEW vue_conflits AS
-- 1. صراعات الطلاب: امتحانان في نفس الوقت تماماً (بالدقيقة والثانية)
SELECT 
    'Conflit etudiant'::text as type_conflit,
    et.prenom || ' ' || et.nom as element,
    et.matricule,
    e1.date_heure::date as date_conflit,
    COUNT(*) as nombre_examens
FROM inscriptions i1
JOIN inscriptions i2 ON i1.etudiant_id = i2.etudiant_id AND i1.module_id < i2.module_id
JOIN examens e1 ON i1.module_id = e1.module_id
JOIN examens e2 ON i2.module_id = e2.module_id
JOIN etudiants et ON i1.etudiant_id = et.id
WHERE e1.date_heure = e2.date_heure -- لا صراع إلا إذا تطابق الوقت تماماً
GROUP BY et.id, et.prenom, et.nom, et.matricule, e1.date_heure

UNION ALL

-- 2. صراعات الأساتذة: مراقبتان في نفس الوقت
SELECT 
    'Conflit professeur'::text,
    p.prenom || ' ' || p.nom,
    p.matricule,
    e.date_heure::date,
    COUNT(*)
FROM surveillances s1
JOIN surveillances s2 ON s1.professeur_id = s2.professeur_id AND s1.id < s2.id
JOIN examens e1 ON s1.examen_id = e1.id
JOIN examens e2 ON s2.examen_id = e2.id
JOIN professeurs p ON s1.professeur_id = p.id
JOIN examens e ON s1.examen_id = e.id
WHERE e1.date_heure = e2.date_heure
GROUP BY p.id, p.prenom, p.nom, p.matricule, e.date_heure;