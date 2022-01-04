import base
import discord
import util
from discord.ext import commands


def setup(bot):
    bot.add_cog(ISSLocator(bot=bot))


class ISSLocator(base.BaseCog):

    ISS_URL = "http://api.open-notify.org/iss-now.json"
    GEO_URL = "https://geocode.xyz/{},{}?geoit=json"

    @util.with_typing
    @commands.command(
        name="iss",
        brief="Finds the ISS",
        description="Returns the location of the International Space Station (ISS)",
    )
    async def iss(self, ctx):
        # get ISS coordinates
        response = await self.bot.http_call("get", self.ISS_URL)
        if not response:
            await util.send_deny_embed(
                ctx, "I had trouble calling the ISS API. Maybe it's down?"
            )
            return
        coordinates = response.get("iss_position", {})
        longitude, latitude = coordinates.get("longitude"), coordinates.get("latitude")
        if not longitude or not latitude:
            await util.send_deny_embed(
                ctx, "I couldn't find the ISS coordinates from the API response"
            )
            return

        # get location information from coordinates
        location = None
        response = await self.bot.http_call(
            "get", self.GEO_URL.format(latitude, longitude)
        )
        if not response:
            await util.send_deny_embed(
                ctx, "I had trouble calling the GEO API. Maybe it's down?"
            )
            return
        else:
            osmtags = response.get("osmtags", {})
            location = osmtags.get("name")

        if not location:
            location = "Unknown"

        embed = discord.Embed(
            title="ISS Location", description="Track the International Space Station!"
        )
        embed.add_field(name="Location", value=location)
        embed.add_field(name="Latitude", value=latitude)
        embed.add_field(name="Longitude", value=longitude)
        embed.add_field(
            name="Real-time tracking",
            value="https://spotthestation.nasa.gov/tracking_map.cfm",
        )
        embed.set_thumbnail(
            url="https://cdn.icon-icons.com/icons2/1389/PNG/512/internationalspacestation_96150.png"
        )
        embed.color = discord.Color.darker_gray()

        await ctx.send(embed=embed)
