-- Run this DDL command once in BigQuery to create the index.
-- Replace project_id, dataset_name, and table_name if they differ from config.
-- Ensure the distance_type matches the 'distance_measure' in your config.yaml.
-- Index creation can take some time depending on the table size.
-- This will only work if you have more than 5000 rows in the table. 
-- For less than 500 rows, Use VECTOR_SEARCH table-valued function directly to perform the similarity search.

CREATE VECTOR INDEX IF NOT EXISTS media_embedding_index -- Choose an index name
ON `your_project_id.trading_platform_data.media_embeddings`(embedding) -- Target table and column
OPTIONS(index_type = 'IVF', distance_type = 'COSINE'); -- Or EUCLIDEAN, DOT_PRODUCT

-- index_type='IVF' is common, but check BQ docs for other options like 'TREE_AH' (Preview)
-- distance_type must match what you intend to use in VECTOR_SEARCH
