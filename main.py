from pydoc import describe
import discord
from discord import option
from discord.commands import option, Option
from discord.ext import commands, tasks
import aiohttp
import yaml
import asyncio
import json
import random
import re
import random, string
import datetime
import dateutil.parser as dp
import urllib.request

# Import local utilities for database management
from database_utils import *

print('Loading Settings...')

# Load Settings
with open('./settings.yml', encoding="utf8") as file:
    try:

        settings = yaml.load(file, Loader=yaml.FullLoader)

        print('Successfully loaded settings!')

    except Exception as e:
        print(f'Error while loading settings! -> {e}')
        exit()

# Set Clash Royale API Key
api = {"Authorization": "Bearer " + settings['api-key']}

# Set Discord HEX Colours
defaultColour = discord.Colour(0x0094e9)
greenColour = discord.Colour(0x2ECC71)
redColour = discord.Colour(0xB21E35)

trophy_emoji = '<:trophies:870361537087414292>'
swords_emoji = '<:swords:870361536923848765>'
cards_emoji = '<:cards:870361537985003541>'
stats_emoji = '<:stats:870368722169233439>'
clashbook_emoji = '<:clashbook:870721637102813224>'
cardsrandom_emoji = '<:cardsrandom:870724355934531619>'
trophieslegendary_emoji = '<:trophieslegendary:870724357641621514>'
clashscroll_emoji = '<:clashscroll:870740831823355917>'

loading_emoji = '<a:loading_gif:1009438327063195718>'
tick_emoji = '<:CircleCheck:1009467320894242956>'
cross_emoji = '<:CircleClose:1009467333678473336>'

clashdot_emoji = '<:ClashRoyaleDot:1022857029930459156>'

join_emoji = '<:join_icon:1048567027683557468>'
leave_emoji = '<:leave_icon:1048567086479310929>'
slashcmd_emoji = '<:slashcmd_icon:1048567479741448194>'
shine_emoji = '<:shine_icon:1048572660721917992>'

# Define Discord Modules
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents, owner_id=490537526436560896, debug_guilds=[settings['servers']['main']])

punishment = bot.create_group("punishment", "Sätt en spelare i skamvrån!")
trade = bot.create_group("trade", "Commands associated with trading")
tournament = bot.create_group("tournament", "Commands associated with tournaments")
disqualify = bot.create_group("disqualify", "Commands associated with disqualifying players")
otherclan = bot.create_group("clan", "Manage roles for other clans")

print('Loading Bot...')

def inverse_dict(my_dict):
    result_dict = {}
    for key, value in my_dict.items():
        if not value in result_dict.keys():
            result_dict[value] = []
        result_dict[value].append(key)
    return result_dict

@bot.event
async def on_ready():
    # Change presence
    server = bot.get_guild(settings['servers']['main'])
    serverName = remove_emojis(server.name)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f'för CRS | crsweden.com'))

    syncall.start() # Start syncing all users automatically
    checkTournamentWinners.start() # Start checking tournaments for ending and winners
    change_banner.start() # Start changing the banner every 24 hours

    print(f'Bot loaded as "{bot.user}"')

@bot.event
async def on_member_join(member):

    linked_users_list = await all_linked_users()

    for userid in linked_users_list:
        if str(member.id) == userid:
            print(f'Syncing {member.id} as they\'ve joined and their account is already linked')
            await sync_command(member.id)
            print('Synced')

            # // Auto verify them
            if settings['roles']['clans']['basic']['wick-verified'] not in [r.id for r in member.roles]:
                await member.add_roles(discord.utils.get(member.guild.roles, id=settings['roles']['clans']['basic']['wick-verified']))

async def log(message, colour):
    channel = bot.get_channel(settings['channels']['bot-logs'])
    embed = discord.Embed(description=message, color=colour)
    await channel.send(embed=embed)

def remove_emojis(text):
    emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                            "]+", flags=re.UNICODE)
    return (emoji_pattern.sub(r'', text))

def unix(input):
  input = str(input)
  input = input.replace('Z', '')
  return round(dp.parse(input).timestamp())

@bot.command(name='info', description = 'View some info about the bot.')
async def info(ctx):

    # Generate Server Name
    server = bot.get_guild(settings['servers']['main'])
    server_name = remove_emojis(server.name)

    # Create Embed
    embed = discord.Embed(title=f'{server_name} Info', color=defaultColour)

    embed.add_field(name='Server ID', value=f':computer: `{server.id}`')
    embed.add_field(name='Bot Version', value=f':robot: `v{bot_version}`')
    embed.add_field(name='Language', value=f':flag_se: `se`')
    embed.add_field(name='Linked Accounts', value=f':handshake: `{await total_linked()}`')
    embed.add_field(name='Open Source Repository', value=f':open_file_folder: [thomaskeig/cr-sweden](https://github.com/thomaskeig/cr-sweden)')

    embed.set_footer(text=f'{bot.user} - Created by thomaskeig', icon_url=bot.user.avatar.url)

    await ctx.respond(embed=embed)

# Check for account link messages
@bot.event
async def on_message(message):

    # // Ignore bot messages
    if message.author == bot.user:
        return
    
    # // Auto publish announcement channel messages
    try:
        if message.channel.is_news():
            await message.publish()
            print(f'Automatically published message from #{message.channel} (Message ID: {message.id})')
    except:
        pass

    if message.channel.id == settings['channels']['link'] and message.author.id != bot.user.id and message.author.id not in settings['link-channel-ignored-ids']:
        #Check if message was sent in link channel ||| message not sent by the bot ||| message not sent by ignored users
        message_content = message.content

        channel = bot.get_channel(message.channel.id)

        if await is_linked_discord(message.author.id):
            embed = discord.Embed(description=f'<@{message.author.id}> Du har redan länkat ett konto! Ta bort länken genom att använda kommandot `/unlink`!', color=redColour)
            embed_message = await channel.send(embed=embed)
            await message.delete()
            await asyncio.sleep(10)
            await embed_message.delete()

        else:
            if len(message_content) > 15:
                embed = discord.Embed(description=f'<@{message.author.id}> Det där ser inte ut som en Clash Royale #tag, dubbelkolla så att du skrivit rätt eller be om hjälp!', color=redColour)
                embed_message = await channel.send(embed=embed)
                await message.delete()
                await asyncio.sleep(10)
                await embed_message.delete()
            
            tag = message_content.replace('#', '')

            if await is_linked_cr(tag): # Check if the tag already linked
                embed = discord.Embed(description=f'<@{message.author.id}> #tag är redan i använding. Vänligen länka ditt egna konto!', color=redColour)
                embed_message = await channel.send(embed=embed)
                await message.delete()
                await asyncio.sleep(10)
                await embed_message.delete()
            
            else:

                async with aiohttp.ClientSession() as cs:
                    async with cs.get(f'https://proxy.royaleapi.dev/v1/players/%23{tag}', headers=api) as data:
                        
                        if data.status == 403:
                            embed = discord.Embed(description=f'<@{message.author.id}> Ett internt problem har skett. API\'n tillåter inte tillgången till den här serverns IP.', color=redColour)
                            embed_message = await channel.send(embed=embed)
                            await message.delete()
                            await asyncio.sleep(10)
                            await embed_message.delete()

                        elif data.status == 404:
                            embed = discord.Embed(description=f'<@{message.author.id}> Jag hittar inte det där kontot. Se till att du skrivit rätt #tag!', color=redColour)
                            embed_message = await channel.send(embed=embed)
                            await message.delete()
                            await asyncio.sleep(10)
                            await embed_message.delete()
                        
                        elif data.status != 200:
                            embed = discord.Embed(description=f'<@{message.author.id}> Ett okänt internt problem har inträffat. Ber om ursäkt för det! Vänligen kontakta en Administratör för hjälp! (Error {data.status})', color=redColour)
                            embed_message = await channel.send(embed=embed)
                            await message.delete()
                            await asyncio.sleep(10)
                            await embed_message.delete()

                        else: # data.status == 200

                            profile = await data.json()

                            official_tag = profile['tag'].replace('#', '')
                            official_name = profile['name']
                            
                            # Link the account in the database
                            await add_user(discordid=message.author.id, cr_tag=official_tag)

                            embed = discord.Embed(description=f'<@{message.author.id}> har länkat sitt konto till "{official_name}" `#{official_tag}`', color=greenColour)
                            embed_message = await channel.send(embed=embed)
                            await message.delete()

                            await sync_command(message.author.id)

                            await asyncio.sleep(10)
                            await embed_message.delete()

                            await log(
                                message = f'<@{message.author.id}> har länkat sitt konto till "{official_name}" `#{official_tag}`',
                                colour = greenColour
                            )

@bot.command(name="unlink", description='Unlink your Clash Royale account from your Discord Account.')
@commands.cooldown(3, 30, commands.BucketType.user)
async def unlink(ctx):
    await ctx.defer(ephemeral=True)

    if not await is_linked_discord(ctx.author.id):

        embed = discord.Embed(description=f'Du har inte länkat ditt konto, därför kan du inte unlinka det!', color=redColour)
        await ctx.send(embed=embed, ephemeral=True)
    
    else:
        
        # Unlink the account from the database
        await remove_user(ctx.author.id)

        embed = discord.Embed(description=f'Klart! Nu kan du länka ett nytt konto', color=greenColour)
        await ctx.send(embed=embed, ephemeral=True)

        # Remove other clan roles
        with open('./data/otherClans.json', 'r') as f:
            other_clans = json.load(f)

        for i in other_clans:

            for roletype in ['member', 'elder', 'coleader', 'leader']:

                if i['roles'][roletype] in [r.id for r in ctx.author.roles]:
                    await ctx.author.remove_roles(discord.utils.get(ctx.author.guild.roles, id=i['roles'][roletype]))

        # King level - Remove Roles
        for i in list(settings['roles']['clans']['king-level'].values()):
            if i in [r.id for r in ctx.author.roles]:
                await ctx.author.remove_roles(discord.utils.get(ctx.author.guild.roles, id=i))

        # Remove Linked account role
        if settings['roles']['clans']['basic']['account-linked'] in [r.id for r in ctx.author.roles]:
            await ctx.author.remove_roles(discord.utils.get(ctx.author.guild.roles, id=settings['roles']['clans']['basic']['account-linked']))

        # Give temporary role
        if settings['roles']['clans']['basic']['temporary'] not in [r.id for r in ctx.author.roles]:
            await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, id=settings['roles']['clans']['basic']['temporary']))

        await log(
                message = f'<@{ctx.author.id}> har unlinkat sitt konto!',
                colour = greenColour
            )
                
def remove_all_values_from_list(the_list, val):
   return [value for value in the_list if value != val]

async def sync_command(userid):
    try:

        channel = bot.get_channel(settings['channels']['sync-logs'])

        if await is_linked_discord(userid):
            
            server = bot.get_guild(settings['servers']['main'])
            user = server.get_member(int(userid))
            
            tag = await get_tag(userid)

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://proxy.royaleapi.dev/v1/players/%23{tag}', headers=api) as data:
                    profile = await data.json()
            
            if data.status != 200:
                embed = discord.Embed(description=f'{cross_emoji} Problem vid försök att införskaffa data om <@{userid}>\'s konto. Felkod: {data.status}: `{profile["reason"]}`', color=redColour)
                await channel.send(embed=embed)
            
            else: # data.status == 200

                name = profile["name"]
                tag = profile["tag"]
                expLevel = profile["expLevel"]

                try:
                    gameRole = profile["role"]
                except:
                    gameRole = 'noClan'

                embed = discord.Embed(description=f'{loading_emoji} Synkar roller åt **{name}** `{tag}`', color=discord.Colour(0xffd500))
                original_msg = await channel.send(embed=embed)


                try:
                    clan_tag = profile["clan"]["tag"]
                except:
                    clan_tag = '#000000'

                # Only change nickname if they don't have the ignore nickname change role
                try:
                    if settings['roles']['utility']['ignore-nickname-change'] not in [r.id for r in user.roles]:
                        await user.edit(nick=name)

                except: # If the bot doesn't have permission to change the nickname, it doesn't halt
                    pass



                clan_member_id_list = []

                with open('./data/otherClans.json', 'r') as f:
                    other_clans = json.load(f)
                
                for i in other_clans:
                    clan_member_id_list.append(i['roles']['member'])
                    clan_member_id_list.append(i['roles']['elder'])
                    clan_member_id_list.append(i['roles']['coleader'])
                    clan_member_id_list.append(i['roles']['leader'])


                # GIVE OTHER CLAN ROLES
                clan_family_roles_given = []
                for clan_family in other_clans:

                    for clanid in clan_family['clans']:

                        if clan_tag == ('#' + clanid):
                            
                            # Add MEMBER role if they don't have it
                            if clan_family['roles']['member'] not in [r.id for r in user.roles]:
                                role = discord.utils.get(user.guild.roles, id=clan_family['roles']['member'])
                                await user.add_roles(role)
                            clan_family_roles_given.append(clan_family['roles']['member'])
                            
                            # Add ELDER role if they need it but don't have it
                            if clan_family['roles']['elder'] is not None: # Check one is defined
                                if gameRole == 'elder':
                                    if clan_family['roles']['elder'] not in [r.id for r in user.roles]:
                                        role = discord.utils.get(user.guild.roles, id=clan_family['roles']['elder'])
                                        await user.add_roles(role)
                                    clan_family_roles_given.append(clan_family['roles']['elder'])

                            # Add COLEADER role if they need it but don't have it
                            if clan_family['roles']['coleader'] is not None: # Check one is defined
                                if gameRole == 'coLeader':
                                    if clan_family['roles']['coleader'] not in [r.id for r in user.roles]:
                                        role = discord.utils.get(user.guild.roles, id=clan_family['roles']['coleader'])
                                        await user.add_roles(role)
                                    clan_family_roles_given.append(clan_family['roles']['coleader'])

                            # Add LEADER role if they need it but don't have it
                            if clan_family['roles']['leader'] is not None: # Check one is defined
                                if gameRole == 'leader':
                                    if clan_family['roles']['leader'] not in [r.id for r in user.roles]:
                                        role = discord.utils.get(user.guild.roles, id=clan_family['roles']['leader'])
                                        await user.add_roles(role)
                                    clan_family_roles_given.append(clan_family['roles']['leader'])
                            
                            break

                # REMOVE OTHER CLAN ROLES
                # Remove items from list1 that appear in list2
                clan_member_id_list = [item for item in clan_member_id_list if item not in clan_family_roles_given]

                for a in clan_member_id_list: # For every clan member role, remove it from the user if them have it
                    if a in [r.id for r in user.roles]:
                        await user.remove_roles(discord.utils.get(user.guild.roles, id=a))
  

                # KING LEVEL SYNC
                kinglevels = list(settings['roles']['clans']['king-level'].keys())

                for i in kinglevels:
                    
                    if expLevel >= i:
                        king_level_dropback = i
                    else:
                        break

                if settings['roles']['clans']['king-level'][king_level_dropback] not in [r.id for r in user.roles]: # If they dont have the role, give it to them
                    await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['king-level'][king_level_dropback]))

                temp_list = [] # Temp list includes all king level roles except their one
                for i in list(settings['roles']['clans']['king-level'].values()):
                    if i != settings['roles']['clans']['king-level'][king_level_dropback]:
                        temp_list.append(i)
                
                for a in temp_list:
                    if a in [r.id for r in user.roles]: # If they have the role, remove it from them
                        await user.remove_roles(discord.utils.get(user.guild.roles, id=a))
                
                # Manage Leader / CoLeader / Elder / Member Role
                if gameRole == 'leader':
                    if settings['roles']['clans']['leader'] not in [r.id for r in user.roles]:
                        await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['leader']))

                        removal_roles = [ settings['roles']['clans']['coleader'], settings['roles']['clans']['elder'], settings['roles']['clans']['member'] ]
                        for looprole in removal_roles:
                            if looprole in [r.id for r in user.roles]:
                                await user.remove_roles(discord.utils.get(user.guild.roles, id=looprole))
                
                elif gameRole == 'coLeader':
                    if settings['roles']['clans']['coleader'] not in [r.id for r in user.roles]:
                        await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['coleader']))

                        removal_roles = [ settings['roles']['clans']['leader'], settings['roles']['clans']['elder'], settings['roles']['clans']['member'] ]
                        for looprole in removal_roles:
                            if looprole in [r.id for r in user.roles]:
                                await user.remove_roles(discord.utils.get(user.guild.roles, id=looprole))
                
                elif gameRole == 'elder':
                    if settings['roles']['clans']['elder'] not in [r.id for r in user.roles]:
                        await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['elder']))

                        removal_roles = [ settings['roles']['clans']['leader'], settings['roles']['clans']['coleader'], settings['roles']['clans']['member'] ]
                        for looprole in removal_roles:
                            if looprole in [r.id for r in user.roles]:
                                await user.remove_roles(discord.utils.get(user.guild.roles, id=looprole))

                elif gameRole == 'member':
                    if settings['roles']['clans']['member'] not in [r.id for r in user.roles]:
                        await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['member']))

                        removal_roles = [ settings['roles']['clans']['leader'], settings['roles']['clans']['coleader'], settings['roles']['clans']['elder'] ]
                        for looprole in removal_roles:
                            if looprole in [r.id for r in user.roles]:
                                await user.remove_roles(discord.utils.get(user.guild.roles, id=looprole))

                else:
                        removal_roles = [ settings['roles']['clans']['leader'], settings['roles']['clans']['coleader'], settings['roles']['clans']['elder'], settings['roles']['clans']['member'] ]
                        for looprole in removal_roles:
                            if looprole in [r.id for r in user.roles]:
                                await user.remove_roles(discord.utils.get(user.guild.roles, id=looprole))

                # Add Linked account role
                if settings['roles']['clans']['basic']['account-linked'] not in [r.id for r in user.roles]:
                    await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['basic']['account-linked']))

                # Remove temporary role
                if settings['roles']['clans']['basic']['temporary'] in [r.id for r in user.roles]:
                    await user.remove_roles(discord.utils.get(user.guild.roles, id=settings['roles']['clans']['basic']['temporary']))

                # GIVE DUNCE ROLE
                dunce = await dunce_status(userid)

                if dunce:
                    if settings['roles']['utility']['dunce'] not in [r.id for r in user.roles]: # If they don't have the role, give it to them
                        await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['utility']['dunce']))
                        
                if not dunce:
                    if settings['roles']['utility']['dunce'] in [r.id for r in user.roles]: # If they have the role, remove it from them
                        await user.remove_roles(discord.utils.get(user.guild.roles, id=settings['roles']['utility']['dunce']))

                embed = discord.Embed(description=f'{tick_emoji} Synkade roller åt **{name}** `{tag}`', color=greenColour)
                await original_msg.edit(embed=embed)

    
    except Exception as e:
        print(f'Sync Error: {e}')
        embed = discord.Embed(description=f'{cross_emoji} Ett problem har inträffat!\n```{e}```', color=discord.Colour(0xb31e35))
        await channel.send(embed=embed)


@bot.command(name='reload', description = 'Reload the bot\'s settings.')
async def reload(ctx):

    if ctx.author.id == 490537526436560896 or ctx.author.id == 282548554285711370:

        with open('./settings.yml', encoding="utf8") as file:
            try:

                global settings
                settings = yaml.load(file, Loader=yaml.FullLoader)

                await ctx.respond(f'{tick_emoji} Successfully reloaded the settings!')

            except Exception as e:
                await ctx.respond(f'{cross_emoji} Error while reloading settings!\n`{e}`')


@bot.command(name='forcesync', description = 'Force a sync on any user')
@option("user", discord.User, description="The user to force sync.", required=True)
async def forcesync(ctx, user:discord.user):

    await ctx.defer()

    await sync_command(user.id)
    embed = discord.Embed(description=f'{tick_emoji} Synkade rollerna åt {user}', color=greenColour)
    await ctx.respond(embed=embed)

@bot.command(name="suggest", description='Make a suggestion for the server & tournaments.')
@option("suggestion", description="Please explain your suggestion in as much detail as possible.", required=True)
@commands.cooldown(3, 600, commands.BucketType.user) # The command can only be used 3 times in 600 seconds
async def suggest(ctx, suggestion):

    embed = discord.Embed(description=suggestion, color=defaultColour)

    embed.set_author(name=f'Suggestion from {ctx.author}', icon_url=ctx.author.avatar.url)

    channel = bot.get_channel(settings['channels']['suggestions'])
    suggestion_message = await channel.send(embed=embed)

    await suggestion_message.add_reaction('✅')
    await suggestion_message.add_reaction('❌')

    embed = discord.Embed(title='Suggestion sent!',
                          description=f'Your suggestion has been sent to <#{settings["channels"]["suggestions"]}>.\n```{suggestion}```',
                          color=greenColour)
    await ctx.respond(embed=embed, ephemeral=True)

@punishment.command(name="list", description='List all users who have been punished')
@commands.cooldown(3, 15, commands.BucketType.user) # The command can only be used 3 times in 15 seconds
async def punishment_list(ctx):
    
    message = ''

    for userid in await all_dunce_users():
        user = await bot.fetch_user(userid)
        message = message + f'- **{user}** `{user.id}`\n'
    
    embed = discord.Embed(title=f'Punished Users', description=message, color=defaultColour)

    await ctx.respond(embed=embed)


@punishment.command(name="add", description='Varna andra om spelarens beteende! Låser ett antal funktioner & ger ut en ful rollfärg.')
@option("user", discord.User, description="Namnet på spelaren!", required=True)
@option("reason", description="Inkludera detaljer om varför du valt att sätta spelaren i skamvrån!", required=True)
@commands.cooldown(5, 3600, commands.BucketType.user) # The command can only be used 5 times in 3600 seconds
async def suggest(ctx, user, reason):
    
    if await dunce_status(user.id):
        await ctx.respond('Den här spelaren är redan placerad i skamvrån!')
    
    else:
        
        change_dunce(user.id, new_value=True)

        channel = bot.get_channel(settings['channels']['dunce-logs'])
        await channel.send(f'**{ctx.author}** `{ctx.author.id}` placerade **{user}** `{user}` i skamvrån pågrund.')
        
        await ctx.respond('Jag placerade den här spelaren i skamvrån!', ephemeral=True)

        await sync_command(user.id)
    
@punishment.command(name="remove", description='Ta ut en spelare ur skamvrån! Återger normal tillgång till servern!')
@option("user", discord.User, description="Namnet på spelaren!", required=True)
@commands.cooldown(5, 3600, commands.BucketType.user) # The command can only be used 5 times in 3600 seconds
async def suggest(ctx, user):
    
    if not await dunce_status(user.id):
        await ctx.respond('Den här spelaren är inte placerad i skamvrån!')
    
    else:
        
        change_dunce(user.id, new_value=False)
        
        await ctx.respond('Jag tog ut spelaren ur skamvrån!', ephemeral=True)

        channel = bot.get_channel(settings['channels']['dunce-logs'])
        await channel.send(f'**{ctx.author}** `{ctx.author.id}` tog ut **{user}** `{user}` ur skamvrån.')

        await sync_command(user.id)

async def cardListWithoutChampions():
    async with aiohttp.ClientSession() as cs:
        async with cs.get(f'https://proxy.royaleapi.dev/v1/cards', headers=api) as data:
            data = await data.json()
    
    cardList = []

    for i in data['items']:
        if i['maxLevel'] != 4: # If the card is not a champion
            cardList.append(i['name'])
    
    return cardList

async def getCards(ctx: discord.AutocompleteContext):
    return [card for card in await cardListWithoutChampions()]

@trade.command(name="addcard", description='Add a card to your list of requests. You\'ll be pinged when someone offers one for a trade.')
@option("card", description="Name of the card", required=True, autocomplete=discord.utils.basic_autocomplete(getCards))
async def trade_addcard(ctx, card):

    if not await is_linked_discord(ctx.author.id):
        embed = discord.Embed(description=f'{slashcmd_emoji} Du har inte länkat ditt konto, länka ditt konto innan du försöker handla!', color=redColour)
        await ctx.respond(embed=embed)
    
    else:
        with open('./data/userTrades.json', 'r') as f:
            data = json.load(f)
        
        if str(ctx.author.id) not in data: # if the user doesn't have a list already
            data[str(ctx.author.id)] = []

            with open('./data/userTrades.json', 'w') as f:
                json.dump(data, f, indent=4)
        
            with open('./data/userTrades.json', 'r') as f: # Reopen file with updated info
                data = json.load(f)
        
        userList = data[str(ctx.author.id)]

        if len(userList) >= settings['trades']['max-cards']:
            embed = discord.Embed(description=f'{slashcmd_emoji} You can only add `{settings["trades"]["max-cards"]}` cards to your list. You currently have `{len(userList)}`.\n\nRemove cards with `/trade removecard` and view your full list with `/trade list`.', color=redColour)
            await ctx.respond(embed=embed)
        
        else:

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://proxy.royaleapi.dev/v1/cards', headers=api) as r:
                    cardData = await r.json()
            
            found = False
            for i in cardData['items']:
                if i['name'].lower() == card.lower():

                    found = True

                    if i['maxLevel'] != 4: # If the card isn't a champion
                        champion = False
                        cardId = i['id']
                    else: # The card is a champion
                        champion = True

                    cardName = i['name']
                    cardIcon = i['iconUrls']['medium']
                    
                    break

            
            if not found:
                embed = discord.Embed(description=f'{slashcmd_emoji} `{card}` cannot be found. Make sure you entered the name correctly!', color=redColour)
                await ctx.respond(embed=embed)
            
            elif champion: # If the card is a champion
                cardName = i['name']
                cardIcon = i['iconUrls']['medium']

                embed = discord.Embed(description=f'{slashcmd_emoji} `{cardName}` is a Champion and cannot be traded. Therefore it cannot be added to your list.', color=redColour)
                embed.set_thumbnail(url=cardIcon)
                await ctx.respond(embed=embed)

            else:
            
                if cardId in userList:
                    embed = discord.Embed(description=f'{slashcmd_emoji} `{cardName}` is already in your list. Remove it with `/trade removecard` or view your current list with `/trade list`.', color=redColour)
                    embed.set_thumbnail(url=cardIcon)
                    await ctx.respond(embed=embed)
                
                else:

                    data[str(ctx.author.id)].append(cardId)

                    with open('./data/userTrades.json', 'w') as f:
                        json.dump(data, f, indent=4)

                    embed = discord.Embed(description=f'{join_emoji} You have added `{cardName}` to your trade request list. You will be pinged when someone offers this card!\n\n> View your full list with: `/trade list`\n\n{shine_emoji} You have used `{len(userList)}/{settings["trades"]["max-cards"]}` notification slots.', color=greenColour)
                    embed.set_thumbnail(url=cardIcon)
                    await ctx.respond(embed=embed)



@trade.command(name="removecard", description='Remove a card from your list of requests.')
@option("card", description="Name of the card", required=True, autocomplete=discord.utils.basic_autocomplete(getCards))
async def trade_removecard(ctx, card):

    if not await is_linked_discord(ctx.author.id):
        embed = discord.Embed(description=f'{slashcmd_emoji} Du har inte länkat ditt konto, länka ditt konto innan du försöker handla!', color=redColour)
        await ctx.respond(embed=embed)
    
    else:
        with open('./data/userTrades.json', 'r') as f:
            data = json.load(f)
        
        if str(ctx.author.id) not in data: # if the user doesn't have a list already
            data[str(ctx.author.id)] = []

            with open('./data/userTrades.json', 'w') as f:
                json.dump(data, f, indent=4)
        
            with open('./data/userTrades.json', 'r') as f: # Reopen file with updated info
                data = json.load(f)
        
        userList = data[str(ctx.author.id)]

        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://proxy.royaleapi.dev/v1/cards', headers=api) as r:
                cardData = await r.json()
        
        found = False
        for i in cardData['items']:
            if i['name'].lower() == card.lower():
                found = True
                cardId = i['id']
                cardName = i['name']
                cardIcon = i['iconUrls']['medium']
                break
        
        if not found:
            embed = discord.Embed(description=f'{slashcmd_emoji} `{card}` cannot be found. Make sure you entered the name correctly!', color=redColour)
            await ctx.respond(embed=embed)

        else:
            if cardId not in userList:
                embed = discord.Embed(description=f'{slashcmd_emoji} `{cardName}` is not in list. Add it with `/trade addcard` or view your current list with `/trade list`.', color=redColour)
                embed.set_thumbnail(url=cardIcon)
                await ctx.respond(embed=embed)
            
            else:

                data[str(ctx.author.id)].remove(cardId)

                with open('./data/userTrades.json', 'w') as f:
                    json.dump(data, f, indent=4)

                embed = discord.Embed(description=f'{leave_emoji} You have removed `{cardName}` from your trade request list. You will not longer be pinged when someone offers this card!\n\n> View your full list with: `/trade list`\n\n{shine_emoji} You have used `{len(userList)}/{settings["trades"]["max-cards"]}` notification slots.', color=greenColour)
                embed.set_thumbnail(url=cardIcon)
                await ctx.respond(embed=embed)

@trade.command(name="list", description='View your cards that you have trade notifications for')
async def trade_list(ctx):

    if not await is_linked_discord(ctx.author.id):
        embed = discord.Embed(description=f'{slashcmd_emoji} Du har inte länkat ditt konto, länka ditt konto innan du försöker handla!', color=redColour)
        await ctx.respond(embed=embed)
    
    else:
        with open('./data/userTrades.json', 'r') as f:
            data = json.load(f)
        
        if str(ctx.author.id) not in data: # if the user doesn't have a list already
            data[str(ctx.author.id)] = []

            with open('./data/userTrades.json', 'w') as f:
                json.dump(data, f, indent=4)
        
            with open('./data/userTrades.json', 'r') as f: # Reopen file with updated info
                data = json.load(f)
        
        userList = data[str(ctx.author.id)]

        message = ''

        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://proxy.royaleapi.dev/v1/cards', headers=api) as r:
                cardData = await r.json()

        for cardId in userList:
            for a in cardData['items']:
                if a['id'] == cardId:
                    cardName = a['name']

            message = message + f'{clashdot_emoji} `{cardName}`\n'

        embed = discord.Embed(title=f'{ctx.author.name}\'s Trade List', description=f'{message}\n{shine_emoji} You have used `{len(userList)}/{settings["trades"]["max-cards"]}` notification slots.', color=defaultColour)
        embed.set_footer(text='Add and remove cards from your list with "/trade addcard" & "/trade removecard"')

        await ctx.respond(embed=embed)

async def findCard(card):

    if card is None: # If the card wasn't given, don't even try to find it.
        return json.loads(json.dumps({"success": None, "cardId": None, "cardName": None, "maxLevel": None, "cardIcon": None}))

    async with aiohttp.ClientSession() as cs:
        async with cs.get(f'https://proxy.royaleapi.dev/v1/cards', headers=api) as r:
            cardData = await r.json()

    found = 'false'
    cardId = None
    cardName = None
    maxLevel = None
    cardIcon = None

    for i in cardData['items']:
        if i['name'].lower() == card.lower():
            found = 'true'
            cardId = i['id']
            cardName = i['name']
            maxLevel = i['maxLevel']
            cardIcon = i['iconUrls']['medium']
            break

    return json.loads(json.dumps({"success": found, "cardId": str(cardId), "cardName": cardName, "maxLevel": str(maxLevel), "cardIcon": cardIcon}))

def allItemsSame(list):


    first = list[0]
    chk = True

    # Comparing each element with first item
    for item in list:
        if first != item:
            if item != None:
                chk = False
                break

    return chk

def duplicatesInList(list):

    # Remove all None occurences from the list
    for i in list:
        if i == None:
            list.remove(i)

    # Return if there are any duplicates
    return len(list) != len(set(list))


@trade.command(name="create", description='Start a trade request')
@option("request", description="[REQUIRED] The card you would like to take from the other player for the trade", required=True, autocomplete=discord.utils.basic_autocomplete(getCards))
@option("offer_1", description="[REQUIRED] The first card you are willing to give away for your trade", required=True, autocomplete=discord.utils.basic_autocomplete(getCards))
@option("offer_2", description="[NOT REQUIRED] The second card you are willing to give away for your trade", required=False, autocomplete=discord.utils.basic_autocomplete(getCards))
@option("offer_3", description="[NOT REQUIRED] The third card you are willing to give away for your trade", required=False, autocomplete=discord.utils.basic_autocomplete(getCards))
@option("offer_4", description="[NOT REQUIRED] The fourth card you are willing to give away for your trade", required=False, autocomplete=discord.utils.basic_autocomplete(getCards))
@commands.cooldown(3, 6000, commands.BucketType.user) # The command can only be used 5 times in 6000 seconds
async def trade_create(ctx, request, offer_1=None, offer_2=None, offer_3=None, offer_4=None):

    if not await is_linked_discord(ctx.author.id):
        embed = discord.Embed(description=f'{slashcmd_emoji} Du har inte länkat ditt konto, länka ditt konto innan du försöker handla!', color=redColour)
        await ctx.respond(embed=embed)
    
    else:

        offerCards = [offer_1, offer_2, offer_3, offer_4]

        # Remove any cards that were not inputted
        offerCards = [i for i in offerCards if i is not None]
        
        # Create JSON of cards
        userRequestCard = await findCard(request)
        userOffer1Card = await findCard(offer_1)
        userOffer2Card = await findCard(offer_2)
        userOffer3Card = await findCard(offer_3)
        userOffer4Card = await findCard(offer_4)

        # Check if request card is valid
        if userRequestCard['success'] == False:
            embed = discord.Embed(description=f'{cross_emoji} The card `{request}` could not be found. Check your entry for spelling mistakes.', color=redColour)
            await ctx.respond(embed=embed)
        
        # Check if all the offer cards are valid
        elif userOffer1Card['success'] == False or userOffer2Card['success'] == False or userOffer3Card['success'] == False or userOffer4Card['success'] == False: # If any offer cards are inputted but are not valid
            embed = discord.Embed(description=f'{cross_emoji} One or more of your offer cards could not be found. Check your entry for spelling mistakes.', color=redColour)
            await ctx.respond(embed=embed)
        
        # Check if any cards are duplicates
        elif duplicatesInList([userRequestCard['cardId'], userOffer1Card['cardId'], userOffer2Card['cardId'], userOffer3Card['cardId'], userOffer4Card['cardId']]):
            embed = discord.Embed(description=f'{cross_emoji} You have given duplicate cards! Remember, you don\'t have to use all the offer slots!', color=redColour)
            await ctx.respond(embed=embed)

        # Check if all items are the same rarity
        elif not allItemsSame([userRequestCard['maxLevel'], userOffer1Card['maxLevel'], userOffer2Card['maxLevel'], userOffer3Card['maxLevel'], userOffer4Card['maxLevel']]): # If item rarities are not the same
            embed = discord.Embed(description=f'{cross_emoji} Please make sure you select cards of the same rarity so you are able to trade them!', color=redColour)
            await ctx.respond(embed=embed)

        # Check if any cards are a champion
        elif userRequestCard['maxLevel'] == 4 or userOffer1Card['maxLevel'] == 4 or userOffer2Card['maxLevel'] == 4 or userOffer3Card['maxLevel'] == 4 or userOffer4Card['maxLevel'] == 4:
            embed = discord.Embed(description=f'{cross_emoji} One or more of your cards are a champion and cannot be traded!', color=redColour)
            await ctx.respond(embed=embed)

        else: # No errors were found

            await ctx.defer()

            tradeId = str(''.join(random.choices(string.ascii_uppercase +  string.digits, k = 8)))

            # Create role for trade ID & assign colour
            designatedRole = await ctx.guild.create_role(name=tradeId)

            # Give role to all users who would like that card
            with open('./data/userTrades.json', 'r') as f:
                tradeReqList = json.load(f)
            tradeReqListKeys = list(tradeReqList.keys())

            server = bot.get_guild(settings['servers']['main'])

            cardsToGive = [userOffer1Card['cardId'], userOffer2Card['cardId'], userOffer3Card['cardId'], userOffer4Card['cardId']]
            cardsToGiveNames = [userOffer1Card['cardName'], userOffer2Card['cardName'], userOffer3Card['cardName'], userOffer4Card['cardName']]

            # Loop through and apply roles
            for userid in tradeReqListKeys:
                userAlertIds = tradeReqList[userid]

                for card in userAlertIds:
                    for i in cardsToGive:
                        if i != None:
                            if int(i) == int(card): # If the user has the card on their list
                                user = server.get_member(int(userid))
                                await user.add_roles(discord.utils.get(user.guild.roles, id=designatedRole.id), reason='Pinging for trade deal')

            # Format cards to give as a string
            cardsToGiveStr = ''
            for i in cardsToGiveNames:
                if i != None:
                    cardsToGiveStr = cardsToGiveStr + i + ', '
            cardsToGiveStr = cardsToGiveStr[:len(cardsToGiveStr) - 2]

            # Get the authors current clan
            tag = await get_tag(ctx.author.id)

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://proxy.royaleapi.dev/v1/players/%23{tag}', headers=api) as data:
                    profile = await data.json()
            
            crIgn = profile['name']
            crTag = profile['tag']
            
            try:
                clanName = profile['clan']['name']
                clanTag = profile['clan']['tag']
            except:
                clanName, clanTag = 'No Clan', '#000000'

            # Get trade clan info
            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://proxy.royaleapi.dev/v1/clans/%23{settings["trades"]["trade-clan-id"]}', headers=api) as data:
                    tradeClan = await data.json()
            
            tradeClanName = tradeClan['name']
            tradeClanTag = tradeClan['tag']



            main = discord.Embed(title=f'Incoming Trade Request from {ctx.author.name}', color=defaultColour)

            main.add_field(name='Terms of the Trade:', value =f'{clashdot_emoji} You must give: `{userRequestCard["cardName"]}`\n{clashdot_emoji} You can recieve either: `{cardsToGiveStr}`', inline = False)
            main.add_field(name=f'{ctx.author.name}\'s IGN:', value =f'{crIgn} `{crTag}`', inline = False)
            main.add_field(name=f'{ctx.author.name}\'s Clan:', value =f'{clanName} `{clanTag}`', inline = False)
            main.set_footer(text='You have requested to be pinged to be able to recieve one of the cards above.')
            main.set_thumbnail(url=userRequestCard["cardIcon"])

            clanPromo = discord.Embed(title=f'Not in the same clan?', description=f'Feel free to use the CRS Trading clan!', color=defaultColour)
            clanPromo.add_field(name=f'Clan Information:', value =f'**Name:** `{tradeClanName}`\n**Tag:** `{tradeClanTag}`', inline = False)
            clanPromo.set_thumbnail(url=bot.user.avatar.url)
            clanPromo.set_footer(text='Make sure the trade clan tag matches the one above and that you leave the clan once you have completed the trade!')

            threadPromo = discord.Embed(description=f'Please use the thread below to discuss & complete this trade:', color=defaultColour)

            channel = bot.get_channel(settings['trades']['incoming-trades'])
            tradeMsg = await channel.send(content=f'<@&{designatedRole.id}>', embeds=[main, clanPromo, threadPromo])

            tradeThread = await tradeMsg.create_thread(name=f'{userRequestCard["cardName"]} requested by {ctx.author} - ({tradeId})', auto_archive_duration=1440) # Auto archive after 1 day

            tradeMsgLink = tradeMsg.jump_url
            tradeThreadLink = tradeThread.jump_url
        
            successEmbed = discord.Embed(description=f'Your trade request for {userRequestCard["cardName"]} has been created successfully!\n\n[Jump to Message]({tradeMsgLink})\n[Jump to Thread]({tradeThreadLink})', color=defaultColour)
            successEmbed.set_footer(text=f'Trade ID: {tradeId}')
            await ctx.respond(embed=successEmbed)

            await asyncio.sleep(10) # Wait 10 seconds then delete role

            tradeRole = discord.utils.get(ctx.guild.roles, id=designatedRole.id)
            await tradeRole.delete()



@tournament.command(name="create", description='Create a tournament')
@option("tag", description="Create the tournament in-game then add the tournament tag here", required=True)
@option("description", description="Tournament Description", required=True)
@option("password", description="Enter the password to join the tournament. Leave blank if there is no password", required=False)
@option("prize", description="What is the prize for the winner. Leave blank if there is no prize", required=False)
@commands.cooldown(3, 6000, commands.BucketType.user) # The command can only be used 5 times in 6000 seconds
async def tournament_create(ctx, tag, description, password=None, prize='No Prize'):
    
    tournamentTag = tag.replace('#', '')

    async with aiohttp.ClientSession() as cs:
        async with cs.get(f'https://proxy.royaleapi.dev/v1/tournaments/%23{tournamentTag}', headers=api) as data:
            tournamentData = await data.json()

    if data.status == 404:
        await ctx.respond('That tournament was not found, make sure you copied the tag correctly!', ephemeral=True)
    
    else:
        
        await ctx.defer()

        allowedContinue = True
        if tournamentData["type"] == 'open':
            password = 'Open (No Password)'
        elif tournamentData["type"] == 'passwordProtected':
            if password is None:
                allowedContinue = False
        
        if not allowedContinue:
            await ctx.respond('That tournament is password protected but you didn\'t supply a password. Please add a password to post the event.', ephemeral=True)

        else:
            
            gamemodeName = 'Not Found'

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://royaleapi.github.io/cr-api-data/json/game_modes.json', headers=api) as data:
                    gamemodeData = await data.json()
            
            for i in gamemodeData:
                if i["id"] == tournamentData["gameMode"]["id"]:
                    gamemodeName = i["name_en"]

            titleEmbed = discord.Embed(color=defaultColour)
            titleEmbed.set_image(url='https://media.discordapp.net/attachments/818205662332452956/1050878672971767918/CRSTurnering.png')

            today = datetime.date.today()
            weekOfYear = today.strftime("%W")
            date = f'{today.strftime("%d")}/{today.strftime("%m")}/{today.strftime("%Y")}'

            battleStart = unix(tournamentData["createdTime"]) + tournamentData["preparationDuration"]

            mainDescription = f'''
            V.{weekOfYear}・{date}

            CRS Presenterar veckans Turnering!
            För allas trevnad, följ våra <#1046453500906840174>

            <:ClashRoyaleExclamation:1022850120313745479>

            **Starting Time:** <t:{battleStart}:t> (<t:{battleStart}:R>)

            **Name:** {tournamentData["name"]} `{tournamentData["tag"]}`

            **Password:** {password}

            **Prize:** {prize}

            **Description:** {description}

            **Gamemode:** {gamemodeName}

            <:ClashRoyaleQuestion:1050892505509544086>

            **Frågor?** Kontakta en Administratör på Servern!

            '''

            descriptionEmbed = discord.Embed(title=f'TURNERING', description=mainDescription, color=defaultColour)
            descriptionEmbed.set_footer(text=f'Ansvaring Administratör: {ctx.author}', icon_url=ctx.author.avatar.url)
            
            channel = bot.get_channel(1046453546897391666)
            tournMessage = await channel.send(content='@everyone', embeds=[titleEmbed, descriptionEmbed])

            # Track the tournament
            with open('./data/trackedTournaments.json', 'r') as f:
                trackedTournaments = json.load(f)

            trackedTournaments.append(tournamentData["tag"].replace('#', ''))

            with open('./data/trackedTournaments.json', 'w') as f:
                json.dump(trackedTournaments, f, indent=4)

            # Send success message
            successEmbed = discord.Embed(description=f'Your Tournament has been posted in <#1046453546897391666>!\n\n[Jump to message]({tournMessage.jump_url})', color=greenColour)
            await ctx.respond(embed=successEmbed, ephemeral=True)

def TournData(tournamentData, rank):

    for i in tournamentData["membersList"]:
        if i['rank'] == rank:
            return i
    
    # If the rank wasn't found
    return json.loads(json.dumps({"name": 'n/a', "tag": '#000000', "score": '0'}))

@tasks.loop(minutes=3)
async def checkTournamentWinners():

    try:
        with open('./data/trackedTournaments.json', 'r') as f:
            trackedTournaments = json.load(f)

        for id in trackedTournaments:

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://proxy.royaleapi.dev/v1/tournaments/%23{id}', headers=api) as data:
                    tournamentData = await data.json()
            
            if tournamentData["status"] == 'ended': # If it's found a tournament that's just ended
                
                mainDescription = f'''
                **{tournamentData["name"]}** - `{tournamentData["tag"]}`

                `[ ★ ]` **{TournData(tournamentData, 1)["name"]}** `{TournData(tournamentData, 1)["tag"]}` ➔ **{TournData(tournamentData, 1)["score"]}** Wins

                `[ #2 ]` **{TournData(tournamentData, 2)["name"]}** `{TournData(tournamentData, 2)["tag"]}` ➔ **{TournData(tournamentData, 2)["score"]}** Wins
                `[ #3 ]` **{TournData(tournamentData, 3)["name"]}** `{TournData(tournamentData, 3)["tag"]}` ➔ **{TournData(tournamentData, 3)["score"]}** Wins
                '''
                embed = discord.Embed(title='Tournament Finished', description=mainDescription, color=defaultColour)

                channel = bot.get_channel(1050910616275140749)
                await channel.send(embed=embed)

                # Remove tournament from tracking
                trackedTournaments.remove(id)
                with open('./data/trackedTournaments.json', 'w') as f:
                    json.dump(trackedTournaments, f, indent=4)
    
    except Exception as e:
        print(f'Tracking Tournaments Error: {e}')
            



@disqualify.command(name="add", description='Disqualify a player')
@option("user", discord.User, description="The user to target.", required=True)
async def disqualify_add(ctx, user):

    # // Remove tournament rule accepted role
    await user.remove_roles(discord.utils.get(user.guild.roles, id=settings['roles']['utility']['accepted-tournament-rules']))

    # // Add disqualified role
    await user.add_roles(discord.utils.get(user.guild.roles, id=settings['roles']['utility']['disqualified']))
    
    embed = discord.Embed(title=f'User Disqualified', description=f'**User:** <@{user.id}>\n\nRevoke this ban with `/disqualify remove`.', color=defaultColour)

    await ctx.respond(embed=embed, ephemeral=True)



@disqualify.command(name="remove", description='Remove a disqualification for a player')
@option("user", discord.User, description="The user to target.", required=True)
async def disqualify_remove(ctx, user):

    # // Remove disqualified role
    await user.remove_roles(discord.utils.get(user.guild.roles, id=settings['roles']['utility']['disqualified']))
    
    embed = discord.Embed(title=f'User Undisqualified', description=f'**User:** <@{user.id}>\n\nBan this user again with `/disqualify add`.', color=defaultColour)

    await ctx.respond(embed=embed, ephemeral=True)



@bot.command(name="royaleapi", description='Lookup a user\'s RoyaleAPI Profile')
@option("user", discord.User, description="The user to target.", required=True)
async def royaleapi(ctx, user):

    tag = await get_tag(user.id)
    
    if tag is None:
        embed = discord.Embed(description='That user has not linked their account yet!', color=defaultColour)
        await ctx.respond(embed=embed, ephemeral=True)
    
    else:
        embed = discord.Embed(title=f'{user}\'s RoyaleAPI Profile', description=f'https://royaleapi.com/player/{tag}', color=defaultColour)
        await ctx.respond(embed=embed, ephemeral=True)



@otherclan.command(name="list", description='List all other clans and roles')
async def clan_list(ctx):

    with open('./data/otherClans.json', 'r') as f:
        other_clans = json.load(f)
    
    description = ''

    for clan in other_clans:

        clanList = ''
        for i in clan['clans']:
            clanList = clanList + f'`{i}`, '
        
        if clanList == '':
            clanList = 'N/A'
        else:
            clanList = clanList[:-2] # Remove last two chars

        if clan["roles"]["member"] is None:
            member_role_mention = '**N/A**'
        else:
            member_role_mention = f'<@&{clan["roles"]["member"]}>'

        if clan["roles"]["elder"] is None:
            elder_role_mention = '**N/A**'
        else:
            elder_role_mention = f'<@&{clan["roles"]["elder"]}>'

        if clan["roles"]["coleader"] is None:
            coleader_role_mention = '**N/A**'
        else:
            coleader_role_mention = f'<@&{clan["roles"]["coleader"]}>'

        if clan["roles"]["leader"] is None:
            leader_role_mention = '**N/A**'
        else:
            leader_role_mention = f'<@&{clan["roles"]["leader"]}>'

        description = description + f'- __**{clan["id"]}**__\n - **Roles:** {member_role_mention}, {elder_role_mention}, {coleader_role_mention}, {leader_role_mention}\n - **Clans:** {clanList}\n\n'
    
    embed = discord.Embed(title='Clan Roles', description=description, color=defaultColour)
    embed.set_footer(text='If a member is in any of these clans, they will get the appropriate role.')
    await ctx.respond(embed=embed, ephemeral=True)


@otherclan.command(name="addfamily", description='Create a new clan family')
@option("id", description="Backend name for the clan family - Only use alphanumeric characters", required=True)
@option("member_role", discord.Role, description="The role to give all members of the clan", required=True)
@option("elder_role", discord.Role, description="The role to give all elders of the clan", required=False)
@option("coleader_role", discord.Role, description="The role to give all co-leaders of the clan", required=False)
@option("leader_role", discord.Role, description="The role to the leader of the clan", required=False)
async def clan_addfamily(ctx, id, member_role: discord.Role, elder_role: discord.Role, coleader_role: discord.Role, leader_role: discord.Role,):

    jsondata = {"id": id, "clans": [], "roles": {"member": member_role.id, "elder": elder_role.id, "coleader": coleader_role.id, "leader": leader_role.id}}

    with open('./data/otherClans.json', 'r') as f:
        data = json.load(f)

    data.append(jsondata)

    with open('./data/otherClans.json', 'w+') as f:
        json.dump(data, f, indent = 4)
    
    embed = discord.Embed(title='Created Clan Family', description=f'<:ClashRoyaleDot:1022857029930459156> **Family ID:** {id}\n<:ClashRoyaleDot:1022857029930459156> **Role:** <@&{member_role.id}>', color=greenColour)
    await ctx.respond(embed=embed, ephemeral=True)


@otherclan.command(name="deletefamily", description='Delete a clan family')
@option("id", description="Clan family ID to delete", required=True)
async def clan_deletefamily(ctx, id):

    with open('./data/otherClans.json', 'r') as f:
        otherClans = json.load(f)
    
    found = False
    for i in otherClans:
        if i["id"] == id:
            found = True

            otherClans.remove(i)
    
            with open('./data/otherClans.json', 'w+') as f:
                json.dump(otherClans, f, indent = 4)

            embed = discord.Embed(description=f'Successfully deleted the clan family **{id}** along with all clans associated.', color=greenColour)
            await ctx.respond(embed=embed, ephemeral=True)

            break

    if not found:
        embed = discord.Embed(description=f'The clan family ID **{id}** was not found.', color=redColour)
        await ctx.respond(embed=embed, ephemeral=True)


@otherclan.command(name="addclan", description='Add a clan to a clan family')
@option("family_id", description="Backend name/ID for the clan family (eg: 'woodland' or '88an')", required=True)
@option("clan_id", description="The Clash Royale Clan ID to add to the family", required=True)
async def clan_addclan(ctx, family_id, clan_id):

    clan_id.replace('#', '')

    with open('./data/otherClans.json', 'r') as f:
        otherClans = json.load(f)
    
    found = False
    index = 0
    for i in otherClans:
        if i["id"] == family_id:
            found = True

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://proxy.royaleapi.dev/v1/clans/%23{clan_id}', headers=api) as data:
                    clanInfo = await data.json()
            
            if data.status == 200:

                otherClans[index]['clans'].append(clan_id)
        
                with open('./data/otherClans.json', 'w+') as f:
                    json.dump(otherClans, f, indent = 4)

                embed = discord.Embed(title='Added Clan', description=f'<:ClashRoyaleDot:1022857029930459156> **Family ID:** {family_id}\n<:ClashRoyaleDot:1022857029930459156> **Clan Name:** {clanInfo["name"]}\n<:ClashRoyaleDot:1022857029930459156> **Members:** {clanInfo["members"]}/50\n<:ClashRoyaleDot:1022857029930459156> **Clan ID:** `#{clan_id}`', color=greenColour)
                await ctx.respond(embed=embed, ephemeral=True)
            
            elif data.status == 404:
                embed = discord.Embed(title='Clan Not Found', description=f'A clan with that ID was not found.', color=redColour)
                await ctx.respond(embed=embed, ephemeral=True)

            else:
                embed = discord.Embed(title='Unexpected Error', description=f'Something strange happened. Error Code: {data.status}', color=redColour)
                await ctx.respond(embed=embed, ephemeral=True)

            break
        
        index += 1

    if not found:
        embed = discord.Embed(description=f'The clan family ID **{family_id}** was not found.', color=redColour)
        await ctx.respond(embed=embed, ephemeral=True)





@otherclan.command(name="deleteclan", description='Delete a clan from a clan family')
@option("family_id", description="Backend name/ID for the clan family (eg: 'woodland' or '88an')", required=True)
@option("clan_id", description="The Clash Royale Clan ID to remove from the family", required=True)
async def clan_deleteclan(ctx, family_id, clan_id):

    clan_id.replace('#', '')

    with open('./data/otherClans.json', 'r') as f:
        otherClans = json.load(f)
    
    found = False
    index = 0
    for i in otherClans:
        if i["id"] == family_id:
            found = True

            if clan_id in otherClans[index]['clans']:

                otherClans[index]['clans'].remove(clan_id)
        
                with open('./data/otherClans.json', 'w+') as f:
                    json.dump(otherClans, f, indent = 4)

                embed = discord.Embed(title='Removed Clan', description=f'Successfully removed `#{clan_id}` from the clan family **{family_id}**.', color=greenColour)
                await ctx.respond(embed=embed, ephemeral=True)
            
            else:
                embed = discord.Embed(description=f'The clan ID **{clan_id}** was not found in the family **{family_id}**.', color=redColour)
                await ctx.respond(embed=embed, ephemeral=True)

            break
        
        index += 1

    if not found:
        embed = discord.Embed(description=f'The clan family **{family_id}** was not found.', color=redColour)
        await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name="changebanner", description='Change the server banner to another piece of random art.')
@commands.cooldown(1, 3600, commands.BucketType.user) # The command can only be used once per hour
async def changebanner(ctx):

    await ctx.defer(ephemeral=True)

    await change_to_random_banner()

    embed = discord.Embed(description=f'Successfully changed the server banner', color=greenColour)
    await ctx.respond(embed=embed, ephemeral=True)

async def change_to_random_banner():
    async with aiohttp.ClientSession() as cs:
        async with cs.get(f'https://thomaskeig.com/api/crs/banners.json', headers=api) as data:
            bannerlist = await data.json()
    
    url = random.choice(bannerlist)

    with urllib.request.urlopen(url) as response:
        byte_data = response.read()

    server = bot.get_guild(settings['servers']['main'])
    await server.edit(banner=byte_data)

    channel = bot.get_channel(settings['channels']['banner-logs'])

    embed = discord.Embed(title='The banner has changed!')
    embed.set_image(url=url)

    await channel.send(embed=embed)

@tasks.loop(hours=24)
async def change_banner():
    await change_to_random_banner()

@change_banner.before_loop
async def wait_until_autobackup():
    now = datetime.datetime.now().astimezone()
    next_run = now.replace(
        hour=6,
        minute=0,
        second=0
        )
    if next_run < now:
        next_run += datetime.timedelta(days=1)
    await discord.utils.sleep_until(next_run)

@tasks.loop(minutes=60)
async def syncall():
    member_list = []
    for guild in bot.guilds:
        for member in guild.members:
            member_list.append(str(member.id))

    linked_users = await all_linked_users()

    for userid in linked_users:
        if str(userid) in member_list:
            await sync_command(userid)
            await asyncio.sleep(5)

    channel = bot.get_channel(settings['channels']['sync-logs'])
    embed = discord.Embed(description=f'Jag har genomfört en synk på alla medlemmars roller!', color=greenColour)
    await channel.send(embed=embed)

@bot.event
async def on_application_command_error(
    ctx: discord.ApplicationContext, error: discord.DiscordException
):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(f'Du behöver vänta {round(error.retry_after, 2)} sekunder innan du kan använda det här kommandot igen.', ephemeral=True)
    else:
        raise error  # Raise other errors so they aren't ignored

bot.run(settings['bot-token'])
