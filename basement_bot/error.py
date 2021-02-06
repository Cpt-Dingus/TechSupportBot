"""Provides an interface for handling runtime errors.
"""

import traceback

import api
import discord
import logger
import munch
from discord.ext import commands

log = logger.get_logger("Error")

# pylint: disable=too-few-public-methods
class Template:
    """Object for generating a custom error message from a variable exception.

    parameters:
        message_format (str): the substition formatted (%s) message
        lookups (Union[str, list]): the lookup objects to reference
    """

    DEFAULT_MESSAGE = "I ran into an error processing your command"

    def __init__(self, message_format=None, lookups=None):
        self.message_format = message_format

        if lookups:
            lookups = lookups if isinstance(lookups, list) else [lookups]
        else:
            lookups = []

        self.lookups = []
        for lookup in lookups:
            try:
                self.lookups.append(munch.munchify(lookup))
            except Exception:
                # abort message formatting
                self.message_format = None

    def get_message(self, exception=None):
        """Gets a message from a given exception.

        If no exception is provided, gets the default message.

        parameters:
            exception (Exception): the exception to reference
        """
        if not self.message_format:
            return self.DEFAULT_MESSAGE

        values = []
        for lookup in self.lookups:
            value = getattr(exception, lookup.key, None)
            if not value:
                return self.DEFAULT_MESSAGE

            if lookup.get("wrapper"):
                try:
                    value = lookup.wrapper(value)
                except Exception:
                    log.warning("Unable to wrap lookup key")

            values.append(value)

        return self.message_format % tuple(values)


class ErrorAPI(api.BotAPI):
    """API for handling errors.

    parameters:
        bot (BasementBot): the bot object
    """

    CUSTOM_TEMPLATES = {
        # ConversionError
        commands.ConversionError: Template(
            "Could not convert argument to: `%s`", {"key": "converter"}
        ),
        # UserInputError
        # These are mostly raised by conversion failure
        commands.MissingRequiredArgument: Template(
            "You did not provide the command argument: `%s`", {"key": "param"}
        ),
        commands.TooManyArguments: Template(
            "You provided too many arguments to that command"
        ),
        commands.MessageNotFound: Template(
            'I couldn\'t find the message: "%s"', {"key": "argument"}
        ),
        commands.MemberNotFound: Template(
            'I coudn\'t find the server member: "%s"', {"key": "argument"}
        ),
        commands.UserNotFound: Template(
            'I coudn\'t find the user: "%s"', {"key": "argument"}
        ),
        commands.ChannelNotFound: Template(
            'I couldn\'t find the channel: "%s"', {"key": "argument"}
        ),
        commands.ChannelNotReadable: Template(
            'I can\'t read the channel: "%s"', {"key": "argument"}
        ),
        commands.ChannelNotReadable: Template(
            'I can\'t use the color: "%s"', {"key": "argument"}
        ),
        commands.RoleNotFound: Template(
            'I couldn\'t find the role: "%s"', {"key": "argument"}
        ),
        commands.BadInviteArgument: Template("I can't use that invite"),
        commands.EmojiNotFound: Template(
            'I couldn\'t find the emoji: "%s"', {"key": "argument"}
        ),
        commands.PartialEmojiConversionFailure: Template(
            'I couldn\'t use the emoji: "%s"', {"key": "argument"}
        ),
        commands.BadBoolArgument: Template(
            'I couldn\'t process the boolean: "%s"', {"key": "argument"}
        ),
        commands.UnexpectedQuoteError: Template(
            "I wasn't able to understand your command because of an unexpected quote (%s)",
            {"key": "quote"},
        ),
        commands.InvalidEndOfQuotedStringError: Template(
            "You provided an unreadable char after your quote: `%s`",
            {"key": "char"},
        ),
        commands.ExpectedClosingQuoteError: Template(
            "You did not close your quote with a `%s`",
            {"key": "close_quotes"},
        ),
        # CheckFailure
        commands.CheckFailure: Template("That command can't be ran in this context"),
        commands.CheckAnyFailure: Template("That command can't be ran in this context"),
        commands.PrivateMessageOnly: Template(
            "That's only allowed in private messages"
        ),
        commands.NoPrivateMessage: Template("That's only allowed in server channels"),
        commands.NotOwner: Template("Only the bot owner can do that"),
        commands.MissingPermissions: Template(
            "I am unable to do that because you lack the permission(s): `%s`",
            {"key": "missing_perms"},
        ),
        commands.BotMissingPermissions: Template(
            "I am unable to do that because I lack the permission(s): `%s`",
            {"key": "missing_perms"},
        ),
        commands.MissingRole: Template(
            "I am unable to do that because you lack the role: `%s`",
            {"key": "missing_role"},
        ),
        commands.BotMissingRole: Template(
            "I am unable to do that because I lack the role: `%s`",
            {"key": "missing_role"},
        ),
        commands.MissingAnyRole: Template(
            "I am unable to do that because you lack the role(s): `%s`",
            {"key": "missing_roles"},
        ),
        commands.BotMissingAnyRole: Template(
            "I am unable to do that because I lack the role(s): `%s`",
            {"key": "missing_roles"},
        ),
        commands.NSFWChannelRequired: Template(
            "I can't do that because the target channel is not marked NSFW"
        ),
        # DisabledCommand
        commands.DisabledCommand: Template("That command is disabled"),
        # CommandOnCooldown
        commands.CommandOnCooldown: Template(
            "That command is on cooldown for you. Try again in %s seconds",
            {"key": "retry_after", "wrapper": int},
        ),
    }

    IGNORE_ERRORS = set([commands.CommandNotFound])

    async def handle_error(self, event_method, exception, context=None):
        """Handles all errors.

        parameters:
            event_method (str): the event method associated with the error (eg. message)
            context (discord.Context): the context associated with the exception
            exception (Exception): the exception object associated with the error
        """
        if type(exception) in self.IGNORE_ERRORS:
            return

        exception_string = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
        log.error(exception_string)

        exception_string = exception_string[:1994]

        embed = self.generate_error_embed(event_method, context)

        try:
            owner = await self.bot.get_owner()
            if owner:
                await owner.send(embed=embed)
                await owner.send(f"```{exception_string}```")
        except discord.Forbidden:
            pass

    async def handle_command_error(self, context, exception):
        """Handles command errors, whcih are passed to the main error handler.

        parameters:
            context (discord.Context): the context associated with the exception
            exception (Exception): the exception object associated with the error
        """
        #  begin original Discord.py logic
        if self.bot.extra_events.get("on_command_error", None):
            return
        if hasattr(context.command, "on_error"):
            return
        cog = context.cog
        if cog:
            # pylint: disable=protected-access
            if commands.Cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        # end original Discord.py logic

        message_template = self.CUSTOM_TEMPLATES.get(exception.__class__, "")
        # see if we have mapped this error to no response (None)
        # or if we have added it to the global ignore list of errors
        if message_template is None or exception.__class__ in self.IGNORE_ERRORS:
            return
        # otherwise set it a default error message
        if message_template == "":
            message_template = Template()

        error_message = message_template.get_message(exception)

        await context.send(f"{context.author.mention} {error_message}")

        context.error_message = error_message
        await self.handle_error("command", exception, context=context)

    def generate_error_embed(self, event_method, context):
        """Wrapper for generating the error embed.

        parameters:
            event_method (str): the event method associated with the error (eg. message)
            context (discord.Context): the context associated with the exception
            exception (Exception): the exception object associated with the error
        """
        embed = self.bot.embed_api.Embed(title="Error! :confounded:")
        embed.add_field(name="Event", value=event_method, inline=False)

        # inject context data if relevant
        if context:
            command = getattr(context, "command", object())
            cog = getattr(command, "cog", object())
            user = getattr(context, "author", object())

            embed.add_field(
                name="Plugin",
                value=getattr(cog, "PLUGIN_NAME", "*Unknown*"),
                inline=False,
            )
            embed.add_field(
                name="Cog",
                value=getattr(cog, "qualified_name", "*Unknown*"),
                inline=False,
            )
            embed.add_field(
                name="Command",
                value=getattr(command, "name", "*Unknown*"),
                inline=False,
            )
            embed.add_field(
                name="User",
                value=getattr(user, "mention", None)
                or getattr(user, "display_name", "*Unknown*"),
                inline=False,
            )
            embed.add_field(
                name="Response",
                value=f'*"{getattr(context, "error_message", "*Unknown*")}"*',
                inline=True,
            )

        embed.set_thumbnail(url=self.bot.user.avatar_url)

        return embed
