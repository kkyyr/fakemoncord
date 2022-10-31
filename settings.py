import discord
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list

from .abc import MixinMeta
from .pokemixin import poke

_ = Translator("Fakemoncord", __file__)

LOCALES = {
    "english": "en",
    "en": "en",
    "eng": "en",
    "chinese": "tw",
    "tw": "tw",
    "cn": "cn",
    "japan": "jp",
    "japanese": "jp",
    "fr": "fr",
    "french": "fr",
}


class SettingsMixin(MixinMeta):
    """Fakemoncord Settings"""

    @poke.command(usage="type")
    @commands.guild_only()
    async def fsilence(self, ctx, _type: bool = None):
        """Toggle Fakemoncord levelling messages on or off."""
        conf = await self.user_is_global(ctx.author)
        if _type is None:
            _type = not await conf.silence()
        await conf.silence.set(_type)
        if _type:
            await ctx.send(_("Your Fakemoncord levelling messages have been silenced."))
        else:
            await ctx.send(_("Your Fakemoncord levelling messages have been re-enabled!"))
        await self.update_user_cache()

    @poke.command()
    @commands.guild_only()
    async def flocale(self, ctx, locale: str):
        """Set the Fakemoncord locale to use for yourself."""
        if locale.lower() not in LOCALES:
            await ctx.send(
                _(
                    "You've specified an invalid locale. Fakemoncord only supports English, Japanese, Chinese and French."
                )
            )
            return
        conf = await self.user_is_global(ctx.author)
        await conf.locale.set(LOCALES[locale.lower()])
        await ctx.tick()
        await self.update_user_cache()

    @poke.group(name="set")
    @commands.admin_or_permissions(manage_channels=True)
    @commands.guild_only()
    async def fakemoncordset(self, ctx):
        """Manage Fakemoncord settings"""

    @fakemoncordset.command(usage="type")
    @commands.admin_or_permissions(manage_guild=True)
    async def toggle(self, ctx, _type: bool = None):
        """Toggle Fakemoncord on or off."""
        if _type is None:
            _type = not await self.config.guild(ctx.guild).toggle()
        await self.config.guild(ctx.guild).toggle.set(_type)
        if _type:
            await ctx.send(_("Fakemoncord has been toggled on!"))
            return
        await ctx.send(_("Fakemoncord has been toggled off!"))
        await self.update_guild_cache()

    @fakemoncordset.command(usage="type")
    @commands.admin_or_permissions(manage_guild=True)
    async def levelup(self, ctx, _type: bool = None):
        """Toggle levelup messages on or off.

        If active channels are set, level up messages will only be sent in said channels. Otherwise it is ignored.
        If no active channels are set then level up messages will send as normal."""
        if _type is None:
            _type = not await self.config.guild(ctx.guild).levelup_messages()
        await self.config.guild(ctx.guild).levelup_messages.set(_type)
        if _type:
            await ctx.send(_("Pokémon levelup messages have been toggled on!"))
            return
        await ctx.send(_("Pokémon levelup messages have been toggled off!"))
        await self.update_guild_cache()

    @fakemoncordset.command()
    @commands.admin_or_permissions(manage_channels=True)
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the channel(s) that Pokémon are to spawn in."""
        async with self.config.guild(ctx.guild).activechannels() as channels:
            if channel.id in channels:
                channels.remove(channel.id)
                await ctx.send(_("Channel has been removed."))
            else:
                channels.append(channel.id)
        await self.update_guild_cache()
        await ctx.tick()

    @fakemoncordset.command()
    @commands.admin_or_permissions(manage_channels=True)
    async def whitelist(self, ctx, channel: discord.TextChannel):
        """Whitelist channels that will contribute to Pokémon spawning."""
        async with self.config.guild(ctx.guild).whitelist() as channels:
            if channel.id in channels:
                channels.remove(channel.id)
                await ctx.send(_("Channel has been removed from the whitelist."))
            else:
                channels.append(channel.id)
        await self.update_guild_cache()
        await ctx.tick()

    @fakemoncordset.command()
    @commands.admin_or_permissions(manage_channels=True)
    async def blacklist(self, ctx, channel: discord.TextChannel):
        """Blacklist channels from contributing to Pokémon spawning."""
        async with self.config.guild(ctx.guild).blacklist() as channels:
            if channel.id in channels:
                channels.remove(channel.id)
                await ctx.send(_("Channel has been removed from the blacklist."))
            else:
                channels.append(channel.id)
        await self.update_guild_cache()
        await ctx.tick()

    @fakemoncordset.command()
    @commands.admin_or_permissions(manage_channels=True)
    async def settings(self, ctx):
        """Overview of pokécord settings."""
        data = await self.config.guild(ctx.guild).all()
        msg = _("**Toggle**: {toggle}\n").format(toggle="Yes" if data["toggle"] else "No")
        msg += _("**Active Channels**: {channels}\n").format(
            channels=humanize_list(
                [ctx.guild.get_channel(x).mention for x in data["activechannels"]]
            )
            if data["activechannels"]
            else "All"
        )
        msg += _("**Blacklist**: {blacklist}\n").format(
            blacklist=humanize_list([ctx.guild.get_channel(x).mention for x in data["blacklist"]])
            if data["blacklist"]
            else "None"
        )
        msg += _("**Whitelist**: {whitelist}\n").format(
            whitelist=humanize_list([ctx.guild.get_channel(x).mention for x in data["whitelist"]])
            if data["whitelist"]
            else "None"
        )
        await ctx.send(msg)

    @fakemoncordset.command(usage="<min amount of messages> <max amount of messages>")
    @commands.is_owner()
    async def spawnchance(self, ctx, _min: int, _max: int):
        """Change the range of messages required for a spawn."""
        if _min < 5:
            return await ctx.send(_("Min must be more than 10."))
        if _max < _min:
            return await ctx.send(_("Max must be more than the minimum."))
        await self.config.spawnchance.set([_min, _max])
        await self.update_spawn_chance()
        await ctx.tick()

    @fakemoncordset.command()
    @commands.is_owner()
    async def spawnloop(self, ctx, state: bool):
        """Turn the bot loop on or off."""
        if state:
            await ctx.send(
                _(
                    "Random spawn loop has been enabled, please reload the cog for this change to take effect."
                )
            )
        else:
            await ctx.send(
                _(
                    "Random spawn loop has been disabled, please reload the cog for this change to take effect."
                )
            )
        await self.config.spawnloop.set(state)
        await ctx.tick()
