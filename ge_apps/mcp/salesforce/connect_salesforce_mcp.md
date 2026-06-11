# Connecting Salesforce MCP to Gemini Enterprise

This document describes the configuration steps required to connect the Salesforce Hosted MCP Server to Gemini Enterprise. Two authentication methods are supported:

1. **OAuth 2.0 without PKCE:** Standard authorization code flow.
2. **OAuth 2.0 with PKCE:** Proof Key for Code Exchange (PKCE) secures the authorization code flow.

---

## Option A: Configuration without PKCE

### 1. Configure the Salesforce External Client App
1. Log in to the Salesforce Org as an Administrator.
2. Navigate to **Setup** > **Apps** > **External Client Apps** > **External Client App Manager**.
3. Click **New External Client App**.
4. Input app details (Name, Contact Email).
5. Under **OAuth Settings**, select **Enable OAuth**.
6. Set the **Callback URL** to: `https://vertexaisearch.cloud.google.com/oauth-redirect`
7. Under **Selected OAuth Scopes**, include:
   - `Access Salesforce hosted MCP services (mcp_api)`
   - `Perform requests on your behalf at any time (refresh_token, offline_access)`
8. Select **Issue JSON Web Token (JWT)-based access tokens for named users**.
9. Ensure the checkbox for **Require Proof Key for Code Exchange (PKCE) extension for Supported Authorization Flows** is **unchecked**.
10. Save the application.
11. Record the **Consumer Key** (Client ID) and **Consumer Secret** (Client Secret).

### 2. Configure the Gemini Enterprise Data Store
1. Navigate to the Google Cloud Console > **Gemini Enterprise** > **Data stores**.
2. Click **Create data store** > **Custom MCP Server (Preview)**.
3. Input the connection parameters:
   - **MCP Server URL:** `https://api.salesforce.com/platform/mcp/v1/platform/sobject-all`
   - **Authorization URL:** `https://<YOUR_SALESFORCE_DOMAIN>.my.salesforce.com/services/oauth2/authorize`
   - **Authorization URL Parameters:** `&prompt=login`
   - **Token URL:** `https://<YOUR_SALESFORCE_DOMAIN>.my.salesforce.com/services/oauth2/token`
   - **Client ID:** `<YOUR_SALESFORCE_CLIENT_ID>`
   - **Client Secret:** `<YOUR_SALESFORCE_CLIENT_SECRET>`
   - **Scopes:** `mcp_api refresh_token`
4. Click **Login** and complete the authentication flow.
5. Provide the metadata configurations (Note: The description and instructions below are basic templates; customize and refine the prompt text based on your specific application requirements):
   - **MCP Server Description:**
     ```text
     Provides tools to create, update, and manage Salesforce customer records (including Accounts, Contacts, Opportunities, Leads, and Cases) and execute direct SOQL queries. Use this as a backup to supplement standard Salesforce search tools when modifications or direct structured queries are required.
     ```
   - **MCP Agent Instructions:**
     ```text
     # Role & Purpose
     You are an assistant with access to tools for managing Salesforce customer records. Use this server to query, create, retrieve, update, or delete records (such as Accounts, Contacts, Opportunities, Leads, and Cases) in the Salesforce database.

     # When to Use This Connector
     - This connector supplements Salesforce search capabilities. Treat it as a backup:
       - For general search, reading information, or querying customer history, prefer using standard Salesforce search tools.
       - Use these database tools when performing write/modify operations (creating, updating, or deleting records) or when executing direct, real-time database queries (`soqlQuery`).
       - Do not redirect the user to other tools; if a write or direct query is requested, use these tools to fulfill the request.

     # Interpreting Customer Record Language
     - Map user intent to the corresponding database entity:
       - Create/Update/Manage a customer, client, or company profile -> Account or Contact
       - Create/Update/Manage a sales deal, pipeline entry, or closing opportunity -> Opportunity
       - Create/Update/Manage a new prospect, inquiry, or inbound lead -> Lead
       - Create/Update/Manage a customer case, issue, or support ticket -> Case
     ```

6. Click **Create** to finalize the Data Store.

### 3. Reload and Activate Tools
1. Navigate to **Data stores** in the Gemini Enterprise console and select the Salesforce MCP data store.
2. Open the **Actions** tab.
3. Click **Reload Tools** (or Reload custom actions). If prompted, complete the authentication flow.
4. Verify that the list of available tools displays.
5. Select the required tools and click **Activate**.
6. Tools are only available to the Gemini Enterprise agents once activated.

---

## Option B: Configuration with PKCE

To configure the connection with PKCE enabled, follow the exact procedure described in Option A (Steps 1, 2, and 3), with the following two modifications:

1. **Salesforce External Client App (Step 1, Sub-step 9):** Check the box for **"Require Proof Key for Code Exchange (PKCE) extension for Supported Authorization Flows"** (instead of leaving it unchecked).
2. **Gemini Enterprise Data Store (Step 2, Sub-step 4):** Check the box/enable the flag for **"Require PKCE"** in the configuration form before logging in.
