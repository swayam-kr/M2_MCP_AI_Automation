import pytest
from unittest.mock import patch, MagicMock
from backend.mcp_dispatcher import MCPDispatcher, MCPDispatcherError

@pytest.fixture
def dispatcher():
    return MCPDispatcher()

@pytest.fixture
def sample_pulse():
    return {
        "generated_at": "2024-05-01T10:00:00Z",
        "period": "Last 4 weeks",
        "total_reviews_analyzed": 150,
        "themes": [
            {"name": "Bugs", "review_count": 50},
            {"name": "UI issues", "review_count": 30}
        ],
        "top_3_themes": ["Bugs", "UI issues"],
        "quotes": [
            {"text": "Sample quote", "star_rating": 2, "date": "2024-04-20"}
        ],
        "summary": "This is a summary.",
        "action_ideas": ["Fix bugs", "Improve UI"]
    }

@pytest.fixture
def sample_explainer():
    return {
        "asset_class": "Stocks",
        "tone": "neutral",
        "explanation_bullets": ["Bullet 1", "Bullet 2"],
        "official_links": ["https://groww.in/pricing/stocks"],
        "last_checked": "2024-05-01T10:00:00Z"
    }

@patch('backend.mcp_dispatcher.MCPDispatcher._call_mcp_tool')
def test_dispatch_all_gates_off(mock_call, dispatcher, sample_pulse):
    """Test 1: All gates OFF -> No MCP calls made."""
    approvals = {"append_to_doc": False, "create_draft": False, "auto_send": False}
    result = dispatcher.dispatch(sample_pulse, "pulse", approvals, [])
    
    mock_call.assert_not_called()
    assert result["doc"]["status"] == "skipped"
    assert result["draft"]["status"] == "skipped"
    assert result["send"]["status"] == "skipped"

@patch('backend.mcp_dispatcher.MCPDispatcher._call_mcp_tool')
def test_dispatch_all_gates_on(mock_call, dispatcher, sample_explainer):
    """Test 2: All gates ON -> 3 MCP calls made."""
    # Mock return values for doc, draft, send
    mock_call.side_effect = [
        {"result": "mock_rev_id"},      # doc
        {"result": "mock_draft_123"},   # draft
        {"result": "mock_msg_456"}      # send
    ]
    
    approvals = {"append_to_doc": True, "create_draft": True, "auto_send": True}
    recipients = ["ceo@company.com"]
    result = dispatcher.dispatch(sample_explainer, "explainer", approvals, recipients)
    
    assert mock_call.call_count == 3
    assert result["doc"]["status"] == "appended"
    assert result["draft"]["status"] == "created"
    assert result["send"]["status"] == "sent"

@patch('backend.mcp_dispatcher.MCPDispatcher._call_mcp_tool')
def test_dispatch_send_without_draft(mock_call, dispatcher, sample_pulse):
    """Test 3: Auto-send ON but Draft OFF -> Auto-send caught and skipped/error."""
    mock_call.return_value = {"result": "mock_rev_id"} # just in case
    
    approvals = {"append_to_doc": True, "create_draft": False, "auto_send": True}
    result = dispatcher.dispatch(sample_pulse, "pulse", approvals, [])
    
    # Doc should be called
    assert mock_call.call_count == 1
    assert result["doc"]["status"] == "appended"
    assert result["draft"]["status"] == "skipped"
    assert result["send"]["status"] == "error"
    assert "without creating a draft" in result["send"]["error"]

@patch('backend.mcp_dispatcher.MCPDispatcher._call_mcp_tool')
def test_partial_failure_proceeds(mock_call, dispatcher, sample_pulse):
    """Test 4: Doc append fails, but Draft still proceeds independently."""
    # First call fails, second succeeds
    def mock_side_effect(cmd, tool, args):
        if tool == "documents.appendText":
            raise MCPDispatcherError("Google Docs API out of quota")
        elif tool == "gmail.createDraft":
            return {"result": "draft_abc"}
    
    mock_call.side_effect = mock_side_effect
    
    approvals = {"append_to_doc": True, "create_draft": True, "auto_send": False}
    result = dispatcher.dispatch(sample_pulse, "pulse", approvals, ["test@test.com"])
    
    assert mock_call.call_count == 2
    assert result["doc"]["status"] == "error"
    assert "out of quota" in result["doc"]["error"]
    assert result["draft"]["status"] == "created"
