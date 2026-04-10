import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv('PROJECT_ID', 'data-n-models')

client = bigquery.Client(project=PROJECT_ID)

with open('synth_data/generate_synthetic_data_30k.sql', 'r') as f:
    sql = f.read()

# Dynamically inject the local user's project ID into the templated SQL string
sql = sql.replace('YOUR_PROJECT_ID', PROJECT_ID)

print('Submitting Distributed BigQuery Job for 30,000 rows (Loop with LIMIT 5000)...')
job = client.query(sql)

print(f'Job submitted. Job ID: {job.job_id}')
