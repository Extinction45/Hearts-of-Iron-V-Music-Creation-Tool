import os
import shutil
import argparse
from pydub import AudioSegment
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
import yaml
# Supported audio formats
VALID_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}


def apply_cover_template(album_cover_path, template_path, output_path):
    album_cover = Image.open(album_cover_path).convert("RGBA")
    overlay = Image.open(template_path).convert("RGBA")
    target_size = (162, 130)
    album_cover = album_cover.resize(target_size, Image.LANCZOS)
    overlay_right = overlay.crop((overlay.width // 2, 0, overlay.width, overlay.height))
    overlay_right = overlay_right.resize(target_size, Image.LANCZOS)
    overlay_right = overlay_right.convert("RGBA")
    combined = Image.alpha_composite(album_cover, overlay_right)
    width, height = target_size
    final_image = Image.new("RGBA", (width * 2, height))
    final_image.paste(album_cover, (0, 0))
    final_image.paste(combined, (width, 0))
    final_image.save(output_path, format="DDS")
    print(f"Saved: {output_path}")

def extract_cover_from_metadata(file_paths):
    covers = []
    for file_path in file_paths:
        try:
            if file_path.endswith(".mp3"):
                audio = MP3(file_path)
                if "APIC:" in audio.tags:
                    covers.append(Image.open(audio.tags["APIC:"].data))
            elif file_path.endswith(".flac"):
                audio = FLAC(file_path)
                if audio.pictures:
                    covers.append(Image.open(audio.pictures[0].data))
            elif file_path.endswith(".ogg"):
                audio = OggVorbis(file_path)
                if "METADATA_BLOCK_PICTURE" in audio:
                    covers.append(Image.open(audio["METADATA_BLOCK_PICTURE"]))
        except Exception as e:
            print(f"Error extracting cover from {file_path}: {e}")
    return covers

def create_placeholder(output_path):
    placeholder = Image.new("RGB", (162, 130), (0, 0, 0))  # Black placeholder
    placeholder.save(output_path, format="DDS")
    return output_path

def process_album_cover(cover_path, file_paths, output_dir, album_name):
    gfx_dir = os.path.join(output_dir, "Hearts of Iron IV", "gfx")
    os.makedirs(gfx_dir, exist_ok=True)
    output_path = os.path.join(gfx_dir, f"GFX_{album_name}_album_art.dds")

    temp = 0    
    if cover_path == "metadata":
        covers = extract_cover_from_metadata(file_paths)
        temp = 1
    else:
        try:
            print(f"Creating album cover at {output_path}")
            image = Image.open(cover_path)
            image = image.resize((162, 130), Image.LANCZOS)
            image.save(output_path, "DDS")
            print(f"Using provided cover image: {cover_path}")
            return output_path
        except Exception as e:
            print(f"Error processing provided cover: {e}")
    
    if temp == 0:
        covers = extract_cover_from_metadata(file_paths)
    if not covers:
        print("No cover found in metadata. Creating black placeholder.")
        return create_placeholder(output_path)
    return create_placeholder(output_path)

def convert_to_ogg(input_path, output_path):
    if input_path == output_path:
        return  # Skip copying if source and destination are the same
    if input_path.endswith(".ogg"):
        shutil.copy(input_path, output_path)
        return
    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="ogg")
        print(f"Converted {input_path} to {output_path}")
    except Exception as e:
        print(f"Error converting {input_path}: {e}")

def get_user_input(prompt, default):
    user_input = input(f"{prompt} (Default: {default}): ")
    return user_input.strip() or default

def process_files(file_paths, album_name, output_dir, cover_path=None):
    base_dir = os.path.join(output_dir, "Hearts of Iron IV")
    music_dir = os.path.join(base_dir, "music", album_name)
    interface_dir = os.path.join(base_dir, "interface")
    localisation_dir = os.path.join(base_dir, "localisation", "english")
    gfx_dir = os.path.join(base_dir, "gfx")

    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(interface_dir, exist_ok=True)
    os.makedirs(localisation_dir, exist_ok=True)
    os.makedirs(gfx_dir, exist_ok=True)

    dds_output = process_album_cover(cover_path, file_paths, output_dir, album_name)
    apply_cover_template(dds_output, "radio_station_cover_template.png", dds_output)

    valid_files = [f for f in file_paths if os.path.splitext(f)[1] in VALID_AUDIO_EXTENSIONS]
    for file_path in valid_files:
        filename = os.path.basename(file_path)
        output_path = os.path.join(music_dir, os.path.splitext(filename)[0] + ".ogg")
        print(f"Converting {filename} > {os.path.basename(output_path)}")
        convert_to_ogg(file_path, output_path)
    
    create_mod_files(album_name, output_dir, valid_files)

def create_mod_files(album_name, output_dir, file_paths):
    base_dir = os.path.join(output_dir, "Hearts of Iron IV")
    mod_dir = os.path.join(base_dir, "music", album_name)
    os.makedirs(mod_dir, exist_ok=True)
    
    music_txt_path = os.path.join(mod_dir, f"{album_name}.txt")
    asset_path = os.path.join(mod_dir, f"{album_name}.asset")
    localization_path = os.path.join(base_dir, "localisation", "english", f"{album_name}_l_english.yml")
    interface_path = os.path.join(base_dir, "interface", f"{album_name}.gui")
    gfx_path = os.path.join(base_dir, "interface", f"{album_name}.gfx")

    valid_files = [f for f in file_paths if os.path.splitext(f)[1] in VALID_AUDIO_EXTENSIONS]
    
    # Writing .txt file
    with open(music_txt_path, "w", encoding="utf-8") as file:
        file.write(f'music_station = "{album_name}"\n')
        for song in valid_files:
            file.write("\n")
            file.write("music = {\n")
            file.write(f'    song = "{os.path.splitext(os.path.basename(song))[0]}"\n')
            file.write("    chance = {\n")
            file.write("      modifier = { factor = 1 }\n")
            file.write("    }\n")
            file.write("}\n")
    print(f"Created {music_txt_path}")
    
    # Writing .asset file
    with open(asset_path, "w", encoding="utf-8") as file:
        for song in valid_files:
            file.write("music = {\n")
            file.write(f'    name = "{os.path.splitext(os.path.basename(song))[0]}"\n')
            file.write(f'    file = "{os.path.basename(song)}"\n')
            file.write("    volume = 0.65\n")
            file.write("}\n")
    print(f"Created {asset_path}")
    
    # Writing localization file
    os.makedirs(os.path.dirname(localization_path), exist_ok=True)
    with open(localization_path, "w", encoding="utf-8-sig") as file:
        file.write(f'l_english:\n {album_name}_TITLE:0 "{album_name} Radio"\n')
        for song in valid_files:
            file.write(f'  {os.path.splitext(os.path.basename(song))[0]}:0 "{os.path.splitext(os.path.basename(song))[0]}"\n')
    print(f"Created {localization_path}")
    
    # Writing interface .gui and .gfx files
    with open(interface_path, "w", encoding="utf-8") as file:
        gui_content = f"""guiTypes = {{
            containerWindowType = {{
                name = "{album_name}_faceplate"
                position = {{ x =0 y=0 }}
                size = {{ width = 590 height = 46 }}

                iconType ={{
                    name ="musicplayer_header_bg"
                    spriteType = "GFX_musicplayer_header_bg"
                    position = {{ x= 0 y = 0 }}
                    alwaystransparent = yes
                }}

                instantTextboxType = {{
                    name = "track_name"
                    position = {{ x = 72 y = 20 }}
                    font = "hoi_20b"
                    text = "Track Name"
                    maxWidth = 450
                    maxHeight = 25
                    format = center
                }}

                instantTextboxType = {{
                    name = "track_elapsed"
                    position = {{ x = 124 y = 30 }}
                    font = "hoi_18b"
                    text = "00:00"
                    maxWidth = 50
                    maxHeight = 25
                    format = center
                }}

                instantTextboxType = {{
                    name = "track_duration"
                    position = {{ x = 420 y = 30 }}
                    font = "hoi_18b"
                    text = "02:58"
                    maxWidth = 50
                    maxHeight = 25
                    format = center
                }}

                buttonType = {{
                    name = "prev_button"
                    position = {{ x = 220 y = 20 }}
                    quadTextureSprite ="GFX_musicplayer_previous_button"
                    buttonFont = "Main_14_black"
                    Orientation = "LOWER_LEFT"
                    clicksound = click_close
                    pdx_tooltip = "MUSICPLAYER_PREV"
                }}

                buttonType = {{
                    name = "play_button"
                    position = {{ x = 263 y = 20 }}
                    quadTextureSprite ="GFX_musicplayer_play_pause_button"
                    buttonFont = "Main_14_black"
                    Orientation = "LOWER_LEFT"
                    clicksound = click_close
                }}

                buttonType = {{
                    name = "next_button"
                    position = {{ x = 336 y = 20 }}
                    quadTextureSprite ="GFX_musicplayer_next_button"
                    buttonFont = "Main_14_black"
                    Orientation = "LOWER_LEFT"
                    clicksound = click_close
                    pdx_tooltip = "MUSICPLAYER_NEXT"
                }}

                extendedScrollbarType = {{
                    name = "volume_slider"
                    position = {{ x = 100 y = 45}}
                    size = {{ width = 75 height = 18 }}
                    tileSize = {{ width = 12 height = 12}}
                    maxValue =100
                    minValue =0
                    stepSize =1
                    startValue = 50
                    horizontal = yes
                    orientation = lower_left
                    origo = lower_left
                    setTrackFrameOnChange = yes

                slider = {{
                        name = "Slider"    
                        quadTextureSprite = "GFX_scroll_drager"
                        position = {{ x=0 y = 1 }}
                        pdx_tooltip = "MUSICPLAYER_ADJUST_VOL"
                    }}

                track = {{
                    name = "Track"
                    quadTextureSprite = "GFX_volume_track"
                    position = {{ x=0 y = 3 }}
                    alwaystransparent = yes
                    pdx_tooltip = "MUSICPLAYER_ADJUST_VOL"
                }}
            }}

                buttonType = {{
                    name = "shuffle_button"
                    position = {{ x = 425 y = 20 }}
                    quadTextureSprite ="GFX_toggle_shuffle_buttons"
                    buttonFont = "Main_14_black"
                    Orientation = "LOWER_LEFT"
                    clicksound = click_close
                }}
            }}

            containerWindowType={{
                name = "{album_name}_stations_entry"
                size = {{ width = 162 height = 130 }}
        
                checkBoxType = {{
                    name = "select_station_button"
                    position = {{ x = 0 y = 0 }}
                    quadTextureSprite = "GFX_{album_name}_album_art"
                    clicksound = decisions_ui_button
                }}
            }}
        }}"""
        file.write(gui_content)
    print(f"Created {interface_path}")
    
    with open(gfx_path, "w", encoding="utf-8") as file:
        file.write(f'spriteTypes = {{\n    spriteType = {{\n')
        file.write(f'        name = "GFX_{album_name}_album_art"\n')
        file.write(f'        texturefile = "gfx/GFX_{album_name}_album_art.dds"\n')
        file.write(f'        noOfFrames = 2\n')
        file.write(f'    }}\n}}\n')
    print(f"Created {gfx_path}")

def main():
    parser = argparse.ArgumentParser(description="HOI4 Music Mod Generator")
    parser.add_argument("-m", "--mode", choices=["file", "files", "folder"], help="Processing mode")
    parser.add_argument("-p", "--path", nargs="+", help="Path to file(s) or folder")
    parser.add_argument("-a", "--album", help="Album name")
    parser.add_argument("-i", "--image", help="Path to album cover (optional)")
    parser.add_argument("-o", "--output", default=os.getcwd(), help="Output directory")
    args = parser.parse_args()

    mode = args.mode or get_user_input("Choose mode (file/files/folder)", "folder")
    paths = args.path or get_user_input("Enter file or folder path", os.getcwd()).split()
    album_name = args.album or get_user_input("Enter album name", os.path.basename(paths[0]))
    cover_path = args.image or get_user_input("Enter image path", "metadata")
    output_dir = args.output or get_user_input("Enter output directory", os.getcwd())

    file_paths = [os.path.join(root, f) for root, _, files in os.walk(paths[0]) for f in files] if mode == "folder" else paths

    process_files(file_paths, album_name, output_dir, cover_path)

if __name__ == "__main__":
    main()
