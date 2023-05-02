import discord
from discord.utils import get
from discord import app_commands
import discord.ui
import asyncio
import random
import logging

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

class aclient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(intents=intents)
        self.synced = False
        self.to_be_synced = [
            discord.Object(id=598899910770950207)
        ]  #            ,discord.Object(id=951628817770885180),discord.Object(id=683688010188980266),discord.Object(id=778335511910940685)

        self.game_vars = {}

        # customizable game settings
        #self.starting_hand = 5  # amount of cards drawn at start
        #self.amount_of_players = 4
        #self.callout_penalty = 2
        #self.regular_draw = 1

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            #await tree.sync(guild=None)
            #global guilds
            for g in self.to_be_synced:
                print(g)
                await tree.sync(guild=g)
            self.synced = True
            #await tree.sync(guild=discord.Object(id=951628817770885180))
            #await tree.sync(guild=discord.Object(id=598899910770950207))
            #await tree.sync(guild=discord.Object(id=683688010188980266))
        for g in self.guilds:
            self.game_vars[g.id] = {
                "game": None,  #uno game instance
                "in_progress": False,
                "enqueued": [],
                "players": [],
                "channel": None,
                "turn": None,
                "reversed": None,
                "skipped": None,
                "to_be_drawn": 0,
                "just_started": bool,
                "wildcolor": None,
                "starting_hand": 5,
                "amount_of_players": 4,
                "callout_penalty": 2,
                "regular_draw": 1
            }
        print(f"logged in as user {self.user}")
        if self.synced:
            print("synced!")

    async def on_guild_join(self, guild):
        self.game_vars[guild.id] = {
            "game": None,
            "in_progress": False,
            "enqueued": [],
            "players": [],
            "channel": None,
            "turn": None,
            "reversed": None,
            "skipped": None,
            "to_be_drawn": 0,
            "just_started": bool,
            "wildcolor": None,
            "starting_hand": 5,
            "amount_of_players": 4,
            "callout_penalty": 2,
            "regular_draw": 1
        }


client = aclient()
tree = discord.app_commands.CommandTree(client)

guilds = client.guilds

import uno


@tree.command(
    name="abort",
    description="use this if things go terribly wrong (resets everything)",
    guilds=guilds)
async def self(interaction: discord.Interaction):
    if interaction.user in client.game_vars[interaction.guild_id]["enqueued"]:
        end_game(interaction.guild_id)
    else:
        await interaction.response.send_message("nahhhhhhhh i won't let you")


@tree.command(
    name="settings",
    description=
    "customize starting hand/max. amount of players, callout penalties etc. for the current server",
    guilds=guilds)
async def self(interaction: discord.Interaction, starting_hand: int,
               amount_of_players: int, callout_penalty: int):
    if not client.game_vars[interaction.guild_id]["in_progress"]:
        client.game_vars[interaction.guild_id]["starting_hand"] = starting_hand
        client.game_vars[
            interaction.guild_id]["amount_of_players"] = amount_of_players
        client.game_vars[
            interaction.guild_id]["callout_penalty"] = callout_penalty
        await interaction.response.send_message(
            f"Starting Hand: {starting_hand} card(s)\nMaximum amount of players: {amount_of_players} Players\nCallout penalty: {callout_penalty} card(s)"
        )
    else:
        await interaction.response.send_message(
            "Don't do this while a game is in session!")


async def start_game(channel: discord.TextChannel):
    guild_id = channel.guild.id
    if not client.game_vars[guild_id]["in_progress"]:
        client.game_vars[guild_id]["in_progress"] = True  # prevent other games from being started
        client.game_vars[guild_id]["game"] = uno.Game()  #preparations for the UNO game (decks,discards,setting up players)
        
        for i in range(len(client.game_vars[guild_id]["enqueued"])):
            print("poop", i)
            if client.game_vars[guild_id]["enqueued"][i] != None:
                client.game_vars[guild_id]['players'].append(
                    uno.Player(
                        client.game_vars[guild_id]["enqueued"][i].name,
                        client.game_vars[guild_id]["game"].drawCards(client.game_vars[guild_id]["starting_hand"]))
                )  # every user that is currently "enqueued" in a lobby is assigned a player object
                print("enqueued player added", client.game_vars[guild_id]["enqueued"][i])
            else:
                client.game_vars[guild_id]['players'].append(
                    uno.Player(
                        "", client.game_vars[guild_id]["game"].drawCards(
                            client.game_vars[guild_id]["starting_hand"])))
                print("nameless bot player added")
        client.game_vars[guild_id]['turn'] = 0  #used to iterate over turn list
        client.game_vars[guild_id]['reversed'] = False  #flag whether the turn order is in reverse
        client.game_vars[guild_id]['skipped'] = False  #flag to see if the next turn is to be skipped
        #print(client.game_vars)
        #print(channel.guild.id)
        #await channel.send("Game started!")
        await channel.send(f"**{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name}**'s turn.\nCards discarded: {len(client.game_vars[guild_id]['game'].discards)}\nRemaining in Deck: {len(client.game_vars[guild_id]['game'].unoDeck)}")
        #client.game_vars[guild_id]['game'].current_discard()
        #await channel.send(file=discord.File(fp="current.png",filename="current.png"))
        await channel.send(file=discord.File(fp=client.game_vars[guild_id]['game'].current_discard(),filename="current.png"))  # message in question that uses the buttons from the view
        
        print("first turn message sent")
        client.game_vars[guild_id]['just_started'] = True
        await playerturn(channel)
    else:
        await channel.send("A game is already in session")


async def playerturn(channel: discord.TextChannel):  # always after a turn finishes
    guild_id = channel.guild.id
    if client.game_vars[guild_id]["in_progress"]:
        play_direction = 1 if not client.game_vars[guild_id]["reversed"] else -1
        if client.game_vars[guild_id]['skipped']:
            await channel.send(
                f"{next_player(guild_id).name}'s turn has been skipped!")
            client.game_vars[guild_id]['turn'] += play_direction
            client.game_vars[guild_id]['skipped'] = False
        if client.game_vars[guild_id]['to_be_drawn'] > 0:
            await channel.send(
                f"{next_player(guild_id).name} has to draw {client.game_vars[guild_id]['to_be_drawn']} card(s) this round! Unless..."
            )
            next_player(guild_id).has_to_draw = True
            #next_player().hand.extend(uno.drawCards(client.game_vars[interaction.guild_id]['to_be_drawn']))
        if not client.game_vars[guild_id]['just_started']:
            client.game_vars[guild_id]['turn'] += play_direction  #next player's turn
        else:
            client.game_vars[guild_id]['just_started'] = False  #game has just started
        if not client.game_vars[guild_id]["reversed"]:  # when the turn order wraps back around to the first player
            if client.game_vars[guild_id]['turn'] >= len(client.game_vars[guild_id]['players']):
                client.game_vars[guild_id]['turn'] = client.game_vars[guild_id]['turn'] - len(client.game_vars[guild_id]['players'])
        elif abs(client.game_vars[guild_id]['turn']) > len(
                client.game_vars[guild_id]['players']):
            client.game_vars[guild_id]['turn'] = client.game_vars[guild_id]['turn'] + len(client.game_vars[guild_id]['players'])
        #if client.game_vars[guild_id]['reversed']:
        #    client.game_vars[guild_id]['players'].reverse()
        #    client.game_vars[guild_id]['reversed'] = False
        client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].turn = True
        
        if len(client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].hand) > 1:
            client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].called_uno_already = False
            
        if client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].is_ai:
            await ai_turn(channel)


async def ai_turn(channel: discord.TextChannel):
    guild_id = channel.guild.id
    playable = client.game_vars[guild_id]['players'][
        client.game_vars[guild_id]['turn']].canPlay(
            client.game_vars[guild_id]['game'])
    deflect = False
    if len(playable) > 0:
        #await channel.send(f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is playing a card")
        await asyncio.sleep(1)
        a = random.choice([
            (i, j) for i, j in enumerate(client.game_vars[guild_id]["players"][
                client.game_vars[guild_id]['turn']].hand) if j in playable
        ])
        played_card = client.game_vars[guild_id]["players"][
            client.game_vars[guild_id]['turn']].hand.pop(a[0])
        if "Wild" in played_card:  #if the card is a wild card, a random color is selected as long as there are cards of that color in the deck
            if "+4" in played_card:
                client.game_vars[guild_id]['to_be_drawn'] += 4
                deflect = True
            wildcolor = {"R": "Red", "G": "Green", "B": "Blue", "Y": "Yellow"}
            await channel.send(
                f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is playing a {played_card}"
            )
            client.game_vars[guild_id]['wildcolor'] = ""
            if [
                    p for p in client.game_vars[guild_id]['players'][
                        client.game_vars[guild_id]['turn']].hand
                    if isinstance(p, tuple)
            ]:
                chosen = random.choice([
                    p[0] for p in client.game_vars[guild_id]['players'][
                        client.game_vars[guild_id]['turn']].hand
                    if isinstance(p, tuple)
                ])  #randomly selects a color from the playable cards
            else:  #if the hand has no playable card (not counting wild cards), the color is randomly selected from the deck
                chosen = random.choice(["R", "G", "B", "Y"])
            print(played_card + " " + chosen)
            client.game_vars[guild_id]['game'].discards.appendleft(
                played_card + chosen)
            await channel.send(
                f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} chose {wildcolor[chosen]}"
            )

        elif played_card[1] == "Skip":
            client.game_vars[guild_id]['skipped'] = True
            client.game_vars[guild_id]['game'].discards.appendleft(played_card)
            await channel.send(
                f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is playing a {played_card}"
            )
            #await channel.send(f"{next_player(guild_id).name}'s turn has been skipped!")

        elif played_card[1] == "Reverse":
            if len(client.game_vars[guild_id]["enqueued"]) > 2:
                client.game_vars[guild_id][
                    'reversed'] = not client.game_vars[guild_id]['reversed']
            else:
                client.game_vars[guild_id]['skipped'] = True
            client.game_vars[guild_id]['game'].discards.appendleft(played_card)
            await channel.send(
                f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is playing a {played_card}"
            )
            await channel.send("The turn order has been reversed!")

        elif played_card[1] == "+2":
            client.game_vars[guild_id]['to_be_drawn'] += 2
            deflect = True
            await channel.send(
                f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is playing a {played_card}"
            )
            client.game_vars[guild_id]['game'].discards.appendleft(played_card)
        else:
            await channel.send(
                f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is playing a {played_card}"
            )
            client.game_vars[guild_id]['game'].discards.appendleft(played_card)

    else:
        await asyncio.sleep(1)
        client.game_vars[guild_id]['players'][
            client.game_vars[guild_id]['turn']].hand.extend(
                client.game_vars[guild_id]['game'].drawCards(
                    client.game_vars[guild_id]['regular_draw']))
        await channel.send(
            f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is drawing a card"
        )

    if not deflect and client.game_vars[guild_id]['to_be_drawn'] > 0:
        await channel.send(
            f"{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name} is forced to draw {client.game_vars[guild_id]['to_be_drawn']} cards"
        )
        client.game_vars[guild_id]['players'][
            client.game_vars[guild_id]['turn']].hand.extend(
                client.game_vars[guild_id]['game'].drawCards(
                    client.game_vars[guild_id]['to_be_drawn']))
        client.game_vars[guild_id]['to_be_drawn'] = 0
    await playerturn(channel)
    if not client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].is_ai:
         await channel.send(f"**{client.game_vars[guild_id]['players'][client.game_vars[guild_id]['turn']].name}**'s turn.\nCards discarded: {len(client.game_vars[guild_id]['game'].discards)}\nRemaining in Deck: {len(client.game_vars[guild_id]['game'].unoDeck)}",file=discord.File(fp=client.game_vars[guild_id]['game'].current_discard(),filename="current.png"))


@tree.command(
    name="callout",
    description="call someone out on not using UNO when he was supposed to ",
    guilds=guilds)
async def self(interaction: discord.Interaction, player: discord.Member):
    if player in client.game_vars[interaction.guild_id]["enqueued"]:
        p = [
            pl for pl in client.game_vars[interaction.guild_id]['players']
            if pl.name == interaction.user.name
        ][0]
        e = [
            en for en in client.game_vars[interaction.guild_id]['players']
            if en.name == player.name
        ][0]
        if (len(e.hand) < 2) and e.called_uno_already == False:
            await interaction.response.send_message(
                f"{p.name} successfully called {e.name} out! {e.name} is forced to draw {client.game_vars[interaction.guild_id]['callout_penalty']} card(s)."
            )
            e.hand.extend(
                client.game_vars[interaction.guild_id]['game'].drawCards(
                    client.game_vars[interaction.guild_id]['callout_penalty']))
        else:
            await interaction.response.send_message(
                f"{e.name} was falsely called out by {p.name}. Penalized by drawing {client.game_vars[interaction.guild_id]['callout_penalty']} card(s)!"
            )
            p.hand.extend(
                client.game_vars[interaction.guild_id]['game'].drawCards(
                    client.game_vars[interaction.guild_id]['callout_penalty']))
    else:
        await interaction.response.send_message(
            "That user isn't participating in the game!")


@tree.command(
    name="uno",
    description="call UNO! when you've only got one card left! (or less) ",
    guilds=guilds)
async def self(interaction: discord.Interaction):
    end_game_flag = False
    if (interaction.user in client.game_vars[interaction.guild_id]["enqueued"]
        ) and client.game_vars[interaction.guild_id]["in_progress"]:
        p = [
            player
            for player in client.game_vars[interaction.guild_id]['players']
            if player.name == interaction.user.name
        ][0]
        if len(p.hand) > 1:
            await interaction.response.send_message(
                content=
                f"{interaction.user} tried to call UNO but had more than one card left in his hand! Penalized by drawing {client.game_vars[interaction.guild_id]['callout_penalty']} card(s)"
            )
            p.hand.extend(
                client.game_vars[interaction.guild_id]['game'].drawCards(
                    client.game_vars[interaction.guild_id]['callout_penalty']))
        else:
            await interaction.response.send_message(
                f"{interaction.user.name} calls UNO!")
            if len(p.hand) < 1:
                await interaction.followup.send(f"{p.name} wins the game")
                with open("leaderboards.txt", "w") as l:
                    #l.writelines(f"{p.name}||1")
                    i = 0
                    for item in current_rating(interaction.guild_id):
                        i += 1
                        l.writelines(f"{item}||{i}\n")
                await interaction.followup.send(
                    f"Ranking:\n{' | '.join(current_rating(interaction.guild_id).keys())}"
                )
                end_game_flag = True
            p.called_uno_already = True
    if end_game_flag:
        end_game(interaction.guild_id)


def next_player(guild_id) -> uno.Player:
    pointer = 1 if not client.game_vars[guild_id]['reversed'] else -1
    next_turn = client.game_vars[guild_id]['turn'] + pointer
    if not client.game_vars[guild_id]['reversed']:
        if next_turn >= len(client.game_vars[guild_id]['players']):
            next_turn = 0
    elif abs(next_turn) > len(client.game_vars[guild_id]['players']):
        next_turn = len(client.game_vars[guild_id]['players']) - 1
    return client.game_vars[guild_id]['players'][next_turn]


def current_rating(guild_id) -> dict:
    scores = {}
    for p in client.game_vars[guild_id]['players']:
        scores[p.name] = len(p.hand)
    return dict(sorted(scores.items(), key=lambda item: item[1]))


@tree.command(name="startgame", description="start uno session", guilds=guilds)
async def self(interaction: discord.Interaction):
    channel = interaction.channel
    #in_progress = client.game_vars[interaction.guild_id]["in_progress"]
    if not client.game_vars[interaction.guild_id]["in_progress"] and (len(client.game_vars[interaction.guild_id]["enqueued"]) > 1) and (client.game_vars[interaction.guild_id]["enqueued"][0]== interaction.user):  #if enough players joined and no other game is in progress
        await interaction.response.send_message(
            content=f"Session started! List of Players:\n{' | '.join([u.name for u in client.game_vars[interaction.guild_id]['enqueued'] if u != None])} + {len([b for b in client.game_vars[interaction.guild_id]['enqueued'] if b is None])} bot(s)")
        await start_game(channel)
        
    elif len(client.game_vars[interaction.guild_id]["enqueued"]) < 2:
        await interaction.response.send_message(
            content=
            f"More players need to enter the lobby to start game ({len(client.game_vars[interaction.guild_id]['enqueued'])} enqueued currently)"
        )
    elif (client.game_vars[interaction.guild_id]["enqueued"][0] !=
          interaction.user):
        await interaction.response.send_message(
            content=
            "Only party leader (first one to join the lobby) can start the game"
        )
    else:
        await interaction.response.send_message(
            content="Wait until the current round has finished")


@tree.command(
    name="play",
    description="shows prompt to let you play/draw a card or call UNO",
    guilds=guilds)
async def self(interaction: discord.Interaction):
    if client.game_vars[interaction.guild_id]["in_progress"] and [
            player
            for player in client.game_vars[interaction.guild_id]['players']
            if player.turn
    ]:
        #print([player.name for player in client.game_vars[interaction.guild_id]['players'] if player.turn])
        if [player.name for player in client.game_vars[interaction.guild_id]['players'] if player.turn][0] == interaction.user.name:
            p = [player for player in client.game_vars[interaction.guild_id]['players'] if player.turn][0]
            v = discord.ui.View(timeout=30)
            s = discord.ui.Select(min_values=1, max_values=1)

            async def my_callback(interaction: discord.Interaction):
                wild_being_played = False  #guhhhhhhhhh
                deflect = False
                if interaction.user.name == client.game_vars[
                        interaction.guild_id]['players'][client.game_vars[
                            interaction.guild_id]['turn']].name:
                    await interaction.response.send_message(content=f"{client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].name} played {s.values[0]}")
                    played_card = ()
                    if s.values[0] in "Draw Card":
                        drawn = client.game_vars[interaction.guild_id]['game'].drawCards(
                                client.game_vars[interaction.guild_id]["regular_draw"])
                        client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].hand.extend(drawn)
                        await interaction.followup.send(content=f"You got {drawn}", ephemeral=True)
                    elif "-" in s.values[0]:
                        guh = s.values[0].split("-")
                        if len(guh[1]) < 2:
                            guh[1] = int(guh[1])
                        elif guh[1] == "Reverse":
                            if len(client.game_vars[interaction.guild_id]["enqueued"]) > 2:
                                client.game_vars[interaction.guild_id]['reversed'] = not client.game_vars[interaction.guild_id]['reversed']
                                await interaction.followup.send("The turn order has been reversed!")
                            else:
                                client.game_vars[interaction.guild_id]['skipped'] = True
                        elif guh[1] == "Skip":
                            client.game_vars[interaction.guild_id]['skipped'] = True
                            #await interaction.followup.send(f"{next_player(interaction.guild_id).name}'s turn has been skipped!")
                        elif guh[1] == "+2":
                            client.game_vars[interaction.guild_id]['to_be_drawn'] += 2
                            deflect = True
                        played_card = tuple(guh)
                        #print(played_card)
                        #print(client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].hand)
                        client.game_vars[interaction.guild_id][
                            'game'].discards.appendleft(played_card)
                        client.game_vars[interaction.guild_id]['players'][
                            client.game_vars[interaction.guild_id]
                            ['turn']].hand.remove(played_card)
                    else:  # when the card is a wild
                        wild_being_played = True
                        played_card = s.values[0]
                        if "+4" in played_card:
                            client.game_vars[
                                interaction.guild_id]['to_be_drawn'] += 4
                            deflect = True
                        wilds = discord.ui.View()
                        wildcolor = discord.ui.Select(min_values=1,
                                                      max_values=1)

                        async def wildcallback(
                                interaction: discord.Interaction,
                                p=played_card):
                            client.game_vars[interaction.guild_id][
                                'wildcolor'] = wildcolor.values[0][0]
                            client.game_vars[interaction.guild_id]['players'][
                                client.game_vars[interaction.guild_id]
                                ['turn']].hand.remove(played_card)
                            client.game_vars[interaction.guild_id][
                                'game'].discards.appendleft(
                                    played_card + client.game_vars[
                                        interaction.guild_id]['wildcolor'])
                            client.game_vars[
                                interaction.guild_id]['wildcolor'] = ""
                            await interaction.response.send_message(
                                f"{client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].name} chose {wildcolor.values[0]}"
                            )
                            #this will be pain
                            client.game_vars[interaction.guild_id]['players'][
                                client.game_vars[
                                    interaction.guild_id]['turn']].turn = False
                            if client.game_vars[
                                    interaction.guild_id]['players'][
                                        client.game_vars[interaction.guild_id]
                                        ['turn']].has_to_draw:
                                if deflect:
                                    client.game_vars[
                                        interaction.guild_id]['players'][
                                            client.game_vars[
                                                interaction.guild_id]
                                            ['turn']].has_to_draw == False
                                else:
                                    client.game_vars[
                                        interaction.guild_id]['players'][
                                            client.game_vars[
                                                interaction.guild_id]
                                            ['turn']].hand.extend(
                                                client.game_vars[
                                                    interaction.guild_id]
                                                ['game'].drawCards(
                                                    client.game_vars[
                                                        interaction.guild_id]
                                                    ['to_be_drawn']))
                                    client.game_vars[
                                        interaction.guild_id]['players'][
                                            client.game_vars[
                                                interaction.guild_id]
                                            ['turn']].has_to_draw == False
                                    if client.game_vars[interaction.guild_id][
                                            'to_be_drawn'] > 0:
                                        await interaction.channel.send(
                                            f"{client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].name} has to draw  {client.game_vars[interaction.guild_id]['to_be_drawn']} card(s)! owned"
                                        )
                                    client.game_vars[interaction.guild_id][
                                        'to_be_drawn'] = 0

                            #print(client.game_vars[interaction.guild_id]['turn'])
                            eee = next_player(interaction.guild_id).is_ai
                            await playerturn(interaction.channel)
                            if eee == False:
                                print("wild has been played")
                                await interaction.channel.send(f"**{client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].name}**'s turn.\nCards discarded: {len(client.game_vars[interaction.guild_id]['game'].discards)}\nRemaining in Deck: {len(client.game_vars[interaction.guild_id]['game'].unoDeck)}")
                                await interaction.channel.send(file=discord.File(fp=client.game_vars[interaction.guild_id]['game'].current_discard(),filename="current.png"))

                        wildcolor.add_option(label="Red", emoji="🟥")
                        wildcolor.add_option(label="Green", emoji="🟩")
                        wildcolor.add_option(label="Blue", emoji="🟦")
                        wildcolor.add_option(label="Yellow", emoji="🟨")
                        wildcolor.callback = wildcallback
                        wilds.add_item(wildcolor)
                        await asyncio.sleep(1)
                        await interaction.followup.send(
                            content="Choose a color for the wild",
                            view=wilds,
                            ephemeral=True)
                    if not wild_being_played:
                        client.game_vars[interaction.guild_id]['players'][
                            client.game_vars[
                                interaction.guild_id]['turn']].turn = False
                        #print(client.game_vars[interaction.guild_id]['turn'])
                        if client.game_vars[interaction.guild_id]['players'][
                                client.game_vars[
                                    interaction.guild_id]['turn']].has_to_draw:
                            if not deflect:
                                client.game_vars[
                                    interaction.guild_id]['players'][
                                        client.game_vars[interaction.guild_id]['turn']].hand.extend(client.game_vars[interaction.guild_id]['game'].drawCards(client.game_vars[interaction.guild_id]['to_be_drawn']))
                                if client.game_vars[interaction.guild_id]['to_be_drawn'] > 0:
                                    await interaction.channel.send(
                                        f"Yikes. {client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].name} has to draw {client.game_vars[interaction.guild_id]['to_be_drawn']} card(s)! owned 😂"
                                    )
                                client.game_vars[
                                    interaction.guild_id]['to_be_drawn'] = 0
                        client.game_vars[interaction.guild_id]['players'][
                            client.game_vars[interaction.guild_id]
                            ['turn']].has_to_draw = False
                        await playerturn(interaction.channel)
                        if next_player(interaction.guild_id).is_ai == False:
                            await interaction.channel.send(f"**{client.game_vars[interaction.guild_id]['players'][client.game_vars[interaction.guild_id]['turn']].name}**'s turn.\nCards discarded: {len(client.game_vars[interaction.guild_id]['game'].discards)}\nRemaining in Deck: {len(client.game_vars[interaction.guild_id]['game'].unoDeck)}")
                            await interaction.channel.send(file=discord.File(fp=client.game_vars[interaction.guild_id]['game'].current_discard(),filename="current.png"))

                else:
                    await interaction.response.send_message(
                        "You can't make a play right now", ephemeral=True)

            s.callback = my_callback
            for card in set(
                    p.canPlay(client.game_vars[interaction.guild_id]['game'])):
                if str(type(card)) == "<class 'tuple'>":
                    emoj = {"R": "🟥", "G": "🟩", "B": "🟦", "Y": "🟨"}
                    val = f"{card[0]}-{card[1]}"
                    s.add_option(label=card[1], emoji=emoj[card[0]], value=val)
                else:
                    s.add_option(label=card, emoji="🃏", value=card)
            s.add_option(label="Draw Card")
            v.add_item(s)
            await interaction.response.send_message("", view=v, ephemeral=True)
        else:
            await interaction.response.send_message("It's not your turn yet",
                                                    ephemeral=True)
    else:
        await interaction.response.send_message("There is no game in session",
                                                ephemeral=True)


@tree.command(name="hand",
              description="see your hand in your current uno session",
              guilds=guilds)
async def self(interaction: discord.Interaction):
    if (interaction.user in client.game_vars[interaction.guild_id]["enqueued"]) and client.game_vars[interaction.guild_id]["in_progress"]:
        print("command hand is being used")
        p = [player for player in client.game_vars[interaction.guild_id]['players'] if player.name == interaction.user.name][0]
        #i = client.game_vars[interaction.guild_id]["enqueued"].index(interaction.user)
        hand = discord.File(fp="assets/nocards.jpg", filename="hand.png")
        if len(p.hand) > 0:
            hand = discord.File(fp=p.showHand(), filename="hand.png")
        other_hands = ""
        for p in client.game_vars[interaction.guild_id]['players']:
            if p.name == interaction.user.name and p == client.game_vars[
                    interaction.guild_id]['players'][client.game_vars[
                        interaction.guild_id]['turn']]:
                other_hands += f"__**{p.name}**__: {len(p.hand)} Cards left (Your turn)\n"
            elif p == client.game_vars[interaction.guild_id]['players'][
                    client.game_vars[interaction.guild_id]['turn']]:
                other_hands += f"__{p.name}__: {len(p.hand)} Cards left \n"
            elif p.name == interaction.user.name:
                other_hands += f"**{p.name}**: {len(p.hand)} Cards left \n"
            else:
                other_hands += f"{p.name}: {len(p.hand)} Cards left \n"
        await interaction.response.send_message(content=other_hands,
                                                file=hand,
                                                ephemeral=True)
    else:
        await interaction.response.send_message("You aren't currently in a session ", ephemeral=True)


@tree.command(name="joinlobby",
              description="enter the uno lobby",
              guilds=guilds)
async def self(interaction: discord.Interaction):
    if client.game_vars[interaction.guild_id]["in_progress"]:
        await interaction.response.send_message(
            "Wait until the current round has finished")
    elif interaction.user not in client.game_vars[
            interaction.guild_id]["enqueued"]:
        if len(client.game_vars[interaction.guild_id]["enqueued"]
               ) < client.game_vars[interaction.guild_id]["amount_of_players"]:
            client.game_vars[interaction.guild_id]["enqueued"].append(interaction.user)
            await interaction.response.send_message(
                f"{interaction.user.name} entered the queue")
        else:
            await interaction.response.send_message(
                f"The queue is full. Wait until the next uno session finishes to rejoin the queue"
            )
    else:
        await interaction.response.send_message("You're already enqueued")


@tree.command(name="ai_joinlobby",
              description="adds an ai player to the current uno queue ",
              guilds=guilds)
async def self(interaction: discord.Interaction):
    if client.game_vars[interaction.guild_id]["in_progress"]:
        await interaction.response.send_message(
            "Wait until the current round has finished")
    elif len(client.game_vars[interaction.guild_id]["enqueued"]) > 0:
        if len(client.game_vars[interaction.guild_id]["enqueued"]
               ) < client.game_vars[interaction.guild_id]["amount_of_players"]:
            client.game_vars[interaction.guild_id]["enqueued"].append(None)
            await interaction.response.send_message(f"An AI-Player entered the queue")
        else:
            await interaction.response.send_message(
                f"The queue is full. Wait until the next uno session finishes to rejoin the queue")
    else:
        await interaction.response.send_message(
            "An AI-Player cannot be the party leader")


@tree.command(name="ai_leave",
              description="removes an ai player from the current uno queue ",
              guilds=guilds)
async def self(interaction: discord.Interaction):
    if client.game_vars[interaction.guild_id]["in_progress"]:
        await interaction.response.send_message(
            "Wait until the current round has finished")
    elif [
            p for p in client.game_vars[interaction.guild_id]["enqueued"]
            if p is None
    ]:
        client.game_vars[interaction.guild_id]["enqueued"].remove(None)
        await interaction.response.send_message(
            f"An AI-Player was removed from the queue. There are now {len(client.game_vars[interaction.guild_id]['enqueued'])} players in the queue"
        )
    else:
        await interaction.response.send_message(
            "There are no AI-Players in the queue")


@tree.command(name="leave",
              description="leave the lobby when the game hasn't started yet",
              guilds=guilds)
async def self(interaction=discord.Interaction):
    if interaction.user in client.game_vars[interaction.guild_id]["enqueued"]:
        if client.game_vars[interaction.guild_id]["in_progress"] == False:
            client.game_vars[interaction.guild_id]["enqueued"].remove(
                interaction.user)
            await interaction.response.send_message(
                f"{interaction.user.name} has left the queue. {len(client.game_vars[interaction.guild_id]['enqueued'])} currently enqueued"
            )
        else:
            await interaction.response.send_message(
                "You can't leave the session while it's in progress! (yet)")
    else:
        await interaction.response.send_message(
            f"You haven't joined the lobby! {len(client.game_vars[interaction.guild_id]['enqueued'])} currently enqueued"
        )


def end_game(id):
    #uno.reset()
    del client.game_vars[id]['game']
    client.game_vars[id]['game'] = None
    client.game_vars[id]["in_progress"] = False
    client.game_vars[id]["enqueued"] = []
    client.game_vars[id]['players'] = []
    client.game_vars[id]['turn'] = None
    client.game_vars[id]['reversed'] = None
    client.game_vars[id]['skipped'] = None
    client.game_vars[id]['to_be_drawn'] = 0
    client.game_vars[id]['wildcolor'] = ""

with open ("token.txt", "r") as f:
    token = f.read()
    
    
client.run(token)

