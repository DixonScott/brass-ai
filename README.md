[![Status](https://img.shields.io/badge/Status-WIP-yellow)](#)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Last Commit](https://img.shields.io/github/last-commit/DixonScott/brass-ai)](https://github.com/DixonScott/brass-ai/commits/main)

# Brass AI

>⚠️ Disclaimer: This project is an independent, fan-made tool. It is not affiliated with, endorsed, or sponsored by Roxley Games or any other rights holders.

## Overview

This project aims to create an AI agent capable of playing the economic strategy board game Brass: Birmingham at a high level.

As a foundation, the entire game has been implemented in Python. The current version is fully playable in a primarily text-based format
(if one has the required data files). While it does not yet include AI players, the program already functions as a powerful companion app:
it tracks the complete game state, manages turns, and automatically calculates scores.
This makes it useful as a game administrator for real-life play, even before the AI component is introduced.

## Why no game data?
Due to copyright restrictions, this repository does not include any game data, so one cannot simply clone the repo and start playing
straight away.

When creating a new game, the program reads various JSON files to set up the "board". These files contain the locations,
which locations they link to, which industries can be built there, the industry tiles and their various attributes etc.

In the future, I might provide some workaround such as a custom map with different locations and different industry tiles,
or a tool to allow users to recreate these files, provided they have access to a physical copy of the game.

## Next Steps
The next major step is action generation: writing code which will generate all valid actions for a given state of the game.
This is essential for developing an AI agent, because it can choose from this list, rather than trying random actions
that are likely invalid.

## Contributing
This project is a work in progress and contributions are welcome!
Since the game data itself cannot be shared, helpful areas include:
- Improving the game engine or data structures
- Improving documentation
- Writing tests
- Building a game board visualizer

The easiest way to contribute is to reach out with any suggestions.
For anything more involved, especially contributions that require access to game data,
please get in touch so we can figure out the best way forward.

## License
This project is licensed under the GNU General Public License v3.0 (GPLv3).  
See the [LICENSE](LICENSE) file for details.