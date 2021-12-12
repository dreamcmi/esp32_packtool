# coding=UTF-8
import argparse
import json
import logging
import os
import sys
import time

import esptool
import toml

logging.basicConfig(format='- [%(levelname)s]: %(message)s', level=logging.INFO)


def pkgRom(chip):
    # 查找固件位置
    with open(config['pkg']['Repo'] + '/build/' + "flasher_args.json", 'r', encoding='utf-8') as flash_args:
        j = json.load(flash_args)
        if j['extra_esptool_args']['chip'] != chip:
            logging.error("The selected chip is inconsistent with the build")
            sys.exit(-1)
        ss = sorted(
            ((o, f) for (o, f) in j['flash_files'].items()),
            key=lambda x: int(x[0], 0),
        )
        flash_args.close()

    # 判断打包类型
    if config['pkg']['Release'] == 0:
        logging.warning("user build")
        firmware_name = config["pkg"]["Name"] + "_" + chip + '_' + \
                        time.strftime("%Y%m%d%H%M%S", time.localtime()) + ".bin"
        config[chip]['Firmware'] = firmware_name
    elif config['pkg']['Release'] == 1:
        logging.warning("release build")
        firmware_name = config["pkg"]["Name"] + "_" + chip + ".bin"
        config[chip]['Firmware'] = firmware_name
    else:
        logging.error("release option error")
        sys.exit(-1)

    # 写入配置
    with open('config.toml', "w", encoding='utf-8') as f:
        toml.dump(config, f)
        f.close()

    # 进入合并流程
    base_offset = 0x0
    with open(firmware_name, "wb") as fout:
        for offset, name in ss:
            fout.write(b"\xff" * (int(offset, 16) - base_offset))
            base_offset = int(offset, 16)
            with open(config['pkg']['Repo'] + 'build/' + name, "rb") as fin:
                data = fin.read()
                fout.write(data)
                base_offset += len(data)
                fin.close()
        fout.close()


def flashRom(rom, port, baud, chip):
    command_erase = ['--chip', chip, '--port', port, '--baud', baud, 'erase_flash']
    command = ['--chip', chip, '--port', port, '--baud', baud, 'write_flash', '0x0', rom]
    if config[chip]["Type"] == "uart":
        logging.info("select uart flash")
    elif config[chip]["Type"] == "usb":
        logging.info("select usb flash")
        command_erase.remove("--baud")
        command_erase.remove(baud)
        command.remove("--baud")
        command.remove(baud)
    else:
        logging.error("Flash Type error")
        sys.exit(-1)

    logging.info("erase flash")
    esptool.main(command_erase)
    logging.info("start flash firmware")
    esptool.main(command)


def get_version():
    return "1.0.1"


if __name__ == '__main__':
    if not os.path.exists("config.toml"):
        logging.error("config.toml not found ,please check")
        sys.exit(-1)
    config = toml.load("config.toml")
    parser = argparse.ArgumentParser(description="ESP32 Pack Tool")
    parser.add_argument('-v', '--version', action='version', version=get_version(), help='Show version')
    parser.add_argument('-t', '--target', help='Chip:esp32,esp32s2,es32c3,esp32s3')
    parser.add_argument('-p', '--pkg', action="store_true", help='打包固件')
    parser.add_argument('-r', '--rom', action="store_true", help='下载固件')
    args = parser.parse_args()

    ChipName = args.target
    if ChipName is None:
        logging.error("未选择chip")
        sys.exit(-1)
    if args.pkg:
        pkgRom(ChipName)
    if args.rom:
        flashRom(config[ChipName]['Firmware'],
                 config[ChipName]['COM'],
                 config[ChipName]['Baud'],
                 ChipName)
