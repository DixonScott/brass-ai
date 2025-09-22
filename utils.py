def iron_cost(iron_cubes: int) -> int:
    """Returns the cost of an iron cube given the number of iron cubes in the market."""
    return (12 - iron_cubes) // 2


def coal_cost(coal_cubes: int) -> int:
    """Returns the cost of a coal cube given the number of coal cubes in the market."""
    return (16 - coal_cubes) // 2


def income_level(income: int) -> int:
    """
    Returns the income level (£ received at the end of the turn)
    given a space on the progress track.
    """
    if 0 <= income < 11:
        return income - 10
    if 11 <= income < 31:
        return (income - 9) // 2
    if 31 <= income < 61:
        return (income + 2) // 3
    if 61 <= income < 100:
        return (income + 23) // 4
    raise ValueError("Income must be from 0 to 99.")


def inverse_income_level(inc_level: int) -> int:
    """Returns the maximum space on the progress track for a given income level."""
    if -10 <= inc_level < 1:
        return inc_level + 10
    if 1 <= inc_level < 11:
        return (inc_level * 2) + 10
    if 11 <= inc_level < 21:
        return inc_level * 3
    if 21 <= inc_level < 30:
        return (inc_level * 4) - 20
    if inc_level == 30:
        return 99
    raise ValueError("Income level must be from -10 to 30.")


def draw_map(map_, links=None, network_locs=None, occupied_locs=None):
    import json
    import networkx as nx
    import matplotlib.pyplot as plt

    with open("coords.json", "r", encoding="utf-8") as f:
        fixed_pos = json.load(f)

    if links is not None:
        nx.draw_networkx_edges(
            map_, fixed_pos, edgelist=links, edge_color="#FF2400", width=3
        )
        nx.draw_networkx_edges(
            map_,
            fixed_pos,
            edgelist=set(map_.edges) - set(links),
            edge_color="#808080",
            style="dashed",
        )
        nx.draw_networkx_nodes(
            map_,
            fixed_pos,
            nodelist=set(map_.nodes) - network_locs - occupied_locs,
            node_color="#FFFFFF",
            edgecolors="#000000",
            node_size=800,
        )
        nx.draw_networkx_nodes(
            map_, fixed_pos, nodelist=network_locs, node_color="#82c8e5", node_size=950
        )
        nx.draw_networkx_nodes(
            map_,
            fixed_pos,
            nodelist=occupied_locs,
            node_color="#FF2400",
            node_size=1500,
        )
        nx.draw_networkx_labels(
            map_, fixed_pos, font_color="#000000", font_size=9, font_weight="bold"
        )
    else:
        nx.draw(
            map_,
            fixed_pos,
            with_labels=True,
            node_color="#FFFFFF",
            edgecolors="#000000",
            node_size=800,
            font_color="#000000",
            font_size=9,
            font_weight="bold",
        )
    plt.show()


def print_scoreboard(scoreboard):
    from rich.console import Console
    from rich.table import Table

    console = Console()

    canal_colour = "rgb(28,163,236)"
    rail_colour = "rgb(255,87,51)"

    categories = [
        f"[{canal_colour}]Merchants[/{canal_colour}]",
        f"[{canal_colour}]Canals[/{canal_colour}]",
        f"[{canal_colour}]Industries[/{canal_colour}]",
        f"[{canal_colour}]Penalties[/{canal_colour}]",
        f"[{rail_colour}]Merchants[/{rail_colour}]",
        f"[{rail_colour}]Rails[/{rail_colour}]",
        f"[{rail_colour}]Industries[/{rail_colour}]",
        f"[{rail_colour}]Penalties[/{rail_colour}]",
    ]

    # Sort the player names so that they appear in descending order of score
    sorted_players = sorted(scoreboard.items(), key=lambda x: sum(x[1]), reverse=True)

    # Update table columns with sorted players
    table = Table(show_header=True)
    table.add_column("", style="bold", justify="left")

    # Add sorted player columns
    for player, _ in sorted_players:
        table.add_column(player, justify="center")

    # Canal era section
    for i, label in enumerate(categories[:3]):
        values = [scores[i] for _, scores in sorted_players]
        if all(v == 0 for v in values):  # Skip categories where all players have 0.
            continue
        table.add_row(label, *[str(v) for v in values])

    # Empty line between canal era components and total
    table.add_row("")

    # Canal era total row
    canal_era_totals = [sum(scores[:4]) for _, scores in sorted_players]
    if any(canal_era_totals):  # Only add if any score in canal era is non-zero
        row = [f"[{canal_colour}]Canal era total[/{canal_colour}]"]
        for total in canal_era_totals:
            row.append(f"[bold]{total}[/bold]")
        table.add_row(*row)

    # Add a new section if there are any rail era scores.
    if any(any(score[4:8]) for score in scoreboard.values()):
        table.add_section()
        # Phase 2 section
        for i, label in enumerate(categories[3:], start=3):
            values = [scores[i] for _, scores in sorted_players]
            if all(v == 0 for v in values):  # Skip categories where all players have 0.
                continue
            table.add_row(label, *[str(v) for v in values])

        # Empty line between rail era components and total
        table.add_row("")

        # Rail era total row
        row = [f"[{rail_colour}]Rail era total[/{rail_colour}]"]
        for _, scores in sorted_players:
            rail_era_total = sum(scores[4:8])
            row.append(f"[bold]{rail_era_total}[/bold]")
        table.add_row(*row)

        table.add_section()

        # Grand total row
        row = ["GRAND TOTAL"]
        for _, scores in sorted_players:
            total = sum(scores)
            row.append(f"[bold]{total}[/bold]")
        table.add_row(*row)

    console.print(table)
