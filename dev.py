import json
import pprint
from typing import Optional

import discord
import tabulate
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import *

from .abc import MixinMeta
from .pokemixin import poke
from .statements import *

_ = Translator("Fakemoncord", __file__)


class Dev(MixinMeta):
    """Fakemoncord Development Commands"""

    @poke.group(hidden=True)
    @commands.is_owner()
    async def dev(self, ctx):
        """Fakemoncord Development Commands"""

    @dev.command(name="fspawn")
    async def dev_spawn(self, ctx, *pokemon):
        """Spawn a Pokémon by name or random"""
        pokemon = " ".join(pokemon).strip().lower()
        if pokemon is "":
            await self.spawn_pokemon(ctx.channel)
            return
        else:
            for i, pokemondata in enumerate(self.pokemondata):
                name = (
                    pokemondata.get("alias").lower()
                    if pokemondata.get("alias")
                    else pokemondata["name"]["english"].lower()
                )
                if name == pokemon:
                    await self.spawn_pokemon(ctx.channel, pokemon=self.pokemondata[i])
                    return
        await ctx.send("No Pokémon found.")

    async def get_pokemon(self, ctx, user: discord.Member, pokeid: int) -> list:
        """Returns Pokémon from user list if exists"""
        if pokeid <= 0:
            return await ctx.send("The ID must be greater than 0!")
        async with ctx.typing():
            result = await self.cursor.fetch_all(query=SELECT_POKEMON, values={"user_id": user.id})
        pokemons = [None]
        for data in result:
            pokemons.append([json.loads(data[0]), data[1]])
        if not pokemons:
            return await ctx.send("You don't have any Pokémon, trainer!")
        if pokeid >= len(pokemons):
            return await ctx.send("There's no Pokémon at that slot.")
        return pokemons[pokeid]

    @dev.command(name="fivs")
    async def dev_ivs(
        self,
        ctx,
        user: Optional[discord.Member],
        pokeid: int,
        hp: int,
        attack: int,
        defence: int,
        spatk: int,
        spdef: int,
        speed: int,
    ):
        """Manually set a Pokémon's IVs"""
        if user is None:
            user = ctx.author
        pokemon = await self.get_pokemon(ctx, user, pokeid)
        if not isinstance(pokemon, list):
            return
        pokemon[0]["ivs"] = {
            "HP": hp,
            "Attack": attack,
            "Defence": defence,
            "Sp. Atk": spatk,
            "Sp. Def": spdef,
            "Speed": speed,
        }
        await self.cursor.execute(
            query=UPDATE_POKEMON,
            values={
                "user_id": user.id,
                "message_id": pokemon[1],
                "pokemon": json.dumps(pokemon[0]),
            },
        )
        await ctx.tick()

    @dev.command(name="fstats")
    async def dev_stats(
        self,
        ctx,
        user: Optional[discord.Member],
        pokeid: int,
        hp: int,
        attack: int,
        defence: int,
        spatk: int,
        spdef: int,
        speed: int,
    ):
        """Manually set a Pokémon's stats"""
        if user is None:
            user = ctx.author
        pokemon = await self.get_pokemon(ctx, user, pokeid)
        if not isinstance(pokemon, list):
            return
        pokemon[0]["stats"] = {
            "HP": hp,
            "Attack": attack,
            "Defence": defence,
            "Sp. Atk": spatk,
            "Sp. Def": spdef,
            "Speed": speed,
        }
        await self.cursor.execute(
            query=UPDATE_POKEMON,
            values={
                "user_id": user.id,
                "message_id": pokemon[1],
                "pokemon": json.dumps(pokemon[0]),
            },
        )
        await ctx.tick()

    @dev.command(name="flevel")
    async def dev_lvl(self, ctx, user: Optional[discord.Member], pokeid: int, lvl: int):
        """Manually set a Pokémon's level"""
        if user is None:
            user = ctx.author
        pokemon = await self.get_pokemon(ctx, user, pokeid)
        if not isinstance(pokemon, list):
            return
        pokemon[0]["level"] = lvl
        await self.cursor.execute(
            query=UPDATE_POKEMON,
            values={
                "user_id": user.id,
                "message_id": pokemon[1],
                "pokemon": json.dumps(pokemon[0]),
            },
        )
        await ctx.tick()

    @dev.command(name="freveal")
    async def dev_reveal(self, ctx, user: Optional[discord.Member], pokeid: int):
        """Shows raw info for an owned Pokémon"""
        if user is None:
            user = ctx.author
        pokemon = await self.get_pokemon(ctx, user, pokeid)
        if not isinstance(pokemon, list):
            return
        await ctx.send(content=pprint.pformat(pokemon[0]))

    @dev.command(name="fstrip")
    async def dev_strip(self, ctx, user: discord.Member, id: int):
        """Forcably removes a Pokémon from user"""
        if id <= 0:
            return await ctx.send("The ID must be greater than 0!")
        async with ctx.typing():
            result = await self.cursor.fetch_all(query=SELECT_POKEMON, values={"user_id": user.id})
        pokemons = [None]
        for data in result:
            pokemons.append([json.loads(data[0]), data[1]])
        if not pokemons:
            return await ctx.send(f"{user.display_name} don't have any Pokémon!")
        if id >= len(pokemons):
            return await ctx.send("There's no Pokémon at that slot.")
        pokemon = pokemons[id]
        msg = ""
        userconf = await self.user_is_global(user)
        pokeid = await userconf.pokeid()
        if id < pokeid:
            msg += _(
                "\nTheir default Pokémon may have changed. I have tried to account for this change."
            )
            await userconf.pokeid.set(pokeid - 1)
        elif id == pokeid:
            msg += _(
                "\nYou have released their selected Pokémon. I have reset their selected pokemon to their first Pokémon."
            )
            await userconf.pokeid.set(1)
        if len(pokemons) == 2:  # it was their last pokemon, resets starter
            await userconf.has_starter.set(False)
            msg = _(
                f"\n{user.display_name} has no Pokémon left. I have granted them another chance to pick a starter."
            )
        await self.cursor.execute(
            query="DELETE FROM users where message_id = :message_id",
            values={"message_id": pokemon[1]},
        )
        name = self.get_name(pokemon[0]["name"], user)
        await ctx.send(
            _(f"{user.display_name}'s {name} has been freed.{msg}").format(name=name, msg=msg)
        )
