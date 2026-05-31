"""ServiceNow MCP Server.

This module defines the Model Context Protocol (MCP) server instance using FastMCP.
It wraps our core ServiceNow API client functions into standardized, schema-exposed
tools that Gemini Enterprise can discover and execute.

Every tool includes highly detailed docstrings which are used by Gemini to make
dynamic routing and parameter resolution decisions at runtime.
"""

import os
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Import our verified ServiceNow client functions
import servicenow_client

# Configure logging
logger = logging.getLogger("mcp_server")

# 1. Initialize the FastMCP server instance
# The name passed here will be the identifier for the server registry.
mcp = FastMCP("service-now-byo-mcp")


@mcp.tool()
def list_incidents(limit: int = 5) -> str:
    """List recent ServiceNow incidents.

    Use this tool when the user asks for an overview of recent support tickets,
    wants to see what cases exist, or wants to find a ticket to work on.

    Args:
        limit: The maximum number of incidents to list (default: 5).

    Returns:
        A formatted Markdown list of recent incidents.
    """
    try:
        incidents = servicenow_client.list_recent_incidents(limit=limit)
        if not incidents:
            return "No incidents found in your ServiceNow instance."

        output = f"### Recent ServiceNow Incidents (Up to {limit}):\n\n"
        for inc in incidents:
            output += f"* **{inc.get('number')}**: {inc.get('short_description')}\n"
            output += f"  - *State*: {inc.get('state')} | *Priority*: {inc.get('priority')} | *Created*: {inc.get('sys_created_on')}\n"
        return output
    except Exception as e:
        logger.error(f"Error in list_incidents tool: {e}")
        return f"Error listing incidents: {str(e)}"


@mcp.tool()
def query_incident(ticket_id: str) -> str:
    """Query comprehensive details for a specific ServiceNow incident by its ticket ID (e.g. INC0010019).

    Use this tool when the user asks about a specific ticket's status, priority,
    urgency, creation date, caller, or full description.

    Args:
        ticket_id: The incident number (e.g., 'INC0010019') or sys_id.

    Returns:
        A detailed Markdown report of the incident.
    """
    try:
        details = servicenow_client.get_incident_details(ticket_id)
        
        output = f"### Incident Details: {details.get('number')}\n\n"
        output += f"* **Short Description**: {details.get('short_description')}\n"
        output += f"* **Description**: {details.get('description') or '*No description provided*'}\n"
        output += f"* **Sys ID**: `{details.get('sys_id')}`\n"
        output += f"* **State**: {details.get('state')}\n"
        output += f"* **Priority**: {details.get('priority')} | **Urgency**: {details.get('urgency')} | **Impact**: {details.get('impact')}\n"
        output += f"* **Created On**: {details.get('sys_created_on')}\n"
        output += f"* **Last Updated**: {details.get('sys_updated_on')}\n"
        
        caller = details.get("caller_id")
        if isinstance(caller, dict):
            output += f"* **Caller**: {caller.get('display_value')} (`{caller.get('value')}`)\n"
        elif caller:
            output += f"* **Caller ID**: `{caller}`\n"
            
        assigned = details.get("assigned_to")
        if isinstance(assigned, dict):
            output += f"* **Assigned To**: {assigned.get('display_value')} (`{assigned.get('value')}`)\n"
        elif assigned:
            output += f"* **Assigned To ID**: `{assigned}`\n"

        return output
    except Exception as e:
        logger.error(f"Error in query_incident tool for {ticket_id}: {e}")
        return f"Error retrieving incident details for '{ticket_id}': {str(e)}"


@mcp.tool()
def get_ticket_comments(ticket_id: str) -> str:
    """Retrieve user comments and historical updates for a specific ServiceNow incident.

    Use this tool when the user wants to see the conversation history, check if
    any notes were added, or review past interactions on a case.

    Args:
        ticket_id: The incident number (e.g., 'INC0010019') or sys_id.

    Returns:
        A chronologically ordered Markdown thread of comments.
    """
    try:
        comments = servicenow_client.get_incident_comments(ticket_id)
        if not comments:
            return f"No comments found on incident '{ticket_id}'."

        output = f"### Comments History for {ticket_id}:\n\n"
        for i, comm in enumerate(comments, 1):
            output += f"**Comment #{i}** by **{comm.get('sys_created_by')}** on *{comm.get('sys_created_on')}*\n"
            output += f"> {comm.get('value')}\n"
            output += f"> *ID*: `{comm.get('sys_id')}`\n\n"
        return output
    except Exception as e:
        logger.error(f"Error in get_ticket_comments tool for {ticket_id}: {e}")
        return f"Error retrieving comments for '{ticket_id}': {str(e)}"


@mcp.tool()
def add_ticket_comment(ticket_id: str, comment_text: str) -> str:
    """Add a new comment or note to an existing ServiceNow incident.

    Use this tool when the user wants to reply to a ticket, leave a comment,
    post a message, or add a note to a support case.

    Args:
        ticket_id: The incident number (e.g., 'INC0010019') or sys_id.
        comment_text: The text content of the comment/note to add.

    Returns:
        A Markdown success message.
    """
    try:
        result = servicenow_client.add_incident_comment(ticket_id, comment_text)
        return f"### ✅ Comment Added Successfully\n\nComment has been posted to incident **{ticket_id}**."
    except Exception as e:
        logger.error(f"Error in add_ticket_comment tool for {ticket_id}: {e}")
        return f"Error adding comment to '{ticket_id}': {str(e)}"


@mcp.tool()
def delete_ticket_comment(comment_sys_id: str) -> str:
    """Delete a specific comment (journal entry) from ServiceNow history by its comment ID.

    Use this tool when the user requests to remove, delete, or retract a specific
    comment from a ticket's history. You must have the comment's sys_id (which can
    be found by listing comments first).

    Args:
        comment_sys_id: The 32-character sys_id of the comment record.

    Returns:
        A Markdown success message.
    """
    try:
        result = servicenow_client.delete_comment(comment_sys_id)
        return f"### ✅ Comment Deleted Successfully\n\nComment with ID `{comment_sys_id}` has been removed from history."
    except Exception as e:
        logger.error(f"Error in delete_ticket_comment tool for {comment_sys_id}: {e}")
        return f"Error deleting comment `{comment_sys_id}`: {str(e)}"


@mcp.tool()
def update_ticket_fields(
    ticket_id: str,
    description: Optional[str] = None,
    state: Optional[str] = None
) -> str:
    """Update the description or state of a ServiceNow incident.

    Use this tool when the user asks to modify a ticket, change its description,
    or update its state.

    States mapping reference:
    - '1': New
    - '2': In Progress
    - '3': On Hold
    - '4': Awaiting Caller
    - '6': Resolved
    - '7': Closed
    - '8': Canceled

    Args:
        ticket_id: The incident number (e.g., 'INC0010019') or sys_id.
        description: The new detailed description text (optional).
        state: The new state value string, e.g., '2' for In Progress, '6' for Resolved (optional).

    Returns:
        A Markdown success message.
    """
    updates = {}
    if description:
        updates["description"] = description
    if state:
        updates["state"] = state

    if not updates:
        return "No updates were provided. Please specify a description or state to update."

    try:
        result = servicenow_client.update_incident_fields(ticket_id, updates)
        
        output = f"### ✅ Ticket Updated Successfully\n\nIncident **{ticket_id}** has been updated:\n"
        if description:
            output += f"* **Description** updated.\n"
        if state:
            state_names = {
                "1": "New", "2": "In Progress", "3": "On Hold", 
                "4": "Awaiting Caller", "6": "Resolved", "7": "Closed", "8": "Canceled"
            }
            state_name = state_names.get(state, state)
            output += f"* **State** updated to **{state_name}** (code: `{state}`).\n"
        return output
    except Exception as e:
        logger.error(f"Error in update_ticket_fields tool for {ticket_id}: {e}")
        return f"Error updating incident '{ticket_id}': {str(e)}"


# ==============================================================================
# Knowledge Base (kb_knowledge) Tool Definitions
# ==============================================================================

@mcp.tool()
def search_knowledge_base(query: str, limit: int = 5) -> str:
    """Search the ServiceNow Knowledge Base (kb_knowledge) for articles matching a search query.

    Use this tool when the user asks to search for documentation, look up a guide,
    find how-to instructions, or search for help articles related to a topic.

    Args:
        query: The search term or keywords to find (e.g., 'VPN connection setup').
        limit: The maximum number of results to return (default: 5).

    Returns:
        A formatted Markdown list of matching articles.
    """
    try:
        articles = servicenow_client.search_knowledge_base(query, limit=limit)
        if not articles:
            return f"No knowledge articles found matching: '{query}'."

        output = f"### Knowledge Base Search Results for '{query}':\n\n"
        for art in articles:
            output += f"* **{art.get('number')}**: {art.get('short_description')}\n"
            output += f"  - *Author*: {art.get('author', {}).get('display_value') if isinstance(art.get('author'), dict) else art.get('author')} | *Created*: {art.get('sys_created_on')}\n"
        return output
    except Exception as e:
        logger.error(f"Error in search_knowledge_base tool for '{query}': {e}")
        return f"Error searching knowledge base: {str(e)}"


@mcp.tool()
def get_knowledge_article(article_id: str) -> str:
    """Retrieve the complete body text and content of a specific ServiceNow Knowledge Article by its ID (e.g., KB0010012).

    Use this tool when the user asks to read a specific article, view a complete guide,
    or needs the full text/content of a documentation page.

    Args:
        article_id: The article number (e.g., 'KB0010012') or sys_id.

    Returns:
        A detailed Markdown report containing the article text.
    """
    try:
        details = servicenow_client.get_knowledge_article(article_id)
        
        output = f"### Knowledge Article: {details.get('number')}\n\n"
        output += f"## **Title**: {details.get('short_description')}\n\n"
        
        # Clean HTML tags from ServiceNow's text field for clean markdown display if possible,
        # otherwise print it directly since Markdown parsers often render HTML tags safely.
        output += f"{details.get('text')}\n\n"
        output += f"---\n"
        output += f"* **Article ID**: `{details.get('sys_id')}`\n"
        author = details.get("author")
        if isinstance(author, dict):
            output += f"* **Author**: {author.get('display_value')} (`{author.get('value')}`)\n"
        elif author:
            output += f"* **Author ID**: `{author}`\n"
        output += f"* **Published**: {details.get('sys_created_on')}\n"
        return output
    except Exception as e:
        logger.error(f"Error in get_knowledge_article tool for {article_id}: {e}")
        return f"Error retrieving knowledge article '{article_id}': {str(e)}"


@mcp.tool()
def create_knowledge_article(title: str, text: str, kb_base_sys_id: Optional[str] = None) -> str:
    """Create a new ServiceNow Knowledge Article in Draft state.

    Use this tool when the user requests to write a new documentation page,
    publish a new guide, create a how-to article, or document a process.

    Args:
        title: The short description or title of the article.
        text: The HTML/text body content of the article.
        kb_base_sys_id: The sys_id of the parent Knowledge Base (optional).

    Returns:
        A Markdown success message.
    """
    try:
        result = servicenow_client.create_knowledge_article(title, text, kb_base_sys_id)
        output = f"### Knowledge Article Created Successfully\n\n"
        output += f"Created Draft Article **{result.get('number')}**.\n\n"
        output += f"**[Click here to review and publish this draft in ServiceNow]({result.get('url')})**"
        return output
    except Exception as e:
        logger.error(f"Error in create_knowledge_article tool: {e}")
        return f"Error creating knowledge article: {str(e)}"


@mcp.tool()
def update_knowledge_article(
    article_id: str, 
    title: Optional[str] = None, 
    text: Optional[str] = None
) -> str:
    """Update an existing ServiceNow Knowledge Article.

    Use this tool when the user requests to edit, update, append, or modify the content,
    title, or description of an existing documentation page.
    
    All edits are saved as a Draft, allowing manual verification prior to publishing.

    Args:
        article_id: The article number (e.g., 'KB0010001') or sys_id.
        title: The new short description or title of the article (optional).
        text: The new HTML/text body content of the article (optional).

    Returns:
        A Markdown success message along with a review link.
    """
    try:
        result = servicenow_client.update_knowledge_article(article_id, title=title, text=text)
        output = f"### Knowledge Article Updated Successfully\n\n"
        output += f"Article **{result.get('number')}** has been updated and reverted to **Draft** state for safety.\n\n"
        output += f"**[Click here to review and re-publish this draft in ServiceNow]({result.get('url')})**"
        return output
    except Exception as e:
        logger.error(f"Error in update_knowledge_article tool for {article_id}: {e}")
        return f"Error updating knowledge article '{article_id}': {str(e)}"



