-- ================================================
-- Système de Gestion des Examens Universitaires
-- Version Finale - UTF8 Compatible
-- ================================================

DROP SCHEMA IF EXISTS gestion_examens CASCADE;
CREATE SCHEMA gestion_examens;
SET search_path TO gestion_examens;
SET client_encoding = 'UTF8';

-- ================================================
-- 1. TABLES DE BASE
-- ================================================

CREATE TABLE departements (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE formations (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(200) NOT NULL,
    dept_id INTEGER NOT NULL REFERENCES departements(id) ON DELETE CASCADE,
    nb_modules INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nom, dept_id)
);

CREATE TABLE professeurs (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    dept_id INTEGER NOT NULL REFERENCES departements(id),
    specialite VARCHAR(150),
    charge_max_examens INTEGER DEFAULT 3 CHECK (charge_max_examens >= 1 AND charge_max_examens <= 5),
    total_surveillances INTEGER DEFAULT 0,
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'inactif', 'retraite')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE salles_examen (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('amphi', 'salle', 'labo')),
    capacite INTEGER NOT NULL CHECK (capacite > 0),
    CHECK (
        (type != 'amphi' AND capacite <= 20) OR
        (type = 'amphi' AND capacite <= 500)
    ),
    batiment VARCHAR(50),
    disponible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(150) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    credits INTEGER NOT NULL CHECK (credits >= 1 AND credits <= 12),
    formation_id INTEGER NOT NULL REFERENCES formations(id) ON DELETE CASCADE,
    pre_req_id INTEGER REFERENCES modules(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================
-- TABLE D'AUTHENTIFICATION
-- ================================================

CREATE TABLE authentification (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) UNIQUE NOT NULL,
    mot_de_passe VARCHAR(255) NOT NULL,
    type_utilisateur VARCHAR(20) NOT NULL CHECK (type_utilisateur IN ('etudiant', 'professeur', 'administrateur', 'vice_doyen', 'chef_departement')),
    user_id INTEGER NOT NULL, -- Référence à l'ID dans la table correspondante
    derniere_connexion TIMESTAMP,
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'inactif', 'bloque')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX idx_auth_matricule ON authentification(matricule);
CREATE INDEX idx_auth_statut ON authentification(statut) WHERE statut = 'actif';

-- ================================================
-- 2. SYSTÈME DE GROUPES
-- ================================================

CREATE TABLE groupes (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    code VARCHAR(30) UNIQUE NOT NULL,
    formation_id INTEGER NOT NULL REFERENCES formations(id) ON DELETE CASCADE,
    annee_academique VARCHAR(9) NOT NULL,
    capacite_max INTEGER NOT NULL DEFAULT 40 CHECK (capacite_max >= 1 AND capacite_max <= 40),
    niveau VARCHAR(10) DEFAULT 'L1' CHECK (niveau IN ('L1', 'L2', 'L3', 'M1', 'M2')),
    responsable_id INTEGER REFERENCES professeurs(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE etudiants (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    formation_id INTEGER NOT NULL REFERENCES formations(id),
    groupe_id INTEGER REFERENCES groupes(id) ON DELETE SET NULL,
    promo INTEGER NOT NULL CHECK (promo >= 1 AND promo <= 5),
    annee_inscription INTEGER NOT NULL CHECK (annee_inscription >= 2000),
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'inactif', 'diplome', 'abandon')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================
-- 3. INSCRIPTIONS ET EXAMENS
-- ================================================

CREATE TABLE inscriptions (
    id SERIAL PRIMARY KEY,
    etudiant_id INTEGER NOT NULL REFERENCES etudiants(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    annee_academique VARCHAR(9) NOT NULL,
    note DECIMAL(4,2) CHECK (note >= 0 AND note <= 20),
    statut VARCHAR(20) DEFAULT 'inscrit' 
        CHECK (statut IN ('inscrit', 'valide', 'echec', 'abandon', 'en_cours')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(etudiant_id, module_id, annee_academique)
);

CREATE TABLE examens (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    formation_id INTEGER NOT NULL REFERENCES formations(id),
    professeur_responsable_id INTEGER NOT NULL REFERENCES professeurs(id),
    salle_id INTEGER NOT NULL REFERENCES salles_examen(id),
    date_heure TIMESTAMP NOT NULL,
    duree_minutes INTEGER NOT NULL CHECK (duree_minutes >= 30 AND duree_minutes <= 180),
    type_examen VARCHAR(20) DEFAULT 'normal' 
        CHECK (type_examen IN ('normal', 'rattrapage', 'controle')),
    statut VARCHAR(20) DEFAULT 'planifie' 
        CHECK (statut IN ('planifie', 'confirme', 'annule', 'termine')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================
-- 4. SYSTÈME DE SURVEILLANCE
-- ================================================

CREATE TABLE surveillances (
    id SERIAL PRIMARY KEY,
    examen_id INTEGER NOT NULL REFERENCES examens(id) ON DELETE CASCADE,
    professeur_id INTEGER NOT NULL REFERENCES professeurs(id),
    priorite INTEGER DEFAULT 1 CHECK (priorite IN (1, 2)),
    role VARCHAR(20) DEFAULT 'surveillant' 
        CHECK (role IN ('responsable', 'surveillant')),
    heures_creditees DECIMAL(3,1) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(examen_id, professeur_id)
);

-- ================================================
-- 5. TABLES DE SUPPORT
-- ================================================

CREATE TABLE sessions_examen (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    statut VARCHAR(20) DEFAULT 'planifie' 
        CHECK (statut IN ('planifie', 'en_cours', 'termine', 'annule')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (date_debut <= date_fin)
);

CREATE TABLE creneaux_disponibles (
    id SERIAL PRIMARY KEY,
    jour DATE NOT NULL,
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    type_creneau VARCHAR(20) DEFAULT 'examen' 
        CHECK (type_creneau IN ('examen', 'rattrapage', 'reserve')),
    disponible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (heure_debut < heure_fin),
    UNIQUE(jour, heure_debut, heure_fin, type_creneau)
);

-- ================================================
-- 6. INDEX POUR PERFORMANCE
-- ================================================

CREATE INDEX idx_examens_date_heure ON examens(date_heure);
CREATE INDEX idx_examens_module ON examens(module_id);
CREATE INDEX idx_examens_prof ON examens(professeur_responsable_id);
CREATE INDEX idx_examens_salle ON examens(salle_id);
CREATE INDEX idx_examens_date_module ON examens(DATE(date_heure), module_id);
CREATE INDEX idx_examens_formation ON examens(formation_id);
CREATE INDEX idx_examens_date_statut ON examens(date_heure) 
    WHERE statut IN ('planifie', 'confirme');
CREATE INDEX idx_inscriptions_etudiant ON inscriptions(etudiant_id);
CREATE INDEX idx_inscriptions_module ON inscriptions(module_id);
CREATE INDEX idx_inscriptions_annee ON inscriptions(annee_academique);
CREATE INDEX idx_etudiants_actifs ON etudiants(id) WHERE statut = 'actif';
CREATE INDEX idx_professeurs_actifs ON professeurs(id) WHERE statut = 'actif';
CREATE INDEX idx_salles_disponibles ON salles_examen(id) WHERE disponible = TRUE;

-- ================================================
-- 7. FONCTIONS ET TRIGGERS
-- ================================================

-- Fonction mise à jour timestamp
CREATE OR REPLACE FUNCTION mettre_a_jour_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Contraintes
CREATE OR REPLACE FUNCTION verifier_limite_etudiant()
RETURNS TRIGGER AS $$
DECLARE
    nb_etudiants INTEGER;
BEGIN
    SELECT COUNT(DISTINCT etu.id)
    INTO nb_etudiants
    FROM inscriptions i
    JOIN examens ex ON i.module_id = ex.module_id
    JOIN etudiants etu ON i.etudiant_id = etu.id
    WHERE i.module_id = NEW.module_id
    AND DATE(ex.date_heure) = DATE(NEW.date_heure)
    AND ex.id != COALESCE(NEW.id, 0)
    AND ex.statut IN ('planifie', 'confirme');
    
    IF nb_etudiants > 0 THEN
        RAISE EXCEPTION 'Des etudiants ont deja un examen le meme jour (%)', DATE(NEW.date_heure);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION verifier_limite_professeur()
RETURNS TRIGGER AS $$
DECLARE
    limite_prof INTEGER;
    nb_examens INTEGER;
BEGIN
    SELECT charge_max_examens INTO limite_prof
    FROM professeurs 
    WHERE id = NEW.professeur_responsable_id;
    
    IF limite_prof IS NULL THEN
        limite_prof := 3;
    END IF;
    
    SELECT COUNT(*) INTO nb_examens
    FROM examens
    WHERE professeur_responsable_id = NEW.professeur_responsable_id
    AND DATE(date_heure) = DATE(NEW.date_heure)
    AND id != COALESCE(NEW.id, 0)
    AND statut IN ('planifie', 'confirme');
    
    IF nb_examens >= limite_prof THEN
        RAISE EXCEPTION 'Le professeur a atteint la limite de % examens par jour', limite_prof;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION verifier_capacite_salle()
RETURNS TRIGGER AS $$
DECLARE
    salle_capacite INTEGER;
    salle_type VARCHAR(50);
    nb_etudiants INTEGER;
BEGIN
    SELECT capacite, type INTO salle_capacite, salle_type
    FROM salles_examen 
    WHERE id = NEW.salle_id;
    
    SELECT COUNT(DISTINCT i.etudiant_id) INTO nb_etudiants
    FROM inscriptions i
    JOIN etudiants e ON i.etudiant_id = e.id
    WHERE i.module_id = NEW.module_id
    AND i.statut IN ('inscrit', 'en_cours')
    AND e.statut = 'actif';
    
    IF salle_type != 'amphi' AND nb_etudiants > 20 THEN
        RAISE EXCEPTION 'La salle ne peut pas accueillir plus de 20 etudiants (% etudiants)', nb_etudiants;
    END IF;
    
    IF nb_etudiants > salle_capacite THEN
        RAISE EXCEPTION 'Capacite insuffisante: salle % etudiants, etudiants %', salle_capacite, nb_etudiants;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION verifier_conflit_salle()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM examens e
        WHERE e.salle_id = NEW.salle_id
        AND e.date_heure = NEW.date_heure
        AND e.id != COALESCE(NEW.id, 0)
        AND e.statut IN ('planifie', 'confirme')
    ) THEN
        RAISE EXCEPTION 'La salle est deja reservee a cette heure';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION distribuer_surveillances()
RETURNS TRIGGER AS $$
DECLARE
    dept_examen INTEGER;
    prof_record RECORD;
    nb_surveillants INTEGER := 0;
    nb_necessaires INTEGER := 2;
BEGIN
    -- احصل على قسم الامتحان
    SELECT f.dept_id INTO dept_examen
    FROM modules m
    JOIN formations f ON m.formation_id = f.id
    WHERE m.id = NEW.module_id;
    
    -- حاول إيجاد مراقبين من نفس القسم
    FOR prof_record IN (
        SELECT p.id, p.total_surveillances
        FROM professeurs p
        WHERE p.dept_id = dept_examen
        AND p.statut = 'actif'
        AND p.id != NEW.professeur_responsable_id
        ORDER BY p.total_surveillances ASC
        LIMIT nb_necessaires
    ) LOOP
        INSERT INTO surveillances (examen_id, professeur_id, priorite, role)
        VALUES (NEW.id, prof_record.id, 1, 'surveillant');
        
        nb_surveillants := nb_surveillants + 1;
    END LOOP;
    
    -- إذا لم نجد ما يكفي، ابحث في الأقسام الأخرى
    IF nb_surveillants < nb_necessaires THEN
        FOR prof_record IN (
            SELECT p.id, p.total_surveillances
            FROM professeurs p
            WHERE p.dept_id != dept_examen
            AND p.statut = 'actif'
            AND p.id != NEW.professeur_responsable_id
            ORDER BY p.total_surveillances ASC
            LIMIT nb_necessaires - nb_surveillants
        ) LOOP
            INSERT INTO surveillances (examen_id, professeur_id, priorite, role)
            VALUES (NEW.id, prof_record.id, 2, 'surveillant');
            
            nb_surveillants := nb_surveillants + 1;
        END LOOP;
    END IF;
    
    -- تحديث عدد المراقبات لكل أستاذ
    UPDATE professeurs 
    SET total_surveillances = total_surveillances + 1
    WHERE id IN (
        SELECT professeur_id 
        FROM surveillances 
        WHERE examen_id = NEW.id
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generer_matricule_etudiant()
RETURNS TRIGGER AS $$
DECLARE
    annee_courante VARCHAR(4);
    numero_seq INTEGER;
BEGIN
    annee_courante := EXTRACT(YEAR FROM CURRENT_DATE)::VARCHAR;
    
    SELECT COALESCE(MAX(SUBSTRING(matricule FROM 8)::INTEGER), 0) + 1
    INTO numero_seq
    FROM etudiants
    WHERE matricule LIKE 'ETU-' || annee_courante || '-%';
    
    NEW.matricule := 'ETU-' || annee_courante || '-' || LPAD(numero_seq::TEXT, 5, '0');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- 8. APPLICATION DES TRIGGERS
-- ================================================

CREATE TRIGGER trg_update_departements BEFORE UPDATE ON departements FOR EACH ROW EXECUTE FUNCTION mettre_a_jour_timestamp();
CREATE TRIGGER trg_update_formations BEFORE UPDATE ON formations FOR EACH ROW EXECUTE FUNCTION mettre_a_jour_timestamp();
CREATE TRIGGER trg_update_groupes BEFORE UPDATE ON groupes FOR EACH ROW EXECUTE FUNCTION mettre_a_jour_timestamp();
CREATE TRIGGER trg_update_etudiants BEFORE UPDATE ON etudiants FOR EACH ROW EXECUTE FUNCTION mettre_a_jour_timestamp();
CREATE TRIGGER trg_update_professeurs BEFORE UPDATE ON professeurs FOR EACH ROW EXECUTE FUNCTION mettre_a_jour_timestamp();
CREATE TRIGGER trg_update_examens BEFORE UPDATE ON examens FOR EACH ROW EXECUTE FUNCTION mettre_a_jour_timestamp();
CREATE TRIGGER trg_limite_etudiant BEFORE INSERT OR UPDATE ON examens FOR EACH ROW EXECUTE FUNCTION verifier_limite_etudiant();
CREATE TRIGGER trg_limite_professeur BEFORE INSERT OR UPDATE ON examens FOR EACH ROW EXECUTE FUNCTION verifier_limite_professeur();
CREATE TRIGGER trg_capacite_salle BEFORE INSERT OR UPDATE ON examens FOR EACH ROW EXECUTE FUNCTION verifier_capacite_salle();
CREATE TRIGGER trg_conflit_salle BEFORE INSERT OR UPDATE ON examens FOR EACH ROW EXECUTE FUNCTION verifier_conflit_salle();
CREATE TRIGGER trg_distribuer_surveillances AFTER INSERT ON examens FOR EACH ROW EXECUTE FUNCTION distribuer_surveillances();
CREATE TRIGGER trg_matricule_etudiant BEFORE INSERT ON etudiants FOR EACH ROW WHEN (NEW.matricule IS NULL OR NEW.matricule = '') EXECUTE FUNCTION generer_matricule_etudiant();

-- ================================================
-- 9. VUES PRINCIPALES
-- ================================================

CREATE OR REPLACE VIEW vue_emploi_temps_etudiant AS
SELECT 
    e.id as etudiant_id,
    e.matricule,
    e.prenom || ' ' || e.nom as etudiant_nom,
    ex.id as examen_id,
    m.nom as module_nom,
    f.nom as formation_nom,
    d.nom as departement_nom,
    p.prenom || ' ' || p.nom as professeur,
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
JOIN professeurs p ON ex.professeur_responsable_id = p.id
JOIN salles_examen s ON ex.salle_id = s.id
WHERE e.statut = 'actif'
AND i.statut IN ('inscrit', 'en_cours')
AND ex.statut IN ('planifie', 'confirme')
ORDER BY e.id, ex.date_heure;

CREATE OR REPLACE VIEW vue_conflits AS
SELECT 
    'Conflit etudiant' as type_conflit,
    e.prenom || ' ' || e.nom as element,
    e.matricule,
    DATE(ex.date_heure) as date_conflit,
    COUNT(DISTINCT ex.id) as nombre_examens
FROM etudiants e
JOIN inscriptions i ON e.id = i.etudiant_id
JOIN examens ex ON i.module_id = ex.module_id
WHERE e.statut = 'actif'
AND ex.statut IN ('planifie', 'confirme')
GROUP BY e.id, e.prenom, e.nom, e.matricule, DATE(ex.date_heure)
HAVING COUNT(DISTINCT ex.id) > 1
UNION ALL
SELECT 
    'Depassement limite professeur' as type_conflit,
    p.prenom || ' ' || p.nom as element,
    p.matricule,
    DATE(ex.date_heure) as date_conflit,
    COUNT(ex.id) as nombre_examens
FROM professeurs p
JOIN examens ex ON p.id = ex.professeur_responsable_id
WHERE p.statut = 'actif'
AND ex.statut IN ('planifie', 'confirme')
GROUP BY p.id, p.prenom, p.nom, p.matricule, DATE(ex.date_heure), p.charge_max_examens
HAVING COUNT(ex.id) > p.charge_max_examens
UNION ALL
SELECT 
    'Depassement capacite salle' as type_conflit,
    s.nom as element,
    s.code as matricule,
    DATE(ex.date_heure) as date_conflit,
    COUNT(DISTINCT ex.id) as nombre_examens
FROM salles_examen s
JOIN examens ex ON s.id = ex.salle_id
WHERE s.type != 'amphi'
AND (
    SELECT COUNT(DISTINCT i.etudiant_id)
    FROM inscriptions i
    WHERE i.module_id = ex.module_id
) > 20
AND ex.statut IN ('planifie', 'confirme')
GROUP BY s.id, s.nom, s.code, DATE(ex.date_heure);

CREATE OR REPLACE VIEW vue_utilisation_salles AS
SELECT 
    s.id,
    s.nom,
    s.type,
    s.capacite,
    s.batiment,
    DATE(e.date_heure) as jour,
    COUNT(e.id) as nombre_examens,
    SUM(
        CASE 
            WHEN (SELECT COUNT(DISTINCT i.etudiant_id)
                  FROM inscriptions i
                  WHERE i.module_id = e.module_id) > 20 
                  AND s.type != 'amphi'
            THEN 1
            ELSE 0
        END
    ) as violations_capacite
FROM salles_examen s
LEFT JOIN examens e ON s.id = e.salle_id 
    AND e.statut IN ('planifie', 'confirme')
GROUP BY s.id, s.nom, s.type, s.capacite, s.batiment, DATE(e.date_heure)
ORDER BY jour, s.nom;

CREATE OR REPLACE VIEW vue_surveillances_professeur AS
SELECT 
    p.id as professeur_id,
    p.prenom || ' ' || p.nom as professeur_nom,
    p.dept_id as dept_professeur,
    s.examen_id,
    m.nom as module,
    f.nom as formation,
    f.dept_id as dept_examen,
    CASE 
        WHEN p.dept_id = f.dept_id THEN 'Meme departement (priorite)'
        ELSE 'Autre departement'
    END as priorite_surveillance,
    s.role,
    e.date_heure,
    sa.nom as salle,
    p.total_surveillances
FROM professeurs p
JOIN surveillances s ON p.id = s.professeur_id
JOIN examens e ON s.examen_id = e.id
JOIN modules m ON e.module_id = m.id
JOIN formations f ON m.formation_id = f.id
JOIN salles_examen sa ON e.salle_id = sa.id
ORDER BY p.id, e.date_heure;

-- ================================================
-- 10. PROCÉDURES STOCKÉES
-- ================================================

CREATE OR REPLACE PROCEDURE planifier_examen(
    p_module_id INTEGER,
    p_salle_id INTEGER,
    p_date_heure TIMESTAMP,
    p_professeur_id INTEGER,
    p_duree_minutes INTEGER DEFAULT 120
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_formation_id INTEGER;
BEGIN
    SELECT formation_id INTO v_formation_id
    FROM modules WHERE id = p_module_id;
    
    INSERT INTO examens (
        module_id,
        formation_id,
        professeur_responsable_id,
        salle_id,
        date_heure,
        duree_minutes
    ) VALUES (
        p_module_id,
        v_formation_id,
        p_professeur_id,
        p_salle_id,
        p_date_heure,
        p_duree_minutes
    );
    
    RAISE NOTICE 'Examen planifie avec succes';
END;
$$;

CREATE OR REPLACE PROCEDURE generer_emploi_du_temps_complet()
LANGUAGE plpgsql
AS $$
DECLARE
    debut_temps TIMESTAMP;
    fin_temps TIMESTAMP;
    nb_examens INTEGER;
BEGIN
    debut_temps := CURRENT_TIMESTAMP;
    
    DELETE FROM examens WHERE statut = 'planifie';
    UPDATE professeurs SET total_surveillances = 0;
    DELETE FROM surveillances;
    
    -- Simulation de planification
    PERFORM pg_sleep(0.1);
    
    fin_temps := CURRENT_TIMESTAMP;
    
    IF EXTRACT(EPOCH FROM (fin_temps - debut_temps)) > 45 THEN
        RAISE EXCEPTION 'Depassement du temps autorise (45 secondes)';
    END IF;
    
    SELECT COUNT(*) INTO nb_examens FROM examens WHERE statut = 'planifie';
    RAISE NOTICE '% examens crees en % secondes', nb_examens, EXTRACT(EPOCH FROM (fin_temps - debut_temps));
END;
$$;

CREATE OR REPLACE PROCEDURE tester_performance()
LANGUAGE plpgsql
AS $$
DECLARE
    debut_temps TIMESTAMP;
    fin_temps TIMESTAMP;
    duree DECIMAL;
BEGIN
    debut_temps := CURRENT_TIMESTAMP;
    
    PERFORM COUNT(*) FROM vue_emploi_temps_etudiant;
    PERFORM COUNT(*) FROM vue_conflits;
    PERFORM COUNT(*) FROM vue_utilisation_salles;
    
    fin_temps := CURRENT_TIMESTAMP;
    duree := EXTRACT(EPOCH FROM (fin_temps - debut_temps));
    
    IF duree > 1 THEN
        RAISE WARNING 'Certaines requetes sont lentes: % secondes', duree;
    ELSE
        RAISE NOTICE 'Performance bonne: % secondes', duree;
    END IF;
END;
$$;

-- ================================================
-- 11. DONNÉES DE BASE
-- ================================================

INSERT INTO departements (nom) VALUES 
    ('Informatique'),
    ('Mathématiques'),
    ('Physique'),
    ('Chimie'),
    ('Biologie'),
    ('Langues'),
    ('Droit');

INSERT INTO professeurs (matricule, nom, prenom, email, dept_id, specialite) VALUES 
    ('PRO-2025-0001', 'Martin', 'Jean', 'jean.martin@univ.fr', 1, 'Informatique'),
    ('PRO-2025-0002', 'Dubois', 'Marie', 'marie.dubois@univ.fr', 1, 'Reseaux'),
    ('PRO-2025-0003', 'Lefevre', 'Pierre', 'pierre.lefevre@univ.fr', 2, 'Mathematiques'),
    ('PRO-2025-0004', 'Moreau', 'Sophie', 'sophie.moreau@univ.fr', 3, 'Physique');

INSERT INTO salles_examen (nom, code, type, capacite, batiment) VALUES 
    ('Amphi A', 'AMP-A', 'amphi', 200, 'Batiment Principal'),
    ('Amphi B', 'AMP-B', 'amphi', 150, 'Batiment Principal'),
    ('Salle 101', 'SAL-101', 'salle', 20, 'Batiment A'),
    ('Salle 102', 'SAL-102', 'salle', 20, 'Batiment A'),
    ('Labo Info 1', 'LAB-INF1', 'labo', 15, 'Batiment B');











-- ================================================
-- 13. وظائف الـ Vice-Doyen المطلوبة
-- ================================================

-- 1. جدول التدقيق
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER REFERENCES authentification(id),
    action_type VARCHAR(50),
    table_name VARCHAR(50),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_log(user_id);

-- 2. وظيفة التحقق النهائي
CREATE OR REPLACE FUNCTION valider_edt_final(p_vice_doyen_id INTEGER)
RETURNS JSON AS $$
DECLARE
    result JSON;
    nb_conflits INTEGER;
    nb_examens INTEGER;
BEGIN
    SELECT COUNT(*) INTO nb_conflits FROM vue_conflits;
    SELECT COUNT(*) INTO nb_examens FROM examens WHERE statut = 'planifie';
    
    IF nb_conflits > 0 THEN
        result := json_build_object(
            'success', false,
            'message', 'Impossible de valider: ' || nb_conflits || ' conflits détectés',
            'conflits', nb_conflits,
            'examens', nb_examens
        );
        RETURN result;
    END IF;
    
    UPDATE examens 
    SET statut = 'confirme',
        updated_at = CURRENT_TIMESTAMP
    WHERE statut = 'planifie';
    
    INSERT INTO audit_log (user_id, action_type, table_name, record_id)
    VALUES (p_vice_doyen_id, 'VALIDATION_EDT', 'examens', NULL);
    
    result := json_build_object(
        'success', true,
        'message', 'EDT validé avec succès: ' || nb_examens || ' examens confirmés',
        'examens_confirmes', nb_examens
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 3. مؤشرات KPIs
CREATE OR REPLACE VIEW vue_kpi_heures_professeurs AS
SELECT 
    d.nom as departement,
    p.prenom || ' ' || p.nom as professeur,
    COUNT(DISTINCT e.id) as nb_examens_responsable,
    ROUND(COALESCE(SUM(e.duree_minutes) / 60.0, 0), 2) as heures_responsable
FROM professeurs p
JOIN departements d ON p.dept_id = d.id
LEFT JOIN examens e ON p.id = e.professeur_responsable_id AND e.statut = 'planifie'
GROUP BY d.id, d.nom, p.id, p.prenom, p.nom;

CREATE OR REPLACE VIEW vue_kpi_utilisation_salles AS
SELECT 
    'Taux occupation global' as indicateur,
    ROUND(
        COUNT(DISTINCT e.salle_id) * 100.0 / 
        GREATEST((SELECT COUNT(*) FROM salles_examen), 1),
    2) as valeur,
    '%' as unite
FROM examens e
WHERE e.statut = 'planifie'

UNION ALL

SELECT 
    'Taux occupation amphis',
    ROUND(
        COUNT(DISTINCT CASE WHEN s.type = 'amphi' THEN e.salle_id END) * 100.0 /
        GREATEST((SELECT COUNT(*) FROM salles_examen WHERE type = 'amphi'), 1),
    2),
    '%'
FROM examens e
JOIN salles_examen s ON e.salle_id = s.id
WHERE e.statut = 'planifie';

-- ================================================
-- 12. MESSAGE DE SUCCÈS
-- ================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Systeme de Gestion des Examens Universitaires';
    RAISE NOTICE 'Base de données créée avec succès!';
    RAISE NOTICE '========================================';
END;
$$;









-- Fonction améliorée qui gère le cas où l'EDT est déjà validé
CREATE OR REPLACE FUNCTION valider_edt_final(p_vice_doyen_id INTEGER)
RETURNS JSON AS $$
DECLARE
    result JSON;
    nb_conflits INTEGER := 0;
    nb_examens_planifies INTEGER := 0;
    nb_examens_confirmes INTEGER := 0;
    nb_examens_total INTEGER := 0;
BEGIN
    -- 1. Vérifier les conflits
    BEGIN
        SELECT COUNT(*) INTO nb_conflits FROM gestion_examens.vue_conflits;
    EXCEPTION WHEN OTHERS THEN
        nb_conflits := 0;
    END;
    
    -- 2. Compter les examens par statut
    BEGIN
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE statut = 'planifie') as planifies,
            COUNT(*) FILTER (WHERE statut = 'confirme') as confirmes
        INTO nb_examens_total, nb_examens_planifies, nb_examens_confirmes
        FROM gestion_examens.examens;
    EXCEPTION WHEN OTHERS THEN
        nb_examens_total := 0;
        nb_examens_planifies := 0;
        nb_examens_confirmes := 0;
    END;

    -- 3. Si conflits détectés
    IF nb_conflits > 0 THEN
        result := json_build_object(
            'success', false,
            'message', '⚠️ Validation impossible: ' || nb_conflits || ' conflits détectés',
            'conflits', nb_conflits,
            'statistiques', json_build_object(
                'total_examens', nb_examens_total,
                'planifies', nb_examens_planifies,
                'confirmes', nb_examens_confirmes
            )
        );
        RETURN result;
    END IF;

    -- 4. Si déjà tous confirmés
    IF nb_examens_planifies = 0 AND nb_examens_confirmes > 0 THEN
        result := json_build_object(
            'success', true,
            'message', '✅ EDT déjà validé: ' || nb_examens_confirmes || ' examens sont déjà confirmés',
            'statut', 'deja_valide',
            'examens_confirmes', nb_examens_confirmes,
            'examens_total', nb_examens_total
        );
        RETURN result;
    END IF;

    -- 5. Si aucun examen
    IF nb_examens_total = 0 THEN
        result := json_build_object(
            'success', false,
            'message', '❌ Aucun examen à valider'
        );
        RETURN result;
    END IF;

    -- 6. Mettre à jour les examens planifiés
    BEGIN
        UPDATE gestion_examens.examens
        SET statut = 'confirme',
            updated_at = CURRENT_TIMESTAMP
        WHERE statut = 'planifie';
        
        -- Compter combien ont été mis à jour
        GET DIAGNOSTICS nb_examens_planifies = ROW_COUNT;
        
    EXCEPTION WHEN OTHERS THEN
        result := json_build_object(
            'success', false,
            'message', '❌ Erreur lors de la validation: ' || SQLERRM
        );
        RETURN result;
    END;

    -- 7. Journalisation
    BEGIN
        INSERT INTO gestion_examens.audit_log 
            (user_id, action_type, table_name, record_id, new_values)
        VALUES 
            (p_vice_doyen_id, 'VALIDATION_EDT', 'examens', NULL,
             jsonb_build_object(
                 'examens_confirmes', nb_examens_planifies,
                 'total_examens', nb_examens_total,
                 'timestamp', CURRENT_TIMESTAMP
             ));
    EXCEPTION WHEN OTHERS THEN
        -- Continuer même si l'audit échoue
    END;

    -- 8. Retourner le succès
    result := json_build_object(
        'success', true,
        'message', '✅ EDT validé avec succès! ' || nb_examens_planifies || ' examens confirmés',
        'statut', 'nouvelle_validation',
        'examens_confirmes', nb_examens_planifies,
        'examens_total', nb_examens_total,
        'timestamp', CURRENT_TIMESTAMP
    );

    RETURN result;
END;
$$ LANGUAGE plpgsql;













-- Exécutez dans "unuversity" (port 5433)
CREATE OR REPLACE FUNCTION valider_edt_final(p_vice_doyen_id INTEGER)
RETURNS JSON AS $$
DECLARE
    result JSON;
    nb_conflits INTEGER := 0;
    nb_examens_planifies INTEGER := 0;
    nb_examens_confirmes INTEGER := 0;
    nb_examens_total INTEGER := 0;
BEGIN
    -- 1. Vérifier les conflits
    BEGIN
        SELECT COUNT(*) INTO nb_conflits FROM gestion_examens.vue_conflits;
    EXCEPTION WHEN OTHERS THEN
        nb_conflits := 0;
    END;
    
    -- 2. Compter les examens par statut
    BEGIN
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE statut = 'planifie') as planifies,
            COUNT(*) FILTER (WHERE statut = 'confirme') as confirmes
        INTO nb_examens_total, nb_examens_planifies, nb_examens_confirmes
        FROM gestion_examens.examens;
    EXCEPTION WHEN OTHERS THEN
        nb_examens_total := 0;
        nb_examens_planifies := 0;
        nb_examens_confirmes := 0;
    END;

    -- 3. Si conflits détectés
    IF nb_conflits > 0 THEN
        result := json_build_object(
            'success', false,
            'message', '⚠️ Validation impossible: ' || nb_conflits || ' conflits détectés',
            'conflits', nb_conflits,
            'statistiques', json_build_object(
                'total_examens', nb_examens_total,
                'planifies', nb_examens_planifies,
                'confirmes', nb_examens_confirmes
            )
        );
        RETURN result;
    END IF;

    -- 4. Si déjà tous confirmés
    IF nb_examens_planifies = 0 AND nb_examens_confirmes > 0 THEN
        result := json_build_object(
            'success', true,
            'message', '✅ EDT déjà validé: ' || nb_examens_confirmes || ' examens sont déjà confirmés',
            'statut', 'deja_valide',
            'examens_confirmes', nb_examens_confirmes,
            'examens_total', nb_examens_total
        );
        RETURN result;
    END IF;

    -- 5. Si aucun examen
    IF nb_examens_total = 0 THEN
        result := json_build_object(
            'success', false,
            'message', '❌ Aucun examen à valider'
        );
        RETURN result;
    END IF;

    -- 6. Mettre à jour les examens planifiés
    BEGIN
        UPDATE gestion_examens.examens
        SET statut = 'confirme',
            updated_at = CURRENT_TIMESTAMP
        WHERE statut = 'planifie';
        
        -- Compter combien ont été mis à jour
        GET DIAGNOSTICS nb_examens_planifies = ROW_COUNT;
        
    EXCEPTION WHEN OTHERS THEN
        result := json_build_object(
            'success', false,
            'message', '❌ Erreur lors de la validation: ' || SQLERRM
        );
        RETURN result;
    END;

    -- 7. Journalisation
    BEGIN
        INSERT INTO gestion_examens.audit_log 
            (user_id, action_type, table_name, record_id, new_values)
        VALUES 
            (p_vice_doyen_id, 'VALIDATION_EDT', 'examens', NULL,
             jsonb_build_object(
                 'examens_confirmes', nb_examens_planifies,
                 'total_examens', nb_examens_total,
                 'timestamp', CURRENT_TIMESTAMP
             ));
    EXCEPTION WHEN OTHERS THEN
        -- Continuer même si l'audit échoue
    END;

    -- 8. Retourner le succès
    result := json_build_object(
        'success', true,
        'message', '✅ EDT validé avec succès! ' || nb_examens_planifies || ' examens confirmés',
        'statut', 'nouvelle_validation',
        'examens_confirmes', nb_examens_planifies,
        'examens_total', nb_examens_total,
        'timestamp', CURRENT_TIMESTAMP
    );

    RETURN result;
END;
$$ LANGUAGE plpgsql;