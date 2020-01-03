import sys

import subprocess
import struct
import threading
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from os.path import join, abspath, isdir, exists, sep
from os import listdir, chdir, walk
from xml.etree import ElementTree as ET
from time import sleep
import re

from dataclasses import dataclass

from urllib.parse import parse_qs, urlparse

from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Game, LicenseInfo, LicenseType, Authentication, LocalGame, NextStep, GameTime
from galaxy.api.consts import Platform, LocalGameState

# Manually override if you dare
# roms_path = [r'E:\Emulator\ROMs\Nintendo - Wii U', ]
# emulator_path = r'E:\Emulator\Emulatoren\Nintendo Wii U - Cemu'
# search_subfolders = False
# level = 2

from user_settings import search_subfolders, level, roms_path, emulator_path


class AuthenticationHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type='text/html'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_GET(self):
        if "setpath" in self.path:
            self._set_headers()
            parse_result = urlparse(self.path)
            params = parse_qs(parse_result.query)
            global roms_path, emulator_path
            if 'path' in params:
                roms_path = [params['path'][0]]
            if 'emulator_path' in params:
                emulator_path = str(params['emulator_path'][0])
                if emulator_path.endswith(".exe"):
                    emulator_path = re.sub(r'(?:.(?!\\))+$', "", emulator_path)

            self.wfile.write("<script>window.location=\"/end\";</script>".encode("utf8"))
            return

        self._set_headers()
        self.wfile.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cemu Integration</title>
            <link href="https://fonts.googleapis.com/css?family=Lato:300&display=swap" rel="stylesheet"> 
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.5/css/bulma.min.css" integrity="sha256-vK3UTo/8wHbaUn+dTQD0X6dzidqc5l7gczvH+Bnowwk=" crossorigin="anonymous" />
            <style>
                @charset "UTF-8";
                html, body {
                    padding: 0;
                    margin: 0;
                    border: 0;
                    background: rgb(40, 39, 42) !important;
                }

                html {
                    font-size: 12px;
                    line-height: 1.5;
                    font-family: 'Lato', sans-serif;
                }

                html {
                    overflow: scroll;
                    overflow-x: hidden;
                }
                ::-webkit-scrollbar {
                    width: 0px;  /* Remove scrollbar space */
                    background: transparent;  /* Optional: just make scrollbar invisible */
                }

                .header {
                    background: rgb(46, 45, 48);
                    height: 66px;
                    line-height: 66px;
                    font-weight: 600;
                    text-align: center;
                    vertical-align: middle;
                    padding: 0;
                    margin: 0;
                    border: 0;
                    font-size: 16px;
                    box-sizing: border-box;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
                    color: white !important;
                }

                .sub-container {
                    width: 90%;
                    min-width: 200px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                Cemu Plugin Configuration
            </div>

            <br />

            <div class="sub-container container">
                <form method="GET" action="/setpath">
                    <div class="field">
                      <label class="label has-text-light">Games Location</label>
                      <div class="control">
                        <input class="input" name="path" type="text" class="has-text-light" placeholder="Enter absolute ROM path">
                      </div>
                    </div>

                    <div class="field">
                      <label class="label has-text-light">Cemu Location</label>
                      <div class="control">
                        <input class="input" name="emulator_path" type="text" class="has-text-light" placeholder="Enter absolute Cemu path">
                      </div>
                    </div>

                    <div class="field is-grouped">
                      <div class="control">
                        <input type="submit" class="button is-link" value="Enable Plugin" />
                      </div>
                    </div>
                </form>
            </div>
        </body>
        </html>
        """.encode('utf8'))


class AuthenticationServer(threading.Thread):
    def __init__(self, port=0):
        super().__init__()
        self.path = ""
        server_address = ('localhost', port)
        self.httpd = HTTPServer(server_address, AuthenticationHandler)  # partial(AuthenticationHandler, self))
        self.port = self.httpd.server_port

    def run(self):
        self.httpd.serve_forever()


class CemuPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(
            Platform.NintendoWiiU,  # Choose platform from available list
            "0.2",  # Version
            reader,
            writer,
            token
        )
        self.game_running = False
        self.running_game = None
        self.games = {}
        self.game_times = {}
        #        self.running_games = []
        self.server = AuthenticationServer()
        self.server.start()

    def tick(self):
        if self.game_running and self.running_game is not None:
            self.game_times[self.running_game][0] += self.TICK_TIME
            self.game_times[self.running_game][1] += self.TICK_TIME
            self.update_game_time(GameTime(self.running_game, self.game_times[self.running_game][0] // 60,
                                           self.game_times[self.running_game][1]))

    def launch_cemu_game(self, game):
        def in_thread(_self, _game):
            for f in listdir(_game.path + "/code"):
                if f.endswith(".rpx"):
                    game_path = abspath(join(_game.path + "/code", f))
                    break
            else:
                logging.debug("no RPX File found, exiting...")
                return

            chdir(emulator_path)
            proc = subprocess.Popen(["./cemu.exe", "-f", "-g", game_path])
            _self.game_running = True
            _self.running_game = _game.game_id
            proc.wait()
            _self.game_running = False
            _self.running_game = None
            _self.update_time(_game)
            logging.debug("GameTime updated, Thread finished")

            return

        thread = threading.Thread(target=in_thread, args=(self, game))
        thread.setDaemon(True)
        thread.start()

        return thread

    def update_time(self, game):
        new_game_times = get_game_times()
        game_time = new_game_times[game.game_id]
        self.game_times[game.game_id] = game_time
        self.update_game_time(GameTime(game.game_id, game_time[0] // 60, game_time[1]))

    def parse_games(self):
        self.games = get_games(roms_path)
        self.game_times = get_game_times()

    async def shutdown(self):
        self.server.httpd.shutdown()

    async def launch_game(self, game_id):
        game = self.games[game_id]
        logging.debug("Launching game " + game.game_id)
        self.launch_cemu_game(game)

        #       if game_id not in self.running_games:
        #           self.running_games.append(game_id)
        return

    def finish_login(self):
        some_dict = dict()
        some_dict["roms_path"] = roms_path
        some_dict["emulator_path"] = emulator_path
        self.store_credentials(some_dict)

        self.parse_games()
        #        thread = UpdateGameTimeThread(self)
        #        thread.start()
        return Authentication(user_id="a_high_quality_cemu_user", user_name=roms_path[0] + "...")

    # implement methods
    async def authenticate(self, stored_credentials=None):
        global roms_path, emulator_path
        # See if we have the path in the cache
        if len(roms_path[0]) == 0 and stored_credentials is not None and "roms_path" in stored_credentials:
            roms_path = stored_credentials["roms_path"]

        if len(emulator_path) == 0 and stored_credentials is not None and "emulator_path" in stored_credentials:
            emulator_path = stored_credentials["emulator_path"]

        if (len(roms_path[0]) == 0) or (len(emulator_path) == 0):
            params = {
                "window_title": "Configure Cemu Plugin",
                "window_width": 400,
                "window_height": 300,
                "start_uri": "http://localhost:" + str(self.server.port),
                "end_uri_regex": ".*/end.*"
            }
            return NextStep("web_session", params)

        return self.finish_login()

    async def pass_login_credentials(self, step, credentials, cookies):
        return self.finish_login()

    async def get_owned_games(self):
        owned_games = []
        for game in self.games.values():
            license_info = LicenseInfo(LicenseType.OtherUserLicense, None)
            owned_games.append(Game(game_id=game.game_id, game_title=game.game_title, dlcs=None,
                                    license_info=license_info))
        return owned_games

    async def get_local_games(self):
        local_games = []
        for game in self.games.values():
            local_game = LocalGame(game.game_id, LocalGameState.Installed)
            local_games.append(local_game)
        return local_games

    async def get_game_time(self, game_id, context=None):
        if game_id in self.game_times:
            game_time = self.game_times[game_id]
            return GameTime(game_id, game_time[0] // 60, game_time[1])


@dataclass
class NUSGame:
    game_id: str
    game_title: str
    path: str
    game_ver: int


def probe_game(path):
    if exists(path + "/meta/meta.xml"):
        root = ET.parse(path + "/meta/meta.xml").getroot()
    else:
        return None

    if root.find("product_code").text.startswith("WUP-M"):  # filter out dlc
        return None
    # Check if English title is valid
    title = root.find("longname_en").text
    if len(title) == 0:
        # logging.debug("No English title for" +  path + "- using Japanese")
        title = root.find("longname_ja").text
    game_id = root.find("title_id").text
    game_ver = int(root.find("title_version").text)
    return NUSGame(game_id=game_id, game_title=title, path=path, game_ver=game_ver)


def get_game_folders(paths):
    games_path = []
    for path in paths:
        if search_subfolders:
            for x in walklevel(path, level):
                games_path.append(x[0])
        else:
            games_path.append(path)
            for folder in listdir(path):
                if isdir(join(path, folder)):
                    games_path.append(join(path, folder))
    return games_path


def walklevel(some_dir, level=1):
    some_dir = some_dir.rstrip(sep)
    assert isdir(some_dir)
    num_sep = some_dir.count(sep)
    for root, dirs, files in walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]


def get_games(path):
    if len(path[0]) == 0:
        return {}
    games_path = get_game_folders(path)
    games = {}
    for game_path in games_path:
        game = probe_game(game_path)
        if game is not None:
            if game.game_id in games:
                if games[game.game_id].game_ver > game.game_ver:
                    games[game.game_id] = game
            else:
                games[game.game_id] = game
    return games


def get_game_times():
    game_times = {}
    if exists(emulator_path + "./settings.xml"):
        root = ET.parse(emulator_path + "./settings.xml").getroot()
    else:
        return
    for game in root.find("GameCache"):
        # convert to hex, remove 0x, add padding
        title_id = str(hex(int(game.find("title_id").text)).split('x')[-1]).rjust(16, '0').upper()
        time_played = int(game.find("time_played").text)
        last_time_played = int(game.find("last_played").text)
        game_times[title_id] = [time_played, last_time_played]
    return game_times


# class UpdateGameTimeThread(threading.Thread):
#    def __init__(self, plugin):
#        super(UpdateGameTimeThread, self).__init__()
#
#
#    def run(self,plugin):
#        logging.debug("Starting updating playtime.")
#        while True:
#            logging.debug("Updating game time...")
#            new_game_times = get_game_times()
#            for game_id in plugin.running_games:
#                if game_id in new_game_times:
#                    game_time = new_game_times[game_id]
#                    plugin.game_times[game_id] = game_time
#                    game_time = GameTime(game_id, game_time[0], game_time[1])
#                    plugin.update_game_time(game_time)
#            sleep(2)


def main():
    create_and_run_plugin(CemuPlugin, sys.argv)


# run plugin event loop
if __name__ == "__main__":
    main()
