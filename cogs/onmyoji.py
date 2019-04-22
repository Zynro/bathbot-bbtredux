from __future__ import print_function
import discord
import json
from discord.ext import commands
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import *
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import io
import csv
import config
import re
import pyexcel as pye
import random

permission = 'You do not have permission to use this command.'
owner_list = config.owner_list
editor_list = config.editor_list

recommend = re.compile(r'recommend',re.IGNORECASE)

with open('lists/stats.json') as file:
    stats_json = json.loads(file.read())

number_dict = {'1':'First', '2':'Second', '3':'Third', '4':'Fourth', '5':'Fifth', '6':'Sixth', '7':'Seventh',1:'First', 2:'Second', 3:'Third', 4:'Fourth', 5:'Fifth', 6:'Sixth', 7:'Seventh'}

def bold(text):
    '''Returns the Discord bolded version of input text.'''
    return f'**{text}**'

def lower_and_underscore(text):
    """Lowers entire string and replaces all whitespace with underscores."""
    return text.lower().replace(' ', '_')

def generate_random_color():
    return random.randint(0, 0xFFFFFF)

class DriveAPI:
    """Manages the Google Drive API Auth and retreiving the CSV database."""
    SERVICE_ACCOUNT_FILE = 'bbt_credentials.json'
    credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=config.SCOPES_DRIVE_READONLY)
    drive_service = build('drive', 'v3', credentials = credentials)

    @classmethod
    def get_gdrive_sheet_database(cls):
        file_id = config.bounty_file_id
        request = cls.drive_service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        buffer_file = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer_file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print ("Download %d%%." % int(status.progress() * 100))
        with open (config.bbt_xlsx_file, 'wb') as f:
            f.write(buffer_file.getvalue())

    @classmethod
    def generate_csv_databases(cls):
        """Generate the CSV files from the given XLSX file obtained from Gdrive."""
       # book = pye.get_book(file_name=config.bbt_xlsx_file)
        #Convert Onmyoguide DB
        pye.save_as(file_name = config.bbt_xlsx_file, sheet_name="Bounty List", dest_file_name=config.onmyoguide_csv_db_file)
        #Convert BBT DB
        pye.save_as(file_name = config.bbt_xlsx_file, sheet_name="Data Logging", dest_file_name=config.bbt_csv_db_file)
        #Convert Shikigami Full List
        pye.save_as(file_name = config.bbt_xlsx_file, sheet_name="Shikigami List", dest_file_name=config.bbt_csv_shikigami_list_file)

class DatabaseGeneration:
    # Opens and creates the onmyoguide bounty db
    with open(config.onmyoguide_csv_db_file, newline='') as bounties:
        bounty_reader = csv.reader(bounties)
        for n in range(0, 3):
            next(bounty_reader) #skips the first 3 rows because its headers + message + example
        onmyoguide_database = [row for row in bounty_reader]
    # Opens the BBT-made database for all stages with all their contents.
    with open(config.bbt_csv_db_file, newline='') as bbt_db:
        user_db_reader = csv.reader(bbt_db)
        for i in range(0,6):
            next(user_db_reader)
        user_db = [row for row in user_db_reader]

    @classmethod
    def generate_user_shikigami_locations(cls, shiki_name):
        user_database_filtered_locations = []
        for row in cls.user_db:
            if shiki_name.lower() in row[2].lower():
                contains = row[2].split('\n')
                temp_list = []
                temp_list.append(row[0])
                temp_list.append(row[1])
                for each in contains:
                    if shiki_name.lower() in each.lower():
                        temp_list.append(each)
                        break
                user_database_filtered_locations.append(temp_list)
        return user_database_filtered_locations

class Embeds:
    def shard_trading_embed(self, user):
        need_list = ''
        have_list = ''
        for i in self.shard_trading_db[str(user.id)]['need']:
            number = ''.join(b for b in i if b.isdigit())
            shiki = ''.join(b for b in i if not b.isdigit())
            need_list = f"{need_list}{bold(number)} {shiki}\n"
        for i in self.shard_trading_db[str(user.id)]['have']:
            number = ''.join(b for b in i if b.isdigit())
            shiki = ''.join(b for b in i if not b.isdigit())
            have_list = f"{have_list}{bold(number)} {shiki}\n"
        if not user.nick:
            nick = user.name
        else:
            nick = user.nick
        if self.check_trading_status(user.id) == True:
            trading_status = "available"
        else:
            trading_status = "unavailable"
        try:
            embed = discord.Embed(title=f"{nick}'s Shard Trading List", colour=discord.Colour(generate_random_color()), description=f"__**Notes:**__ {self.shard_trading_db[str(user.id)]['notes']}\n\nYou are **{trading_status}** for trading.")
        except KeyError:
            embed = discord.Embed(title=f"{nick}'s Shard Trading List", colour=discord.Colour(generate_random_color()), description=f"You are **{trading_status}** for trading.")            
        embed.set_thumbnail(url=user.avatar_url)
        #embed.set_footer(text="Up-to-Date as of <<timestamp>>")
        embed.add_field(name="Needs these Shards:", value=need_list, inline=True)
        embed.add_field(name="Has these Shards:", value=have_list, inline=True)
        return embed

    def shiki_bounty_embed(self, shiki):
        color = generate_random_color()
        icon = discord.File(self.shikigami_class[shiki].icon, filename = self.shikigami_class[shiki].icon_name)
        embed = discord.Embed(title=f"__**{self.shikigami_class[shiki].name}**__", colour=discord.Colour(color), description=f"{self.shikigami_class[shiki].name}'s hints are:")
        embed.set_thumbnail(url=f"attachment://{self.shikigami_class[shiki].icon_name}")
        embed.add_field(name="OnmyoGuide Bounty Locations (Probably Outdated):", value=self.location_finder(shiki))

        if "None" not in self.shikigami_class[shiki].user_database_locations:
            all_locations = []
            count = 0
            for main in self.shikigami_class[shiki].user_database_locations:
                if count == 5:
                    break
                sub_locs = ', '.join(main[1])
                all_locations.append(f'{bold(main[0])} - {sub_locs}')
                count+=1
            all_locations = '\n'.join(all_locations)
            embed.add_field(name="BBT-Databased Bounty Locations:", value=all_locations)
        else:
            embed.add_field(name="BBT-Databased Bounty Locations:", value='None found in database.')
        return embed, icon

class Shikigami:
    def __init__(self, input_name):
        self.name = input_name
        self.alias = self.hints = self.locations = self.icon_name = self.icon = None
        self.icon_name = f"{lower_and_underscore(self.name)}.png"
        self.icon = f"{config.shikigami_icon_location}/{self.icon_name}"
        if not os.path.isfile(self.icon):
            self.icon_name = config.unknown_icon_file_name
            self.icon = f'{config.shikigami_icon_location}/{self.icon_name}'
        for row in DatabaseGeneration.onmyoguide_database:
            #need to re-do, uses only shiki from onmyoguide
            shiki_name, alias, hints, locations = row[0], row[1], row[2], row[3]
            if input_name in shiki_name:
                self.alias = [other_name.lower() for other_name in alias.split('\n')]
                self.hints = hints
                self.locations = locations.split('\n')
                break
        user_database = DatabaseGeneration.generate_user_shikigami_locations(self.name)
        if len(user_database) != 0:
            self.user_database_locations = sorted(self.generate_user_database_locations(user_database))
        else:
            self.user_database_locations = 'None found in database.'
        if not self.alias: self.alias = ''
        if not self.hints: self.hints = ''
        if not self.locations: self.locations = 'None found in database.'

    def generate_user_database_locations(self, user_location_database):
        """Generates the BBT Database list of locations"""
        #If no locations, end and return none.
        if len(user_location_database)==0:
            return None
        main_sub_and_shiki_list = []
        for row in user_location_database:
            if "chapter" in row[0].lower():
                sub_loc_stage_name = ''.join(i for i in row[1] if not i.isdigit())
                if any(ch.isdigit() for ch in row[1]):
                    sub_loc_stage_number = number_dict[''.join(i for i in row[1] if i.isdigit())]
                    sub_loc_final = f'{sub_loc_stage_number} {sub_loc_stage_name}'
                else:
                    sub_loc_final = f'{sub_loc_stage_name} '
                amount = ''.join(i for i in row[2] if i.isdigit())
                new_row = [row[0], f'{sub_loc_final}has {amount}']
            else:
                sub_loc_stage_name = row[1]
                amount = ''.join(i for i in row[2] if i.isdigit())
                new_row = [row[0], f'{sub_loc_stage_name} has {amount}']
            main_sub_and_shiki_list.append(new_row)
        final_result = []
        for row in main_sub_and_shiki_list:
            sub_locale = []
            location = row[0]
            for again in main_sub_and_shiki_list:
                if location == again[0]:
                    sub_locale.append(again[1])
            for row in main_sub_and_shiki_list:
                if row[0] == location:
                    main_sub_and_shiki_list.remove(row)
            final_result.append([location, sub_locale])
        return final_result


class Onmyoji(commands.Cog, Embeds):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.shikigami_class = self.create_classes()
        except FileNotFoundError:
            DriveAPI.get_gdrive_sheet_database()
            DriveAPI.generate_csv_databases()
            self.shikigami_class = self.create_classes()
        self.shard_load_json()

    async def has_permission(ctx):
        return ctx.author.id in owner_list or ctx.author.id in editor_list

    def create_classes(self):
        """Creates all the Shikigami classes with each of their vairables in a dictionary."""
        # Opens and creates the shikigami list from the full list of shikigami
        with open(config.bbt_csv_shikigami_list_file, newline='') as shiki_list_csv:
            shiki_list_reader = csv.reader(shiki_list_csv)
            next(shiki_list_reader) #skips header
            shikigami_full_list = [row[0] for row in shiki_list_reader]
        return {shiki.lower(): Shikigami(shiki) for shiki in shikigami_full_list if "frog" not in shiki.lower()}

    def location_finder(self, shiki):
        if 'None' in self.shikigami_class[shiki].locations:
            return "None found in database."
        locations_base = [location for location in self.shikigami_class[shiki].locations]
        for location in locations_base:
            match_recommend = recommend.search(location)
            if match_recommend:
                locations_base[locations_base.index(location)] = bold(location)
        locations_onmyoguide = '\n'.join(locations_base)
        return locations_onmyoguide

    @commands.command()
    async def shikistats(self, ctx, *search):
        name = ' '.join([term.lower() for term in search])
        result = stats_json.get(name)
        if not result:
            fuzzy_name = [key for key in stats_json.keys() if name in key]
            if fuzzy_name:
                result = stats_json.get(fuzzy_name[0])
        if result:
            await ctx.send(f"""The stats for {name.title()} at level 40 are:
            **ATK:** _{result['attack']}_
            **HP:** _{result['health']}_
            **DEF:** _{result['defense']}_
            **SPD:** _{result['speed']}_
            **CRIT:** _{result['crit']}_
            **CDMG:** _{result['crit dmg']}_
            **EHIT:** _{result['eff hit']}_
            **ERES:** _{result['eff res']}_""")
            return
        await ctx.send(f'Couldn\'t find stats for {name.title()}')

    @commands.command(name='database', aliases=['googledoc', 'link', 'share'])
    @commands.check(has_permission)
    async def get_shared_doc_link(self, ctx):
        '''If Officer, returns the link for the database.'''
        if ctx.channel.id != config.officer_chat_id:
            await ctx.send('This command cannot be used in this channel.')
        else:
            await ctx.send(f'Here is the link for the Onmyoji database:\n{config.database_google_link}')

    @get_shared_doc_link.error
    async def get_shared_doc_link_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to uuse this command.")

    @commands.command(name='database_update', aliases=['update', 'download'])
    async def download_shikigami_update_excel(self, ctx):
        '''If Officer, updates the bot's local database file.'''
        await ctx.send("Now updating... Please wait while BathBot pulls the latest database.")
        DriveAPI.get_gdrive_sheet_database()
        DriveAPI.generate_csv_databases()
        self.create_classes()
        await ctx.send("The Shikigami bounty list database has been successfully updated!")

    @download_shikigami_update_excel.error
    async def download_shikigami_update_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to update the database file.\nPlease tag an @Officer to have them update it.")

    @commands.command()
    async def bounty(self, ctx, *search):
        if not search:
            await ctx.send('Search term cannot be blank, try again.')
            return
        search = ' '.join([term.lower() for term in search])
        for shiki in self.shikigami_class.keys():
            if search in shiki:
                shiki_embed, shiki_icon = self.shiki_bounty_embed(shiki)
                await ctx.send(file=shiki_icon, embed=shiki_embed)
                return
            if search in self.shikigami_class[shiki].hints.lower():
                shiki_embed, shiki_icon = self.shiki_bounty_embed(shiki)
                await ctx.send(file=shiki_icon, embed=shiki_embed)
                return
            if search in self.shikigami_class[shiki].alias:                
                shiki_embed, shiki_icon = self.shiki_bounty_embed(shiki)
                await ctx.send(file=shiki_icon, embed=shiki_embed)
                return
        await ctx.send("For all my bath powers, I could not find your term, or something went wrong.")

    @commands.command()
    async def tengu(self, ctx):
        """hurrhurrhurr"""
        await ctx.send(file=discord.File('./images/tengu.jpg'))

#=====================Shard Trading===========================

    def shard_load_json(self):
        try:
            try:
                with open(f'{config.list_path}/shard-trading-db.json', 'r') as shard_file:
                    self.shard_trading_db = json.loads(shard_file.read())
            except ValueError:
                self.shard_trading_db = {}
        except FileNotFoundError:
            with open(f'{config.list_path}/shard-trading-db.json', 'w') as shard_file:
                self.shard_trading_db = {}
                print('New Json file generated!')
        return

    def shard_file_writeout(self):
        with open(f'{config.list_path}/shard-trading-db.json', 'w+') as shard_file:
            json.dump(self.shard_trading_db, shard_file, indent=4)
        return

    def shard_print_need_list(self, user):
        need_list = []
        for i in self.shard_trading_db[user]['need']:
            if not i:
                continue
            numbers = ''.join(b for b in i if b.isdigit())
            shiki = ''.join(b for b in i if not b.isdigit())
            need_list.append(f"{numbers} {shiki}")
        self.shard_load_json()
        return need_list
        

    def shard_print_have_list(self, user):
        have_list = []
        for i in self.shard_trading_db[user]['have']:
            if not i:
                continue
            numbers = ''.join(b for b in i if b.isdigit())
            shiki = ''.join(b for b in i if not b.isdigit())
            have_list.append(f"{numbers} {shiki}")
        self.shard_load_json()
        return have_list

    def shard_entry_init(self, ctx):
        self.shard_trading_db[str(ctx.message.author.id)] = {'status': True, 'notes':'', 'have':'', 'need':''}
        self.shard_file_writeout()
        return

    @commands.group()
    async def shard(self, ctx):
        """
        Shard trading command group. Use the various commands to assign and initialize shard trading.
        """
        if ctx.invoked_subcommand is None:
            if self.shard_trading_db.get(str(ctx.message.author.id)) is None:
                self.shard_entry_init(ctx)
            await ctx.send("""
Welcome to BathBot's Shard Trading implementation!
To begin, make a list of shards you have and need, each on a new line, and use the follow commands:
`&shard need list` 
and
`&shard have list`
where 'list' is the list of your shards copy pasted.
An example for each would be:
```&shard need Orochi
Miketsu
Ootengu
Yotohime``` 
```&shard have Shuten Doji 4
Ibaraki Doji 5
10 Orochi
Miketsu 19``` 
The numbers placement does not matter.

Please make sure to use proper spelling, or when using the search function your entry may be skipped.

Once you have set your lists, use the `&shard search` command to search users and the entire database for people to trade with!

To change your trading status so people wont get you in their results, use `&shard stauts on` or `&shard stauts off`

To receive help on commands at any time, use the `&help shard` command, or tag @Zynro.
""")

    
    @shard.command(name='list')
    async def shard_print_list(self, ctx, *other_user):
        """
        If blank, prints list for both need and have lists for the user.
        Otherwise, if provided a @user, prints that users lists.
        """
        if not other_user:
            embed = self.shard_trading_embed(ctx.author)
            await ctx.send(embed=embed)


    @shard.command(name="need")
    async def shard_set_need(self,ctx,*,args=None):
        """
        Returns the list of shards you need.
        If shards are listed, assigns those shards to your needed list.
        """
        if not args:
            try: 
                need_list = '\n'.join(self.shard_print_need_list(str(ctx.message.author.id)))
                await ctx.send(f"Shards you **need**: ```\n{need_list}```")
                return
            except KeyError:
                await ctx.send('You do not have a "Need" list yet! Use `&shard` to generate your entry first!')
                return
        arg_list = args.split("\n")
        self.shard_load_json()
        try: 
            self.shard_trading_db[str(ctx.message.author.id)]['need'] = arg_list
        except KeyError:
            self.shard_trading_db[str(ctx.message.author.id)] = {}
            self.shard_trading_db[str(ctx.message.author.id)]['need'] = arg_list
        self.shard_file_writeout()
        arg_string = '\n'.join(self.shard_trading_db[str(ctx.message.author.id)]['need'])
        await ctx.send(f'The shards you need are now set to: ```\n{arg_string}```')

    @shard.command(name="have")
    async def shard_set_have(self,ctx,*,args=None):
        """
        Returns the list of shards you have.
        If shards are listed, assigns those shards to your have list.
        """
        if not args:
            try: 
                have_list = '\n'.join(self.shard_print_have_list(str(ctx.message.author.id)))
                await ctx.send(f"Shards you **have**: ```\n{have_list}```")
                return
            except KeyError:
                await ctx.send('You do not have a "Have" list yet! Use `&shard` to generate your entry first!')
                return
        arg_list = args.split("\n")
        self.shard_load_json()
        try: 
            self.shard_trading_db[str(ctx.message.author.id)]['have'] = arg_list
        except KeyError:
            self.shard_trading_db[str(ctx.message.author.id)] = {}
            self.shard_trading_db[str(ctx.message.author.id)]['have'] = arg_list
        self.shard_file_writeout()
        arg_string = '\n'.join(self.shard_trading_db[str(ctx.message.author.id)]['have'])
        await ctx.send(f'The shards you have are now set to: ```\n{arg_string}```\nYou are currently')

    @shard.command(name="notes")
    async def shard_set_notes(self, ctx, *, args):
        """
        Sets the user note for their shard trading database entry.
        Leave the field blank to disable, otherwise type in a note to set that note.
        """
        self.shard_load_json()
        if not args:
            self.shard_trading_db[str(ctx.author.id)]['notes'] = ''
            await ctx.send("Notes disabled.")
            self.shard_file_writeout()
        else:
            self.shard_trading_db[str(ctx.author.id)]['notes'] = args
            await ctx.send(f"Your Shard Trading entry Notes have been set to:\n```{args}```")
            self.shard_file_writeout()

    def check_trading_status(self, user):
        try:
            return self.shard_trading_db[str(user)]['status']
        except KeyError:
            return True

    @shard.command(name="status")
    async def shard_set_trading_status(self, ctx, *arg):
        """
        Toggles the trading status for the user.
        If no terms are given, toggles it.
        Otherwise, if on/off is given as a term, sets it to that state.
        """
        self.shard_load_json()
        try:
            temp = self.shard_trading_db[str(ctx.author.id)]['status']
        except KeyError:
            self.shard_trading_db[str(ctx.author.id)]['status'] = True
            self.shard_file_writeout();
            return await ctx.send(f"{ctx.author.mention} is now available to be searched for trading.")
        if not arg:
            if self.check_trading_status(ctx.author.id) == True:
                self.shard_trading_db[str(ctx.author.id)]['status'] = False
                self.shard_file_writeout();
                return await ctx.send(f"{ctx.author.mention} is now unavailable to be searched for trading.")
            else:
                self.shard_trading_db[str(ctx.author.id)]['status'] = True
                self.shard_file_writeout();
                return await ctx.send(f"{ctx.author.mention} is now available to be searched for trading.")
        else:
            if arg == "on":
                self.shard_trading_db[str(ctx.author.id)]['status'] = True
                self.shard_file_writeout();
                return await ctx.send(f"{ctx.author.mention} is now available to be searched for trading.")
            elif arg == "off":
                self.shard_trading_db[str(ctx.author.id)]['status'] = False
                self.shard_file_writeout();
                return await ctx.send(f"{ctx.author.mention} is unavailable to be searched for trading.")

    def compare_shard_db(self, main_user, other_user):
        try:
            if self.check_trading_status(main_user) == False or self.check_trading_status(other_user) == False:
                return None, None
            user1_have_list = [''.join(i for i in value if not i.isdigit()) for value in self.shard_trading_db[main_user]['have']]
            user1_have_list = [i.strip().lower() for i in user1_have_list]
            user1_need_list = [''.join(i for i in value if not i.isdigit()) for value in self.shard_trading_db[main_user]['need']]
            user1_need_list = [i.strip().lower() for i in user1_need_list]
            
            user2_have_list = [''.join(i for i in value if not i.isdigit()) for value in self.shard_trading_db[str(other_user)]['have']]
            user2_have_list = [i.strip().lower() for i in user2_have_list]
            user2_need_list = [''.join(i for i in value if not i.isdigit()) for value in self.shard_trading_db[str(other_user)]['need']]
            user2_need_list = [i.strip().lower() for i in user2_need_list]
            
            you_have_they_need = []
            you_need_they_have = []
            comparison_list = []
            for user1_have in user1_have_list:
                for user2_need in user2_need_list:
                    if user1_have.lower() == user2_need.lower():
                        you_have_they_need.append(user1_have)
            for user1_need in user1_need_list:
                for user2_have in user2_have_list:
                    if user1_need.lower() == user2_have.lower():
                        you_need_they_have.append(user1_need)
            you_have_they_need = [shiki.capitalize() for shiki in you_have_they_need]
            you_need_they_have = [shiki.capitalize() for shiki in you_need_they_have]
        except KeyError:
            return None, None
        if len(you_have_they_need) == 0 and len(you_need_they_have) == 0:
            return None, None
        return you_have_they_need, you_need_they_have


    @shard.command(name="search")
    async def shard_search(self, ctx, other_user_raw):
        """
        Compares shard trading lists with other users.
        Specify a name, or an @user tag to compare to that single user.
            e.g. &shard search Zynro
        Specify "all" to search the entire database.
            e.g. &shard search all
        """
        self.shard_load_json()
        main_user = str(ctx.message.author.id)
        other_user = None
        if not other_user_raw:
            await ctx.send("Must enter either a user's name, nickname, @tag, or the term 'all' to search the database!")
            return
        if other_user_raw.lower().strip() == "all":
            match_list = []
            for user in self.shard_trading_db:
                if user == main_user:
                    continue
                you_have_they_need, you_need_they_have = self.compare_shard_db(main_user, user)
                if not you_have_they_need:
                    continue
                if len(you_have_they_need) >= 1 and len(you_need_they_have) >= 1:
                    try:
                        if not ctx.guild.get_member(int(user)).nick:
                            match_list.append(ctx.guild.get_member(int(user)).name)
                        else:
                            match_list.append(ctx.guild.get_member(int(user)).nick)
                    except AttributeError:
                        continue
            if not match_list:
                return await ctx.send("I apologize, I was not able to find any other members that match shard needs and haves with you.")
            if len(match_list) == 1:
                match_string = match_list[0]
            else:
                match_string = '\n'.join(match_list)
            return await ctx.send(f"""
__Good news everyone!__
You and the following users have shards that can be traded:
**{match_string}**
Use `&search @user` where user is one of the ones listed above to check which shards each of you need/have!
""")
        for member in ctx.guild.members:
            if "@" in other_user_raw:
                other_user = ''.join(i for i in other_user_raw if i.isdigit())
                break
            else:
                try:
                    if other_user_raw.lower().strip() in member.nick.lower():
                        other_user = str(member.id)
                        break
                except (TypeError, AttributeError):
                    if other_user_raw.lower().strip() in member.name.lower():
                        other_user = str(member.id)
                        break
        if not other_user:
            return await ctx.send("I could not find that user, or you typed an improper keyword.")
        you_have_they_need, you_need_they_have = self.compare_shard_db(main_user, other_user)
        if not you_have_they_need:
            await ctx.send("Either you or the user you're checking doesn't have entries in the shard database, or one of you isn't available for trading.")
            return
        if len(you_have_they_need) == 0 or len(you_need_they_have) == 0:
            await ctx.send(f"Unfortunately, based on your lists, you and {other_user_raw} do not have any shards that can be exchanged.")
            return
        else:
            you_need_they_have = ', '.join(you_need_they_have)
            you_have_they_need = ', '.join(you_have_they_need)
            if not ctx.guild.get_member(int(other_user)).nick:
                searched_user = ctx.guild.get_member(int(other_user)).name
            else:
                searched_user = ctx.guild.get_member(int(other_user)).nick
            await ctx.send(f"""
__Good news everyone!__
You and {searched_user} have shards that can be exchanged!
Shards you **need** that {searched_user} has:
```
{you_need_they_have}
```
Shards you **have** that {searched_user} needs:
```
{you_have_they_need}
```
""")
            return
        return await ctx.send("I didn't understand what you meant, try again.")
#=====================Shard Trading===========================

        

def setup(bot):
    bot.add_cog(Onmyoji(bot))

