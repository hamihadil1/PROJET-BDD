-- ================================================
-- DONNÉES DE TEST POUR LE PROJET - VERSION CORRIGÉE
-- 534 étudiants, 30 examens, 2657 inscriptions
-- ================================================

SET search_path TO gestion_examens;

-- ================================================
-- 1. FORMATIONS COMPLÈTES
-- ================================================

INSERT INTO formations (nom, dept_id, nb_modules) VALUES
('Licence Informatique L1', 1, 6),
('Licence Informatique L2', 1, 7),
('Licence Informatique L3', 1, 8),
('Master Informatique M1', 1, 9),
('Master Informatique M2', 1, 8),
('Licence Mathématiques L1', 2, 6),
('Licence Mathématiques L2', 2, 7),
('Licence Mathématiques L3', 2, 8),
('Licence Physique L1', 3, 6),
('Licence Physique L2', 3, 7),
('Licence Chimie L1', 4, 6),
('Licence Chimie L2', 4, 7),
('Licence Biologie L1', 5, 6),
('Licence Biologie L2', 5, 7),
('Licence Anglais L1', 6, 6),
('Licence Anglais L2', 6, 7),
('Licence Droit L1', 7, 6),
('Licence Droit L2', 7, 7),
('Master Physique M1', 3, 9),
('Master Chimie M1', 4, 9);

-- ================================================
-- 2. PROFESSEURS SUPPLÉMENTAIRES (avec emails uniques)
-- ================================================

INSERT INTO professeurs (matricule, nom, prenom, email, dept_id, specialite, charge_max_examens) VALUES
('PROF-INF-011', 'Martin', 'Jean-Paul', 'jeanpaul.martin@univ.fr', 1, 'Algorithmique', 3),
('PROF-INF-012', 'Dubois', 'Marie-Claire', 'marieclaire.dubois@univ.fr', 1, 'Base de données', 3),
('PROF-INF-013', 'Leroy', 'Pierre-Louis', 'pierrelouis.leroy@univ.fr', 1, 'Réseaux', 3),
('PROF-INF-014', 'Bernard', 'Sophie-Anne', 'sophieanne.bernard@univ.fr', 1, 'Programmation', 2),
('PROF-INF-015', 'Petit', 'Thomas-Jean', 'thomasjean.petit@univ.fr', 1, 'Systèmes d''Exploitation', 3),
('PROF-INF-016', 'Richard', 'Isabelle-Marie', 'isabellemarie.richard@univ.fr', 1, 'Intelligence Artificielle', 2),
('PROF-MATH-011', 'Robert', 'François-Xavier', 'francoisxavier.robert@univ.fr', 2, 'Analyse', 3),
('PROF-MATH-012', 'Simon', 'Catherine-Louise', 'catherinelouise.simon@univ.fr', 2, 'Algèbre', 3),
('PROF-MATH-013', 'Durand', 'Philippe-Jacques', 'philippejacques.durand@univ.fr', 2, 'Probabilités', 2),
('PROF-MATH-014', 'Moreau', 'Nathalie-Claire', 'nathalieclaire.moreau@univ.fr', 2, 'Statistiques', 3),
('PROF-PHY-011', 'Laurent', 'Michel-André', 'michelandre.laurent@univ.fr', 3, 'Mécanique', 3),
('PROF-PHY-012', 'Roux', 'Élise-Marie', 'elisemarie.roux@univ.fr', 3, 'Électromagnétisme', 3),
('PROF-PHY-013', 'Vincent', 'Patrick-Jean', 'patrickjean.vincent@univ.fr', 3, 'Thermodynamique', 2),
('PROF-CHIM-011', 'Garcia', 'Julie-Anne', 'julieanne.garcia@univ.fr', 4, 'Chimie Organique', 3),
('PROF-CHIM-012', 'Fournier', 'Antoine-Louis', 'antoinelouis.fournier@univ.fr', 4, 'Chimie Analytique', 2),
('PROF-BIO-011', 'Lemoine', 'Caroline-Marie', 'carolinemarie.lemoine@univ.fr', 5, 'Biologie Cellulaire', 3),
('PROF-BIO-012', 'Mercier', 'David-Pierre', 'davidpierre.mercier@univ.fr', 5, 'Génétique', 2),
('PROF-LANG-011', 'Blanc', 'Sarah-Jane', 'sarahjane.blanc@univ.fr', 6, 'Linguistique', 3),
('PROF-LANG-012', 'Noir', 'Paul-Henri', 'paulhenri.noir@univ.fr', 6, 'Traduction', 2),
('PROF-DROIT-011', 'Girard', 'Émilie-Claire', 'emilieclaire.girard@univ.fr', 7, 'Droit Civil', 3),
('PROF-DROIT-012', 'Bonnet', 'Christophe-Louis', 'christophelouis.bonnet@univ.fr', 7, 'Droit Pénal', 2);




-- أنشأنا هذه الحسابات:
INSERT INTO authentification (matricule, mot_de_passe, type_utilisateur, user_id, statut) VALUES
('VD-001', 'vicedoyen123', 'vice_doyen', 1, 'actif'),
('ADMIN-001', 'admin123', 'administrateur', 2, 'actif'),
('CHEF-INF-001', 'chef123', 'chef_departement', (SELECT id FROM professeurs WHERE matricule = 'CHEF-INF-001'), 'actif'),
('PROF-INF-011', '011', 'professeur', (SELECT id FROM professeurs WHERE matricule = 'PROF-INF-011'), 'actif'),
('ETU-2024-00001', '00001', 'etudiant', (SELECT id FROM etudiants WHERE matricule = 'ETU-2024-00001'), 'actif');




-- ===========================
=====================
-- 3. SALLES SUPPLÉMENTAIRES
-- ================================================

INSERT INTO salles_examen (nom, code, type, capacite, batiment) VALUES
('Amphi C', 'AMP-C', 'amphi', 100, 'Bâtiment Sciences'),
('Salle 103', 'SAL-103', 'salle', 18, 'Bâtiment A'),
('Salle 104', 'SAL-104', 'salle', 15, 'Bâtiment A'),
('Salle 201', 'SAL-201', 'salle', 20, 'Bâtiment B'),
('Salle 202', 'SAL-202', 'salle', 20, 'Bâtiment B'),
('Salle 203', 'SAL-203', 'salle', 16, 'Bâtiment B'),
('Salle 204', 'SAL-204', 'salle', 15, 'Bâtiment B'),
('Salle 301', 'SAL-301', 'salle', 20, 'Bâtiment C'),
('Salle 302', 'SAL-302', 'salle', 20, 'Bâtiment C'),
('Salle 303', 'SAL-303', 'salle', 18, 'Bâtiment C'),
('Salle 304', 'SAL-304', 'salle', 15, 'Bâtiment C'),
('Labo Info 2', 'LAB-INF2', 'labo', 15, 'Bâtiment Informatique'),
('Labo Physique', 'LAB-PHY1', 'labo', 12, 'Bâtiment Sciences'),
('Labo Chimie', 'LAB-CHIM1', 'labo', 10, 'Bâtiment Sciences'),
('Labo Biologie', 'LAB-BIO1', 'labo', 12, 'Bâtiment Sciences');

-- ================================================
-- 4. GROUPES (2 par formation L1/L2)
-- ================================================

DO $$
DECLARE
    formation_rec RECORD;
    i INTEGER;
    niveau_val VARCHAR(10);
BEGIN
    FOR formation_rec IN SELECT * FROM formations WHERE nom LIKE '%L1%' OR nom LIKE '%L2%' LOOP
        IF formation_rec.nom LIKE '%L1%' THEN
            niveau_val := 'L1';
        ELSIF formation_rec.nom LIKE '%L2%' THEN
            niveau_val := 'L2';
        ELSE
            niveau_val := 'L1';
        END IF;
        
        FOR i IN 1..2 LOOP
            INSERT INTO groupes (nom, code, formation_id, annee_academique, capacite_max, niveau) VALUES
            (
                'Groupe ' || CHR(64 + i) || ' - ' || formation_rec.nom,
                'GRP-' || 
                CASE 
                    WHEN formation_rec.nom LIKE '%Informatique%' THEN 'INF'
                    WHEN formation_rec.nom LIKE '%Math%' THEN 'MATH'
                    WHEN formation_rec.nom LIKE '%Physique%' THEN 'PHY'
                    WHEN formation_rec.nom LIKE '%Chimie%' THEN 'CHIM'
                    WHEN formation_rec.nom LIKE '%Biologie%' THEN 'BIO'
                    WHEN formation_rec.nom LIKE '%Anglais%' THEN 'ANG'
                    WHEN formation_rec.nom LIKE '%Droit%' THEN 'DROIT'
                    ELSE 'GEN'
                END || '-' || niveau_val || '-' || CHR(64 + i),
                formation_rec.id,
                '2024-2025',
                40,
                niveau_val
            );
        END LOOP;
    END LOOP;
END $$;

-- ================================================
-- 5. MODULES (6 par formation)
-- ================================================

DO $$
DECLARE
    formation_rec RECORD;
    module_noms TEXT[] := ARRAY['Introduction', 'Fondamentaux', 'Spécialité I', 'Spécialité II', 'Projet', 'Mémoire'];
    i INTEGER;
    prefixe TEXT;
BEGIN
    FOR formation_rec IN SELECT * FROM formations LOOP
        prefixe := 
            CASE 
                WHEN formation_rec.nom LIKE '%Informatique%' THEN 'INF'
                WHEN formation_rec.nom LIKE '%Math%' THEN 'MATH'
                WHEN formation_rec.nom LIKE '%Physique%' THEN 'PHY'
                WHEN formation_rec.nom LIKE '%Chimie%' THEN 'CHIM'
                WHEN formation_rec.nom LIKE '%Biologie%' THEN 'BIO'
                WHEN formation_rec.nom LIKE '%Anglais%' THEN 'ANG'
                WHEN formation_rec.nom LIKE '%Droit%' THEN 'DROIT'
                ELSE 'GEN'
            END;
        
        FOR i IN 1..6 LOOP
            INSERT INTO modules (nom, code, credits, formation_id) VALUES
            (
                module_noms[i] || ' - ' || formation_rec.nom,
                prefixe || '-' || 
                CASE 
                    WHEN formation_rec.nom LIKE '%L1%' THEN 'L1'
                    WHEN formation_rec.nom LIKE '%L2%' THEN 'L2'
                    WHEN formation_rec.nom LIKE '%L3%' THEN 'L3'
                    WHEN formation_rec.nom LIKE '%M1%' THEN 'M1'
                    WHEN formation_rec.nom LIKE '%M2%' THEN 'M2'
                    ELSE ''
                END || '-' || i,
                CASE i
                    WHEN 1 THEN 4
                    WHEN 2 THEN 5
                    WHEN 3 THEN 6
                    WHEN 4 THEN 6
                    WHEN 5 THEN 8
                    WHEN 6 THEN 10
                END,
                formation_rec.id
            );
        END LOOP;
    END LOOP;
END $$;

-- ================================================
-- 6. ÉTUDIANTS (534 étudiants) - VERSION CORRIGÉE
-- ================================================

-- Désactiver le trigger de matricule temporairement
DROP TRIGGER IF EXISTS trg_matricule_etudiant ON etudiants;

DO $$
DECLARE
    groupe_rec RECORD;
    etudiant_count INTEGER;
    total_etudiants INTEGER := 0;
    i INTEGER;
    etudiant_num INTEGER := 0;
    matricule_base VARCHAR;
BEGIN
    FOR groupe_rec IN SELECT * FROM groupes LOOP
        etudiant_count := 15 + (random() * 10)::INTEGER;
        
        FOR i IN 1..etudiant_count LOOP
            etudiant_num := etudiant_num + 1;
            matricule_base := 'ETU-2024-' || LPAD(etudiant_num::TEXT, 5, '0');
            
            INSERT INTO etudiants (matricule, nom, prenom, email, formation_id, groupe_id, promo, annee_inscription, statut) VALUES
            (
                matricule_base,
                'Nom_' || etudiant_num,
                CASE (etudiant_num % 10)
                    WHEN 0 THEN 'Mohamed'
                    WHEN 1 THEN 'Fatima'
                    WHEN 2 THEN 'Ahmed'
                    WHEN 3 THEN 'Amina'
                    WHEN 4 THEN 'Youssef'
                    WHEN 5 THEN 'Sarah'
                    WHEN 6 THEN 'Karim'
                    WHEN 7 THEN 'Leila'
                    WHEN 8 THEN 'Hassan'
                    WHEN 9 THEN 'Nadia'
                END,
                'etu' || etudiant_num || '@univ.fr',
                groupe_rec.formation_id,
                groupe_rec.id,
                CASE groupe_rec.niveau
                    WHEN 'L1' THEN 1
                    WHEN 'L2' THEN 2
                    WHEN 'L3' THEN 3
                    WHEN 'M1' THEN 4
                    WHEN 'M2' THEN 5
                    ELSE 1
                END,
                2024,
                'actif'
            );
            
            total_etudiants := total_etudiants + 1;
        END LOOP;
    END LOOP;
END $$;

-- Réactiver le trigger
CREATE TRIGGER trg_matricule_etudiant 
BEFORE INSERT ON etudiants 
FOR EACH ROW 
WHEN (NEW.matricule IS NULL OR NEW.matricule = '') 
EXECUTE FUNCTION generer_matricule_etudiant();

-- ================================================
-- 7. INSCRIPTIONS (2657 inscriptions)
-- ================================================

DO $$
DECLARE
    etudiant_rec RECORD;
    module_rec RECORD;
    inscription_count INTEGER := 0;
BEGIN
    FOR etudiant_rec IN SELECT * FROM etudiants LOOP
        FOR module_rec IN 
            SELECT * FROM modules 
            WHERE formation_id = etudiant_rec.formation_id 
            ORDER BY random() 
            LIMIT (4 + (random() * 2)::INTEGER)
        LOOP
            INSERT INTO inscriptions (etudiant_id, module_id, annee_academique, statut) VALUES
            (
                etudiant_rec.id,
                module_rec.id,
                '2024-2025',
                CASE 
                    WHEN random() < 0.7 THEN 'inscrit'
                    WHEN random() < 0.9 THEN 'en_cours'
                    ELSE 'valide'
                END
            );
            
            inscription_count := inscription_count + 1;
        END LOOP;
    END LOOP;
END $$;

-- ================================================
-- 8. EXAMENS (30 examens planifiés)
-- ================================================

ALTER TABLE examens DISABLE TRIGGER ALL;

DO $$
DECLARE
    module_rec RECORD;
    prof_rec RECORD;
    salle_rec RECORD;
    exam_date DATE := '2025-01-20';
    exam_time TIME;
    exam_count INTEGER := 0;
    heures TIME[] := ARRAY['08:30', '10:15', '13:30', '15:15']::TIME[];
    i INTEGER;
    j INTEGER := 0;
BEGIN
    FOR module_rec IN 
        SELECT m.*, f.dept_id 
        FROM modules m
        JOIN formations f ON m.formation_id = f.id
        WHERE EXISTS (SELECT 1 FROM inscriptions WHERE module_id = m.id)
        ORDER BY random() 
        LIMIT 30
    LOOP
        SELECT * INTO prof_rec
        FROM professeurs 
        WHERE dept_id = module_rec.dept_id 
        AND statut = 'actif'
        ORDER BY random()
        LIMIT 1;
        
        IF prof_rec.id IS NULL THEN CONTINUE; END IF;
        
        DECLARE
            nb_etudiants INTEGER;
        BEGIN
            SELECT COUNT(*) INTO nb_etudiants
            FROM inscriptions 
            WHERE module_id = module_rec.id
            AND statut IN ('inscrit', 'en_cours');
            
            IF nb_etudiants = 0 THEN CONTINUE; END IF;
            
            IF nb_etudiants <= 20 THEN
                SELECT * INTO salle_rec
                FROM salles_examen 
                WHERE type IN ('salle', 'labo')
                AND capacite >= nb_etudiants
                AND disponible = TRUE
                ORDER BY random()
                LIMIT 1;
            ELSE
                SELECT * INTO salle_rec
                FROM salles_examen 
                WHERE type = 'amphi'
                AND capacite >= nb_etudiants
                AND disponible = TRUE
                ORDER BY random()
                LIMIT 1;
            END IF;
            
            IF salle_rec.id IS NULL THEN CONTINUE; END IF;
            
            i := j % 4;
            exam_time := heures[i + 1];
            
            WHILE EXTRACT(DOW FROM exam_date) IN (0, 6) LOOP
                exam_date := exam_date + 1;
            END LOOP;
            
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
                module_rec.id,
                module_rec.formation_id,
                prof_rec.id,
                salle_rec.id,
                exam_date + exam_time + (INTERVAL '1 day' * (j / 4)),
                90,
                'normal',
                'planifie'
            );
            
            exam_count := exam_count + 1;
            j := j + 1;
        END;
    END LOOP;
END $$;

ALTER TABLE examens ENABLE TRIGGER ALL;

-- ================================================
-- 9. NOTES ET SESSIONS
-- ================================================

-- Mettre à jour quelques notes
UPDATE inscriptions 
SET note = (10 + random() * 10)::DECIMAL(4,2),
    statut = CASE WHEN random() < 0.8 THEN 'valide' ELSE 'echec' END
WHERE id IN (SELECT id FROM inscriptions ORDER BY random() LIMIT 100);

INSERT INTO sessions_examen (nom, date_debut, date_fin, statut) VALUES
('Session Janvier 2025', '2025-01-20', '2025-01-31', 'planifie'),
('Session Juin 2025', '2025-06-10', '2025-06-25', 'planifie');

-- ================================================
-- 10. MESSAGE FINAL
-- ================================================

DO $$
DECLARE
    nb_etudiants INTEGER;
    nb_examens INTEGER;
    nb_inscriptions INTEGER;
    nb_professeurs INTEGER;
    nb_salles INTEGER;
BEGIN
    SELECT COUNT(*) INTO nb_etudiants FROM etudiants;
    SELECT COUNT(*) INTO nb_examens FROM examens;
    SELECT COUNT(*) INTO nb_inscriptions FROM inscriptions;
    SELECT COUNT(*) INTO nb_professeurs FROM professeurs;
    SELECT COUNT(*) INTO nb_salles FROM salles_examen;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'DONNÉES DE TEST CRÉÉES AVEC SUCCÈS!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Statistiques:';
    RAISE NOTICE '- Étudiants: %', nb_etudiants;
    RAISE NOTICE '- Examens: %', nb_examens;
    RAISE NOTICE '- Inscriptions: %', nb_inscriptions;
    RAISE NOTICE '- Professeurs: %', nb_professeurs;
    RAISE NOTICE '- Salles: %', nb_salles;
    RAISE NOTICE '========================================';
END $$;