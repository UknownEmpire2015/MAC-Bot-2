import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import random
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')  # Remove default help to create custom one

# In-memory storage (use a database for production)
warnings = {}  # {user_id: [{'reason': str, 'date': datetime, 'moderator': str}]}
custom_commands = {}  # {command_name: response}
reaction_roles = {}  # {message_id: {emoji: role_id}}
bad_words = ['badword1', 'badword2']  # Add words to filter
welcome_channel_id = None  # Set this to your welcome channel ID or use !setwelcome

# Bot ready event
@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='!help for commands'))

# Auto-moderation: Bad word filter
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check for bad words
    content_lower = message.content.lower()
    if any(word in content_lower for word in bad_words):
        await message.delete()
        await message.channel.send(f'{message.author.mention}, please watch your language!')
        return
    
    # Check for custom commands
    if message.content.startswith('!'):
        cmd = message.content[1:].split()[0].lower()
        if cmd in custom_commands:
            await message.channel.send(custom_commands[cmd])
            return
    
    await bot.process_commands(message)

# HELP COMMAND
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title='📋 Bot Commands',
        description='Here are all available commands:',
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name='**Moderation**',
        value='`!kick @user [reason]`\n`!ban @user [reason]`\n`!mute @user [duration]`\n`!unmute @user`\n`!warn @user [reason]`\n`!warnings [@user]`\n`!clearwarnings @user`',
        inline=False
    )
    
    embed.add_field(
        name='**Custom Commands**',
        value='`!cc add <n> <response>`\n`!cc remove <n>`\n`!cc list`',
        inline=False
    )
    
    embed.add_field(
        name='**Reaction Roles**',
        value='`!rr setup`\n`!rr add <messageId> <emoji> <@role>`\n`!rr remove <messageId> <emoji>`',
        inline=False
    )
    
    embed.add_field(
        name='**Utility**',
        value='`!serverinfo`\n`!userinfo [@user]`\n`!poll <question>`',
        inline=False
    )
    
    embed.add_field(
        name='**Fun Commands**',
        value='`!meme`\n`!joke`\n`!8ball <question>`\n`!coinflip`\n`!dice [sides]`\n`!choose <option1> | <option2> | ...`',
        inline=False
    )
    
    embed.add_field(
        name='**Games**',
        value='`!trivia`\n`!rps <rock/paper/scissors>`\n`!gtn` (Guess the Number)',
        inline=False
    )
    
    embed.add_field(
        name='**Welcome System**',
        value='`!setwelcome <#channel>`\n`!testwelcome`',
        inline=False
    )
    
    embed.add_field(
        name='**Auto-mod**',
        value='Automatic bad word filtering and welcome messages enabled',
        inline=False
    )
    
    embed.set_footer(text='Prefix: !')
    await ctx.send(embed=embed)

# KICK COMMAND
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason='No reason provided'):
    try:
        await member.kick(reason=reason)
        await ctx.send(f'✅ {member.mention} has been kicked. Reason: {reason}')
    except Exception as e:
        await ctx.send(f'❌ I was unable to kick this user. Error: {e}')

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to kick members.')
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('❌ Please mention a valid user to kick.')

# BAN COMMAND
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason='No reason provided'):
    try:
        await member.ban(reason=reason)
        await ctx.send(f'✅ {member.mention} has been banned. Reason: {reason}')
    except Exception as e:
        await ctx.send(f'❌ I was unable to ban this user. Error: {e}')

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to ban members.')
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('❌ Please mention a valid user to ban.')

# MUTE COMMAND
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration='10m'):
    try:
        # Parse duration
        time_dict = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1]
        amount = int(duration[:-1])
        
        if unit not in time_dict:
            await ctx.send('❌ Invalid duration format. Use: 10s, 10m, 1h, or 1d')
            return
        
        seconds = amount * time_dict[unit]
        until = datetime.utcnow() + timedelta(seconds=seconds)
        
        await member.timeout(until, reason='Muted by moderator')
        await ctx.send(f'✅ {member.mention} has been muted for {duration}.')
    except Exception as e:
        await ctx.send(f'❌ I was unable to mute this user. Error: {e}')

@mute.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to mute members.')

# UNMUTE COMMAND
@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await ctx.send(f'✅ {member.mention} has been unmuted.')
    except Exception as e:
        await ctx.send(f'❌ I was unable to unmute this user. Error: {e}')

@unmute.error
async def unmute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to unmute members.')

# WARN COMMAND
@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason='No reason provided'):
    if member.id not in warnings:
        warnings[member.id] = []
    
    warning_data = {
        'reason': reason,
        'date': datetime.now(),
        'moderator': str(ctx.author)
    }
    
    warnings[member.id].append(warning_data)
    
    await ctx.send(f'⚠️ {member.mention} has been warned. Reason: {reason}\nTotal warnings: {len(warnings[member.id])}')

@warn.error
async def warn_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to warn members.')

# WARNINGS COMMAND
@bot.command()
async def warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_warnings = warnings.get(member.id, [])
    
    if not user_warnings:
        await ctx.send(f'{member.mention} has no warnings.')
        return
    
    embed = discord.Embed(
        title=f'⚠️ Warnings for {member.name}',
        color=discord.Color.orange()
    )
    
    for i, w in enumerate(user_warnings, 1):
        embed.add_field(
            name=f'Warning {i}',
            value=f"**Reason:** {w['reason']}\n**Date:** {w['date'].strftime('%Y-%m-%d')}\n**By:** {w['moderator']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

# CLEAR WARNINGS COMMAND
@bot.command()
@commands.has_permissions(moderate_members=True)
async def clearwarnings(ctx, member: discord.Member):
    if member.id in warnings:
        del warnings[member.id]
        await ctx.send(f'✅ Cleared all warnings for {member.mention}.')
    else:
        await ctx.send(f'{member.mention} has no warnings to clear.')

@clearwarnings.error
async def clearwarnings_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to clear warnings.')

# CUSTOM COMMAND GROUP
@bot.group(name='cc')
async def custom_command(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send('❌ Use: `!cc add/remove/list`')

@custom_command.command(name='add')
@commands.has_permissions(manage_guild=True)
async def cc_add(ctx, name: str, *, response: str):
    custom_commands[name.lower()] = response
    await ctx.send(f'✅ Custom command `!{name}` has been added.')

@custom_command.command(name='remove')
@commands.has_permissions(manage_guild=True)
async def cc_remove(ctx, name: str):
    if name.lower() in custom_commands:
        del custom_commands[name.lower()]
        await ctx.send(f'✅ Custom command `!{name}` has been removed.')
    else:
        await ctx.send('❌ That custom command does not exist.')

@custom_command.command(name='list')
async def cc_list(ctx):
    if not custom_commands:
        await ctx.send('No custom commands have been set up yet.')
        return
    
    cmd_list = ', '.join([f'!{cmd}' for cmd in custom_commands.keys()])
    await ctx.send(f'**Custom Commands:** {cmd_list}')

# REACTION ROLES GROUP
@bot.group(name='rr')
async def reaction_role(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send('❌ Use: `!rr setup/add/remove`')

@reaction_role.command(name='setup')
@commands.has_permissions(manage_roles=True)
async def rr_setup(ctx):
    embed = discord.Embed(
        title='🎭 Reaction Roles',
        description='React to this message to get your role!\n\nUse `!rr add <messageId> <emoji> <@role>` to set up roles.',
        color=discord.Color.green()
    )
    
    msg = await ctx.send(embed=embed)
    await ctx.send(f'✅ Reaction role message created! ID: {msg.id}')

@reaction_role.command(name='add')
@commands.has_permissions(manage_roles=True)
async def rr_add(ctx, message_id: int, emoji: str, role: discord.Role):
    try:
        message = await ctx.channel.fetch_message(message_id)
        
        if message_id not in reaction_roles:
            reaction_roles[message_id] = {}
        
        reaction_roles[message_id][emoji] = role.id
        
        await message.add_reaction(emoji)
        await ctx.send(f'✅ Reaction role added: {emoji} → {role.name}')
    except discord.NotFound:
        await ctx.send('❌ Could not find that message.')
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@reaction_role.command(name='remove')
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, emoji: str):
    if message_id in reaction_roles and emoji in reaction_roles[message_id]:
        del reaction_roles[message_id][emoji]
        await ctx.send(f'✅ Reaction role removed: {emoji}')
    else:
        await ctx.send('❌ That reaction role does not exist.')

# Reaction role handler
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    
    if payload.message_id not in reaction_roles:
        return
    
    emoji = str(payload.emoji)
    if emoji not in reaction_roles[payload.message_id]:
        return
    
    guild = bot.get_guild(payload.guild_id)
    role = guild.get_role(reaction_roles[payload.message_id][emoji])
    member = guild.get_member(payload.user_id)
    
    if role and member:
        await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    
    if payload.message_id not in reaction_roles:
        return
    
    emoji = str(payload.emoji)
    if emoji not in reaction_roles[payload.message_id]:
        return
    
    guild = bot.get_guild(payload.guild_id)
    role = guild.get_role(reaction_roles[payload.message_id][emoji])
    member = guild.get_member(payload.user_id)
    
    if role and member:
        await member.remove_roles(role)

# SERVER INFO COMMAND
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    
    embed = discord.Embed(
        title=f'📊 {guild.name}',
        color=discord.Color.blurple()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name='Owner', value=guild.owner.mention, inline=True)
    embed.add_field(name='Members', value=str(guild.member_count), inline=True)
    embed.add_field(name='Created', value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Roles', value=str(len(guild.roles)), inline=True)
    embed.add_field(name='Channels', value=str(len(guild.channels)), inline=True)
    
    await ctx.send(embed=embed)

# USER INFO COMMAND
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f'👤 {member.name}#{member.discriminator}',
        color=discord.Color.purple()
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    embed.add_field(name='ID', value=str(member.id), inline=False)
    embed.add_field(name='Joined Server', value=member.joined_at.strftime('%Y-%m-%d'), inline=False)
    embed.add_field(name='Account Created', value=member.created_at.strftime('%Y-%m-%d'), inline=False)
    
    roles = ', '.join([role.name for role in member.roles[1:]]) or 'None'
    embed.add_field(name='Roles', value=roles, inline=False)
    
    await ctx.send(embed=embed)

# POLL COMMAND
@bot.command()
async def poll(ctx, *, question: str):
    embed = discord.Embed(
        title='📊 Poll',
        description=question,
        color=discord.Color.gold()
    )
    
    embed.set_footer(text=f'Poll by {ctx.author.name}')
    
    poll_msg = await ctx.send(embed=embed)
    await poll_msg.add_reaction('👍')
    await poll_msg.add_reaction('👎')

# ============ FUN COMMANDS ============

@bot.command()
async def meme(ctx):
    memes = [
        "https://i.imgur.com/3GJZoqM.jpg",
        "https://i.imgur.com/8ubx3JD.jpg",
        "https://i.imgur.com/NZQZtKi.jpg",
        "https://i.imgur.com/vzWvb0j.jpg",
        "https://i.imgur.com/QyZso8L.jpg"
    ]
    
    embed = discord.Embed(
        title="😂 Random Meme",
        color=discord.Color.random()
    )
    embed.set_image(url=random.choice(memes))
    await ctx.send(embed=embed)

@bot.command()
async def joke(ctx):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What do you call a fake noodle? An impasta!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What did the ocean say to the beach? Nothing, it just waved!",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "What's a computer's favorite snack? Microchips!",
        "Why was the math book sad? It had too many problems!",
        "What do you call a dinosaur that crashes his car? Tyrannosaurus Wrecks!"
    ]
    
    await ctx.send(f'😄 {random.choice(jokes)}')

@bot.command(name='8ball')
async def eight_ball(ctx, *, question: str):
    responses = [
        "Yes, definitely!",
        "It is certain.",
        "Without a doubt.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Question:** {question}\n**Answer:** {random.choice(responses)}",
        color=discord.Color.purple()
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def coinflip(ctx):
    result = random.choice(['Heads', 'Tails'])
    await ctx.send(f'🪙 The coin landed on: **{result}**!')

@bot.command()
async def dice(ctx, sides: int = 6):
    if sides < 2:
        await ctx.send('❌ Dice must have at least 2 sides!')
        return
    
    result = random.randint(1, sides)
    await ctx.send(f'🎲 You rolled a **{result}** (1-{sides})')

@bot.command()
async def choose(ctx, *, choices: str):
    options = [choice.strip() for choice in choices.split('|')]
    
    if len(options) < 2:
        await ctx.send('❌ Please provide at least 2 options separated by |')
        return
    
    choice = random.choice(options)
    await ctx.send(f'🤔 I choose: **{choice}**')

# ============ GAME COMMANDS ============

@bot.command()
async def trivia(ctx):
    questions = [
        {"q": "What is the capital of France?", "a": ["paris"], "c": "Paris"},
        {"q": "What is 2 + 2?", "a": ["4", "four"], "c": "4"},
        {"q": "What color is the sky on a clear day?", "a": ["blue"], "c": "Blue"},
        {"q": "How many continents are there?", "a": ["7", "seven"], "c": "7"},
        {"q": "What is the largest planet in our solar system?", "a": ["jupiter"], "c": "Jupiter"},
        {"q": "What year did World War 2 end?", "a": ["1945"], "c": "1945"},
        {"q": "What is the fastest land animal?", "a": ["cheetah"], "c": "Cheetah"},
        {"q": "Who painted the Mona Lisa?", "a": ["leonardo da vinci", "da vinci", "leonardo"], "c": "Leonardo da Vinci"},
        {"q": "What is the chemical symbol for gold?", "a": ["au"], "c": "Au"},
        {"q": "How many legs does a spider have?", "a": ["8", "eight"], "c": "8"}
    ]
    
    trivia_q = random.choice(questions)
    
    embed = discord.Embed(
        title="🧠 Trivia Time!",
        description=trivia_q["q"],
        color=discord.Color.blue()
    )
    embed.set_footer(text="You have 15 seconds to answer!")
    
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', timeout=15.0, check=check)
        
        if msg.content.lower() in trivia_q["a"]:
            await ctx.send(f'✅ Correct, {ctx.author.mention}! The answer is **{trivia_q["c"]}**')
        else:
            await ctx.send(f'❌ Wrong! The correct answer was **{trivia_q["c"]}**')
    except asyncio.TimeoutError:
        await ctx.send(f'⏰ Time\'s up! The answer was **{trivia_q["c"]}**')

@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    
    if choice not in ['rock', 'paper', 'scissors']:
        await ctx.send('❌ Please choose rock, paper, or scissors!')
        return
    
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    # Determine winner
    if choice == bot_choice:
        result = "It's a tie! 🤝"
    elif (choice == 'rock' and bot_choice == 'scissors') or \
         (choice == 'paper' and bot_choice == 'rock') or \
         (choice == 'scissors' and bot_choice == 'paper'):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    emoji_map = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
    
    embed = discord.Embed(
        title="Rock, Paper, Scissors!",
        description=f"You chose: {emoji_map[choice]} **{choice.capitalize()}**\nI chose: {emoji_map[bot_choice]} **{bot_choice.capitalize()}**\n\n{result}",
        color=discord.Color.green()
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def gtn(ctx):
    number = random.randint(1, 100)
    attempts = 0
    max_attempts = 7
    
    embed = discord.Embed(
        title="🎯 Guess the Number!",
        description=f"I'm thinking of a number between 1 and 100.\nYou have {max_attempts} attempts to guess it!",
        color=discord.Color.gold()
    )
    
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
    
    while attempts < max_attempts:
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            guess = int(msg.content)
            attempts += 1
            
            if guess == number:
                await ctx.send(f'🎉 Congratulations! You guessed it in {attempts} attempts!')
                return
            elif guess < number:
                await ctx.send(f'📈 Higher! ({max_attempts - attempts} attempts left)')
            else:
                await ctx.send(f'📉 Lower! ({max_attempts - attempts} attempts left)')
                
        except asyncio.TimeoutError:
            await ctx.send(f'⏰ Time\'s up! The number was **{number}**')
            return
    
    await ctx.send(f'❌ Game over! The number was **{number}**')

# ============ WELCOME SYSTEM ============

@bot.event
async def on_member_join(member):
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}! 👋",
                description=f"{member.mention} just joined the server!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Member Count", value=f"We now have {member.guild.member_count} members!")
            embed.set_footer(text=f"Account created: {member.created_at.strftime('%Y-%m-%d')}")
            
            await channel.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    await ctx.send(f'✅ Welcome channel set to {channel.mention}')

@setwelcome.error
async def setwelcome_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You need Manage Server permission to set the welcome channel.')

@bot.command()
async def testwelcome(ctx):
    if not welcome_channel_id:
        await ctx.send('❌ Welcome channel not set! Use `!setwelcome #channel` first.')
        return
    
    channel = bot.get_channel(welcome_channel_id)
    if channel:
        embed = discord.Embed(
            title=f"Welcome to {ctx.guild.name}! 👋",
            description=f"{ctx.author.mention} just joined the server!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Member Count", value=f"We now have {ctx.guild.member_count} members!")
        embed.set_footer(text=f"Account created: {ctx.author.created_at.strftime('%Y-%m-%d')}")
        
        await channel.send(embed=embed)
        await ctx.send('✅ Test welcome message sent!')
    else:
        await ctx.send('❌ Welcome channel not found!')

# Run the bot
bot.run(TOKEN)
