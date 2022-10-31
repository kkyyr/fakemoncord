import asyncio
import copy
import json

import discord
import tabulate
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import *
from redbot.core.utils.predicates import MessagePredicate

from .abc import MixinMeta
from .converters import Args
from .functions import chunks, poke_embed
from .menus import GenericMenu, PokedexFormat, PokeList, PokeListMenu, SearchFormat
from .pokemixin import poke
from .statements import *

_ = Translator("Fakemoncord", __file__)


class GeneralMixin(MixinMeta):
    """Fakemoncord General Commands"""

    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.command(name="flist", aliases=["mon"])
    async def _list(self, ctx, user: discord.Member = None):
        """List a trainers or your own Pokémon!"""
        conf = await self.user_is_global(ctx.author)
        if not await conf.has_starter():
            return await ctx.send(
                _(
                    "You haven't picked a starter Pokémon yet! Check out {prefix}starter before trying to list your Pokémon."
                ).format(prefix=ctx.clean_prefix)
            )
        user = user or ctx.author
        async with ctx.typing():
            result = await self.cursor.fetch_all(query=SELECT_POKEMON, values={"user_id": user.id})
        pokemons = []
        for i, data in enumerate(result, start=1):
            poke = json.loads(data[0])
            poke["sid"] = i
            pokemons.append(poke)
        if not pokemons:
            return await ctx.send(_("You don't have any pokémon, go get catching trainer!"))
        _id = await conf.pokeid()
        await ctx.send(
            _("{user}'s selected Pokémon ID is {id}").format(user=user, id=_id),
            delete_after=5,
        )
        await PokeListMenu(
            source=PokeList(pokemons),
            cog=self,
            ctx=ctx,
            user=user,
            delete_message_after=False,
        ).start(ctx=ctx, wait=False)

    @commands.max_concurrency(1, commands.BucketType.user)
    @poke.command()
    async def fnick(self, ctx, id: int, *, nickname: str):
        """Set a Pokémon's nickname.

        ID refers to the position within your Pokémon listing.
        This is found at the bottom of the Pokémon on `[p]list`"""
        conf = await self.user_is_global(ctx.author)
        if not await conf.has_starter():
            return await ctx.send(
                _(
                    "You haven't picked a starter Pokémon yet! Check out {prefix}starter before trying to nickname a Pokémon."
                ).format(prefix=ctx.clean_prefix)
            )
        if id <= 0:
            return await ctx.send(_("The ID must be greater than 0!"))
        if len(nickname) > 40:
            await ctx.send(
                "The nickname you have specified is too big. It must be under 40 characters."
            )
            return
        async with ctx.typing():
            result = await self.cursor.fetch_all(
                query=SELECT_POKEMON, values={"user_id": ctx.author.id}
            )
        pokemons = [None]
        for data in result:
            pokemons.append([json.loads(data[0]), data[1]])
        if not pokemons:
            return await ctx.send(_("You don't have any Pokémon, trainer!"))
        if id > len(pokemons):
            return await ctx.send(
                _(
                    "You don't have a Pokémon at that slot.\nID refers to the position within your Pokémon listing.\nThis is found at the bottom of the Pokémon on `[p]list`"
                )
            )
        pokemon = pokemons[id]
        pokemon[0]["nickname"] = nickname
        await self.cursor.execute(
            query=UPDATE_POKEMON,
            values={
                "user_id": ctx.author.id,
                "message_id": pokemon[1],
                "pokemon": json.dumps(pokemon[0]),
            },
        )
        await ctx.send(
            _("Your {pokemon} has been nicknamed `{nickname}`").format(
                pokemon=self.get_name(pokemon[0]["name"], ctx.author), nickname=nickname
            )
        )

    @commands.max_concurrency(1, commands.BucketType.user)
    @poke.command(aliases=["free"])
    async def frelease(self, ctx, id: int):
        """Release a Pokémon."""
        conf = await self.user_is_global(ctx.author)
        if not await conf.has_starter():
            return await ctx.send(
                _(
                    "You haven't picked a starter Pokémon yet! Check out {prefix}starter before trying to release a Pokémon."
                ).format(prefix=ctx.clean_prefix)
            )
        if id <= 0:
            return await ctx.send(_("The ID must be greater than 0!"))
        async with ctx.typing():
            result = await self.cursor.fetch_all(
                query=SELECT_POKEMON,
                values={"user_id": ctx.author.id},
            )
        pokemons = [None]
        for data in result:
            pokemons.append([json.loads(data[0]), data[1]])
        if not pokemons:
            return await ctx.send(_("You don't have any Pokémon, trainer!"))
        if id >= len(pokemons):
            return await ctx.send(
                _(
                    "You don't have a Pokémon at that slot.\nID refers to the position within your Pokémon listing.\nThis is found at the bottom of the Pokémon on `[p]list`"
                )
            )
        pokemon = pokemons[id]
        name = self.get_name(pokemon[0]["name"], ctx.author)
        if len(pokemons) == 2:
            return await ctx.send(
                _(
                    f"**{name}** is the last Pokémon you've got. You cannot release it to the wilds."
                )
            )
        await ctx.send(
            _(
                "You are about to free {name}, if you wish to continue type `yes`, otherwise type `no`."
            ).format(name=name)
        )
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=pred, timeout=20)
        except asyncio.TimeoutError:
            await ctx.send("Exiting operation.")
            return

        if pred.result:
            msg = ""
            userconf = await self.user_is_global(ctx.author)
            pokeid = await userconf.pokeid()
            if id < pokeid:
                msg += _(
                    "\nYour default Pokémon may have changed. I have tried to account for this change."
                )
                await userconf.pokeid.set(pokeid - 1)
            elif id == pokeid:
                msg += _(
                    "\nYou have released your selected Pokémon. I have reset your selected Pokémon to your first Pokémon."
                )
                await userconf.pokeid.set(1)
            await self.cursor.execute(
                query="DELETE FROM users where message_id = :message_id",
                values={"message_id": pokemon[1]},
            )
            await ctx.send(_("Your {name} has been freed.{msg}").format(name=name, msg=msg))
        else:
            await ctx.send(_("Operation cancelled."))

    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.command(usage="id_or_latest")
    @commands.guild_only()
    async def fselect(self, ctx, _id: Union[int, str]):
        """Select your default Pokémon."""
        conf = await self.user_is_global(ctx.author)
        if not await conf.has_starter():
            return await ctx.send(
                _(
                    "You haven't chosen a starter Pokémon yet, check out {prefix}starter for more information."
                ).format(prefix=ctx.clean_prefix)
            )
        async with ctx.typing():
            result = await self.cursor.fetch_all(
                query="""SELECT Pokémon, message_id from users where user_id = :user_id""",
                values={"user_id": ctx.author.id},
            )
            pokemons = [None]
            for data in result:
                pokemons.append([json.loads(data[0]), data[1]])
            if not pokemons:
                return await ctx.send(_("You don't have any Pokémon to select."))
            if isinstance(_id, str):
                if _id == "latest":
                    _id = len(pokemons) - 1
                else:
                    await ctx.send(
                        _("Unidentified keyword, the only supported action is `latest` as of now.")
                    )
                    return
            if _id < 1 or _id > len(pokemons) - 1:
                return await ctx.send(
                    _(
                        "You've specified an invalid ID.\nID refers to the position within your Pokémon listing.\nThis is found at the bottom of the Pokémon on `[p]list`"
                    )
                )
            await ctx.send(
                _("You have selected {pokemon} as your default Pokémon.").format(
                    pokemon=self.get_name(pokemons[_id][0]["name"], ctx.author)
                )
            )
        conf = await self.user_is_global(ctx.author)
        await conf.pokeid.set(_id)
        await self.update_user_cache()

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def fdex(self, ctx):
        """Check your caught Pokémon!"""
        async with ctx.typing():
            pokemons = await self.config.user(ctx.author).pokeids()
            pokemonlist = copy.deepcopy(self.pokemonlist)
            for i, pokemon in enumerate(pokemonlist, start=1):
                if str(pokemon) in pokemons:
                    pokemonlist[i]["amount"] = pokemons[str(pokemon)]
            a = [value for value in pokemonlist.items()]
            chunked = [item for item in chunks(a, 20)]
            await GenericMenu(
                source=PokedexFormat(chunked),
                delete_message_after=False,
                cog=self,
                len_poke=len(pokemonlist),
            ).start(
                ctx=ctx,
                wait=False,
            )

    @commands.command()
    async def fsearch(self, ctx, *, args: Args):
        """Search your Pokémon.

        Arguements must have `--` before them.
            `--name` | `--n` - Search Pokémon by name.
            `--level`| `--l` - Search Pokémon by level.
            `--id`   | `--i` - Search Pokémon by ID.
            `--variant`   | `--v` - Search Pokémon by variant.
            `--type`   | `--t` - Search Pokémon by type.
            `--gender` | `--g` - Search by gender.
            `--iv` | - Search by total IV.
        """
        async with ctx.typing():
            result = await self.cursor.fetch_all(
                query="""SELECT Pokémon, message_id from users where user_id = :user_id""",
                values={"user_id": ctx.author.id},
            )
            if not result:
                await ctx.send(_("You don't have any Pokémon, trainer!"))
            pokemons = [None]
            for data in result:
                pokemons.append([json.loads(data[0]), data[1]])
            correct = ""
            for i, poke in enumerate(pokemons[1:], 1):
                name = self.get_name(poke[0]["name"], ctx.author)
                poke_str = _(
                    "{pokemon} **|** Level: {level} **|** ID: {id} **|** Index: {index}\n"
                ).format(pokemon=name, level=poke[0]["level"], id=poke[0]["id"], index=i)
                if args["names"]:
                    if name.lower() == args["names"].lower():
                        correct += poke_str
                elif args["level"]:
                    if poke[0]["level"] == args["level"][0]:
                        correct += poke_str
                elif args["id"]:
                    if poke[0]["id"] == args["id"][0]:
                        correct += poke_str
                elif args["variant"]:
                    if poke[0].get("variant", "None").lower() == args["variant"].lower():
                        correct += poke_str
                elif args["iv"]:
                    if sum(poke[0]["ivs"].values()) == args["iv"][0]:
                        correct += poke_str
                elif args["gender"]:
                    if (
                        args["gender"].lower()
                        == poke[0].get("gender", "No Gender").lower().split()[0]
                    ):
                        correct += poke_str
                elif args["type"]:
                    if args["type"].lower() in [x.lower() for x in poke[0]["type"]]:
                        correct += poke_str

            if not correct:
                await ctx.send("No Pokémon returned for that search.")
                return
            content = list(pagify(correct, page_length=1024))
            await GenericMenu(
                source=SearchFormat(content),
                delete_message_after=False,
            ).start(ctx=ctx, wait=False)

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def fcurrent(self, ctx):
        """Show your current selected Pokémon"""
        conf = await self.user_is_global(ctx.author)
        if not await conf.has_starter():
            return await ctx.send(
                _(
                    "You haven't picked a starter Pokémon yet! Check out {prefix}starter before trying to list your Pokémon."
                ).format(prefix=ctx.clean_prefix)
            )
        user = ctx.author
        async with ctx.typing():
            result = await self.cursor.fetch_all(query=SELECT_POKEMON, values={"user_id": user.id})
        pokemons = []
        for i, data in enumerate(result, start=1):
            poke = json.loads(data[0])
            poke["sid"] = i
            pokemons.append(poke)
        if not pokemons:
            return await ctx.send(_("You don't have any Pokémon, go get catching trainer!"))
        _id = await conf.pokeid()
        try:
            pokemon = pokemons[_id - 1]
        except IndexError:
            await ctx.send(
                _(
                    "An error occured trying to find your Pokémon at slot {slotnum}\nAs a result I have set your default Pokémon to 1."
                ).format(slotnum=_id)
            )
            await conf.pokeid.set(1)
            return
        else:
            embed, _file = await poke_embed(self, ctx, pokemon, file=True)
            await ctx.send(embed=embed, file=_file)
