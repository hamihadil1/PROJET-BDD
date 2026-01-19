-- ================================================
-- FONCTIONS D'AUTHENTIFICATION
-- ================================================

-- Fonction pour vérifier les identifiants
CREATE OR REPLACE FUNCTION verifier_authentification(
    p_matricule VARCHAR,
    p_mot_de_passe VARCHAR
)
RETURNS TABLE (
    id INTEGER,
    matricule VARCHAR,
    type_utilisateur VARCHAR,
    user_id INTEGER,
    nom_complet VARCHAR, -- المخرج المتوقع VARCHAR
    statut VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.matricule,
        a.type_utilisateur,
        a.user_id,
        (CASE 
            WHEN a.type_utilisateur = 'etudiant' THEN 
                (SELECT (e.prenom || ' ' || e.nom)::varchar FROM gestion_examens.etudiants e WHERE e.id = a.user_id)
            WHEN a.type_utilisateur IN ('professeur', 'chef_departement') THEN 
                (SELECT (p.prenom || ' ' || p.nom)::varchar FROM gestion_examens.professeurs p WHERE p.id = a.user_id)
            WHEN a.type_utilisateur = 'administrateur' THEN 'Administrateur Système'::varchar
            WHEN a.type_utilisateur = 'vice_doyen' THEN 'Vice-Doyen'::varchar
            ELSE 'Utilisateur'::varchar
        END) as nom_complet,
        a.statut
    FROM gestion_examens.authentification a
    WHERE a.matricule = p_matricule
    AND a.mot_de_passe = p_mot_de_passe
    AND a.statut = 'actif';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour mettre à jour la dernière connexion
CREATE OR REPLACE FUNCTION mettre_a_jour_connexion(p_auth_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE authentification 
    SET derniere_connexion = CURRENT_TIMESTAMP
    WHERE id = p_auth_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour changer le mot de passe
CREATE OR REPLACE FUNCTION changer_mot_de_passe(
    p_matricule VARCHAR,
    p_ancien_mdp VARCHAR,
    p_nouveau_mdp VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_auth_id INTEGER;
BEGIN
    -- Vérifier l'ancien mot de passe
    SELECT id INTO v_auth_id
    FROM authentification
    WHERE matricule = p_matricule
    AND mot_de_passe = p_ancien_mdp
    AND statut = 'actif';
    
    IF v_auth_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Mettre à jour le mot de passe
    UPDATE authentification 
    SET mot_de_passe = p_nouveau_mdp,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = v_auth_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour récupérer les informations utilisateur
CREATE OR REPLACE FUNCTION get_utilisateur_info(p_auth_id INTEGER)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'id', a.id,
        'matricule', a.matricule,
        'type', a.type_utilisateur,
        'user_id', a.user_id,
        'nom_complet', 
            CASE 
                WHEN a.type_utilisateur = 'etudiant' THEN 
                    (SELECT e.prenom || ' ' || e.nom FROM etudiants e WHERE e.id = a.user_id)
                WHEN a.type_utilisateur = 'professeur' THEN 
                    (SELECT p.prenom || ' ' || p.nom FROM professeurs p WHERE p.id = a.user_id)
                ELSE 'Administrateur'
            END,
        'details', 
            CASE 
                WHEN a.type_utilisateur = 'etudiant' THEN 
                    (SELECT json_build_object(
                        'formation', f.nom,
                        'departement', d.nom,
                        'promo', e.promo,
                        'groupe', g.nom
                    ) FROM etudiants e
                    JOIN formations f ON e.formation_id = f.id
                    JOIN departements d ON f.dept_id = d.id
                    LEFT JOIN groupes g ON e.groupe_id = g.id
                    WHERE e.id = a.user_id)
                WHEN a.type_utilisateur = 'professeur' THEN 
                    (SELECT json_build_object(
                        'departement', d.nom,
                        'specialite', p.specialite,
                        'email', p.email
                    ) FROM professeurs p
                    JOIN departements d ON p.dept_id = d.id
                    WHERE p.id = a.user_id)
                ELSE json_build_object('role', 'Administration')
            END
    ) INTO result
    FROM authentification a
    WHERE a.id = p_auth_id;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;