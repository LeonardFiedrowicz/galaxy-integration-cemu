# Cemu Plugin for GOG Galaxy 2.0

Requires Cemu to be installed. This implementation is a modification of the [Citra Plugin](https://github.com/j-selby/galaxy-integration-citra).

## Features

* Library: Wii U games (in decrypted NUS format with code, content and meta folder, not .wud or .wux) in your ROM folder
* Library: Imports your playtime and last time played for games (imported from Cemu)
* Launch: Launches games with Cemu in Fullscreen

## Installation

Download the latest release and extract it to:
- (WINDOWS) `%localappdata%\GOG.com\Galaxy\plugins\installed\galaxy-integration-cemu`
- (MACOS) `~/Library/Application Support/GOG.com/Galaxy/plugins/installed/galaxy-integration-cemu`

i.e 
`C:\Users\Leonard\AppData\Local\GOG.com\Galaxy\plugins\installed\galaxy-integration-cemu`

## Issues

- might show updates as well as the base game if they are in the same folder
- only updates playtime on startup
- Cemu doesn't track playtime when the games are not launched from cemu's library view

## License

Apache-2.0
