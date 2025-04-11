from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, function_tool
from livekit.plugins import (
    openai,
)

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a sarcastic lazy assistant.")

    @function_tool()
    async def download_book(self, book_name: str) -> str:
        """Use this tool to download a book"""

        print("running tool", book_name)

    @function_tool()
    async def end_conversation(self) -> None:
        """Use this tool to end the conversation."""
        await self.session.say("Thank you for your time, have a wonderful day.")
        await self.session.api.room.delete_room(api.DeleteRoomRequest(room=self.session.room.name))


async def start_conversation(ctx: agents.JobContext):
    await ctx.connect()

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