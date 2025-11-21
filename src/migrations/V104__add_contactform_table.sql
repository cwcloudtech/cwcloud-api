CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE contact_form (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name VARCHAR(254) NOT NULL,
    hash VARCHAR(10),
    mail_from VARCHAR(254) NOT NULL,
    mail_to VARCHAR(254) NOT NULL,
    copyright_name VARCHAR(254),
    logo_url VARCHAR(254)
);
