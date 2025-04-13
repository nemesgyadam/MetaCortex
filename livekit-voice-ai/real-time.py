import asyncio
import aiohttp
import json
from typing import Optional
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, function_tool
from livekit.plugins import openai

# Load environment variables
load_dotenv()

# API endpoint for creating tasks
METACORTEX_API_URL = "http://localhost:8000/tasks"


class Assistant(Agent):
    """Voice-enabled AI Assistant that integrates with MetaCortex API"""
    
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice assistant that can execute tasks using MetaCortex.")
        
    @function_tool()
    async def execute_task(self, task: str) -> str:
        """Use this tool to execute a task by sending it to the MetaCortex API"""
        # Do not use session.say() as it requires TTS configuration
        # Just proceed with the task execution
        
        try:
            # Create a task through the API
            async with aiohttp.ClientSession() as session:
                # Send the task creation request
                async with session.post(METACORTEX_API_URL, json={"query": task}) as response:
                    if response.status != 200:
                        return f"Error creating task: HTTP {response.status} - {await response.text()}"
                    
                    # Parse the response to get the task ID
                    task_data = await response.json()
                    task_id = task_data.get('task_id')
                    
                    if not task_id:
                        return "Error: No task ID received from the server"
                    
                    # Don't use session.say() as it requires TTS configuration
                    # Just log the message
                    print(f"Task created with ID: {task_id}. Waiting for results...")
                    
                    # Poll for results (with timeout)
                    max_retries: int = 30  # 30 seconds timeout
                    for _ in range(max_retries):
                        # Check task status
                        async with session.get(f"{METACORTEX_API_URL}/{task_id}") as status_response:
                            if status_response.status != 200:
                                return f"Error checking task status: HTTP {status_response.status}"
                            
                            status_data = await status_response.json()
                            current_status = status_data.get('status')
                            
                            # If the task is completed, return the result
                            if current_status == "completed":
                                result = status_data.get('result', 'No result provided')
                                return result
                            # If there was an error, return the error
                            elif current_status == "error":
                                error_msg = status_data.get('result', 'Unknown error')
                                return f"Error executing task: {error_msg}"
                        
                        # Wait before polling again
                        await asyncio.sleep(1)
                    
                    # If we've reached the maximum number of retries
                    return "Task is taking longer than expected. Please check the API server for results later."
        
        except Exception as e:
            return f"Error communicating with the MetaCortex API: {str(e)}"
        
    @function_tool()
    async def end_conversation(self) -> None:
        """Use this tool to end the conversation."""
        print("Ending conversation...")
        await self.session.api.room.delete_room(agents.api.DeleteRoomRequest(room=self.session.room.name))


async def start_conversation(ctx: agents.JobContext):
    await ctx.connect()
    
    # Configure a text-only model to avoid TTS errors
    # The error shows it's having trouble with realtime models
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(voice="ash"),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )

    await session.generate_reply(instructions="Greet the user sarcastically.")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=start_conversation))