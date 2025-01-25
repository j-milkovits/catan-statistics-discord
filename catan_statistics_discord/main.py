import io
import os
import time
import typing as t
from uuid import uuid4 as generate_uuid

import discord
import matplotlib.pyplot as plt
import numpy as np
from discord import User
from discord.ext import commands
from dotenv import load_dotenv

from catan_statistics_discord.database import (Expansions, connection, cursor,
                                               db_expansions)

# process discord token
load_dotenv(".env")
discord_token: str | None = os.getenv("DISCORD_TOKEN")
assert discord_token is not None, "Discord token is not found"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

cte = """
with winners as (
    select 
        gs.game_uuid, 
        gs.user_uuid 
    from 
        game_scores gs
    group by gs.game_uuid having max(gs.score)
),
wins_per_game as (
    select
        g.uuid as game_uuid,
        u.username,
        (select 
            case 
                when exists (select * from winners w where w.game_uuid = g.uuid and w.user_uuid = u.uuid) then 1
                else 0
            end
        ) as won
    from
        games g
        join game_scores gs on g.uuid = gs.game_uuid
        join users u on u.uuid = gs.user_uuid
)
"""


@bot.tree.command(
    name="log_game", description="Log the statistics of a played Catan game"
)
async def log_game(
    interaction: discord.Interaction,
    player1: User,
    score_player1: int,
    player2: User,
    score_player2: int,
    player3: User,
    score_player3: int,
    twos: int,
    threes: int,
    fours: int,
    fives: int,
    sixes: int,
    sevens: int,
    eights: int,
    nines: int,
    tens: int,
    elevens: int,
    twelves: int,
    player4: User | None = None,
    score_player4: int | None = None,
    player5: User | None = None,
    score_player5: int | None = None,
    player6: User | None = None,
    score_player6: int | None = None,
    expansion1: Expansions | None = None,
    expansion2: Expansions | None = None,
) -> None:
    """Method to handle the input of a new game into the database.

    Args:
        interaction: discordpy interaction object
        player1: one of the players
        score1: final score of player1
        player2: one of the players
        score2: final score of player2
        player3: one of the players
        score3: final score of player3
        twos: number of twos rolled in the game
        threes: number of threes rolled in the game
        fours: number of fours rolled in the game
        fives: number of fives rolled in the game
        sixes: number of sixes rolled in the game
        sevens: number of sevens rolled in the game
        eights: number of eights rolled in the game
        nines: number of nines rolled in the game
        tens: number of tens rolled in the game
        elevens: number of elevens rolled in the game
        twelves: number of twelves rolled in the game
        player4: one of the players
        score4: final score of player4
        player5: one of the players
        score5: final score of player5
        player6: one of the players
        score6: final score of player6
        expansion1: first expansion played in this game
        expansion2: second expansion played in this game
    """
    player_tuples = [
        (player1, score_player1),
        (player2, score_player2),
        (player3, score_player3),
        (player4, score_player4),
        (player5, score_player5),
        (player6, score_player6),
    ]

    # ensure that player data is input correctly for optional players
    assert (player4 is None and score_player4 is None) or (
        player4 is not None and score_player4 is not None
    ), "Either provide player4 and score_player4 or none of them"
    assert (player5 is None and score_player5 is None) or (
        player5 is not None and score_player5 is not None
    ), "Either provide player5 and score_player5 or none of them"
    assert (player6 is None and score_player6 is None) or (
        player6 is not None and score_player6 is not None
    ), "Either provide player6 and score_player6 or none of them"

    # generate dictionary of players
    player_dict: t.Dict[str, t.Dict[str, t.Any]] = {}
    for tup in [tup for tup in player_tuples if tup[0] and tup[1]]:
        player_dict[tup[0].name] = {
            "score": tup[1],
            "uuid": None,
        }

    # check which players are in db
    query = f"select uuid, username from users where username in ({", ".join("?" * len(player_dict))});"
    players_db = cursor.execute(query, list(player_dict.keys())).fetchall()

    # set uuid for found players
    for uuid, player in players_db:
        player_dict[player]["uuid"] = uuid

    # insert non existant players into db
    for name, val in player_dict.items():
        uuid = val["uuid"]
        if uuid is not None:
            continue
        uuid = str(generate_uuid())
        query = "insert into users (uuid, username) values (?, ?);"
        cursor.execute(query, (uuid, name))
        connection.commit()

        player_dict[name]["uuid"] = uuid

    # add game to db
    game_uuid = str(generate_uuid())
    timestamp = time.time()
    game_insert = (
        game_uuid,
        timestamp,
        twos,
        threes,
        fours,
        fives,
        sixes,
        sevens,
        eights,
        nines,
        tens,
        elevens,
        twelves,
    )
    query = f"insert into games values ({", ".join("?" * len(game_insert))});"
    cursor.execute(query, game_insert)
    connection.commit()

    # add game scores to db
    query = f"insert into game_scores values (?, ?, ?);"
    score_insert = [
        (val["uuid"], game_uuid, val["score"]) for val in player_dict.values()
    ]
    cursor.executemany(query, score_insert)
    connection.commit()

    given_expansions = [expansion1, expansion2]
    # add expansions to db
    query = f"insert into game_expansions values (?, ?);"
    expansion_inserts = []
    for expansion in given_expansions:
        if expansion is None:
            continue
        expansion_uuid = [exp[0] for exp in db_expansions if expansion.name == exp[1]][
            0
        ]
        expansion_inserts.append((expansion_uuid, game_uuid))
    cursor.executemany(query, expansion_inserts)
    connection.commit()

    await interaction.response.send_message("Game successfully logged.")


@bot.tree.command(
    name="win_distribution",
    description="Get the win distribution of all played games so far.",
)
async def win_distribution(
    interaction: discord.Interaction,
):
    query = (
        cte
        + """
    select 
        wpg.username,
        count(wpg.won) as wins
    from 
        wins_per_game wpg
    where
        wpg.won = 1
    group by wpg.username
    """
    )
    winners = cursor.execute(query).fetchall()
    usernames = [winner[0] for winner in winners]
    win_count = [winner[1] for winner in winners]

    def make_custom_autopct(values):
        def autopct_percentages_and_values(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return "{p:.2f}%  ({v:d})".format(p=pct, v=val)

        return autopct_percentages_and_values

    plt.figure(figsize=(6, 6))

    cmap = plt.get_cmap("tab20")
    colors = [cmap(i) for i in np.linspace(0, 1, len(win_count))]

    plt.pie(
        win_count,
        labels=usernames,
        autopct=make_custom_autopct(win_count),
        startangle=90,
        colors=colors,
        wedgeprops={"edgecolor": "black", "linewidth": 1, "linestyle": "solid"},
    )

    plt.title("Win Distribution", fontsize=16, fontweight="bold")
    plt.axis("equal")  # equal aspect ratio ensures the pie chart is circular.

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    file = discord.File(fp=buffer, filename="win_distribution.png")
    await interaction.response.send_message(
        "Here is the win distribution of all games played so far:", file=file
    )


@bot.tree.command(
    name="win_rate",
    description="Get the win rate for each player.",
)
async def win_rate(
    interaction: discord.Interaction,
):
    query = (
        cte
        + """
    select 
        wpg.username,
        avg(won) * 100 as win_rate
    from 
        wins_per_game wpg
    group by wpg.username
    """
    )
    winrates = cursor.execute(query).fetchall()
    usernames = [winner[0] for winner in winrates]
    winrate = [winner[1] for winner in winrates]

    cmap = plt.get_cmap("tab20")
    colors = [cmap(i) for i in np.linspace(0, 1, len(winrate))]

    plt.figure(figsize=(10, 6))
    plt.bar(usernames, winrate, color=colors)

    plt.title("Win Rate in games played", fontsize=16, fontweight="bold")
    plt.xlabel("Usernames", fontsize=12)
    plt.ylabel("Win Rate (Percent)", fontsize=12)

    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    file = discord.File(fp=buffer, filename="win rate.png")
    await interaction.response.send_message(
        "Here is the individual win rate for each player (only games played):",
        file=file,
    )


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced commands: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Logged in as {bot.user}!")


bot.run(token=discord_token)
