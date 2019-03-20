import discord
from discord.ext import commands
import asyncio
import requests
import config
import bot_token

initial_extensions = ['cogs.admin', 'cogs.voicecmd', 'cogs.onmyoji',]

def get_prefix(bot, message):
    prefixes = ['&']
    return commands.when_mentioned_or(*prefixes)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, description='I am Bathbot. I meme.')

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    #bot.remove_command('help')
    await bot.change_presence(activity=discord.Game(name='Shower With Your Dad Simulator 2015: Do You Still Shower With Your Dad'))
    if __name__ == '__main__':
        for extension in initial_extensions:
            try:
                bot.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()
    print(f'Bathbot is fully ready!')
    if not discord.opus.is_loaded():
            discord.opus.load_opus('libopus.so')
            print('Opus has been loaded!')

@bot.command(name='b-load', hidden=True)
async def cog_load_backup(self, ctx, *, cog: str):
    """Command which Loads a Module.
    Remember to use dot path. e.g: cogs.owner"""
    try:
        self.bot.load_extension('cogs.'+cog)
    except Exception as e:
        await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
    else:
        await ctx.send('**Success: **cogs.'+cog+' has been loaded!')

@bot.command(name='b-unload', hidden=True)
async def cog_unload_backup(self, ctx, *, cog: str):
    """Command which Unloads a Module.
    Remember to use dot path. e.g: cogs.owner"""
    if ctx.message.author.id != owner:
        await ctx.send(config.permission)
        return
    else:
        try:
            self.bot.unload_extension('cogs.'+cog)
        except Exception as e:
            await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
        else:
            await ctx.send('**Success:** cogs.'+cog+' has been unloaded!')

@bot.command(name='b-reload', hidden=True)
async def cog_reload(self, ctx, *, cog: str):
    """Command which Reloads a Module.
    Remember to use dot path. e.g: cogs.owner"""
    try:
        self.bot.unload_extension('cogs.'+cog)
        self.bot.load_extension('cogs.'+cog)
    except Exception as e:
        await ctx.send(f'**Error:** {type(e).__name__} - {e}')
    else:
        await ctx.send('**Success:** cogs.'+cog+' has been reloaded!')


bot.run(bot_token.TOKEN)
