-- generate_synthetic_data.sql
-- BigQuery ML Generator for Data Gravity Demo
-- 1. Setup DDL: Create Connection
-- We use a dedicated connection in the 'us-central1' region.
-- IMPORTANT: The service account created by this connection needs 'roles/aiplatform.user'.
-- 2. Setup DDL: Create Model
CREATE OR REPLACE MODEL `tuning_2k.gemini_simulator`
REMOTE WITH CONNECTION `us.vertex_ai_conn_us`
OPTIONS (
  endpoint = 'projects/YOUR_PROJECT_ID/locations/global/publishers/google/models/gemini-3-flash-preview'
);

-- 2. Create Downstream Tables
CREATE OR REPLACE TABLE `tuning_2k.cpt_data` (
  id STRING,
  category STRING,
  theme STRING,
  initial_description STRING,
  raw_artifact STRING,
  investigation_notes STRING,
  remediation_steps STRING,
  q_and_a_pairs JSON
);

CREATE OR REPLACE TABLE `tuning_2k.sft_data` (
  cpt_id STRING,
  messages JSON
);

CREATE OR REPLACE TABLE `tuning_2k.lora_data` (
  cpt_id STRING,
  messages JSON
);

-- Uncomment to reset the entire dataset completely:
-- TRUNCATE TABLE `tuning_2k.cpt_data`;

-- ==============================================================================
-- STEP 0: SEED CONTEXTS (NATIVE BIGQUERY ML)
-- Generates abstract UUID scenarios natively without Python.
-- ==============================================================================

-- 0.1: Instantiate 30,000 empty scenarios (Production Scale)
INSERT INTO `tuning_2k.cpt_data` (id, category)
SELECT
  GENERATE_UUID() AS id,
  ['SOC Telemetry / SIEM Logs', 'JIRA/ServiceNow Analyst Investigation Ticket', 'Application Security Bug Fix (Git Diff and developer comments)', 'Threat Intelligence Actor Profile or Post-Mortem', 'Cloud Architecture Threat Model or IaC Misconfiguration'][OFFSET(CAST(FLOOR(RAND() * 5) AS INT64))] AS category
FROM UNNEST(GENERATE_ARRAY(1, 2000))
WHERE NOT EXISTS (SELECT 1 FROM `tuning_2k.cpt_data` LIMIT 1);

-- 0.2: Generate Themes and Descriptions via Gemini (Batched)
WHILE EXISTS (SELECT 1 FROM `tuning_2k.cpt_data` WHERE theme IS NULL) DO
  CREATE TEMP TABLE temp_themes AS
  WITH prompt_data AS (
    SELECT
      id,
      CONCAT(
        'Generate exactly one highly technical, unique cybersecurity scenario. ',
        'Focus specifically on the reporting category: ', category, '. ',
        'This scenario will be used as a seed to generate detailed training artifacts later. ',
        'Output strictly a JSON object with two keys: "theme" (2-5 words) and "initial_description" (2-3 sentences outlining the scenario context). Do not output markdown or any other text.'
      ) AS prompt
    FROM `tuning_2k.cpt_data`
    WHERE theme IS NULL
    LIMIT 500
  )
  SELECT
    id,
    SAFE.PARSE_JSON(
      REPLACE(REPLACE(JSON_EXTRACT_SCALAR(ml_generate_text_result, '$.candidates[0].content.parts[0].text'), '```json', ''), '```', '')
    ) AS generated_json
  FROM ML.GENERATE_TEXT(
    MODEL `tuning_2k.gemini_simulator`,
    TABLE prompt_data,
    STRUCT(
      1.0 AS temperature,
      65536 AS max_output_tokens,
      0.95 AS top_p,
      40 AS top_k
    )
  );

  UPDATE `tuning_2k.cpt_data` AS t
  SET 
    theme = CAST(JSON_EXTRACT_SCALAR(temp.generated_json, '$.theme') AS STRING),
    initial_description = CAST(JSON_EXTRACT_SCALAR(temp.generated_json, '$.initial_description') AS STRING)
  FROM temp_themes AS temp
  WHERE t.id = temp.id;

  DROP TABLE temp_themes;
END WHILE;

-- ==============================================================================
-- STEP 1: GENERATE RAW CPT ARTIFACTS
-- Updates the `cpt_data` master table dynamically based on category. (Batched)
-- ==============================================================================
WHILE EXISTS (SELECT 1 FROM `tuning_2k.cpt_data` WHERE raw_artifact IS NULL AND theme IS NOT NULL) DO
  CREATE TEMP TABLE temp_artifacts AS
  WITH prompt_data AS (
    SELECT
      id,
      CONCAT(
        'Act as an expert Cybersecurity Instructor and Red Team operator. ',
        'I am building a training dataset. Analyze this scenario:\n',
        'Category: ', category, '\n',
        'Theme: ', theme, '\n',
        'Description: ', initial_description, '\n\n',
        'Based STRICTLY on the Category above, generate a highly dense, realistic, and highly technical artifact representing this scenario. ',
        'If the category is SIEM/Telemetry, output raw log dumps. ',
        'If the category is JIRA/ServiceNow, output the raw JSON of an analyst ticket and investigation notes. ',
        'If the category is AppSec, output a Git Diff with developer comments explaining the vulnerability and patch. ',
        'If the category is Threat Intel, output a raw Markdown intelligence report. ',
        'If the category is Cloud Architecture, output a vulnerable IAM JSON policy or Terraform snippet. ',
        'Do NOT include any introductory or concluding text. Output ONLY the raw artifact data.'
      ) AS prompt
    FROM `tuning_2k.cpt_data`
    WHERE raw_artifact IS NULL AND theme IS NOT NULL
    LIMIT 500
  )
  SELECT
    id,
    JSON_EXTRACT_SCALAR(ml_generate_text_result, '$.candidates[0].content.parts[0].text') AS generated_artifact
  FROM ML.GENERATE_TEXT(
    MODEL `tuning_2k.gemini_simulator`,
    TABLE prompt_data,
    STRUCT(
      1.0 AS temperature,
      65536 AS max_output_tokens,
      0.95 AS top_p,
      40 AS top_k
    )
  );

  UPDATE `tuning_2k.cpt_data` AS t
  SET raw_artifact = temp.generated_artifact
  FROM temp_artifacts AS temp
  WHERE t.id = temp.id;

  DROP TABLE temp_artifacts;
END WHILE;

-- ==============================================================================
-- STEP 2: GENERATE QA DATA (SFT/LoRA Staging in master table)
-- Updates the `cpt_data` master table with structured QA based on the artifacts. (Batched)
-- ==============================================================================
WHILE EXISTS (SELECT 1 FROM `tuning_2k.cpt_data` WHERE q_and_a_pairs IS NULL AND raw_artifact IS NOT NULL) DO
  CREATE TEMP TABLE temp_qa_pairs AS
  WITH prompt_data AS (
    SELECT
      id,
      CONCAT(
        'Act as an expert SOC Analyst and AppSec instructor. ',
        'Read this raw cybersecurity artifact data:\n', raw_artifact, '\n\n',
        'Your task is to output a STRICT JSON array containing exactly 3 highly technical Interaction pairs based STRICTLY on the artifact data above. ',
        'The interactions should emulate a real analyst conversation with an AI assistant. Ensure realistic variation: ',
        '- Interaction 1 should be a simple, direct question asking for identification or an overview of a specific indicator. ',
        '- Interaction 2 should feature the analyst explicitly copy-pasting a chunk of the raw artifact data as context inside their question, asking a targeted question about that specific snippet. ',
        '- Interaction 3 should be a very complex, multi-part analytical question requiring deep reasoning across multiple parts of the artifact. ',
        'The answers must be helpful, highly technical, and accurate to the artifact.\n\n',
        'Output format MUST be strictly a JSON array of objects:\n',
        '[{"question": "...", "answer": "..."}, {"question": "...", "answer": "..."}, {"question": "...", "answer": "..."}]'
      ) AS prompt
    FROM `tuning_2k.cpt_data`
    WHERE q_and_a_pairs IS NULL AND raw_artifact IS NOT NULL
    LIMIT 500
  )
  SELECT
    id,
    SAFE.PARSE_JSON(
      REPLACE(REPLACE(JSON_EXTRACT_SCALAR(ml_generate_text_result, '$.candidates[0].content.parts[0].text'), '```json', ''), '```', '')
    ) AS generated_qa
  FROM ML.GENERATE_TEXT(
    MODEL `tuning_2k.gemini_simulator`,
    TABLE prompt_data,
    STRUCT(
      1.0 AS temperature,
      65536 AS max_output_tokens,
      0.95 AS top_p,
      40 AS top_k
    )
  );

  UPDATE `tuning_2k.cpt_data` AS t
  SET q_and_a_pairs = temp.generated_qa
  FROM temp_qa_pairs AS temp
  WHERE t.id = temp.id;

  DROP TABLE temp_qa_pairs;
END WHILE;

-- ==============================================================================
-- STEP 3: PARSE AND POPULATE SFT DATA
-- SFT requires Vertex AI conversational formatting (messages array)
-- ==============================================================================
TRUNCATE TABLE `tuning_2k.sft_data`;

INSERT INTO `tuning_2k.sft_data` (cpt_id, messages)
SELECT
  id AS cpt_id,
  JSON_ARRAY(
      JSON_OBJECT('role', 'system', 'content', 'You are an expert AI security analyst assistant.'),
      JSON_OBJECT('role', 'user', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[0].question') AS STRING)),
      JSON_OBJECT('role', 'assistant', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[0].answer') AS STRING))
  ) AS messages
FROM `tuning_2k.cpt_data`
WHERE JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[0].question') IS NOT NULL
UNION ALL
SELECT
  id AS cpt_id,
  JSON_ARRAY(
      JSON_OBJECT('role', 'system', 'content', 'You are an expert AI security analyst assistant.'),
      JSON_OBJECT('role', 'user', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[1].question') AS STRING)),
      JSON_OBJECT('role', 'assistant', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[1].answer') AS STRING))
  ) AS messages
FROM `tuning_2k.cpt_data`
WHERE JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[1].question') IS NOT NULL
UNION ALL
SELECT
  id AS cpt_id,
  JSON_ARRAY(
      JSON_OBJECT('role', 'system', 'content', 'You are an expert AI security analyst assistant.'),
      JSON_OBJECT('role', 'user', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[2].question') AS STRING)),
      JSON_OBJECT('role', 'assistant', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[2].answer') AS STRING))
  ) AS messages
FROM `tuning_2k.cpt_data`
WHERE JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[2].question') IS NOT NULL;

-- ==============================================================================
-- STEP 4: PARSE AND POPULATE LORA DATA
-- LoRA uses identical formatting to SFT based on specification
-- ==============================================================================
TRUNCATE TABLE `tuning_2k.lora_data`;

INSERT INTO `tuning_2k.lora_data` (cpt_id, messages)
SELECT
  id AS cpt_id,
  JSON_ARRAY(
      JSON_OBJECT('role', 'system', 'content', 'You are an expert AI security analyst assistant.'),
      JSON_OBJECT('role', 'user', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[0].question') AS STRING)),
      JSON_OBJECT('role', 'assistant', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[0].answer') AS STRING))
  ) AS messages
FROM `tuning_2k.cpt_data`
WHERE JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[0].question') IS NOT NULL
UNION ALL
SELECT
  id AS cpt_id,
  JSON_ARRAY(
      JSON_OBJECT('role', 'system', 'content', 'You are an expert AI security analyst assistant.'),
      JSON_OBJECT('role', 'user', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[1].question') AS STRING)),
      JSON_OBJECT('role', 'assistant', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[1].answer') AS STRING))
  ) AS messages
FROM `tuning_2k.cpt_data`
WHERE JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[1].question') IS NOT NULL
UNION ALL
SELECT
  id AS cpt_id,
  JSON_ARRAY(
      JSON_OBJECT('role', 'system', 'content', 'You are an expert AI security analyst assistant.'),
      JSON_OBJECT('role', 'user', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[2].question') AS STRING)),
      JSON_OBJECT('role', 'assistant', 'content', CAST(JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[2].answer') AS STRING))
  ) AS messages
FROM `tuning_2k.cpt_data`
WHERE JSON_EXTRACT_SCALAR(q_and_a_pairs, '$[2].question') IS NOT NULL;
