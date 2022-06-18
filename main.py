import discord
import os
import time
from discord.utils import get
from discord import app_commands
import json
import discord.ui
import asyncio

#guilds = [discord.Object(id=598899910770950207),discord.Object(id=951628817770885180),discord.Object(id=683688010188980266)]

class aclient(discord.Client):
    def __init__(self):
      intents=discord.Intents.default()
      intents.members = True
      super().__init__(intents=intents)
      self.synced = False
      self.added = False
      self.in_progress = False
      self.enqueued  = []
      self.players = []
      self.limbo = True
      self.channel = None #channel where uno game takes place
      
      # Game variables
      self.turn = None
      self.reversed = None
      self.skipped = None
      self.to_be_drawn = 0
      self.just_started = bool
      self.wildcolor = ""

      # customizable game settings
      self.starting_hand = 5 # amount of cards drawn at start
      self.amount_of_players = 4
      self.callout_penalty = 2
      self.regular_draw = 1
  
    async def on_ready(self):
      await self.wait_until_ready()
      if not self.synced:
        await tree.sync(guild = None)
        #global guilds
        #for g in range(len(guilds(self))):
          #await tree.sync(guild=guilds(self)[g])
        #await tree.sync(guild=discord.Object(id=951628817770885180)) 
        #await tree.sync(guild=discord.Object(id=598899910770950207))
        #await tree.sync(guild=discord.Object(id=683688010188980266))
        
      print(f"logged in as user {self.user}")
      if self.synced:
            print("synced!")


client = aclient()
tree = discord.app_commands.CommandTree(client)

guilds = client.guilds

import uno


@tree.command(name = "abort",description="use this if things go terribly wrong (resets everything)",guilds=guilds)
async def self(interaction:discord.Interaction):
  if interaction.user in client.enqueued:
    end_game()
  else:
    await interaction.response.send_message("nahhhhhhhh i won't let you")
    

@tree.command(name = "settings",description="customize starting hand/max. amount of players, callout penalties etc.",guilds=guilds)
async def self(interaction:discord.Interaction,starting_hand:int,amount_of_players:int,callout_penalty:int):
  if not client.in_progress:
    client.starting_hand = starting_hand
    client.amount_of_players = amount_of_players
    client.callout_penalty = callout_penalty
    await interaction.response.send_message(f"Starting Hand: {starting_hand} card(s)\nMaximum amount of players: {amount_of_players} Players\nCallout penalty: {callout_penalty} card(s)")
  else:
    await interaction.response.send_message("Don't do this while a game is in session!")
    
              
async def start_game(channel):
  if not client.in_progress:
      client.in_progress = True # prevent other games from being started 
      uno.initialize() #preparations for the UNO game (decks,discards,setting up players)
      for i in range(len(client.enqueued)): 
        client.players.append(uno.Player(client.enqueued[i].name,uno.drawCards(client.starting_hand)))# every user that is currently "enqueued" in a lobby is assigned a player object 
      client.turn = 0 #used to iterate over turn list
      client.reversed = False #flag whether the turn order is in reverse
      client.skipped = False #flag to see if the next turn is to be skipped
      await channel.send(f"**{client.players[client.turn].name}**'s turn.\nCards discarded: {len(uno.discards)}\nRemaining in Deck: {len(uno.unoDeck)}",file=discord.File(fp=uno.current_discard(),filename="current.png"))# message in question that uses the buttons from the view
      client.just_started = True
      await playerturn(channel)
  else:
      await channel.send("A game is already in session")


async def playerturn(channel): # always after a turn finishes
  if client.in_progress:
    if client.skipped:
      await channel.send(f"{next_player().name}'s turn has been skipped!")
      client.turn += 1
      client.skipped = False
    if client.to_be_drawn > 0:
      await channel.send(f"{next_player().name} has to draw {client.to_be_drawn} card(s) this round! Unless...")
      next_player().has_to_draw = True
      #next_player().hand.extend(uno.drawCards(client.to_be_drawn))  
    if not client.just_started:
      client.turn += 1
    else:
      client.just_started = False
    if client.turn >= len(client.players):
          client.turn = client.turn - len(client.players)
    if client.reversed:
          client.players.reverse()
    client.players[client.turn].turn = True
    if len(client.players[client.turn].hand) > 1:
      client.players[client.turn].called_uno_already = False
    #print(client.turn)

@tree.command(name="callout",description="call someone out on not using UNO when he was supposed to ",guilds=guilds)
async def self(interaction:discord.Interaction,player:discord.Member):
  if player in client.enqueued:
    p = [pl for pl in client.players if pl.name == interaction.user.name][0]
    e = [en for en in client.players if en.name == player.name][0]
    if (len(e.hand) < 2) and e.called_uno_already == False:
      await interaction.response.send_message(f"{p.name} successfully called {e.name} out! {e.name} is forced to draw {client.callout_penalty} card(s).")
      e.hand.extend(uno.drawCards(client.callout_penalty))
    else:
      await interaction.response.send_message(f"{e.name} was falsely called out by {p.name}. Penalized by drawing {client.callout_penalty} card(s)!")
      p.hand.extend(uno.drawCards(client.callout_penalty))
  else:
    await interaction.response.send_message("That user isn't participating in the game!")

@tree.command(name="uno",description="call UNO! when you've only got one card left! (or less) ",guilds=guilds)  
async def self(interaction:discord.Interaction):
  end_game_flag = False
  if (interaction.user in client.enqueued) and client.in_progress:
    p = [player for player in client.players if player.name == interaction.user.name][0]
    if len(p.hand) > 1:
      await interaction.response.send_message(content=f"{interaction.user} tried to call UNO but had more than one card left in his hand! Penalized by drawing {client.callout_penalty} card(s)")
      p.hand.extend(uno.drawCards(client.callout_penalty))
    else:
      await interaction.response.send_message(f"{interaction.user.name} calls UNO!")
      if len(p.hand) < 1:
        await interaction.followup.send(f"{p.name} wins the game")
        with open("leaderboards.txt","w") as l:
          #l.writelines(f"{p.name}||1")
          i = 0
          for item in current_rating():
            i+=1
            l.writelines(f"{item}||{i}\n")
        await interaction.followup.send(f"Ranking:\n{' | '.join(current_rating().keys())}")
        end_game_flag = True
      p.called_uno_already = True
  if end_game_flag:
    end_game()    

def next_player()->uno.Player:
  next_turn = client.turn + 1
  if next_turn >= len(client.players):
    next_turn = 0
  return client.players[next_turn]

def current_rating()->dict:
  scores = {}
  for p in client.players:
    scores[p.name] = len(p.hand)
  return dict(sorted(scores.items(), key=lambda item: item[1]))
          
@tree.command(name="startgame",description="start uno session",guilds=guilds)
async def self(interaction:discord.Interaction):
  channel = interaction.channel
  #in_progress = client.in_progress
  if not client.in_progress and (len(client.enqueued) > 1) and (client.enqueued[0]== interaction.user): #if enough players joined and no other game is in progress
    await interaction.response.send_message(content=f"Session started! List of Players:\n{' | '.join([u.name for u in client.enqueued])}")
    await start_game(channel)
  elif len(client.enqueued) < 2:
    await interaction.response.send_message(content=f"More players need to enter the lobby to start game ({len(client.enqueued)} enqueued currently)")
  elif (client.enqueued[0]!= interaction.user):
    await interaction.response.send_message(content="Only party leader (first one to join the lobby) can start the game")
  else:
    await interaction.response.send_message(content="Wait until the current round has finished")

      
@tree.command(name="play",description="shows prompt to let you play/draw a card or call UNO",guilds=guilds)
async def self(interaction:discord.Interaction):
  if client.in_progress and [player for player in client.players if player.turn]:
    #print([player.name for player in client.players if player.turn])
    if [player.name for player in client.players if player.turn][0] == interaction.user.name:
      p = [player for player in client.players if player.turn][0]
      v = discord.ui.View(timeout=30)
      s = discord.ui.Select(min_values=1,max_values=1)
      
      async def my_callback(interaction:discord.Interaction):
        wild_being_played = False #guhhhhhhhhh
        deflect = False
        if interaction.user.name == client.players[client.turn].name:
          await interaction.response.send_message(content=f"{client.players[client.turn].name} played {s.values[0]}")
          played_card = ()
          if s.values[0] in "Draw Card":
            drawn = uno.drawCards(client.regular_draw)
            client.players[client.turn].hand.extend(drawn)
            await interaction.followup.send(content=f"You got {drawn}",ephemeral=True)
          elif "-" in s.values[0]:
            guh = s.values[0].split("-")
            if len(guh[1]) < 2:
              guh[1] = int(guh[1])
            elif guh[1] == "Reverse":
              if len(client.enqueued)>2:
                client.reversed = not client.reversed
              else:
                client.skipped = True
              await interaction.followup.send("The turn order has been reversed!")
            elif guh[1] == "Skip":
              client.skipped = True
              await interaction.followup.send("The next turn has been skipped!")
            elif guh[1] == "+2":
              client.to_be_drawn += 2
              deflect = True
            played_card = tuple(guh)
            #print(played_card)
            #print(client.players[client.turn].hand)
            uno.discards.appendleft(played_card)
            client.players[client.turn].hand.remove(played_card)
          else: # when the card is a wild
            wild_being_played = True
            played_card = s.values[0]
            if "+4" in played_card:
              client.to_be_drawn += 4
              deflect = True
            wilds = discord.ui.View()
            wildcolor = discord.ui.Select(min_values=1,max_values=1)
            
            async def wildcallback(interaction:discord.Interaction,p = played_card):
              client.wildcolor = wildcolor.values[0][0]
              client.players[client.turn].hand.remove(played_card)
              uno.discards.appendleft(played_card+client.wildcolor)
              client.wildcolor = ""
              await interaction.response.send_message(f"{client.players[client.turn].name} chose {wildcolor.values[0]}")
              #this will be pain
              client.players[client.turn].turn = False
              if client.players[client.turn].has_to_draw:
                if deflect:
                  client.players[client.turn].has_to_draw == False
                else:
                  client.players[client.turn].hand.extend(uno.drawCards(client.to_be_drawn))
                  client.players[client.turn].has_to_draw == False
                  await interaction.channel.send(f"{client.players[client.turn].name} has to draw  {client.to_be_drawn} card(s)! owned") 
                  client.to_be_drawn = 0
                               
              #print(client.turn)
              await playerturn(interaction.channel)
              await interaction.channel.send(f"**{client.players[client.turn].name}**'s turn.\nCards discarded: {len(uno.discards)}\nRemaining in Deck: {len(uno.unoDeck)}",file=discord.File(fp=uno.current_discard(),filename="current.png"))

            wildcolor.add_option(label="Red",emoji="🟥")
            wildcolor.add_option(label="Green",emoji="🟩")
            wildcolor.add_option(label="Blue",emoji="🟦")
            wildcolor.add_option(label="Yellow",emoji="🟨")
            wildcolor.callback = wildcallback 
            wilds.add_item(wildcolor) 
            await interaction.followup.send(content="Choose a color for the wild",view=wilds,ephemeral=True)
          if not wild_being_played:
            client.players[client.turn].turn = False
            #print(client.turn)
            if client.players[client.turn].has_to_draw:
              if not deflect:
                client.players[client.turn].hand.extend(uno.drawCards(client.to_be_drawn))
                await interaction.channel.send(f"Yikes. {client.players[client.turn].name} has to draw {client.to_be_drawn} card(s)! owned 😂")
                client.to_be_drawn = 0
            client.players[client.turn].has_to_draw = False
            await playerturn(interaction.channel)
            await interaction.channel.send(f"**{client.players[client.turn].name}**'s turn.\nCards discarded: {len(uno.discards)}\nRemaining in Deck: {len(uno.unoDeck)}",file=discord.File(fp=uno.current_discard(),filename="current.png"))
            
        else:
          await interaction.response.send_message("You can't make a play right now",ephemeral=True) 
          
      s.callback = my_callback
      for card in set(p.canPlay()):
          if str(type(card)) == "<class 'tuple'>":
            emoj = {"R":"🟥","G":"🟩","B":"🟦","Y":"🟨"}
            val =f"{card[0]}-{card[1]}"
            s.add_option(label=card[1],emoji=emoj[card[0]],value=val)
          else:
            s.add_option(label=card,emoji="🃏",value=card)
      s.add_option(label="Draw Card")
      v.add_item(s)
      await interaction.response.send_message("",view=v,ephemeral=True)
      #if not client.limbo:
      #  client.players[client.turn].turn = False
      #  next_turn = client.turn+1
      #  await interaction.followup.send(f"{client.players[next_turn].name}'s turn.\nCards discarded: {len(uno.discards)}",file=discord.File(fp=uno.current_discard(client.wildcolor),filename="current.png"))# message in question that uses the buttons from the view)
    else:
      await interaction.response.send_message("It's not your turn yet",ephemeral=True)
  else:
    await interaction.response.send_message("There is no game in session",ephemeral=True)

  
@tree.command(name="hand",description="see your hand in your current uno session",guilds=guilds)
async def self(interaction:discord.Interaction):
  if (interaction.user in client.enqueued) and client.in_progress:
    p = [player for player in client.players if player.name == interaction.user.name][0]
    #i = client.enqueued.index(interaction.user)
    hand = None
    if len(p.hand) > 0: 
      hand = discord.File(fp=p.showHand(),filename="hand.png")
    other_hands = ""
    for p in client.players:
      if p.name == interaction.user.name and p ==client.players[client.turn]:
        other_hands+=f"__**{p.name}**__: {len(p.hand)} Cards left (Your turn)\n"
      elif p ==client.players[client.turn]:
        other_hands+=f"__{p.name}__: {len(p.hand)} Cards left \n"
      elif p.name == interaction.user.name:
        other_hands+=f"**{p.name}**: {len(p.hand)} Cards left \n"
      else:
        other_hands+=f"{p.name}: {len(p.hand)} Cards left \n"    
    await interaction.response.send_message(content = other_hands,file=hand,ephemeral=True)
  else:
    await interaction.response.send_message("You aren't currently in a session ",ephemeral=True)
        

@tree.command(name = "joinlobby",description="enter the uno lobby",guilds=guilds)
async def self(interaction:discord.Interaction):
  if client.in_progress:
    await interaction.response.send_message("Wait until the current round has finished")
  elif interaction.user not in client.enqueued:
    if len(client.enqueued) < client.amount_of_players:
      client.enqueued.append(interaction.user)
      await interaction.response.send_message(f"{interaction.user.name} entered the queue")
    else:
      await interaction.response.send_message(f"The queue is full. Wait until the next uno session finishes to rejoin the queue")
  else:
    await interaction.response.send_message("You're already enqueued")

@tree.command(name = "leave",description="leave the lobby when the game hasn't started yet",guilds=guilds)
async def self(interaction=discord.Interaction):
  if interaction.user in client.enqueued:
    client.enqueued.remove(interaction.user)
    await interaction.response.send_message(f"{interaction.user.name} has left the queue.{len(client.enqueued)} currently enqueued")
  else:
    await interaction.response.send_message(f"You haven't joined the lobby! {len(client.enqueued)} currently enqueued")
  
def end_game():
  uno.reset()
  client.in_progress = False
  client.enqueued = []
  client.players = []
  client.limbo = True
  client.channel = None #channel where uno game takes place
  client.turn = None
  client.reversed = None
  client.skipped = None
  client.to_be_drawn = 0
  client.wildcolor = ""

client.run(os.getenv("TOKEN"))

