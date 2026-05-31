"""ServiceNow REST API Client.

This module provides a clean, robust, and fully documented interface to interact
with ServiceNow's Table API. It manages credentials, resolves incident numbers to
internal sys_ids, and performs CRUD operations on incidents and comments.

It is designed to be independent of the Model Context Protocol (MCP), serving
as the core integration library.
"""

import os
import logging
import requests
from typing import Dict, Any, List, Tuple, Optional


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("servicenow_client")

class ServiceNowClientError(Exception):
    """Base exception class for ServiceNow Client errors."""
    pass

class CredentialsMissingError(ServiceNowClientError):
    """Raised when required ServiceNow credentials are missing in the environment."""
    pass


def _get_connection_details() -> Tuple[str, Tuple[str, str]]:
    """Retrieves and validates connection details from environment variables.

    Returns:
        A tuple of (instance_url, (username, password)).

    Raises:
        CredentialsMissingError: If any required variable is missing.
    """
    instance_url = os.environ.get("SN_INSTANCE_URL")
    username = os.environ.get("SN_USERNAME")
    password = os.environ.get("SN_PASSWORD")

    if not instance_url or not username or not password:
        raise CredentialsMissingError(
            "ServiceNow connection details missing. "
            "Please ensure SN_INSTANCE_URL, SN_USERNAME, and SN_PASSWORD are set in the environment."
        )
    
    return instance_url.rstrip("/"), (username, password)


def _get_sys_id(ticket_id: str, instance_url: str, auth: Tuple[str, str]) -> str:
    """Resolves a ticket number (e.g., 'INC0010001') to its internal 32-character sys_id.

    If the ticket_id already looks like a sys_id, it is returned directly.

    Args:
        ticket_id: The incident number (e.g., 'INC0010001') or sys_id.
        instance_url: The base URL of the ServiceNow instance.
        auth: A tuple of (username, password).

    Returns:
        The 32-character sys_id string.

    Raises:
        ServiceNowClientError: If the ticket cannot be found or API fails.
    """
    # If it already looks like a 32-character hex sys_id, return it
    if len(ticket_id) == 32 and all(c in '0123456789abcdefABCDEF' for c in ticket_id):
        return ticket_id

    url = f"{instance_url}/api/now/table/incident"
    params = {
        "sysparm_query": f"number={ticket_id}",
        "sysparm_fields": "sys_id",
        "sysparm_limit": 1
    }

    try:
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 200:
            result = response.json().get("result", [])
            if result:
                sys_id = result[0].get("sys_id")
                logger.info(f"Resolved ticket number {ticket_id} to sys_id {sys_id}")
                return sys_id
            else:
                raise ServiceNowClientError(f"Incident with number '{ticket_id}' not found.")
        else:
            raise ServiceNowClientError(
                f"Failed to resolve ticket number. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow during sys_id resolution: {e}")
        raise


def get_incident_details(ticket_id: str) -> Dict[str, Any]:
    """Retrieves comprehensive details for a specific ServiceNow incident.

    Args:
        ticket_id: The incident number (e.g., 'INC0010001') or sys_id.

    Returns:
        A dictionary containing the incident fields (number, short_description, 
        description, state, priority, urgency, sys_id, sys_created_on, etc.).

    Raises:
        ServiceNowClientError: If the API call fails or credentials are missing.
    """
    instance_url, auth = _get_connection_details()
    sys_id = _get_sys_id(ticket_id, instance_url, auth)

    url = f"{instance_url}/api/now/table/incident/{sys_id}"
    
    # Fields we want to fetch for rich context
    fields = [
        "sys_id", "number", "short_description", "description", "state", 
        "priority", "urgency", "impact", "sys_created_on", "sys_updated_on",
        "caller_id", "assigned_to", "comments"
    ]
    params = {"sysparm_fields": ",".join(fields)}

    try:
        logger.info(f"Fetching details for incident sys_id: {sys_id}")
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("result", {})
        else:
            raise ServiceNowClientError(
                f"Failed to fetch incident details. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


def list_recent_incidents(limit: int = 10) -> List[Dict[str, Any]]:
    """Lists recent ServiceNow incidents for a high-level overview.

    Args:
        limit: Maximum number of incidents to return (default: 10).

    Returns:
        A list of dictionaries containing basic ticket details.

    Raises:
        ServiceNowClientError: If the API call fails.
    """
    instance_url, auth = _get_connection_details()
    url = f"{instance_url}/api/now/table/incident"
    
    params = {
        "sysparm_fields": "sys_id,number,short_description,state,priority,sys_created_on",
        "sysparm_limit": limit,
        "sysparm_query": "ORDERBYDESCsys_created_on"
    }

    try:
        logger.info(f"Listing up to {limit} recent incidents")
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("result", [])
        else:
            raise ServiceNowClientError(
                f"Failed to list incidents. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


def get_incident_comments(ticket_id: str) -> List[Dict[str, Any]]:
    """Retrieves all user-facing comments (journal entries) for a specific incident.

    ServiceNow stores audit history and comments in the sys_journal_field table.
    We query this table to reconstruct the thread of comments in chronological order.

    Args:
        ticket_id: The incident number (e.g., 'INC0010001') or sys_id.

    Returns:
        A list of dictionaries, each representing a comment with keys:
        - sys_id (unique identifier of the comment)
        - sys_created_on (timestamp)
        - sys_created_by (username/author)
        - value (the comment text)

    Raises:
        ServiceNowClientError: If the API call fails.
    """
    instance_url, auth = _get_connection_details()
    sys_id = _get_sys_id(ticket_id, instance_url, auth)

    # Query the sys_journal_field table for comments matching this incident's sys_id
    url = f"{instance_url}/api/now/table/sys_journal_field"
    
    # Query: element_id = incident's sys_id AND element = 'comments'
    query = f"element_id={sys_id}^element=comments^ORDERBYsys_created_on"
    params = {
        "sysparm_query": query,
        "sysparm_fields": "sys_id,sys_created_on,sys_created_by,value"
    }

    try:
        logger.info(f"Fetching comments for incident sys_id: {sys_id}")
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("result", [])
        else:
            raise ServiceNowClientError(
                f"Failed to fetch incident comments. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


def add_incident_comment(ticket_id: str, comment_text: str) -> Dict[str, Any]:
    """Adds a new user-facing comment to an existing ServiceNow incident.

    Args:
        ticket_id: The incident number (e.g., 'INC0010001') or sys_id.
        comment_text: The text content of the comment to add.

    Returns:
        A dictionary indicating success, e.g., {"success": True, "ticket_id": ...}

    Raises:
        ServiceNowClientError: If the API call fails.
    """
    instance_url, auth = _get_connection_details()
    sys_id = _get_sys_id(ticket_id, instance_url, auth)

    url = f"{instance_url}/api/now/table/incident/{sys_id}"
    
    # ServiceNow automatically appends anything in 'comments' field to journal history
    payload = {"comments": comment_text}

    try:
        logger.info(f"Adding comment to incident sys_id: {sys_id}")
        response = requests.patch(
            url,
            auth=auth,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully added comment to incident {ticket_id}")
            return {"success": True, "message": "Comment added successfully.", "ticket_id": ticket_id}
        else:
            raise ServiceNowClientError(
                f"Failed to add comment. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


def update_incident_fields(ticket_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates specific fields (e.g., description, state, urgency) of a ServiceNow incident.

    Args:
        ticket_id: The incident number (e.g., 'INC0010001') or sys_id.
        updates: A dictionary containing the fields and their new values.
                 Example: {"description": "New description", "state": "2"}

    Returns:
        A dictionary indicating success, e.g., {"success": True, "ticket_id": ...}

    Raises:
        ServiceNowClientError: If the API call fails or updates are empty.
    """
    if not updates:
        raise ServiceNowClientError("Updates dictionary cannot be empty.")

    instance_url, auth = _get_connection_details()
    sys_id = _get_sys_id(ticket_id, instance_url, auth)

    url = f"{instance_url}/api/now/table/incident/{sys_id}"

    try:
        logger.info(f"Updating fields {list(updates.keys())} on incident sys_id: {sys_id}")
        response = requests.patch(
            url,
            auth=auth,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=updates,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully updated fields on incident {ticket_id}")
            return {"success": True, "message": "Incident updated successfully.", "ticket_id": ticket_id}
        else:
            raise ServiceNowClientError(
                f"Failed to update incident. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


def delete_comment(comment_sys_id: str) -> Dict[str, Any]:
    """Deletes a specific comment (journal entry) by its sys_id directly from sys_journal_field.

    Note: In production, deleting journal history is usually restricted. In a PDI
    running as admin, this is supported and useful for cleanups/simulations.

    Args:
        comment_sys_id: The 32-character sys_id of the comment record.

    Returns:
        A dictionary indicating success.

    Raises:
        ServiceNowClientError: If the API call fails.
    """
    instance_url, auth = _get_connection_details()
    url = f"{instance_url}/api/now/table/sys_journal_field/{comment_sys_id}"

    try:
        logger.info(f"Deleting journal comment sys_id: {comment_sys_id}")
        response = requests.delete(url, auth=auth, timeout=10)
        
        if response.status_code == 204:
            logger.info(f"Successfully deleted comment sys_id: {comment_sys_id}")
            return {"success": True, "message": "Comment deleted successfully.", "comment_sys_id": comment_sys_id}
        else:
            raise ServiceNowClientError(
                f"Failed to delete comment. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


# ==============================================================================
# Knowledge Base (kb_knowledge) Integration Functions
# ==============================================================================

def _get_kb_article_sys_id(article_id: str, instance_url: str, auth: Tuple[str, str]) -> str:
    """Resolves a KB article number (e.g., 'KB0010001') to its internal 32-character sys_id."""
    if len(article_id) == 32 and all(c in '0123456789abcdefABCDEF' for c in article_id):
        return article_id

    url = f"{instance_url}/api/now/table/kb_knowledge"
    params = {
        "sysparm_query": f"number={article_id}",
        "sysparm_fields": "sys_id",
        "sysparm_limit": 1
    }

    try:
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 200:
            result = response.json().get("result", [])
            if result:
                return result[0].get("sys_id")
            else:
                raise ServiceNowClientError(f"Knowledge article with number '{article_id}' not found.")
        else:
            raise ServiceNowClientError(
                f"Failed to resolve article number. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error during article sys_id resolution: {e}")
        raise


def _get_default_kb_base(instance_url: str, auth: Tuple[str, str]) -> str:
    """Retrieves the sys_id of the first active Knowledge Base in the ServiceNow instance."""
    url = f"{instance_url}/api/now/table/kb_knowledge_base"
    params = {
        "sysparm_query": "active=true",
        "sysparm_fields": "sys_id,title",
        "sysparm_limit": 1
    }

    try:
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 200:
            result = response.json().get("result", [])
            if result:
                logger.info(f"Using active Knowledge Base: {result[0].get('title')} ({result[0].get('sys_id')})")
                return result[0].get("sys_id")
            else:
                raise ServiceNowClientError("No active Knowledge Base found in the instance.")
        else:
            raise ServiceNowClientError(
                f"Failed to retrieve active knowledge bases. Status: {response.status_code}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error querying knowledge bases: {e}")
        raise


def search_knowledge_base(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches the ServiceNow Knowledge Base (kb_knowledge) for matching articles."""
    instance_url, auth = _get_connection_details()
    url = f"{instance_url}/api/now/table/kb_knowledge"

    # Construct sysparm_query: active=true AND (short_description LIKE query OR text LIKE query)
    sys_query = f"active=true^short_descriptionLIKE{query}^ORtextLIKE{query}^ORDERBYDESCsys_created_on"
    params = {
        "sysparm_query": sys_query,
        "sysparm_fields": "sys_id,number,short_description,author,sys_created_on",
        "sysparm_limit": limit
    }

    try:
        logger.info(f"Searching Knowledge Base for: '{query}'")
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 200:
            return response.json().get("result", [])
        else:
            raise ServiceNowClientError(
                f"Knowledge search failed. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error searching knowledge base: {e}")
        raise


def get_knowledge_article(article_id: str) -> Dict[str, Any]:
    """Retrieves complete fields and content body of a specific Knowledge Article."""
    instance_url, auth = _get_connection_details()
    sys_id = _get_kb_article_sys_id(article_id, instance_url, auth)

    url = f"{instance_url}/api/now/table/kb_knowledge/{sys_id}"
    fields = ["sys_id", "number", "short_description", "text", "author", "sys_created_on", "kb_knowledge_base"]
    params = {"sysparm_fields": ",".join(fields)}

    try:
        logger.info(f"Fetching details for article sys_id: {sys_id}")
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 200:
            return response.json().get("result", {})
        else:
            raise ServiceNowClientError(
                f"Failed to fetch article details. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error retrieving article details: {e}")
        raise


def create_knowledge_article(title: str, text: str, kb_base_sys_id: str = None) -> Dict[str, Any]:
    """Creates a new Knowledge Base article in draft state."""
    instance_url, auth = _get_connection_details()

    if not kb_base_sys_id:
        kb_base_sys_id = _get_default_kb_base(instance_url, auth)

    url = f"{instance_url}/api/now/table/kb_knowledge"
    payload = {
        "short_description": title,
        "text": text,
        "kb_knowledge_base": kb_base_sys_id,
        "workflow_state": "draft"
    }

    try:
        logger.info(f"Creating knowledge article: '{title}' under base sys_id: {kb_base_sys_id}")
        response = requests.post(
            url,
            auth=auth,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=payload,
            timeout=10
        )
        if response.status_code == 201:
            result = response.json().get("result", {})
            sys_id = result.get("sys_id")
            logger.info(f"Successfully created KB article: {result.get('number')}")
            return {
                "success": True,
                "message": "Knowledge article created successfully as Draft.",
                "number": result.get("number"),
                "sys_id": sys_id,
                "url": f"{instance_url}/kb_knowledge.do?sys_id={sys_id}"
            }
        else:
            raise ServiceNowClientError(
                f"Failed to create KB article. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error creating KB article: {e}")
        raise


def update_knowledge_article(
    article_id: str, 
    title: Optional[str] = None, 
    text: Optional[str] = None
) -> Dict[str, Any]:
    """Updates fields on an existing Knowledge Article and reverts its state to Draft for review.

    Args:
        article_id: The article number (e.g., 'KB0010001') or its 32-char sys_id.
        title: New short description/title (optional).
        text: New HTML content body (optional).

    Returns:
        A dictionary indicating success, along with the Direct UI Verification URL.

    Raises:
        ServiceNowClientError: If the API call fails or no updates are provided.
    """
    updates = {}
    if title:
        updates["short_description"] = title
    if text:
        updates["text"] = text

    if not updates:
        raise ServiceNowClientError("No update values were provided. Specify a title or text to update.")

    # Enforce draft state on every update to guarantee human review before re-publishing
    updates["workflow_state"] = "draft"

    instance_url, auth = _get_connection_details()
    sys_id = _get_kb_article_sys_id(article_id, instance_url, auth)

    url = f"{instance_url}/api/now/table/kb_knowledge/{sys_id}"

    try:
        logger.info(f"Updating fields {list(updates.keys())} on Knowledge Article sys_id: {sys_id}")
        response = requests.patch(
            url,
            auth=auth,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=updates,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json().get("result", {})
            logger.info(f"Successfully updated KB article {result.get('number')}")
            return {
                "success": True,
                "message": "Knowledge article updated successfully and returned to Draft for review.",
                "number": result.get("number"),
                "sys_id": sys_id,
                "url": f"{instance_url}/kb_knowledge.do?sys_id={sys_id}"
            }
        else:
            raise ServiceNowClientError(
                f"Failed to update Knowledge Article. Status: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error communicating with ServiceNow: {e}")
        raise


def delete_knowledge_article(article_sys_id: str) -> Dict[str, Any]:
    """Deletes a specific Knowledge Article by its sys_id (useful for test cleanup)."""
    instance_url, auth = _get_connection_details()
    url = f"{instance_url}/api/now/table/kb_knowledge/{article_sys_id}"

    try:
        logger.info(f"Deleting knowledge article sys_id: {article_sys_id}")
        response = requests.delete(url, auth=auth, timeout=10)
        if response.status_code == 204:
            return {"success": True, "message": "Knowledge article deleted successfully."}
        else:
            raise ServiceNowClientError(
                f"Failed to delete knowledge article. Status: {response.status_code}"
            )
    except Exception as e:
        if not isinstance(e, ServiceNowClientError):
            raise ServiceNowClientError(f"Error deleting knowledge article: {e}")
        raise



