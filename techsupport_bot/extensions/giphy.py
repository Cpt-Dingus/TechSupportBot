"""Module for giphy extension in the bot."""
import base
import ui
import util
from base import auxiliary
from discord.ext import commands


async def setup(bot):
    """Method to add giphy to the config."""
    await bot.add_cog(Giphy(bot=bot))


class Giphy(base.BaseCog):
    """Class for the giphy extension."""

    GIPHY_URL = "http://api.giphy.com/v1/gifs/search?q={}&api_key={}&limit={}"
    SEARCH_LIMIT = 10

    @staticmethod
    def parse_url(url):
        """Method to parse the url."""
        index = url.find("?cid=")
        return url[:index]

    @util.with_typing
    @commands.guild_only()
    @commands.command(
        name="giphy",
        brief="Grabs a random Giphy image",
        description="Grabs a random Giphy image based on your search",
        usage="[query]",
    )
    async def giphy(self, ctx, *, query: str):
        """Method to send giphy to discord."""
        response = await self.bot.http_call(
            "get",
            self.GIPHY_URL.format(
                query.replace(" ", "+"),
                self.bot.file_config.api.api_keys.giphy,
                self.SEARCH_LIMIT,
            ),
        )

        data = response.get("data")
        if not data:
            await auxiliary.send_deny_embed(
                message=f"No search results found for: *{query}*", channel=ctx.channel
            )
            return

        embeds = []
        for item in data:
            url = item.get("images", {}).get("original", {}).get("url")
            url = self.parse_url(url)
            embeds.append(url)

        await ui.PaginateView().send(ctx.channel, ctx.author, embeds)
