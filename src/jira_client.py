"""
Jira Cloud REST API v3 Wrapper.

Provides a clean interface for creating and managing Jira issues
using Basic Auth (email + API token).
"""

import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx
from pydantic import BaseModel, Field, SecretStr

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JiraIssue(BaseModel):
    """Jira issue response model."""
    id: str
    key: str
    self: str
    fields: Dict[str, Any] = Field(default_factory=dict)


class JiraClient:
    """Jira Cloud REST API v3 Client."""
    
    def __init__(
        self,
        base_url: str = None,
        email: str = None,
        api_token: SecretStr = None,
        project_key: str = None,
        issue_type: str = None,
    ):
        self.base_url = (base_url or settings.jira_base_url).rstrip("/")
        self.email = email or settings.jira_email
        self.api_token = (api_token or settings.jira_api_token).get_secret_value()
        self.project_key = project_key or settings.jira_project_key
        self.issue_type = issue_type or settings.jira_issue_type
        
        if not all([self.base_url, self.email, self.api_token, self.project_key]):
            raise ValueError("Jira configuration incomplete: base_url, email, api_token, and project_key are required")
        
        # Create Basic Auth header
        auth_string = f"{self.email}:{self.api_token}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
    
    async def create_issue(self, defect_data) -> Optional[Dict[str, Any]]:
        """
        Create a Jira issue for a defect.
        
        Args:
            defect_data: JiraDefect model or dict with defect details
            
        Returns:
            Created issue dict or None if failed
        """
        # Convert to dict if Pydantic model
        if hasattr(defect_data, "model_dump"):
            defect_data = defect_data.model_dump()
        
        # Build Jira issue payload
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": defect_data.get("summary", "Automated Test Failure"),
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": defect_data.get("description", "")}
                            ]
                        }
                    ]
                },
                "issuetype": {"name": self.issue_type},
                "priority": {"name": defect_data.get("priority", "Medium")},
                "labels": defect_data.get("labels", ["automated-test", "ai-generated"]),
                "components": [{"name": c} for c in defect_data.get("components", [])],
            }
        }
        
        # Add custom fields for reproduction steps, etc.
        # These would need to match your Jira instance's custom field IDs
        custom_fields = self._build_custom_fields(defect_data)
        payload["fields"].update(custom_fields)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/rest/api/3/issue",
                json=payload,
            )
            response.raise_for_status()
            
            issue = response.json()
            logger.info(f"Created Jira issue: {issue.get('key')}")
            return issue
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create Jira issue: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to create Jira issue: {e}")
            return None
    
    def _build_custom_fields(self, defect_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build custom fields for Jira issue."""
        # These field IDs are example - replace with your actual Jira custom field IDs
        custom_fields = {}
        
        # Example custom field mappings (configure based on your Jira instance)
        # custom_fields["customfield_10001"] = defect_data.get("steps_to_reproduce", [])
        # custom_fields["customfield_10002"] = defect_data.get("expected_behavior", "")
        # custom_fields["customfield_10003"] = defect_data.get("actual_behavior", "")
        # custom_fields["customfield_10004"] = defect_data.get("root_cause_analysis", "")
        # custom_fields["customfield_10005"] = defect_data.get("test_case_id", "")
        
        return custom_fields
    
    async def add_comment(self, issue_key: str, comment: str) -> bool:
        """Add comment to existing issue."""
        try:
            response = await self.client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                json={
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": comment}]
                            }
                        ]
                    }
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to add comment to {issue_key}: {e}")
            return False
    
    async def add_attachment(self, issue_key: str, file_path: str, file_name: str = None) -> bool:
        """Add attachment to issue."""
        try:
            import os
            if not os.path.exists(file_path):
                logger.warning(f"Attachment file not found: {file_path}")
                return False
            
            file_name = file_name or os.path.basename(file_path)
            
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "application/octet-stream")}
                response = await self.client.post(
                    f"{self.base_url}/rest/api/3/issue/{issue_key}/attachments",
                    files=files,
                    headers={"X-Atlassian-Token": "no-check"},
                )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to add attachment to {issue_key}: {e}")
            return False
    
    async def link_issues(self, issue_key: str, linked_issue_key: str, link_type: str = "Relates") -> bool:
        """Link two issues together."""
        try:
            response = await self.client.post(
                f"{self.base_url}/rest/api/3/issueLink",
                json={
                    "type": {"name": link_type},
                    "inwardIssue": {"key": issue_key},
                    "outwardIssue": {"key": linked_issue_key},
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to link issues {issue_key} and {linked_issue_key}: {e}")
            return False
    
    async def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """Transition issue to a new status."""
        try:
            # Get available transitions
            response = await self.client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
            )
            response.raise_for_status()
            transitions = response.json().get("transitions", [])
            
            # Find matching transition
            transition_id = None
            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break
            
            if not transition_id:
                logger.warning(f"Transition '{transition_name}' not found for {issue_key}")
                return False
            
            # Perform transition
            response = await self.client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                json={"transition": {"id": transition_id}},
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to transition {issue_key}: {e}")
            return False
    
    async def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search issues using JQL."""
        try:
            response = await self.client.get(
                f"{self.base_url}/rest/api/3/search",
                params={"jql": jql, "maxResults": max_results},
            )
            response.raise_for_status()
            return response.json().get("issues", [])
        except Exception as e:
            logger.error(f"JQL search failed: {e}")
            return []
    
    async def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get issue details."""
        try:
            response = await self.client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_jira_client() -> JiraClient:
    """Factory function to create JiraClient from settings."""
    return JiraClient()


# Convenience function for quick defect creation
async def create_defect_issue(defect_data) -> Optional[Dict[str, Any]]:
    """Create a defect issue using default Jira client."""
    async with create_jira_client() as client:
        return await client.create_issue(defect_data)