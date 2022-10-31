from .fakemoncord import Fakemoncord


async def setup(bot):
    cog = Fakemoncord(bot)
    await cog.initalize()
    bot.add_cog(cog)
