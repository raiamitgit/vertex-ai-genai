# Connecting Salesforce MCP to Gemini Enterprise

This guide provides step-by-step instructions for connecting the native Salesforce Hosted MCP Server to Gemini Enterprise, with **non-PKCE** configuration using the Refresh Token flow.

## 1. Configure the Salesforce External Client App

In Salesforce, you must configure an External Client App to serve as the OAuth provider.

1. Log in to your Salesforce Org as Administrator.
2. Navigate to **Setup** > **Apps** > **External Client Apps** > **External Client App Manager**.
3. Click **New External Client App**.
4. Provide basic details (Name, Contact Email, etc.).
5. Under **OAuth Settings**, check **Enable OAuth**.
6. Set the **Callback URL** to: `https://vertexaisearch.cloud.google.com/oauth-redirect`
7. **Important:** Under **Selected OAuth Scopes**, you must include:
   - `Access Salesforce hosted MCP services (mcp_api)`
   - `Perform requests on your behalf at any time (refresh_token, offline_access)`
8. **CRITICAL FOR NON-PKCE:** Ensure the checkbox for **Require Proof Key for Code Exchange (PKCE) extension for Supported Authorization Flows** is **UNCHECKED**.
9. Save the application.
10. Retrieve and securely store your **Consumer Key** (Client ID) and **Consumer Secret** (Client Secret).

> **Note:** Salesforce External Client App changes can take up to 10 minutes to propagate globally.

## 2. Configure Gemini Enterprise Data Store

Next, register the Salesforce MCP server as a Data Store in Gemini Enterprise.

1. Log in to the [Google Cloud Console](https://console.cloud.google.com/) and navigate to **Gemini Enterprise** (or Vertex AI Agent Builder).
2. Go to **Data stores** > **Create data store** > **Custom MCP Server (Preview)**.
3. Fill in the connection details using the following templates:
   - **MCP Server URL:** `https://api.salesforce.com/platform/mcp/v1/platform/sobject-all`
   - **Authorization URL:** `https://<YOUR_SALESFORCE_DOMAIN>.my.salesforce.com/services/oauth2/authorize`
   - **Authorization URL Parameters:** `?prompt=login`
   - **Token URL:** `https://<YOUR_SALESFORCE_DOMAIN>.my.salesforce.com/services/oauth2/token`
   - **Client ID:** `<YOUR_SALESFORCE_CLIENT_ID>`
   - **Client Secret:** `<YOUR_SALESFORCE_CLIENT_SECRET>`
   - **Scopes:** `mcp_api refresh_token` *(Ensure these are separated by a space)*


4. Click **Login**. A popup will appear prompting you to log in to Salesforce and grant consent.
5. Once authenticated, the popup will close, and you will see a green checkmark.
### Advanced Configuration

6. To ensure your Gemini agent understands how to utilize the Salesforce tools effectively, paste the following into the **Advanced Options** fields:

**MCP Server Description:**
```text
Provides direct access to the native Salesforce SObject database. Exposes standard and custom Salesforce objects (such as Accounts, Contacts, Leads, Opportunities, Cases, Tasks, and custom tables) for full CRUD (Create, Read, Update, Delete) operations, metadata descriptions, and SOQL custom querying.
```

**MCP Agent Instructions:**
```text
# Role & Purpose
You are an expert Salesforce assistant. Use this server to query, create, retrieve, update, or delete records in the target Salesforce Org.

# Guidelines for Tool Selection
1. SCHEMA DISCOVERY: Before creating or updating records on an unfamiliar object, use the SObject description/metadata tools to discover required fields, field types, and valid Picklist values.
2. RECORD SEARCHING: To search for records, prefer using SOQL query tools. 
3. SPECIFIC CRUD: For single-record retrieval, updates, or deletions, use the dedicated get, update, and delete tools for optimal performance.
```

7. Click **Create** to finalize the Data Store.

## 3. Reload and Activate Tools

Once the MCP Data Store is created, you must fetch the available tools from Salesforce and activate them.

1. In the Gemini Enterprise console, go to the **Data stores** page and click on your newly created Salesforce MCP data store.
2. Navigate to the **Actions** tab.
3. Click on the **Reload Tools** (or Reload custom actions) button. 
4. *Note:* During the reload process, you may be prompted to authenticate again. If so, follow the prompts to log in to Salesforce.
5. Once the reload is complete, a list of all available tools exposed by the Salesforce MCP server will appear. 
   - *Troubleshooting:* If the tools do not appear, it means the MCP connection was unsuccessful. Double-check your OAuth scopes and credentials.
6. Select the tools you wish to use (you can select all of them) and click **Activate**.
7. **Important:** The tools will only be visible and usable by your Gemini Enterprise agents *after* they have been explicitly activated in this step.
