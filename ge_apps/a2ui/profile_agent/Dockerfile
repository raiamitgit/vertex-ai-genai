# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Force fresh rebuild for final visual postback check
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --index-url https://pypi.org/simple/

# Copy application source files
COPY main.py agent.py a2ui_schema.py agent_executor.py agent_card.json ./

# Expose standard Cloud Run port
EXPOSE 8080

# Start FastAPI application via Uvicorn on standard port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
