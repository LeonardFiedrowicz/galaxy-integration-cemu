print("Hello")
path = r"E:\Emulator\ROMs\Nintendo - Wii U\Mario Kart 8"
print(path)
from xml.etree import ElementTree as ET

#d = open(r"C:\Users\Leonard\Desktop\debug.txt","a+")
root = ET.parse(path + "/meta/meta.xml").getroot()
print("root read")
# Check if English title is valid
title = root.find("longname_en").text
print(title)

import os
game_path = r"E:\Emulator\ROMs\Nintendo - Wii U\Mario Kart 8\code\Turbo.rpx"
subprocess.Popen([r"E:\Emulator\Emulatoren\Nintendo Wii U - Cemu\Cemu.exe","-f", "-g", game_path])
##    if len(title_structs[1]) > 0:
##        title = title_structs[1]
##        else:
##            d.write("No English title for" +  path + "- using Japanese")
##            title = title_structs[0]
##
##        d.write(path + "=" + title + "(" +  program_id + ")")
##        return NCCHGame(program_id=program_id, game_title=title, path=path)
