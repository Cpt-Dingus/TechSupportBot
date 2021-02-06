import cogs
from discord.ext import commands


def setup(bot):
    bot.add_cog(Greeter(bot))


class Greeter(cogs.BasicPlugin):

    PLUGIN_NAME = __name__
    HAS_CONFIG = False

    @commands.command(
        name="hello",
        brief="Says hello to the bot",
        description="Says hello to the bot (because they are doing such a great job!)",
        usage="",
    )
    async def hello(self, ctx):
        # H, E, Y
        emojis = ["🇭", "🇪", "🇾"]
        for emoji in emojis:
            await ctx.message.add_reaction(emoji)
