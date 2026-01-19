-- ================================================
-- INITIALISATION DES COMPTES UTILISATEURS
-- ================================================

SET search_path TO gestion_examens;

-- Remplacer la fonction generer_mot_de_passe_defaut par :
CREATE OR REPLACE FUNCTION generer_mot_de_passe_defaut(matricule VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
    -- Extraire les chiffres du matricule
    RETURN (SELECT SUBSTRING(matricule FROM '\d+'));
END;
$$ LANGUAGE plpgsql;

-- Créer les comptes pour les étudiants
INSERT INTO authentification (matricule, mot_de_passe, type_utilisateur, user_id)
SELECT 
    e.matricule,
    generer_mot_de_passe_defaut(e.matricule) as mot_de_passe,
    'etudiant' as type_utilisateur,
    e.id as user_id
FROM etudiants e
WHERE e.statut = 'actif'
ON CONFLICT (matricule) DO NOTHING;

-- Créer les comptes pour les professeurs
INSERT INTO authentification (matricule, mot_de_passe, type_utilisateur, user_id)
SELECT 
    p.matricule,
    generer_mot_de_passe_defaut(p.matricule) as mot_de_passe,
    'professeur' as type_utilisateur,
    p.id as user_id
FROM professeurs p
WHERE p.statut = 'actif'
ON CONFLICT (matricule) DO NOTHING;

-- Créer les comptes administrateurs
INSERT INTO authentification (matricule, mot_de_passe, type_utilisateur, user_id) VALUES
('ADMIN-001', 'admin123', 'administrateur', 1),
('ADMIN-002', 'admin456', 'administrateur', 2),
('VD-001', 'vicedoyen123', 'vice_doyen', 1);

-- Message de confirmation
DO $$
DECLARE
    nb_etudiants INTEGER;
    nb_professeurs INTEGER;
    nb_admin INTEGER;
BEGIN
    SELECT COUNT(*) INTO nb_etudiants FROM authentification WHERE type_utilisateur = 'etudiant';
    SELECT COUNT(*) INTO nb_professeurs FROM authentification WHERE type_utilisateur = 'professeur';
    SELECT COUNT(*) INTO nb_admin FROM authentification WHERE type_utilisateur IN ('administrateur', 'vice_doyen');
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'COMPTES UTILISATEURS CRÉÉS AVEC SUCCÈS';
    RAISE NOTICE '========================================';
    RAISE NOTICE '- Étudiants: % comptes', nb_etudiants;
    RAISE NOTICE '- Professeurs: % comptes', nb_professeurs;
    RAISE NOTICE '- Administrateurs: % comptes', nb_admin;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Matricules de test:';
    RAISE NOTICE '- Étudiant: ETU-2024-00001 / mdp: 00001';
    RAISE NOTICE '- Professeur: PROF-INF-011 / mdp: 011';
    RAISE NOTICE '- Administrateur: ADMIN-001 / mdp: admin123';
    RAISE NOTICE '========================================';
END $$;