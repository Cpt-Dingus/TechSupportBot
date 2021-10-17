import json
import re

import base
import discord
import munch


def setup(bot):
    bot.process_plugin_setup(cogs=[CDIParser, SpeccyParser, HWInfoParser])


class CDIParser(base.MatchCog):

    API_URL = "http://134.122.122.133"
    ICON_URL = "https://cdn.icon-icons.com/icons2/24/PNG/256/harddiskdrive_hardware_discodur_2522.png"

    async def match(self, config, ctx, content):
        if not ctx.message.attachments:
            return False

        attachment = ctx.message.attachments[0]

        if attachment.filename.lower().endswith(".txt"):
            return attachment.url

        return False

    async def response(self, _, ctx, __, result):
        confirmed = await self.bot.confirm(
            ctx,
            "Is this a Crystal Disk Info (CDI) file?",
            delete_after=True,
        )
        if not confirmed:
            return

        confirmed = await self.bot.confirm(
            ctx,
            "Great! Would you like me to parse the results?",
            delete_after=True,
        )
        if not confirmed:
            return

        found_message = await self.bot.send_with_mention(
            ctx, "Parsing CDI results now..."
        )

        api_response = await self.call_api(result)

        try:
            response_text = await api_response.text()
            response_data = munch.munchify(json.loads(response_text))
        except Exception as e:
            await self.bot.send_with_mention(
                ctx, "I was unable to convert the parse results to JSON"
            )
            log_channel = await self.bot.get_log_channel_from_guild(
                ctx.guild, "logging_channel"
            )
            await self.bot.logger.error(
                "Could not deserialize CDI parse response to JSON",
                exception=e,
                channel=log_channel,
            )
            return await found_message.delete()

        try:
            embed = await self.generate_embed(ctx, response_data)
            await self.bot.send_with_mention(ctx, embed=embed)
        except Exception as e:
            await self.bot.send_with_mention(
                ctx, "I had trouble reading the HWInfo logs"
            )
            log_channel = await self.bot.get_log_channel_from_guild(
                ctx.guild, "logging_channel"
            )
            await self.bot.logger.error(
                "Could not read CDI data",
                exception=e,
                channel=log_channel,
            )

        return await found_message.delete()

    async def call_api(self, speccy_id):
        response = await self.bot.http_call(
            "get",
            f"{self.API_URL}/?cdi={speccy_id}&json=true",
            get_raw_response=True,
        )
        return response

    async def generate_embed(self, ctx, response_data):
        total_drives = len(response_data.keys())

        embed = discord.Embed(
            title=f"CDI Results for {ctx.author}",
            description=f"{total_drives} total drive(s)",
        )

        for drive_data in response_data.values():
            drive_name = drive_data.get("Model", "Unknown")
            cdi_health = drive_data.get("CDI Health", "Unknown")
            consult_health = drive_data.get("r/TS Health", "Unknown")
            embed.add_field(
                name=f"`{drive_name}`",
                value=f"{cdi_health} | {consult_health}",
                inline=False,
            )

        embed.set_thumbnail(url=self.ICON_URL)

        return embed


class SpeccyParser(base.MatchCog):

    URL_PATTERN = r"http://speccy.piriform.com/results/[a-zA-Z0-9]+"
    API_URL = "http://134.122.122.133"
    ICON_URL = "https://cdn.icon-icons.com/icons2/195/PNG/256/Speccy_23586.png"

    async def match(self, config, ctx, content):
        matches = re.findall(self.URL_PATTERN, content, re.MULTILINE)
        return matches

    async def response(self, _, ctx, __, result):
        speccy_id = result[0].split("/")[-1]
        if not speccy_id:
            return

        confirmed = await self.bot.confirm(
            ctx,
            "Speccy link detected. Would you like me to parse the results?",
            delete_after=True,
        )
        if not confirmed:
            return

        found_message = await self.bot.send_with_mention(
            ctx, "Parsing Speccy results now..."
        )

        api_response = await self.call_api(speccy_id)
        response_text = await api_response.text()

        try:
            response_data = munch.munchify(json.loads(response_text))
            parse_status = response_data.get("Status", "Unknown")
        except Exception as e:
            response_data = None
            parse_status = "Error"
            log_channel = await self.bot.get_log_channel_from_guild(
                ctx.guild, "logging_channel"
            )
            await self.bot.logger.error(
                "Could not deserialize Speccy parse response to JSON",
                exception=e,
                channel=log_channel,
            )

        if parse_status == "Parsed":
            try:
                embed = await self.generate_embed(ctx, response_data)
                await self.bot.send_with_mention(ctx, embed=embed)
            except Exception as e:
                await self.bot.send_with_mention(
                    ctx, "I had trouble reading the Speccy results"
                )
                log_channel = await self.bot.get_log_channel_from_guild(
                    ctx.guild, "logging_channel"
                )
                await self.bot.logger.error(
                    "Could not read Speccy results",
                    exception=e,
                    channel=log_channel,
                )
        else:
            await self.bot.send_with_mention(
                ctx,
                f"I was unable to parse that Speccy link (parse status = {parse_status})",
            )

        await found_message.delete()

    async def call_api(self, speccy_id):
        response = await self.bot.http_call(
            "get",
            f"{self.API_URL}/?speccy={speccy_id}&json=true",
            get_raw_response=True,
        )
        return response

    async def generate_embed(self, ctx, response_data):
        embed = discord.Embed(
            title=f"Speccy Results for {ctx.author}", description=response_data.Link
        )

        # define the order of rendering and any metadata for each render
        order = [
            {"key": "Yikes", "transform": "Yikes Score"},
            {"key": "HardwareSummary", "transform": "HW Summary"},
            {"key": "HardwareCheck", "transform": "HW Check"},
            {"key": "OSCheck", "transform": "OS Check"},
            {"key": "SecurityCheck", "transform": "Security"},
            {"key": "SoftwareCheck", "transform": "SW Check"},
        ]

        for section in order:
            key = section.get("key")
            if not key:
                continue

            content = response_data.get(key)
            if not content:
                continue

            try:
                content = self.generate_multiline_content(content)
            except Exception:
                continue

            embed.add_field(
                name=f"__{section.get('transform', key.upper())}__",
                value=content,
                inline=False,
            )

        embed.set_thumbnail(url=self.ICON_URL)

        yikes_score = response_data.get("Yikes", 0)
        if yikes_score > 3:
            embed.color = discord.Color.red()
        elif yikes_score > 0:
            embed.color = discord.Color.gold()
        else:
            embed.color = discord.Color.green()

        return embed

    def generate_multiline_content(self, check_data):
        if not isinstance(check_data, dict):
            return check_data

        result = ""
        for key, value in check_data.items():
            if isinstance(value, list):
                value = ", ".join(value)

            if not value:
                continue

            result += f"**{key}**: {value}\n"

        return result


class HWInfoParser(base.MatchCog):

    API_URL = "http://134.122.122.133"
    ICON_URL = (
        "https://cdn.icon-icons.com/icons2/39/PNG/128/hwinfo_info_hardare_6211.png"
    )

    async def match(self, _, ctx, __):
        if not ctx.message.attachments:
            return False

        attachment = ctx.message.attachments[0]

        if attachment.filename.lower().endswith(".csv"):
            return attachment.url

        return False

    async def response(self, _, ctx, __, result):
        confirmed = await self.bot.confirm(
            ctx,
            "If this is a HWINFO log file, I can try parsing it. Would you like me to do that?",
            delete_after=True,
        )
        if not confirmed:
            return

        found_message = await self.bot.send_with_mention(
            ctx, "Parsing HWInfo logs now..."
        )

        api_response = await self.call_api(result)

        try:
            response_text = await api_response.text()
            response_data = munch.munchify(json.loads(response_text))
        except Exception as e:
            await self.bot.send_with_mention(
                ctx, "I was unable to convert the parse results to JSON"
            )
            log_channel = await self.bot.get_log_channel_from_guild(
                ctx.guild, "logging_channel"
            )
            await self.bot.logger.error(
                "Could not deserialize HWInfo parse response to JSON",
                exception=e,
                channel=log_channel,
            )
            return await found_message.delete()

        try:
            embed = await self.generate_embed(ctx, response_data)
            await self.bot.send_with_mention(ctx, embed=embed)
        except Exception as e:
            await self.bot.send_with_mention(
                ctx, "I had trouble reading the HWInfo logs"
            )
            log_channel = await self.bot.get_log_channel_from_guild(
                ctx.guild, "logging_channel"
            )
            await self.bot.logger.error(
                "Could not read HWInfo logs",
                exception=e,
                channel=log_channel,
            )

        return await found_message.delete()

    async def call_api(self, hwinfo_url):
        response = await self.bot.http_call(
            "get",
            f"{self.API_URL}/?hwinfo={hwinfo_url}&json=true",
            get_raw_response=True,
        )
        return response

    async def generate_embed(self, ctx, response_data):
        embed = discord.Embed(
            title=f"HWInfo Summary for {ctx.author}", description="min/average/max"
        )

        summary = ""
        for key, value in response_data.items():
            if key == "ToC":
                continue
            summary += f"**{key.upper()}**: {value}\n"

        embed.add_field(name="__Summary__", value=summary)

        toc_content = ""
        for key, value in response_data.get("ToC", {}).items():
            toc_content += f"**{key.upper()}**: {value}\n"

        embed.add_field(
            name="__Temperatures of Concern__", value=toc_content, inline=False
        )

        embed.set_thumbnail(url=self.ICON_URL)

        return embed
