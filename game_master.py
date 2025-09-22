import json
import os
import sys
from datetime import datetime
import time

import action_generation
import game_entities


class GameMaster:
    def __init__(self, game=None):
        with open("inputs.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.options_dict = data["categories"]
        self.id_to_name = data["abbreviations"]

        if game is not None:
            self.game = game
        else:
            self.game = self.load_game()

        self.rounds_per_era = 12 - len(self.game.turn_order)

    @staticmethod
    def list_save_files():
        # Make a list of .pkl files in the saves folder
        save_files = [
            (f, os.path.getmtime(os.path.join("saves", f)))
            for f in os.listdir("saves")
            if f.endswith(".pkl") and os.path.isfile(os.path.join("saves", f))
        ]
        # Sort list by modified time
        save_files = sorted(save_files, key=lambda x: x[1], reverse=True)
        # Parse each file name: e.g. Alice_Bob_Charlie-canal-1.pkl
        for i, (f, mod_time) in enumerate(save_files):
            name_part, round_part = f.split("-", 1)
            name_part = name_part.replace("_", ", ")
            round_part = round_part.replace("-", " era: Round ").capitalize()[:-4]
            mod_time = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
            print(f"{i + 1}. {name_part}    {round_part}    {mod_time}")
        return [f[0] for f in save_files]

    def load_game(self):
        choice = self.valid_input(
            "Enter 'new' to start a new game or 'load' to continue an existing game: ",
            "new",
            "load",
        )
        if choice == "load":
            print("Games found in saves folder:")
            save_files = self.list_save_files()
            if save_files:
                while True:
                    try:
                        save_no = int(
                            input("Enter the number of a saved game to load it: ")
                        )
                        if save_no < 1 or save_no > len(save_files):
                            print("Input outside of valid range.")
                            continue
                        return game_entities.GameState.load_game(
                            os.path.join("saves", save_files[save_no - 1])
                        )
                    except ValueError:
                        print("Input must be an integer.")
            else:
                print("None! Starting a new game...")
        player_names = self.get_player_names()
        return game_entities.GameState(player_names)

    def play_game(self):
        print("\nStarting game.")

        # The first round of canal is different because each player gets one action.
        if self.game.era == "canal" and self.game.current_turn == 1:
            self.game.save_game(
                os.path.join(
                    "saves", f"{"_".join(self.game.players.keys())}-canal-1.pkl"
                )
            )
            print("~^" * 15 + "~")
            print(f"    Canal era: round 1 of {self.rounds_per_era}")
            print("~^" * 15 + "~\n")
            for player in self.game.turn_order:
                print(f"It is {player}'s turn.\n")
                start_time = time.time()
                self.player_action(player)
                self.game.draw_cards(player, 1)
                minutes, seconds = divmod(int(time.time() - start_time), 60)
                print(f"Turn time: {minutes}m {seconds}s\n")
            self.next_turn()

        if self.game.era == "canal":
            for round_ in range(self.game.current_turn, self.rounds_per_era + 1):
                self.game.save_game(
                    os.path.join(
                        "saves",
                        f"{"_".join(self.game.players.keys())}-canal-{round_}.pkl",
                    )
                )
                print("~^" * 15 + "~")
                print(f"    Canal era: round {round_} of {self.rounds_per_era}")
                print("~^" * 15 + "~\n")
                for player in self.game.turn_order:
                    print(f"It is {player}'s turn.\n")
                    start_time = time.time()
                    for _ in range(2):
                        self.player_action(player)
                    self.game.draw_cards(player, 2)
                    minutes, seconds = divmod(int(time.time() - start_time), 60)
                    print(f"Turn time: {minutes}m {seconds}s\n")
                self.next_turn()
            self.game.end_of_canal()
            self.game.scoreboard()
            action_generation.reset_connection_cache()

        if self.game.era == "rail":
            for round_ in range(self.game.current_turn, self.rounds_per_era + 1):
                self.game.save_game(
                    os.path.join(
                        "saves",
                        f"{"_".join(self.game.players.keys())}-rail-{round_}.pkl",
                    )
                )
                print("╤" * 30)
                print(f"│   Rail era: round {round_} of {self.rounds_per_era}   │")
                print("╧" * 30 + "\n")
                for player in self.game.turn_order:
                    print(f"It is {player}'s turn.\n")
                    start_time = time.time()
                    for _ in range(2):
                        self.player_action(player)
                    self.game.draw_cards(player, 2)
                    minutes, seconds = divmod(int(time.time() - start_time), 60)
                    print(f"Turn time: {minutes}m {seconds}s\n")
                if round_ != self.rounds_per_era:
                    self.next_turn()
            self.game.end_of_game()
            self.game.save_game(
                os.path.join("saves", f"{"_".join(self.game.players.keys())}-end.pkl")
            )

        self.game.scoreboard()

    def next_turn(self):
        debts = self.game.next_turn()
        for player, debt in debts:
            print(f"{player.name} must remove industry tiles to cover their debt.")
            while debt:
                print(f"Debt: £{debt}")
                loc = self.valid_input(
                    "Enter the location (id or name) of the tile"
                    " to remove or 'none' if you don't have any:\n",
                    "none",
                    *self.options_dict["locations"],
                )
                if loc == "none":
                    i = 3 if self.game.era == "canal" else 7
                    player.increase_vps(-debt, i)
                    break
                space = int(
                    self.valid_input(f"Which space in {loc}?\n", "0", "1", "2", "3")
                )
                debt = self.game.pay_debt(player, debt, loc, space)
            print(f"{player.name} cleared their debt.")

    def player_action(self, player):
        hand = self.game.players[player].cards
        while True:
            discard = self.valid_input(
                f"Choose a card to discard {hand}:\nOr press enter to discard the first card.\n"
                "(other options: enter 'summary' to see a "
                "player summary, 'map' to see your network, 'scores' to see the scoreboard, "
                "'markets' to see a market summary, or 'quit'.)\n",
                *hand,
                "summary",
                "map",
                "scores",
                "markets",
                "quit",
                "",
            )
            if discard == "quit":
                sys.exit()
            elif discard == "summary":
                print(self.game.players[player].summary(self.game.era == "canal"))
            elif discard == "map":
                self.game.map_.draw_map(player)
            elif discard == "scores":
                self.game.live_scores()
            elif discard == "markets":
                self.game.map_.print_markets()
                print(f"Coal market: ⬛ x {self.game.coal_market}")
                print(f"Iron market: 🟧 x {self.game.iron_market}\n")
            else:
                break

        if discard == "":
            discard = hand[0]
        self.game.discard(player, discard)

        action = self.valid_input(
            "Choose an action (build, network, develop, sell, loan, scout, pass):\n",
            *self.options_dict["actions"],
        )

        if action == "loan":
            self.game.loan(player)
        elif action == "scout":
            self.scout(player, hand)
        elif action == "develop":
            self.develop(player)
        elif action == "sell":
            self.sell(player)
        elif action == "build":
            self.build(player)
        elif action == "network":
            self.network(player)

    def scout(self, player, hand):
        card1 = self.valid_input(
            "Choose two cards to discard (enter one at a time):\n", *hand
        )
        card2 = self.valid_input("", *hand)
        self.game.scout(player, card1, card2)

    def develop(self, player):
        industry1 = self.valid_input(
            "Choose an industry to develop (coal, iron, brew, manu, cott, ptry):\n",
            *self.options_dict["industries"],
        )
        iron1 = self.valid_input(
            "Where does the iron come from (enter 'iron market' or a location name/id)?\n",
            "iron market",
            *self.options_dict["locations"],
        )
        if iron1 != "iron market":
            iron1_space = int(
                self.valid_input(f"Which space in {iron1}?\n", "0", "1", "2", "3")
            )
        else:
            iron1_space = None
        industry2 = self.valid_input(
            "Choose an industry to develop (coal, iron, brew, manu, cott, ptry), or 'skip':\n",
            "skip",
            *self.options_dict["industries"],
        )
        iron2, iron2_space = None, None
        if industry2 == "skip":
            industry2 = None
        else:
            iron2 = self.valid_input(
                "Where does the iron come from (enter 'iron market' or a location name/id)?\n",
                "iron market",
                *self.options_dict["locations"],
            )
            if iron2 != "iron market":
                iron2_space = int(
                    self.valid_input(f"Which space in {iron2}?\n", "0", "1", "2", "3")
                )
        self.game.develop(
            player,
            industry1,
            industry2,
            iron1=iron1,
            iron1_space=iron1_space,
            iron2=iron2,
            iron2_space=iron2_space,
        )

    def sell(self, player):
        tiles, beers = [], []
        develop = None
        while True:
            loc = self.valid_input(
                "Enter the location (id or name) of the tile to sell:\n",
                *self.options_dict["locations"],
            )
            space = int(
                self.valid_input(f"Which space in {loc}?\n", "0", "1", "2", "3")
            )
            tiles.append((loc, space))
            beers_per_tile = []
            while True:
                loc = self.valid_input(
                    "Enter the location (id or name) of the beer to use, "
                    "or 'done' if you have consumed the required beer for this tile:\n",
                    "done",
                    *self.options_dict["locations"],
                    *self.options_dict["markets"],
                )
                if loc == "done":
                    break
                if loc == "Gloucester":
                    develop = self.valid_input(
                        "Gloucester merchant bonus: which industry will you develop "
                        "(coal, iron, brew, manu, cott, ptry)?\n",
                        *self.options_dict["industries"],
                    )
                space = int(
                    self.valid_input(f"Which space in {loc}?\n", "0", "1", "2", "3")
                )
                beers_per_tile.append((loc, space))
            beers.append(beers_per_tile)
            done = self.valid_input("Have you finished selling (y/n)?\n", "y", "n")
            if done == "y":
                break
        self.game.sell(player, tiles, beers, develop)

    def build(self, player):
        industry = self.valid_input(
            "Choose an industry to build (coal, iron, brew, manu, cott, ptry):\n",
            *self.options_dict["industries"],
        )
        loc = self.valid_input(
            "Enter the location (id or name) of where you want to build:\n",
            *self.options_dict["locations"],
        )
        market_connection = False
        if industry == "Coal Mine":
            market_connection = self.valid_input(
                f"Does {loc} have a connection to a market (y/n)?\n", "y", "n"
            )
            market_connection = market_connection == "y"
        space = int(self.valid_input(f"Which space in {loc}?\n", "0", "1", "2", "3"))

        cube1, cube1_space, cube2, cube2_space = None, None, None, None
        resource_needed = self.valid_input(
            "Do you require iron or coal (y/n)?\n", "y", "n"
        )
        if resource_needed == "y":
            cube1 = self.valid_input(
                "Where does the (first) iron/coal come from "
                "(enter 'iron market', 'coal market', or a location)?\n",
                "iron market",
                "coal market",
                *self.options_dict["locations"],
            )
            if cube1[-6:] != "market":
                cube1_space = int(
                    self.valid_input(f"Which space in {cube1}?\n", "0", "1", "2", "3")
                )
            resource_needed = self.valid_input(
                "Do you require another iron or coal (y/n)?\n", "y", "n"
            )
            if resource_needed == "y":
                cube2 = self.valid_input(
                    "Where does the iron/coal come from "
                    "(enter 'iron market', 'coal market', or a location)?\n",
                    "iron market",
                    "coal market",
                    *self.options_dict["locations"],
                )
                if cube2[-6:] != "market":
                    cube2_space = int(
                        self.valid_input(
                            f"Which space in {cube2}?\n", "0", "1", "2", "3"
                        )
                    )
        self.game.build(
            player,
            industry,
            loc,
            space,
            cube1=cube1,
            cube1_space=cube1_space,
            cube2=cube2,
            cube2_space=cube2_space,
            market_connection=market_connection,
        )

    def network(self, player):
        link1_start = self.valid_input(
            "Enter the location of a link endpoint:\n",
            *self.options_dict["locations"],
            *self.options_dict["markets"],
        )
        link1_end = self.valid_input(
            "Enter the location of the other link endpoint:\n",
            *self.options_dict["locations"],
            *self.options_dict["markets"],
        )
        if self.game.era == "canal":
            self.game.network(player, link1_start, link1_end)
            return  # Exit early because we don't need to worry about coal or double network.

        (
            link2_start,
            link2_end,
            coal1_space,
            coal2,
            coal2_space,
            beer,
            beer_space,
        ) = (None, None, None, None, None, None, None)
        coal1 = self.valid_input(
            "Where does the coal come from (enter 'coal market' or a location)?\n",
            "coal market",
            *self.options_dict["locations"],
        )
        if coal1 != "coal market":
            coal1_space = int(
                self.valid_input(f"Which space in {coal1}?\n", "0", "1", "2", "3")
            )
        double_rail = self.valid_input(
            "Do you wish to place a second rail link (y/n)?\n", "y", "n"
        )
        if double_rail == "y":
            link2_start = self.valid_input(
                "Enter the location of a link endpoint:\n",
                *self.options_dict["locations"],
                *self.options_dict["markets"],
            )
            link2_end = self.valid_input(
                "Enter the location of the other link endpoint:\n",
                *self.options_dict["locations"],
                *self.options_dict["markets"],
            )
            coal2 = self.valid_input(
                "Where does the coal come from (enter 'coal market' or a location)?\n",
                "coal market",
                *self.options_dict["locations"],
            )
            if coal2 != "coal market":
                coal2_space = int(
                    self.valid_input(f"Which space in {coal2}?\n", "0", "1", "2", "3")
                )
            beer = self.valid_input(
                "Where does the beer come from (enter a 4-letter location id)?\n",
                *self.options_dict["locations"],
            )
            beer_space = int(
                self.valid_input(f"Which space in {beer}?\n", "0", "1", "2", "3")
            )
        self.game.network(
            player,
            link1_start,
            link1_end,
            link2_start=link2_start,
            link2_end=link2_end,
            coal1=coal1,
            coal1_space=coal1_space,
            coal2=coal2,
            coal2_space=coal2_space,
            beer=beer,
            beer_space=beer_space,
        )

    def valid_input(self, prompt, *args):
        options = tuple(args)
        while True:
            user_input = input(prompt)
            if user_input in self.id_to_name:
                user_input = self.id_to_name[user_input]
            if user_input in options:
                return user_input
            print(f"Invalid input. Choose from: {", ".join(options)}")

    @staticmethod
    def get_player_names():
        while True:
            player_count = input("How many players? (2, 3 or 4)\n")
            if player_count in {"2", "3", "4"}:
                player_count = int(player_count)
                break
            print("Invalid input!")

        players = []
        i = 1
        while len(players) < player_count:
            name = input(f"Enter name for player {i}: ").strip()
            if name == "":
                print("Name cannot be empty.")
            elif not name.isalnum():
                print("Name must contain only A-Z, a-z, 0-9.")
            elif name in players:
                print(
                    f"The name '{name}' is already taken. Please choose a different name."
                )
            else:
                players.append(name)
                i += 1
        return players
