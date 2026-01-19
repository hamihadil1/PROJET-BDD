-- ================================================
-- CREATION DES CRENEAUX HORAIRES DETAILS
-- ================================================
CREATE OR REPLACE PROCEDURE creer_creneaux_horaires()
LANGUAGE plpgsql
AS $$
DECLARE
    v_heure_debut TIME := '08:30:00';
    v_heure_fin TIME;
    v_creneau_count INTEGER := 0;
    v_date DATE;
    v_jours INTEGER := 15; -- 15 jours d'examens
    v_duree_examen INTERVAL := '90 minutes';
    v_pause INTERVAL := '15 minutes';
    v_total_creneaux INTEGER := 0;
BEGIN
    -- Supprimer les anciens créneaux
    DELETE FROM gestion_examens.creneaux_disponibles;
    
    -- Créer les créneaux pour chaque jour
    FOR i IN 0..(v_jours-1) LOOP
        v_date := '2026-01-06'::DATE + i;
        
        -- Passer les weekends
        CONTINUE WHEN EXTRACT(DOW FROM v_date) IN (0, 6);
        
        -- Initialiser l'heure pour ce jour
        v_heure_debut := '08:30:00';
        
        -- Créer 4 créneaux par jour
        FOR j IN 1..4 LOOP
            v_heure_fin := v_heure_debut + v_duree_examen;
            
            -- Vérifier que l'heure de fin ne dépasse pas 17:00
            IF v_heure_fin <= '17:00:00' THEN
                INSERT INTO gestion_examens.creneaux_disponibles (
                    jour,
                    heure_debut,
                    heure_fin,
                    type_creneau,
                    disponible
                ) VALUES (
                    v_date,
                    v_heure_debut,
                    v_heure_fin,
                    'examen',
                    TRUE
                );
                
                v_total_creneaux := v_total_creneaux + 1;
                
                -- Mettre à jour l'heure pour le prochain créneau
                v_heure_debut := v_heure_fin + v_pause;
            END IF;
        END LOOP;
    END LOOP;
    
    RAISE NOTICE '✅ % créneaux horaires créés', v_total_creneaux;
END;
$$;

-- ================================================
-- PROCEDURE: GENERER_EDT_COMPLET_8H30_16H
-- Création d'emploi du temps complet avec 4 créneaux/jour
-- ================================================
CREATE OR REPLACE PROCEDURE generer_edt_complet_8h30_16h()
LANGUAGE plpgsql
AS $$
DECLARE
    -- Variables pour les créneaux
    v_creneau RECORD;
    v_counter INTEGER := 0;
    v_examens_crees INTEGER := 0;
    
    -- Variables pour l'examen
    v_module_id INTEGER;
    v_formation_id INTEGER;
    v_prof_id INTEGER;
    v_salle_id INTEGER;
    v_groupe_id INTEGER;
    v_nb_etudiants INTEGER;
    
    -- Liste des modules par niveau
    modules_l1 TEXT[] := ARRAY[
        'ALGEBRE1', 'ANALYSE1', 'PHYSIQUE1', 'CHIMIE1', 
        'ANGLAIS1', 'INFORMATIQUE1', 'MATHS1', 'STATISTIQUES1'
    ];
    modules_l2 TEXT[] := ARRAY[
        'ALGEBRE2', 'ANALYSE2', 'PHYSIQUE2', 'CHIMIE2',
        'ANGLAIS2', 'PROGRAMMATION', 'BASE DE DONNEES', 'RESEAUX'
    ];
    modules_l3 TEXT[] := ARRAY[
        'ALGEBRE3', 'ANALYSE3', 'PHYSIQUE3', 'CHIMIE3',
        'ANGLAIS3', 'IA', 'SECURITE', 'CLOUD COMPUTING'
    ];
    
    -- Groupes par niveau
    groupes_l1 TEXT[] := ARRAY[
        'L101-A', 'L101-B', 'L102-A', 'L102-B', 'L103-A', 'L103-B',
        'L104-A', 'L104-B', 'L105-A', 'L105-B'
    ];
    groupes_l2 TEXT[] := ARRAY[
        'L201-A', 'L201-B', 'L202-A', 'L202-B', 'L203-A', 'L203-B'
    ];
    groupes_l3 TEXT[] := ARRAY[
        'L301-A', 'L301-B', 'L302-A', 'L302-B'
    ];
    
    -- Salles par capacité
    salles_petites TEXT[] := ARRAY['S.4.01', 'S.4.02', 'S.4.03', 'S.4.04', 'S.4.05'];
    salles_moyennes TEXT[] := ARRAY['S.4.06', 'S.4.07', 'S.4.08', 'S.4.09', 'S.4.10'];
    salles_grandes TEXT[] := ARRAY['AMP01', 'AMP02', 'AMP03', 'AMP100', 'AMP101'];
    
BEGIN
    -- Nettoyage initial
    DELETE FROM gestion_examens.examens WHERE statut = 'planifie';
    UPDATE gestion_examens.professeurs SET total_surveillances = 0;
    DELETE FROM gestion_examens.surveillances;
    
    -- Créer les créneaux horaires
    CALL creer_creneaux_horaires();
    
    -- 1. Planifier les examens L1
    RAISE NOTICE 'Planification L1...';
    PERFORM planifier_examens_par_niveau('L1', modules_l1, groupes_l1, 20);
    
    -- 2. Planifier les examens L2
    RAISE NOTICE 'Planification L2...';
    PERFORM planifier_examens_par_niveau('L2', modules_l2, groupes_l2, 15);
    
    -- 3. Planifier les examens L3
    RAISE NOTICE 'Planification L3...';
    PERFORM planifier_examens_par_niveau('L3', modules_l3, groupes_l3, 10);
    
    -- Récupérer le nombre total d'examens
    SELECT COUNT(*) INTO v_examens_crees 
    FROM gestion_examens.examens 
    WHERE statut = 'planifie';
    
    RAISE NOTICE '✅ % examens planifiés avec succès', v_examens_crees;
    
    -- Distribuer les surveillants
    PERFORM distribuer_surveillants_auto();
    
END;
$$;

-- ================================================
-- FUNCTION: PLANIFIER_EXAMENS_PAR_NIVEAU
-- ================================================
CREATE OR REPLACE FUNCTION planifier_examens_par_niveau(
    p_niveau VARCHAR(10),
    p_modules TEXT[],
    p_groupes TEXT[],
    p_etudiants_par_groupe INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_module_nom TEXT;
    v_groupe_nom TEXT;
    v_creneau RECORD;
    v_examens_crees INTEGER := 0;
    v_module_id INTEGER;
    v_formation_id INTEGER;
    v_groupe_id INTEGER;
    v_prof_id INTEGER;
    v_salle_id INTEGER;
    v_nb_etudiants INTEGER;
    v_salle_type VARCHAR;
    v_capacite INTEGER;
BEGIN
    -- Pour chaque module
    FOREACH v_module_nom IN ARRAY p_modules LOOP
        -- Pour chaque groupe
        FOREACH v_groupe_nom IN ARRAY p_groupes LOOP
            -- Chercher un créneau disponible
            FOR v_creneau IN (
                SELECT cd.id, cd.jour, cd.heure_debut, cd.heure_fin
                FROM gestion_examens.creneaux_disponibles cd
                WHERE cd.disponible = TRUE
                AND cd.type_creneau = 'examen'
                ORDER BY cd.jour, cd.heure_debut
                LIMIT 1
            ) LOOP
                
                -- Vérifier si le groupe a déjà un examen à cette heure
                IF EXISTS (
                    SELECT 1
                    FROM gestion_examens.etudiants e
                    JOIN gestion_examens.groupes g ON e.groupe_id = g.id
                    JOIN gestion_examens.inscriptions i ON e.id = i.etudiant_id
                    JOIN gestion_examens.examens ex ON i.module_id = ex.module_id
                    WHERE g.nom = v_groupe_nom
                    AND DATE(ex.date_heure) = v_creneau.jour
                    AND ex.statut = 'planifie'
                ) THEN
                    CONTINUE;
                END IF;
                
                -- Trouver ou créer le module
                SELECT id, formation_id INTO v_module_id, v_formation_id
                FROM gestion_examens.modules 
                WHERE nom ILIKE '%' || v_module_nom || '%'
                AND formation_id IN (
                    SELECT id FROM gestion_examens.formations 
                    WHERE nom ILIKE '%' || p_niveau || '%'
                )
                LIMIT 1;
                
                IF v_module_id IS NULL THEN
                    -- Créer le module si nécessaire
                    INSERT INTO gestion_examens.modules (nom, code, credits, formation_id)
                    VALUES (
                        v_module_nom || ' - Niveau ' || p_niveau,
                        'MOD-' || p_niveau || '-' || v_module_nom,
                        4,
                        (SELECT id FROM gestion_examens.formations 
                         WHERE nom ILIKE '%' || p_niveau || '%' LIMIT 1)
                    )
                    RETURNING id, formation_id INTO v_module_id, v_formation_id;
                END IF;
                
                -- Trouver le groupe
                SELECT id INTO v_groupe_id
                FROM gestion_examens.groupes
                WHERE nom = v_groupe_nom
                OR code ILIKE '%' || v_groupe_nom || '%'
                LIMIT 1;
                
                IF v_groupe_id IS NULL THEN
                    -- Créer le groupe si nécessaire
                    INSERT INTO gestion_examens.groupes (nom, code, formation_id, niveau)
                    VALUES (
                        v_groupe_nom,
                        'GRP-' || p_niveau || '-' || v_groupe_nom,
                        v_formation_id,
                        p_niveau
                    )
                    RETURNING id INTO v_groupe_id;
                END IF;
                
                -- Nombre d'étudiants dans le groupe
                v_nb_etudiants := p_etudiants_par_groupes;
                
                -- Choisir la salle selon la capacité
                IF v_nb_etudiants <= 20 THEN
                    v_salle_type := 'salle';
                    v_capacite := 20;
                ELSIF v_nb_etudiants <= 50 THEN
                    v_salle_type := 'amphi';
                    v_capacite := 50;
                ELSE
                    v_salle_type := 'amphi';
                    v_capacite := 100;
                END IF;
                
                -- Trouver une salle disponible
                SELECT s.id INTO v_salle_id
                FROM gestion_examens.salles_examen s
                WHERE s.type = v_salle_type
                AND s.capacite >= v_nb_etudiants
                AND s.disponible = TRUE
                AND NOT EXISTS (
                    SELECT 1 FROM gestion_examens.examens ex
                    WHERE ex.salle_id = s.id
                    AND ex.date_heure = (v_creneau.jour + v_creneau.heure_debut)
                    AND ex.statut = 'planifie'
                )
                ORDER BY s.capacite - v_nb_etudiants
                LIMIT 1;
                
                IF v_salle_id IS NULL THEN
                    CONTINUE;
                END IF;
                
                -- Trouver un professeur disponible
                SELECT p.id INTO v_prof_id
                FROM gestion_examens.professeurs p
                WHERE p.dept_id = (
                    SELECT dept_id FROM gestion_examens.formations WHERE id = v_formation_id
                )
                AND p.statut = 'actif'
                AND (
                    SELECT COUNT(*)
                    FROM gestion_examens.examens ex
                    WHERE ex.professeur_responsable_id = p.id
                    AND DATE(ex.date_heure) = v_creneau.jour
                ) < p.charge_max_examens
                ORDER BY RANDOM()
                LIMIT 1;
                
                IF v_prof_id IS NULL THEN
                    CONTINUE;
                END IF;
                
                -- Créer l'examen
                INSERT INTO gestion_examens.examens (
                    module_id,
                    formation_id,
                    professeur_responsable_id,
                    salle_id,
                    date_heure,
                    duree_minutes,
                    type_examen,
                    statut
                ) VALUES (
                    v_module_id,
                    v_formation_id,
                    v_prof_id,
                    v_salle_id,
                    v_creneau.jour + v_creneau.heure_debut,
                    90,
                    'normal',
                    'planifie'
                );
                
                -- Marquer le créneau comme utilisé
                UPDATE gestion_examens.creneaux_disponibles
                SET disponible = FALSE
                WHERE id = v_creneau.id;
                
                v_examens_crees := v_examens_crees + 1;
                
                -- Sortir de la boucle des créneaux pour ce module/groupe
                EXIT;
                
            END LOOP; -- Fin boucle créneaux
            
        END LOOP; -- Fin boucle groupes
        
    END LOOP; -- Fin boucle modules
    
    RETURN v_examens_crees;
    
END;
$$;

-- ================================================
-- PROCEDURE: GENERER_EDT_MASSE
-- Génération massive d'examens pour démonstration
-- ================================================
CREATE OR REPLACE PROCEDURE generer_edt_masse()
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_examens INTEGER := 0;
    v_niveaux TEXT[] := ARRAY['L1', 'L2', 'L3', 'M1', 'M2'];
    v_modules_par_niveau INTEGER := 8;
    v_groupes_par_niveau INTEGER := 10;
    v_examens_par_jour INTEGER := 4;
    v_jours INTEGER := 15;
    v_creneaux_par_jour INTEGER := 4;
BEGIN
    -- Nettoyage
    DELETE FROM gestion_examens.examens WHERE statut = 'planifie';
    DELETE FROM gestion_examens.creneaux_disponibles;
    
    -- Créer les créneaux
    INSERT INTO gestion_examens.creneaux_disponibles (jour, heure_debut, heure_fin, type_creneau, disponible)
    SELECT 
        jour,
        heure_debut,
        heure_debut + INTERVAL '90 minutes',
        'examen',
        TRUE
    FROM (
        SELECT 
            generate_series(
                '2026-01-06'::DATE,
                '2026-01-06'::DATE + (v_jours-1),
                '1 day'
            ) as jour,
            unnest(ARRAY['08:30', '10:15', '13:30', '15:15']::TIME[]) as heure_debut
    ) t
    WHERE EXTRACT(DOW FROM jour) NOT IN (0, 6); -- Exclure weekends
    
    -- Générer les examens
    FOR i IN 1..(v_jours * v_creneaux_par_jour * 3) LOOP
        BEGIN
            PERFORM creer_examen_aleatoire();
            v_total_examens := v_total_examens + 1;
        EXCEPTION WHEN OTHERS THEN
            CONTINUE;
        END;
    END LOOP;
    
    RAISE NOTICE '✅ % examens générés avec succès', v_total_examens;
    
    -- Distribuer les surveillants
    PERFORM distribuer_surveillants_auto();
    
END;
$$;

-- ================================================
-- FUNCTION: CREER_EXAMEN_ALEATOIRE
-- ================================================
CREATE OR REPLACE FUNCTION creer_examen_aleatoire()
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_creneau RECORD;
    v_module RECORD;
    v_formation RECORD;
    v_prof RECORD;
    v_salle RECORD;
    v_groupe RECORD;
    v_date_heure TIMESTAMP;
BEGIN
    -- Trouver un créneau disponible
    SELECT * INTO v_creneau
    FROM gestion_examens.creneaux_disponibles
    WHERE disponible = TRUE
    AND type_creneau = 'examen'
    ORDER BY RANDOM()
    LIMIT 1;
    
    IF v_creneau.id IS NULL THEN
        RAISE EXCEPTION 'Aucun créneau disponible';
    END IF;
    
    v_date_heure := v_creneau.jour + v_creneau.heure_debut;
    
    -- Trouver un module aléatoire
    SELECT m.*, f.dept_id INTO v_module
    FROM gestion_examens.modules m
    JOIN gestion_examens.formations f ON m.formation_id = f.id
    ORDER BY RANDOM()
    LIMIT 1;
    
    -- Trouver un groupe pour cette formation
    SELECT * INTO v_groupe
    FROM gestion_examens.groupes
    WHERE formation_id = v_module.formation_id
    ORDER BY RANDOM()
    LIMIT 1;
    
    IF v_groupe.id IS NULL THEN
        -- Créer un groupe si nécessaire
        INSERT INTO gestion_examens.groupes (nom, code, formation_id, niveau)
        VALUES (
            'GRP-' || v_module.formation_id || '-A',
            'GRP-' || v_module.formation_id || '-A',
            v_module.formation_id,
            'L1'
        )
        RETURNING * INTO v_groupe;
    END IF;
    
    -- Nombre d'étudiants dans le groupe (15-25)
    DECLARE
        v_nb_etudiants INTEGER := 15 + (RANDOM() * 10)::INTEGER;
    BEGIN
        -- Trouver une salle appropriée
        SELECT * INTO v_salle
        FROM gestion_examens.salles_examen
        WHERE disponible = TRUE
        AND capacite >= v_nb_etudiants
        AND (
            (type = 'amphi' AND v_nb_etudiants > 20) OR
            (type != 'amphi' AND v_nb_etudiants <= 20)
        )
        AND NOT EXISTS (
            SELECT 1 FROM gestion_examens.examens ex
            WHERE ex.salle_id = salles_examen.id
            AND ex.date_heure = v_date_heure
        )
        ORDER BY RANDOM()
        LIMIT 1;
        
        IF v_salle.id IS NULL THEN
            RAISE EXCEPTION 'Aucune salle disponible';
        END IF;
        
        -- Trouver un professeur disponible
        SELECT * INTO v_prof
        FROM gestion_examens.professeurs
        WHERE dept_id = v_module.dept_id
        AND statut = 'actif'
        AND (
            SELECT COUNT(*)
            FROM gestion_examens.examens ex
            WHERE ex.professeur_responsable_id = professeurs.id
            AND DATE(ex.date_heure) = v_creneau.jour
        ) < charge_max_examens
        ORDER BY RANDOM()
        LIMIT 1;
        
        IF v_prof.id IS NULL THEN
            RAISE EXCEPTION 'Aucun professeur disponible';
        END IF;
        
        -- Créer l'examen
        INSERT INTO gestion_examens.examens (
            module_id,
            formation_id,
            professeur_responsable_id,
            salle_id,
            date_heure,
            duree_minutes,
            type_examen,
            statut
        ) VALUES (
            v_module.id,
            v_module.formation_id,
            v_prof.id,
            v_salle.id,
            v_date_heure,
            90,
            'normal',
            'planifie'
        );
        
        -- Marquer le créneau comme utilisé
        UPDATE gestion_examens.creneaux_disponibles
        SET disponible = FALSE
        WHERE id = v_creneau.id;
        
    END;
END;
$$;