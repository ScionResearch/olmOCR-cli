-- Initialize PostgreSQL database for OCR jobs
-- This file is automatically executed when the postgres container starts

-- Create the database (already created by POSTGRES_DB env var, but include for completeness)
-- CREATE DATABASE ocr_db;

-- Grant all privileges to the OCR user (already granted by default, but explicit)
GRANT ALL PRIVILEGES ON DATABASE ocr_db TO ocr_user;

-- Create any additional indexes or configurations if needed
-- Tables will be created automatically by SQLAlchemy/Alembic