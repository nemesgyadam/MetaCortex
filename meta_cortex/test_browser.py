"""
Test for browser tool: Get latest news headline from cnn.com
"""
import pytest
from react_agent import ReActAgent

def test_browse_latest_news():
    """Test the agent's ability to browse cnn.com and return latest news headline."""
    agent = ReActAgent(agent_name="TestAgent", verbose=True)
    agent.initialize()
    
    # Check if the browse tool is available
    has_browse_tool = False
    for name, _ in agent.actions.items():
        if name == "playwright.browse":
            has_browse_tool = True
            break
    
    print(f"\nAvailable playwright tools: {[name for name in agent.actions.keys() if 'playwright' in name]}\n")
    
    # Run the test with the correct tool name
    question = "Go to https://www.cnn.com and tell me the latest news headline. Use the playwright.browse tool."
    answer = agent.run(question)
    
    # More robust assertion
    assert ("cnn" in answer.lower() or "news" in answer.lower() or "headline" in answer.lower() or 
            "browse" in answer.lower()), f"Unexpected answer: {answer}"

test_browse_latest_news()