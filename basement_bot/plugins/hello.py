from cogs import BasicPlugin
from discord.ext import commands
from utils.helpers import emoji_reaction


def setup(bot):
    bot.add_cog(Greeter(bot))


class Greeter(BasicPlugin):

    PLUGIN_NAME = __name__
    HAS_CONFIG = False

    @commands.command(
        name="hello",
        brief="Hello!",
        description="Returns the greeting 'HEY' as a reaction to the original command message.",
        usage="",
    )
    async def hello(self, ctx):
        # H, E, Y
        # emojis = [u"\U0001F1ED", u"\U0001F1EA", u"\U0001F1FE"]
        # await emoji_reaction(ctx, emojis)
        from discord import Embed

        embed = Embed()
        embed.add_field(value="bitch")
        await ctx.send(embed=embed)
