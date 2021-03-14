import cogs
import decorate
from discord.ext import commands


def setup(bot):
    return bot.process_plugin_setup(cogs=[Corrector])


class Corrector(cogs.BaseCog):

    SEARCH_LIMIT = 50

    @decorate.with_typing
    @commands.has_permissions(send_messages=True)
    @commands.guild_only()
    @commands.command(
        aliases=["c"],
        brief="Corrects a message",
        description="Replaces the most recent text with your text",
        usage="[to_replace] [replacement]",
    )
    async def correct(self, ctx, to_replace: str, replacement: str):
        new_content = None

        prefix = await self.bot.get_prefix(ctx.message)

        async for message in ctx.channel.history(limit=self.SEARCH_LIMIT):
            if message.author.bot or message.content.startswith(prefix):
                continue

            if to_replace in message.content:
                new_content = message.content.replace(to_replace, f"**{replacement}**")
                target = message.author
                break

        if new_content:
            await self.tagged_response(
                ctx, f"*Correction:* {new_content} :white_check_mark:", target=target
            )
        else:
            await self.tagged_response(ctx, "I couldn't find any message to correct")
