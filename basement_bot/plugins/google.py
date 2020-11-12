from cogs import HttpPlugin
from discord import Embed
from discord.ext import commands
from utils.helpers import paginate, priv_response, tagged_response


def setup(bot):
    bot.add_cog(Googler(bot))


class Googler(HttpPlugin):

    PLUGIN_NAME = __name__
    GOOGLE_URL = "https://www.googleapis.com/customsearch/v1"
    YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/search?part=id&maxResults=1"

    async def get_items(self, url, data):
        data = await self.http_call("get", url, params=data)
        return data.json().get("items")

    @commands.command(
        name="g",
        brief="Googles that for you",
        description=(
            "Returns the top Google search result of the given search terms."
            " Returns nothing if one is not found."
        ),
        usage="[search-terms]",
        help="\nLimitations: Mentions should not be used.",
    )
    async def google(self, ctx, *args):
        if not args:
            await priv_response(ctx, "I can't search for nothing!")
            return

        args = " ".join(args)

        data = {
            "cx": self.config.cse_id,
            "q": args,
            "key": self.config.dev_key,
        }
        if getattr(ctx, "image_search", None):
            data["searchType"] = "image"

        items = await self.get_items(self.GOOGLE_URL, data)

        if not items:
            args = f"*{args}*"
            await priv_response(ctx, f"No search results found for: {args}")
            return

        message = embed = None
        if not getattr(ctx, "image_search", None):
            field_counter = 1
            embeds = []
            for index, item in enumerate(items):
                link = item.get("link")
                snippet = item.get("snippet", "<Details Unknown>").replace("\n", "")
                embed = (
                    Embed(title=f"Results for {args}", value="https://google.com")
                    if field_counter == 1
                    else embed
                )
                embed.add_field(name=link, value=snippet, inline=False)
                if (
                    field_counter == self.config.responses_max
                    or index == len(items) - 1
                ):
                    embed.set_thumbnail(
                        url="https://cdn.icon-icons.com/icons2/673/PNG/512/Google_icon-icons.com_60497.png"
                    )
                    embeds.append(embed)
                    field_counter = 1
                else:
                    field_counter += 1

            await paginate(ctx, embeds=embeds)

        else:
            message = items[0].get("link")
            if not message:
                await priv_response(
                    ctx,
                    "I had an issue processing Google's response... try again later!",
                )
                return

        await tagged_response(ctx, message=message, embed=embed)

    @commands.command(
        name="gis",
        brief="Google Image searches that for you",
        description=(
            "Returns the top Google image search result of the given search terms."
            " Returns nothing if one is not found."
        ),
        usage="[search-terms]",
        help="\nLimitations: Mentions should not be used.",
    )
    async def google_image(self, ctx, *args):
        ctx.image_search = True
        await self.google(ctx, *args)

    @commands.command(
        name="yt",
        brief="Returns top YouTube video result of search terms",
        description=(
            "Returns the top YouTube video result of the given search terms."
            " Returns nothing if one is not found."
        ),
        usage="[search-terms]",
        help="\nLimitations: Mentions should not be used.",
    )
    async def youtube(self, ctx, *args):
        if not args:
            await priv_response(ctx, "I can't search for nothing!")
            return

        args = " ".join(args)
        items = await self.get_items(
            self.YOUTUBE_URL,
            data={
                "q": args,
                "key": self.config.dev_key,
                "type": "video",
            },
        )

        if not items:
            if args:
                args = f"*{args}*"
            await priv_response(ctx, f"No video results found for: {args}")
            return

        video_id = items[0].get("id", {}).get("videoId")
        link = f"http://youtu.be/{video_id}"

        await tagged_response(ctx, link)
