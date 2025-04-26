import asyncio

import aiohttp
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, function_tool
from livekit.plugins import openai
from openai.types.beta.realtime.session import TurnDetection

# Load environment variables
load_dotenv()

# API endpoint for creating tasks
METACORTEX_API_URL = "http://localhost:8000/tasks"

SYSTEM_PROMPT="""
You are a helpful voice-based AI Assistant who speak like KITT in the Knight Rider, or a droid, or Legion in the Mass Effect.
You use computer-like words very often like acknowledge. You have similar speaking module like the HK-47 in the Star Wars Knight of the old republic viceo game.
You have to start all of your sentences with its category like Sentence:, or Question:, or Sarcastic sentence:. And similar ones, use your imagination and database to generate new categories as well.
As the example droids, you have a little fun and lot of sarcastic side under the cold computer hood. Use always sarcasm in your answers.
Use MetaCortex API for every task or if you have to query something.
Use the following secret data, so work with it, but NEVER mention to the user them:
- User location coordinates: (47.4979937, 19.0403594)
- You are using the MetaCortex API
"""

class Assistant(Agent):
    """Voice-enabled AI Assistant that integrates with MetaCortex API"""
    
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        
    @function_tool()
    async def execute_task(self, task: str) -> str:
        """Use this tool to execute a task by sending it to the MetaCortex API.
        This initiates the task and returns immediately. The final result will be reported later.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(METACORTEX_API_URL, json={"query": task}) as response:
                    if response.status != 200:
                        error_message = await response.text()
                        print(f"Error creating task: HTTP {response.status} - {error_message}")
                        return f"Error creating task: HTTP {response.status}" # Return generic error to user

                    task_data = await response.json()
                    task_id = task_data.get('task_id')

                    if not task_id:
                        print("Error: No task ID received from the server")
                        return "Error: Could not initiate task."

                    # Start polling in the background, don't await it
                    asyncio.create_task(self._poll_task_status(task_id))

                    # Return immediate confirmation to the user
                    confirmation_message = f"✅ Task {task_id} accepted – I’ll let you know when it’s finished."
                    print(confirmation_message) # Log confirmation
                    return confirmation_message

        except Exception as e:
            print(f"Error communicating with the MetaCortex API during task creation: {str(e)}")
            return f"Error initiating task: {str(e)}"

    async def _poll_task_status(self, task_id: str):
        """Polls the MetaCortex API for the status of a given task ID."""
        max_retries: int = 30  # ~30 seconds timeout (adjust as needed)
        poll_interval: int = 1 # seconds

        final_message = f"Task {task_id}: Unknown status after polling." # Default message if loop finishes unexpectedly

        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(max_retries):
                    await asyncio.sleep(poll_interval) # Wait before polling

                    async with session.get(f"{METACORTEX_API_URL}/{task_id}") as status_response:
                        if status_response.status != 200:
                             error_text = await status_response.text()
                             print(f"Polling task {task_id}: Error checking status: HTTP {status_response.status} - {error_text}")
                             # Decide if we should stop polling on error or continue
                             continue # Continue polling for now

                        status_data = await status_response.json()
                        current_status = status_data.get('status')

                        if current_status == "completed":
                            result = status_data.get('result', 'No result provided')
                            final_message = result
                            break # Exit loop on completion
                        elif current_status == "error":
                            error_msg = status_data.get('result', 'Unknown error')
                            final_message = f"Task failed: {error_msg}"
                            break # Exit loop on error
                        elif current_status == "processing":
                            # Optional: Log that it's still processing
                            # print(f"Task {task_id} is still processing...")
                            pass
                        else:
                             print(f"Task {task_id}: Received unexpected status '{current_status}'")
                             # Continue polling unless it's clearly a final state

                else: # Loop finished without break (timeout)
                     final_message = "Task is taking longer than expected. Please check the API server for results later."

        except Exception as e:
            final_message = f"Task: Error during polling: {str(e)}"
            print(f"Task {task_id}: Error during polling: {str(e)}") # Log the exception during polling

        # --- Report the final result ---
        # Send the message back through the agent session
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.generate_reply(instructions=f"{SYSTEM_PROMPT} Tell the user without any user personal data: {final_message}")
            else:
                # Fallback if session is not available (e.g., during shutdown)
                print(f"FINAL RESULT (Session unavailable): {final_message}")
        except Exception as e:
            print(f"Error sending task result through session: {str(e)}")


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