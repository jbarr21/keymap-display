#!/usr/bin/env python3
import argparse
import configparser
import os
import subprocess

from download import save_image
from parse import parse

def main() -> None:
    parser = argparse.ArgumentParser(description='Convert QMK/ZMK layout to KLE/KD image')
    parser.add_argument('keymap', type=str, help='Path to keymap file')
    parser.add_argument('-c', '--config', default='') 
    parser.add_argument('-i', '--input', choices=['qmk', 'zmk', 'nf'], required=True) 
    parser.add_argument('-o', '--output', choices=['kle', 'kd'], required=True)
    parser.add_argument('-j', '--json')
    parser.add_argument('-s', '--save_image', help='Save the KLE image', action='store_true')
    parser.add_argument('-l', '--link', action='store_true')
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(__file__))
    if args.config is None or len(args.config) == 0 or args.config == "None":
        props_suffix = "qmk" if args.input == "qmk" else "zmk"
        config_path = f"{repo_root}/config/legends-{props_suffix}.properties"
    else:
        config_path = args.config

    config = load_config(config_path)

    keymap = parse(args.keymap, config, args.input)
    
    match args.output:
        case 'kle':
            print(keymap.to_kle_url() if args.link else keymap.to_kle())
            if args.save_image:
                save_image(keymap.to_kle_url())
        case 'kd':
            if args.input == "qmk" and (args.json is None or len(args.json) == 0):
                print("Must pass json keymap file for kd in QMK")
                exit(1)

            keymap_yaml_path = "/tmp/keymap.yaml"
            with open(keymap_yaml_path, "w") as keymap_yaml:
                subprocess.call(["sh", f"{repo_root}/scripts/json2yaml", args.json, args.keymap], stdout=keymap_yaml)
                draw_cmd = ["keymap", "draw", keymap_yaml_path]
                if args.save_image:
                    with open(f"{repo_root}/keymap.svg", "w") as keymap_svg:
                        subprocess.call(draw_cmd, stdout=keymap_svg)
                else:
                    subprocess.call(draw_cmd)

def load_config(config_path) -> dict:
    config = configparser.ConfigParser()
    config.optionxform = str
    with open(config_path, 'r') as f:
        config.read_file(f)
        if 'legends' in config._sections:
            return config._sections.get("legends")

if __name__ == '__main__':
    main()
