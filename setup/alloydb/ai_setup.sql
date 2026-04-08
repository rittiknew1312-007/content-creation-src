CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;

GRANT EXECUTE ON FUNCTION embedding TO postgres;

-- Optional: only run this block if you want in-database Gemini model registration.
-- Replace YOUR_PROJECT_ID before executing.
--
-- CALL google_ml.create_model(
--   model_id => 'gemini-3-flash-preview',
--   model_request_url => 'https://aiplatform.googleapis.com/v1/projects/YOUR_PROJECT_ID/locations/global/publishers/google/models/gemini-3-flash-preview:generateContent',
--   model_qualified_name => 'gemini-3-flash-preview',
--   model_provider => 'google',
--   model_type => 'llm',
--   model_auth_type => 'alloydb_service_agent_iam'
-- );
