ALTER TABLE prompt 
    ALTER COLUMN prompt_list_id DROP NOT NULL,
    ALTER COLUMN prompt_list_id SET DEFAULT NULL;
