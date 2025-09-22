import csv
import copy
import json
import pickle
import random
from dataclasses import dataclass

import networkx as nx

import utils


@dataclass
class Industry:
    id: str
    type: str
    level: int
    production: int
    beers_to_sell: int
    points: int
    link_points: int
    income: int
    era: str
    cost: int
    coal_cost: int
    iron_cost: int
    develop: int


class BuildSpot:
    def __init__(self, allowed_industries):
        self.allowed_industries = allowed_industries
        self.industry = None
        self.owned_by = None
        self.flipped = False
        self.resource_type = None
        self.resource_amount = 0

    def __hash__(self):
        return hash(
            (
                tuple(self.allowed_industries),
                self.industry,
                self.owned_by,
                self.flipped,
                self.resource_type,
                self.resource_amount,
            )
        )

    def __eq__(self, other):
        if not isinstance(other, BuildSpot):
            return NotImplemented
        return (
            self.allowed_industries == other.allowed_industries
            and self.industry == other.industry
            and self.owned_by == other.owned_by
            and self.flipped == other.flipped
            and self.resource_type == other.resource_type
            and self.resource_amount == other.resource_amount
        )

    def consume_resource(self):
        self.resource_amount -= 1
        if self.resource_amount == 0:
            self.resource_type = None
            self.flipped = True
            return True
        return False

    def build(self, player, industry_tile, resource=None, amount=0):
        self.industry = industry_tile
        self.owned_by = player
        self.flipped = False
        self.resource_type = resource
        self.resource_amount = amount
        if resource in {"coal", "iron"}:
            if amount == 0:  # Building a coal mine/ironworks which instantly flips
                self.resource_type = None
                self.flipped = True
                return True
        return False

    def flip(self):
        self.flipped = True
        return self.industry

    def remove_obsolete_industry(self):
        if isinstance(self.industry, str) and self.industry[-1] == "1":
            self.remove_tile()

    def remove_tile(self):
        self.industry = None
        self.owned_by = None
        self.flipped = False
        self.resource_type = None
        self.resource_amount = 0

    def __str__(self):
        return f"""Allowed industries: {self.allowed_industries}
Tile: {self.industry}
Owned by: {self.owned_by}
Flipped? {self.flipped}
Resource: {self.resource_type if self.resource_amount else ""}
Amount: {self.resource_amount if self.resource_amount else ""}
"""


class Market:
    def __init__(self, identifier, name, min_players, merchants, bonus):
        self.id = identifier
        self.name = name
        self.min_players = int(min_players)
        # Initialise merchants and beer.
        # "merchants" is either "1" or "2" (Shrewsbury has 1 merchant slot, the others have 2).
        # These are changed with the add_merchant method.
        self.merchants = [None] * int(merchants)
        self.beer = [0] * int(merchants)
        self.bonus = bonus  # List like ["vps", 4] or ["develop"]

    def add_merchant(self, merchant, i):
        self.merchants[i] = merchant
        print(f"{self.name} has a {merchant} merchant!")
        self.beer[i] = 1

    def consume_beer(self, space):
        self.beer[space] -= 1
        return self.bonus

    def reset_merchant_beer(self):
        for i, merchant in enumerate(self.merchants):
            if merchant is not None:
                self.beer[i] = 1

    def __str__(self):
        return f"""{self.name}
Merchants: {self.merchants}
Beer:      {self.beer}
Bonus:     {self.bonus}
"""


class Player:
    def __init__(self, name, cards):
        self.name = name
        self.money = 17
        self.spent_this_turn = 0
        self.link_tiles = 14
        self.industry_tiles = {
            "Manufacturer": [
                "manu1",
                "manu2",
                "manu2",
                "manu3",
                "manu4",
                "manu5",
                "manu5",
                "manu6",
                "manu7",
                "manu8",
                "manu8",
            ],
            "Cotton Mill": [
                "cott1",
                "cott1",
                "cott1",
                "cott2",
                "cott2",
                "cott3",
                "cott3",
                "cott3",
                "cott4",
                "cott4",
                "cott4",
            ],
            "Brewery": ["brew1", "brew1", "brew2", "brew2", "brew3", "brew3", "brew4"],
            "Ironworks": ["iron1", "iron2", "iron3", "iron4"],
            "Coal Mine": [
                "coal1",
                "coal2",
                "coal2",
                "coal3",
                "coal3",
                "coal4",
                "coal4",
            ],
            "Pottery": ["ptry1", "ptry2", "ptry3", "ptry4", "ptry5"],
        }
        self.discard_pile = [cards.pop()]
        self.cards = cards
        self.income = 10
        # Victory points (vps) are broken up into categories.
        # The first four are canal era scores. The second four are rail era scores.
        # Within each four: merchants, links, industries, penalties.
        self.vps = [0, 0, 0, 0, 0, 0, 0, 0]

    def take_income(self):
        self.spent_this_turn = 0

        income = utils.income_level(self.income)
        self.money += income
        if self.money < 0:
            debt = abs(self.money)
            self.money = 0
            print(f"{self.name} is £{debt} in debt!")
            return debt
        if income == 0:
            print(f"{self.name} earned no income (£{self.money}).")
        elif income < 0:
            print(f"{self.name} lost £{abs(income)} (£{self.money}).")
        else:
            print(f"{self.name} gained £{income} (£{self.money}).")
        return 0

    def restock_link_tiles(self):
        self.link_tiles = 14

    def clear_discard_pile(self):
        self.discard_pile = []

    def draw_cards(self, cards):
        self.cards.extend(cards)

    def discard(self, card):
        self.cards.remove(card)
        if card not in {
            "Wild Industry",
            "Wild Location",
        }:
            self.discard_pile.append(card)

    def loan(self):
        self.money += 30
        self.income = utils.inverse_income_level(utils.income_level(self.income) - 3)
        print(
            f"{self.name} took a loan. They gained £30 (£{self.money}) "
            f"and their income dropped to {self.income}.\n"
        )

    def scout(self, card1, card2):
        if card1 is None:
            card1 = self.cards.pop()
        else:
            self.cards.remove(card1)
        if card2 is None:
            card2 = self.cards.pop()
        else:
            self.cards.remove(card2)
        self.discard_pile.extend([card1, card2])
        self.cards.extend(["Wild Location", "Wild Industry"])

    def develop(self, industry_tile1, industry_tile2=None, cost=0):
        self.industry_tiles[industry_tile1].pop(0)
        if industry_tile2 is not None:
            self.industry_tiles[industry_tile2].pop(0)
        if cost:
            self.money -= cost
            self.spent_this_turn += cost
            print(f"Cost of action: £{cost}\n")

    def build(self, industry_tile, cost, revenue=0):
        self.industry_tiles[industry_tile].pop(0)
        self.money += revenue - cost
        self.spent_this_turn += cost
        print(f"Cost of action: £{cost}\n")

    def network(self, link_tiles, cost):
        self.link_tiles -= link_tiles
        self.money -= cost
        self.spent_this_turn += cost
        print(f"Cost of action: £{cost}\n")

    def increase_income(self, income_increase):
        self.income = min(99, self.income + income_increase)

    def increase_money(self, money):
        self.money += money

    def increase_vps(self, points, i):
        if points < 0:
            total_vps = sum(self.vps)
            points = max(-total_vps, points)
        self.vps[i] += points

    def summary(self, canal_era=True):
        if canal_era:  # Do not show the first discard in canal era.
            discards = ["???"] + self.discard_pile[1:]
        else:
            discards = self.discard_pile
        return f"""
{self.name}
Points: {sum(self.vps)}
Income: £{utils.income_level(self.income)} per turn
Money:  £{self.money} (spent £{self.spent_this_turn} this turn)
Cards in hand: {self.cards}
Discarded cards: {discards}
Link tiles remaining: {self.link_tiles}
Industry tiles remaining: {self.industry_tiles}
"""


class GameState:
    def __init__(self, player_names):
        player_count = len(player_names)
        self.era = "canal"
        self.current_turn = 1
        self.deck = self._load_cards(player_count)
        random.shuffle(self.deck)
        self.players = {
            name: Player(name, self.deck[9 * i : 9 * (i + 1)])
            for i, name in enumerate(player_names)
        }
        del self.deck[: 9 * player_count]
        self.turn_order = list(self.players.keys())
        random.shuffle(self.turn_order)
        self.industries = self._load_industries()
        self.map_ = GameMap(player_count)
        self.coal_market = 13
        self.iron_market = 8
        self.wild_location_cards = player_count
        self.wild_industry_cards = player_count

    def next_turn(self):
        self.current_turn += 1
        self.turn_order.sort(key=lambda name: self.players[name].spent_this_turn)
        debts = []
        for player in self.players.values():
            debt = player.take_income()
            if debt:
                debts.append((player, debt))
        return debts

    def pay_debt(self, player, debt, loc, space):
        tile_id = self.map_.nodes[loc]["build_spots"][space].industry
        self.map_.nodes[loc]["build_spots"][space].remove_tile()

        debt -= self.industries[tile_id].cost // 2
        if debt < 0:
            player.increase_money(-debt)
            print(f"Refunded {player.name} £{-debt}.\n")
            return 0
        return debt

    def end_of_canal(self):
        self._score_links()
        self.map_.remove_links()
        self._score_industries()
        self.map_.remove_obsolete_industries()
        self.map_.reset_merchant_beer()
        for player in self.players.values():
            player.restock_link_tiles()
            self.deck.extend(player.discard_pile)
            player.clear_discard_pile()
        random.shuffle(self.deck)
        for player in self.players.values():
            hand = self.deck[:8]
            del self.deck[:8]
            player.draw_cards(hand)
        self.era = "rail"
        self.current_turn = 1

    def end_of_game(self):
        self._score_links()
        self._score_industries()
        self.era = "end"

    def live_scores(self):
        backup_scores = copy.deepcopy(
            {name: player.vps for name, player in self.players.items()}
        )
        self._score_links()
        self._score_industries()
        self.scoreboard()
        for name, player in self.players.items():
            player.vps = backup_scores[name]

    def _score_links(self):
        i = 1 if self.era == "canal" else 5
        for u, v, data in self.map_.edges(data=True):
            if data["player"] is None:  # Skip if nobody has built the link.
                continue
            if (
                u == "Farm Brewery South" or v == "Farm Brewery South"
            ):  # Skip the links to Farm Brewery South.
                continue
            points = 0
            if {u, v} == {
                "Kidderminster",
                "Worcester",
            }:  # This particular link must also add the score for Farm Brewery South.
                space = self.map_.nodes["Farm Brewery South"]["build_spots"][0]
                if space.flipped:
                    points += self.industries[space.industry].link_points
            if self.map_.nodes[u]["type"] == "market":
                points += 2
            else:
                for space in self.map_.nodes[u]["build_spots"]:
                    if space.flipped:
                        points += self.industries[space.industry].link_points
            if self.map_.nodes[v]["type"] == "market":
                points += 2
            else:
                for space in self.map_.nodes[v]["build_spots"]:
                    if space.flipped:
                        points += self.industries[space.industry].link_points
            self.players[data["player"]].increase_vps(points, i)

    def _score_industries(self):
        i = 2 if self.era == "canal" else 6
        for _, data in self.map_.nodes(data=True):
            if data["type"] == "location":
                for space in data["build_spots"]:
                    if space.flipped:
                        points = self.industries[space.industry].points
                        player = space.owned_by
                        self.players[player].increase_vps(points, i)

    def scoreboard(self):
        scoreboard = {name: player.vps for name, player in self.players.items()}
        utils.print_scoreboard(scoreboard)

    def draw_cards(self, player, n):
        if n <= len(self.deck):
            cards = self.deck[:n]
            del self.deck[:n]
            self.players[player].draw_cards(cards)

    def discard(self, player, card):
        if card == "Wild Industry":
            self.wild_industry_cards += 1
        if card == "Wild Location":
            self.wild_location_cards += 1
        self.players[player].discard(card)

    def loan(self, player):
        self.players[player].loan()

    def scout(self, player, card1=None, card2=None):
        self.wild_location_cards -= 1
        self.wild_industry_cards -= 1
        self.players[player].scout(card1, card2)
        print(f"{player} scouted.\n")

    def develop(
        self,
        player,
        industry1,
        industry2=None,
        *,
        iron1="iron market",
        iron1_space=None,
        iron2=None,
        iron2_space=None,
    ):
        cost = self._consume_cube(iron1, iron1_space)
        if iron2 is not None:
            cost += self._consume_cube(iron2, iron2_space)
            print(f"{player} developed {industry1} and {industry2}.\n")
        else:
            print(f"{player} developed {industry1}.\n")
        self.players[player].develop(industry1, industry2, cost)

    def build(
        self,
        player,
        industry,
        location,
        space,
        *,
        cube1=None,
        cube1_space=None,
        cube2=None,
        cube2_space=None,
        market_connection=False,
    ):
        tile_id = self.players[player].industry_tiles[industry][0]
        cost = self.industries[tile_id].cost

        if cube1 is not None:
            cost += self._consume_cube(cube1, cube1_space)
        if cube2 is not None:
            cost += self._consume_cube(cube2, cube2_space)

        print(f"{player} built {tile_id} in {location}.")

        revenue, resource, amount = 0, None, 0
        if self.industries[tile_id].type == "Ironworks":
            resource = "iron"
            amount = self.industries[tile_id].production
            to_move = min(amount, 10 - self.iron_market)
            amount -= to_move
            revenue = sum(
                utils.iron_cost(n)
                for n in range(self.iron_market + 1, self.iron_market + 1 + to_move)
            )
            self.iron_market += to_move
            if to_move:
                print(f"{player} sold {to_move} iron to the market for £{revenue}.")
        if self.industries[tile_id].type == "Coal Mine":
            resource = "coal"
            amount = self.industries[tile_id].production
            if market_connection:
                to_move = min(amount, 14 - self.coal_market)
                amount -= to_move
                revenue = sum(
                    utils.coal_cost(n)
                    for n in range(self.coal_market + 1, self.coal_market + 1 + to_move)
                )
                self.coal_market += to_move
                if to_move:
                    print(f"{player} sold {to_move} coal to the market for £{revenue}.")
        if self.industries[tile_id].type == "Brewery":
            resource = "beer"
            amount = 1 if self.era == "canal" else 2

        flipped = self.map_.nodes[location]["build_spots"][space].build(
            player, tile_id, resource, amount
        )
        # Check if the building was instantly flipped.
        if flipped:
            space = self.map_.nodes[location]["build_spots"][space]
            income_increase = self.industries[space.industry].income
            self.players[player].increase_income(income_increase)
            print(
                f"{player}'s {tile_id} in {location} flipped! "
                f"Their income increased by {income_increase} to {self.players[player].income}."
            )
        print()
        self.players[player].build(industry, cost, revenue)

    def network(
        self,
        player,
        link1_start,
        link1_end,
        *,
        link2_start=None,
        link2_end=None,
        coal1=None,
        coal1_space=None,
        coal2=None,
        coal2_space=None,
        beer=None,
        beer_space=None,
    ):
        self.map_.place_link(player, link1_start, link1_end)
        print(f"{player} built a {self.era} from {link1_start} to {link1_end}.")

        if link2_start is None:
            print()
            link_tiles = 1
            if self.era == "canal":
                cost = 3
            else:
                cost = 5 + self._consume_cube(coal1, coal1_space)
        else:  # Double network action
            self.map_.place_link(player, link2_start, link2_end)
            print(f"{player} built a {self.era} from {link2_start} to {link2_end}.\n")
            link_tiles = 2
            cost = 15
            for res, space in (
                (coal1, coal1_space),
                (coal2, coal2_space),
                (beer, beer_space),
            ):
                cost += self._consume_cube(res, space)

        self.players[player].network(link_tiles, cost)

    def sell(self, player, tiles, beers, develop=None):
        income_increase = 0
        for tile, beer_per_tile in zip(tiles, beers):
            tile_id = self.map_.nodes[tile[0]]["build_spots"][tile[1]].flip()
            income_increase += self.industries[tile_id].income
            for beer in beer_per_tile:
                if beer[0] in (
                    "Warrington",
                    "Nottingham",
                    "Shrewsbury",
                    "Gloucester",
                    "Oxford",
                ):  # Check if it is a merchant beer.
                    bonus = self.map_.nodes[beer[0]]["market"].consume_beer(beer[1])
                    if bonus[0] == "vps":
                        i = (
                            0 if self.era == "canal" else 4
                        )  # Check current era in order to update scoreboard correctly.
                        self.players[player].increase_vps(bonus[1], i)
                        print(
                            f"Merchant bonus: {player} gained {bonus[1]} vps "
                            f"({sum(self.players[player].vps)} vps)."
                        )
                    elif bonus[0] == "money":
                        self.players[player].increase_money(bonus[1])
                        print(
                            f"Merchant bonus: {player} received £{bonus[1]} "
                            f"(£{self.players[player].money})."
                        )
                    elif bonus[0] == "income":
                        self.players[player].increase_income(bonus[1])
                        print(
                            f"Merchant bonus: {player}'s income increased by {bonus[1]} "
                            f"({self.players[player].income})."
                        )
                    else:  # It is a develop bonus.
                        self.players[player].develop(develop)
                else:
                    self._consume_cube(beer[0], beer[1])
            print(f"{player} sold {tile_id} in {tile[0]}!")
        self.players[player].increase_income(income_increase)
        print(
            f"{player}'s income increased by {income_increase} to {self.players[player].income}.\n"
        )

    def _consume_cube(self, loc, space):
        cost = 0
        if loc == "iron market":
            cost += utils.iron_cost(self.iron_market)
            self.iron_market = max(0, self.iron_market - 1)
        elif loc == "coal market":
            cost += utils.coal_cost(self.coal_market)
            self.coal_market = max(0, self.coal_market - 1)
        else:
            flipped = self.map_.nodes[loc]["build_spots"][space].consume_resource()
            if flipped:
                space = self.map_.nodes[loc]["build_spots"][space]
                tile_id = space.industry
                income_increase = self.industries[tile_id].income
                receiving_player = space.owned_by
                self.players[receiving_player].increase_income(income_increase)
                print(
                    f"{receiving_player}'s {tile_id} in {loc} flipped! "
                    f"Their income increased by {income_increase} to "
                    f"{self.players[receiving_player].income}.\n"
                )
        return cost

    @staticmethod
    def _load_cards(player_count):
        deck = []
        with open("cards.csv", mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                name = row[0]
                freq = int(row[player_count - 1])
                deck.extend([name] * freq)
        return deck

    @staticmethod
    def _load_industries():
        industries = {}
        with open("industry_tiles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for ind in data:
            industry_instance = Industry(**ind)
            industries[ind["id"]] = industry_instance
        return industries

    def save_game(self, filename):
        with open(filename, "wb") as f:
            pickle.dump(self, f)
        print(f"Saved game as {filename}.\n")

    @staticmethod
    def load_game(filename):
        with open(filename, "rb") as f:
            return pickle.load(f)


class GameMap(nx.Graph):
    def __init__(self, player_count):
        super().__init__()
        self._add_locations()
        self._add_markets(player_count)
        self._add_links()
        print("Map loaded.")

    def _add_locations(self):
        with open("locations.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for loc in data:
            build_spots = [
                BuildSpot(allowed_industries=ind) for ind in loc["industries"]
            ]
            self.add_node(
                loc["name"], id=loc["id"], type="location", build_spots=build_spots
            )

    def _add_markets(self, player_count):
        markets = []
        with open("markets.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for market in data:
            market_instance = Market(**market)
            markets.append(market_instance)
        markets = self._merchant_setup(player_count, markets)
        for market in markets:
            self.add_node(market.name, id=market.id, type="market", market=market)

    @staticmethod
    def _merchant_setup(player_count, markets):
        print("Randomly assigning merchants...")
        merchant_tiles = [None, None, "Manufacturer", "Cotton Mill", "Wild"]
        if player_count >= 3:
            merchant_tiles.extend([None, "Pottery"])
            if player_count == 4:
                merchant_tiles.extend(["Manufacturer", "Cotton Mill"])

        random.shuffle(merchant_tiles)
        for market in markets:
            if player_count >= market.min_players:
                for i in range(len(market.merchants)):
                    merchant = merchant_tiles.pop()
                    if merchant is not None:
                        market.add_merchant(merchant, i)
        return markets

    def _add_links(self):
        with open("links.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for link in data:
            loc1_id, loc2_id = link["locations"]
            self.add_edge(
                loc1_id, loc2_id, type=link["accepted_link_type"], player=None
            )

    def place_link(self, player, link_start, link_end):
        if "Farm Brewery South" in (link_start, link_end) or {link_start, link_end} == {
            "Kidderminster",
            "Worcester",
        }:
            self["Kidderminster"]["Farm Brewery South"]["player"] = player
            self["Worcester"]["Farm Brewery South"]["player"] = player
            self["Kidderminster"]["Worcester"]["player"] = player
        else:
            self[link_start][link_end]["player"] = player

    def remove_links(self):
        nx.set_edge_attributes(self, {(u, v): None for u, v in self.edges()}, "player")

    def remove_obsolete_industries(self):
        for _, data in self.nodes(data=True):
            if data["type"] == "location":
                for space in data["build_spots"]:
                    space.remove_obsolete_industry()

    def reset_merchant_beer(self):
        for _, data in self.nodes(data=True):
            if data["type"] == "market":
                data["market"].reset_merchant_beer()

    def print_markets(self):
        for _, data in self.nodes(data=True):
            if data["type"] == "market":
                print(data["market"])

    def print_occupied_locations(self):
        for loc, data in self.nodes(data=True):
            if data["type"] == "location":
                for space in data["build_spots"]:
                    if space.industry is not None:
                        print(f"{loc}: {space}")

    def draw_map(self, player=None):
        if player is None:
            utils.draw_map(self)
            return

        links = [
            (u, v) for u, v, link in self.edges(data=True) if link["player"] == player
        ]
        occupied_locs = set()
        for n, data in self.nodes(data=True):
            if data["type"] == "location":
                for space in data["build_spots"]:
                    if space.owned_by == player:
                        occupied_locs.add(n)
                        break
        network_locs = set()
        for u, v in links:
            network_locs.add(u)
            network_locs.add(v)
        network_locs -= occupied_locs
        utils.draw_map(self, links, network_locs, occupied_locs)
