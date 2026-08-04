import serial
import threading
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
import os
import json

# ---------------- LOAD TOKEN ----------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- CONFIG ----------------
COMMAND_CHANNEL_NAME = "commands"
SCHEDULE_CHANNEL_NAME = "schedule"
STATUS_CHANNEL_NAME = "chores-status"
MAX_PEOPLE = 3
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
STATE_FILE = "state.json"

schedule = {
    day: [] for day in [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]
}

people = []
schedule_message = None
day_skip = 0

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)


# ---------------- HELPERS ----------------
def load_state():

    global people
    global schedule
    global day_skip

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)

        people = data.get("people", [])
        schedule = data.get("schedule", {})
        day_skip = data.get("day_skip", 0)

        # ensure last_date exists in file
        if "last_date" not in data:
            save_state()

    except:
        pass

def save_state():

    data = {
        "day_skip": day_skip,
        "people": people,
        "schedule": schedule,
        "last_date": datetime.now().strftime("%Y-%m-%d")
    }

    temp_file = STATE_FILE + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(data, f, indent=4)

    os.replace(temp_file, STATE_FILE)

def check_new_day():
    global day_skip

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)

        last_date = data.get("last_date")
        today = datetime.now().strftime("%Y-%m-%d")

        if last_date != today:
            day_skip = 0
            save_state()

    except:
        pass

def is_command_channel(ctx):
    return ctx.channel.name == COMMAND_CHANNEL_NAME


def format_schedule():

    text = "**📅 CHORE SCHEDULE**\n"

    text += "\n**👥 People Living Together**\n"

    if not people:
        text += "- (none)\n"
    else:
        for p in people:
            text += f"- {p}\n"

    text += "\n------------------------\n"

    for day, entries in schedule.items():

        text += f"\n__{day}__\n"

        if not entries:
            text += "- (empty)\n"
        else:
            for e in entries:
                status = " ✅" if e.get("completed") else ""
                text += f"- {e['name']}: {e['chore']}{status}\n"

    return text


def format_commands_text():
    return (
        "**📌 CHORE BOT COMMANDS**\n"
        "----------------------------------\n\n"

        "**➕ Add chore**\n"
        "`!add name day chore`\n"
        "Adds a chore for a specific person on a given day.\n\n"

        "**❌ Remove chore**\n"
        "`!remove name day chore`\n"
        "Removes a specific chore assigned to a person on a given day.\n\n"

        "**🔄 Update chore**\n"
        "`!update oldName newName day optionalNewChore`\n"
        "Updates a chore by changing the assigned person and/or chore details.\n\n"

        "**👤 Add roommate**\n"
        "`!addPerson name`\n"
        "Adds a new roommate to the system.\n\n"

        "**🚪 Remove roommate**\n"
        "`!removePerson name`\n"
        "Removes a roommate and all associated data.\n\n"

        "**👥 Replace roommate**\n"
        "`!replacePerson oldName newName`\n"
        "Replaces an existing roommate with a new name while preserving data.\n\n"

        "**🧹 Clean chat**\n"
        "`!clean`\n"
        "Deletes recent bot and user messages to keep this channel tidy.\n\n"

        "**🔄 Reset system**\n"
        "`!reset`\n"
        "Completely clears all chores and roommates (irreversible)."
    )

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

def get_current_day():

    today_index = datetime.now().weekday()

    active_index = (today_index + day_skip) % 7

    return DAYS[active_index]

# ---------------- AUTO UPDATE SCHEDULE ----------------
async def update_schedule():

    global schedule_message

    if schedule_message is None:
        return

    try:
        await schedule_message.edit(content=format_schedule())
    except:
        pass

# ---------------- COMPLETE CHORE ----------------
async def complete_person_chore(person_name):

    day = get_current_day()

    if day not in schedule:
        return

    entries = schedule[day]

    for e in entries:

        if e["name"] == person_name:

            # already completed
            if e.get("completed"):
                return

            e["completed"] = True

            save_state()

            await update_schedule()

            # send status message
            for guild in bot.guilds:

                status_channel = discord.utils.get(
                    guild.text_channels,
                    name=STATUS_CHANNEL_NAME
                )

                if status_channel:

                    await status_channel.send(
                        f"{day}: {person_name} has completed "
                        f"{e['chore']} ✅"
                    )

            return

# ---------------- ESP32 SERIAL LISTENER ----------------
def serial_listener():
    global day_skip

    while True:
        check_new_day()
        try:

            if ser.in_waiting:

                line = ser.readline().decode().strip()

                if line:

                    print("ESP32:", line)

                    if line == "Person 1 complete":

                        if len(people) >= 1:
                            asyncio.run_coroutine_threadsafe(
                                complete_person_chore(people[0]),
                                bot.loop
                            )

                    elif line == "Person 2 complete":

                        if len(people) >= 2:
                            asyncio.run_coroutine_threadsafe(
                                complete_person_chore(people[1]),
                                bot.loop
                            )

                    elif line == "Person 3 complete":

                        if len(people) >= 3:
                            asyncio.run_coroutine_threadsafe(
                                complete_person_chore(people[2]),
                                bot.loop
                            )

                    elif line == "Skip +1 days":
                        day_skip = (day_skip + 1) % 7
                        save_state()

                    elif line == "Skip +2 days":
                        day_skip = (day_skip + 2) % 7
                        save_state()

                    elif line == "Skip +3 days":
                        day_skip = (day_skip + 3) % 7
                        save_state()

                    elif line == "Skip +4 days":
                        day_skip = (day_skip + 4) % 7
                        save_state()

                    elif line == "Skip +5 days":
                        day_skip = (day_skip + 5) % 7
                        save_state()

                    elif line == "Skip +6 days":
                        day_skip = (day_skip + 6) % 7
                        save_state()

        except Exception as e:
            print("Serial Error:", e)

# ---------------- READY EVENT ----------------
@bot.event
async def on_ready():

    global schedule_message

    print(f"Logged in as {bot.user}")

    load_state()

    for guild in bot.guilds:

        schedule_channel = discord.utils.get(
            guild.text_channels,
            name=SCHEDULE_CHANNEL_NAME
        )

        commands_channel = discord.utils.get(
            guild.text_channels,
            name=COMMAND_CHANNEL_NAME
        )

        async def clear(channel):
            async for msg in channel.history(limit=100):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                    except:
                        pass

        if schedule_channel:
            await clear(schedule_channel)
            schedule_message = await schedule_channel.send(format_schedule())

        if commands_channel:
            await clear(commands_channel)
            msg = await commands_channel.send(format_commands_text())
            await msg.pin()

    threading.Thread(
        target=serial_listener,
        daemon=True
    ).start()


# ---------------- MESSAGE SYSTEM (FIXED RULE ENGINE) ----------------
@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    channel_name = message.channel.name

    if channel_name == SCHEDULE_CHANNEL_NAME:
        await bot.process_commands(message)
        return

    if message.content.startswith("!"):

        ctx = await bot.get_context(message)

        if ctx.valid:
            await bot.process_commands(message)
            return

        if channel_name == COMMAND_CHANNEL_NAME:

            try:
                await message.delete()
            except:
                pass

            await message.channel.send(
                f"{message.author.mention} ❗ Invalid command. Use pinned list.",
                delete_after=7
            )

            return

    if channel_name == COMMAND_CHANNEL_NAME:

        if "shit" in message.content.lower():

            try:
                await message.delete()
            except:
                pass

            await message.channel.send(
                f"{message.author.mention} - don't use that word!",
                delete_after=5
            )

            return

    await bot.process_commands(message)


# ---------------- COMMANDS ----------------

@bot.command()
async def addPerson(ctx, name):

    if not is_command_channel(ctx):
        return

    if name in people:
        return await ctx.send("Person already exists")

    if len(people) >= MAX_PEOPLE:
        return await ctx.send("Max 3 people allowed")

    people.append(name)

    save_state()

    await ctx.send(f"Added roommate: {name}")
    await update_schedule()


@bot.command()
async def removePerson(ctx, name):

    if not is_command_channel(ctx):
        return

    if name in people:
        people.remove(name)

    for day in schedule:
        schedule[day] = [
            e for e in schedule[day]
            if e["name"] != name
        ]

    save_state()

    await ctx.send(f"Removed roommate: {name}")
    await update_schedule()


@bot.command()
async def replacePerson(ctx, oldName, newName):

    if not is_command_channel(ctx):
        return

    if oldName not in people:
        return await ctx.send("Original person not found")

    if newName in people:
        return await ctx.send("New name already exists")

    people[people.index(oldName)] = newName

    for day in schedule:
        for e in schedule[day]:
            if e["name"] == oldName:
                e["name"] = newName

    save_state()

    await ctx.send(f"Replaced {oldName} with {newName}")
    await update_schedule()


@bot.command()
async def add(ctx, name, day, *, chore):

    if not is_command_channel(ctx):
        return

    day = day.capitalize()

    if name not in people:
        return await ctx.send("Person must be added first")

    if day not in schedule:
        return await ctx.send("Invalid day")

    # ----------------------------
    # NEW RULE: ONE CHORE PER PERSON PER DAY
    # ----------------------------
    for e in schedule[day]:
        if e["name"] == name:
            return await ctx.send("This person already has a chore for this day")

    # optional: keep your total limit (you can remove if you want)
    if len(schedule[day]) >= 3:
        return await ctx.send("Day full (max 3)")

    schedule[day].append({
        "name": name,
        "chore": chore,
        "completed": False
    })

    save_state()

    await ctx.send(f"Added {name} → {chore} on {day}")
    await update_schedule()


@bot.command()
async def remove(ctx, name, day, *, chore):

    if not is_command_channel(ctx):
        return

    day = day.capitalize()

    for i, e in enumerate(schedule[day]):

        if e["name"] == name and e["chore"] == chore:

            schedule[day].pop(i)

            save_state()

            await ctx.send("Removed entry")
            await update_schedule()
            return

    await ctx.send("Entry not found")


@bot.command()
async def update(ctx, oldName, newName, day, *, newChore=None):

    if not is_command_channel(ctx):
        return

    day = day.capitalize()

    if oldName not in people:
        return await ctx.send("Original person not found")

    if oldName != newName and newName not in people:
        return await ctx.send("New person must exist")

    updated = False

    for e in schedule[day]:

        if e["name"] == oldName:

            e["name"] = newName

            if newChore is not None:
                e["chore"] = newChore

            updated = True

    if updated:
        save_state()
        await ctx.send("Updated entry")
        await update_schedule()
    else:
        await ctx.send("Entry not found")


@bot.command()
async def reset(ctx):

    if not is_command_channel(ctx):
        return

    people.clear()

    for day in schedule:
        schedule[day] = []

    save_state()

    await ctx.send("System reset")
    await update_schedule()


# ---------------- CLEAN (UPDATED FIX) ----------------
@bot.command()
async def clean(ctx):

    if not is_command_channel(ctx):
        return

    channel = ctx.channel

    pinned_ids = set()

    try:
        pinned = await channel.pins()
        pinned_ids = {m.id for m in pinned}
    except:
        pass

    deleted = 0

    async for msg in channel.history(limit=200):

        # KEEP pinned messages (command list)
        if msg.id in pinned_ids:
            continue

        try:
            await msg.delete()
            deleted += 1
        except:
            pass

    await ctx.send(f"Cleaned {deleted} messages", delete_after=5)


@bot.command()
async def show(ctx):

    if not is_command_channel(ctx):
        return

    await ctx.send(format_schedule())


# ---------------- RUN BOT ----------------
bot.run(TOKEN)
