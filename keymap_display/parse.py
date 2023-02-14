from abc import abstractmethod
from dataclasses import dataclass
import os
import re
from sys import argv
from textwrap import dedent
from tree_sitter import Language, Parser
import urllib.parse

# KLE JSON for a 3x5+3
KLE_LAYOUT = dedent('''
    [{{a:7,f:3}},{{y:0.3}},{0},{{y:-0.2}},{1},{{y:-0.1}},{2},{{y:0.1}},{3},{{y:0.2}},{4},{{x:3}},{5},{{y:-0.1}},{6},{{y:-0.1}},{7},{{y:0.1}},{8},{{y:0.2}},{9},{{y:-0.4}}],
    [{{y:0.3}},{10},{{y:-0.2}},{11},{{y:-0.1}},{12},{{y:0.1}},{13},{{y:0.2}},{14},{{x:3}},{15},{{y:-0.1}},{16},{{y:-0.1}},{17},{{y:0.1}},{18},{{y:0.2}},{19},{{y:-0.4}}],
    [{{y:0.3}},{20},{{y:-0.2}},{21},{{y:-0.1}},{22},{{y:0.1}},{23},{{y:0.2}},{24},{{x:3}},{25},{{y:-0.1}},{26},{{y:-0.1}},{27},{{y:0.1}},{28},{{y:0.2}},{29}],
    [{{x:3,y:0.5}},{30},{31},{{h:1.5,y:-0.5}},{32},{{x:1}},{{h:1.5}},{33},{{y:0.5}},{34},{35}],
''')

MODS = ['GUI', 'SFT', 'ALT', 'CTL', 'LGUI', 'LSHFT', 'LALT', 'LCTRL', 'RGUI', 'RSHFT', 'RALT', 'RCTRL']
kle_chars_needing_escaping = ['/', ';', '@', '&', '_', '=', ':']
fw_to_name = { }

@dataclass
class KeyAction:
    type: str
    tap: str
    hold: str

@dataclass
class Key:
    cells: list[str]

    def label(self, defines, encoded=False) -> str:
        action = self._action(defines)
        label = action.tap
        if encoded:
            for ch in [c for c in kle_chars_needing_escaping if c in label]:
                label = label.replace(ch, '/' + ch)

        if action.hold is not None:
            label += f"\n\n\n\n{action.hold}"

        if not encoded:
            label = label.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')
 
        return urllib.parse.quote(label).replace('/', '%2F') if encoded else label

    def _action(self, defines) -> KeyAction:
        type = self.cells[0][1:]
        args = [self._legend(x) for x in self.cells[1:]]

        if len(self.cells) > 1 or self.cells[0].startswith('&'):
            # ZMK
            if type == 'kp':
                return KeyAction(type=type, tap=args[0], hold=None)
            elif type in ['mt', 'lt', 'lt2', 'hml', 'hmr']:
                return KeyAction(type=type, tap=args[1], hold=args[0])
            elif type == 'mo':
                return KeyAction(type=type, tap='', hold=args[0])
            elif type in ['sk', 'sl']:
                return KeyAction(type=type, tap=f"{args[0]}<br>{type.upper()}", hold=None)
            elif type == 'trans':
                return KeyAction(type=type, tap='___', hold=None) 
            elif type == 'none' or type == '___':
                return KeyAction(type=type, tap='', hold=None)
            else:
                type = self.cells[0][1:] if self.cells[0][0] == '&' else self.cells[0]
                tap = self._legend((type if len(args) == 0 else ' '.join(args)).upper())
                return KeyAction(type=type, tap=tap, hold=None)
        else:
            # QMK
            code = self.cells[0]
            defined_code = defines.get(code, code)
            code = code.replace('KC_', '').replace('XXXXXXX', '')

            if '_T(' in defined_code:
                tap = defined_code[defined_code.find('_T(')+3+3:len(defined_code)-1]
                hold = defined_code[1:4]
                return KeyAction(type="mt", tap=tap, hold=hold)
            elif 'LT(' in defined_code:
                comma_index = defined_code.find(',')
                tap = defined_code[comma_index+1:defined_code.find(')')].replace('KC_', '')
                hold = defined_code[defined_code.find('(')+1:comma_index]
                return KeyAction(type="lt", tap=tap, hold=hold)
            elif 'MO(' in defined_code:
                return KeyAction(type="mo", tap='', hold=defined_code[3:-1])
            elif 'OSM' in defined_code:
                tap = defined_code[defined_code.find('_')+1:len(defined_code)-1]
                if tap[0] == 'L' or tap[0] == 'R':
                    tap = tap[1:]
                tap = f"{fw_to_name.get(tap, tap)}<br>OSM"
                return KeyAction(type="osm", tap=tap, hold=None)
            elif defined_code.startswith('TO('):
                tap = defined_code.replace('(', ' ').replace(')', '')
                return KeyAction(type="to", tap=tap, hold=None)
            elif defined_code.startswith('OSL('):
                tap = defined_code.replace('(', ' ').replace(')', '')
                return KeyAction(type="osl", tap=tap, hold=None)
            elif any([code.startswith(f"{mod}_") for mod in MODS]):
                tap = code.split('_')[1]
                hold = code.split('_')[0]
                return KeyAction(type="mod", tap=tap, hold=None)
            else:
                tap = fw_to_name.get(code, code.replace('_', ' '))
                return KeyAction(type="kc", tap=tap, hold=None)

    def _legend(self, code) -> str:
        code = fw_to_name.get(code, code)
        if len(code) == 2 and code.startswith('N'):
            code = code[1:]
        elif code.startswith('C_'):
            code = code[2:]
        elif re.match(r'\w\w\(\w+\)', code):
            print(code)
            code = fw_to_name.get(code[0:2]) + ' + ' +code[3:-1]
        
        if len(code) > 1:
            code = code.replace('_', ' ')
        return code

@dataclass
class Layer:
    name: str
    label: str
    keys: list[Key]

    def to_kle(self, defines, encoded=False):
        replacements = [('=' if encoded else '') + key.label(defines=defines, encoded=encoded) for key in self.keys]
        if not encoded:
            replacements = [f'"{x}"' for x in replacements]
        kle_layout = KLE_LAYOUT.format(*replacements)

        layer_name = (self.label if self.label is not None else self.name.upper()).replace('_', '%20' if encoded else ' ')
        header = '''[{d:true,w:5,a:6,f:5}, %s],''' % (f"={layer_name}" if encoded else f"\"{layer_name}\"")
        data = f"{header}\n{kle_layout.strip()}"
        if encoded:
            data = self._kle_encode(data)

        return data

    def to_kle_url(self, defines):
        return self.to_kle(defines, encoded=True).replace('\n', '')

    def _kle_encode(self, text):
        semicolon = urllib.parse.quote(';')
        chars = {
            ',': '&',
            '[': '@',
            '{': '_',
            '}': semicolon,
            ']': semicolon,
            ' ':'',
        }
        for k, v in chars.items():
            text = text.replace(k, v)
        return text

@dataclass
class Keymap:
    layers: list[Layer]
    defines: dict[str, str]

    def to_kle(self):
        return '\n'.join([layer.to_kle(self.defines) for layer in self.layers])

    def to_kle_url(self):
        layer_urls = ''.join([layer.to_kle_url(self.defines) for layer in self.layers])
        return f"http://www.keyboard-layout-editor.com/##@{layer_urls}=undefined"

class KeymapParser:
    @abstractmethod
    def parse_keymap(self, keymap_text) -> Keymap:
        pass

    def parse(self, keymap_path) -> Keymap:
        with open(keymap_path, 'r') as f:
            keymap_text = f.read()
            return self.parse_keymap(keymap_text)

class QmkKeymapParser(KeymapParser):
    Layer = re.compile(r'#define\s+\_([A-Z]+)\s+\\(.+?(?:^$|\Z))', re.DOTALL | re.MULTILINE)
    Key = re.compile(r'\S{2,}(?=(,|$|\n))')
    Define = re.compile(r'(?<=#define )((?:\w|_)+)\s+(.+\(.+\).*)')

    def parse_keymap(self, keymap_text) -> Keymap:
        defines = {}
        for define in QmkKeymapParser.Define.finditer(keymap_text):
            defines[define.group(1)] = define.group(2)
        
        keymap_layers = []
        for layer in QmkKeymapParser.Layer.finditer(keymap_text):
            layer_name = layer.group(1)
            layer_text = layer.group(2)
            layer_key_lines = [line for line in layer_text.splitlines() if not (line.startswith('//') or line.startswith(')'))]
            layer_text = re.sub('XTR_\w+', '', '\n'.join(layer_key_lines))
            
            keys = []
            for key in QmkKeymapParser.Key.finditer(layer_text):
                cells = key.group(0).strip().split(' ')
                keys += [Key(cells)]

            keymap_layers += [Layer(layer_name, layer_name, keys)]
        
        return Keymap(keymap_layers, defines)


class ZmkNodefreeKeymapParser(KeymapParser):
    Layer = re.compile(r'ZMK_LAYER\((\w+),(.+?(?:^\)|\Z|\())', re.DOTALL | re.MULTILINE)
    Key = re.compile(r'(&\w+(?:\s[A-Za-z0-9]\w*)*|_{3}|_HELD_|RGB_\w+)')

    def parse_keymap(self, keymap_text) -> Keymap:
        keymap_layers = []
        for layer in ZmkNodefreeKeymapParser.Layer.finditer(keymap_text):
            layer_name = layer.group(1)
            layer_text = layer.group(2)
            layer_key_lines = [line for line in layer_text.splitlines() if not (line.startswith('//') or line.startswith(')'))]
            layer_text = re.sub('XTR_\w+', '', '\n'.join(layer_key_lines))
            
            keys = []
            for key in ZmkNodefreeKeymapParser.Key.finditer(layer_text):
                cells = key.group(0).strip().split(' ')
                keys += [Key(cells)]

            keymap_layers += [Layer(layer_name, layer_name, keys)]
        
        return Keymap(keymap_layers, {}) # TODO: parse defines

class ZmkKeymapParser(KeymapParser):
    def parse_keymap(self, keymap_text) -> Keymap:
        main_file = os.path.dirname(__file__)
        so_path = f"{main_file}/devicetree.so" if not os.environ.get('GITHUB_WORKSPACE', None) else (os.environ.get('HOME')+'/.cache/tree-sitter/lib/devicetree.so')
        DTS_LANGUAGE = Language(so_path, 'devicetree')
        parser = Parser()
        parser.set_language(DTS_LANGUAGE)
        tree = parser.parse(bytes(keymap_text, 'utf8'))
        
        slash = [c for c in tree.root_node.children if c.type == 'node' and ZmkKeymapParser.node_name(c) == '/'][0]
        keymap = [c for c in slash.children if c.type == 'node' and ZmkKeymapParser.node_name(c) == 'keymap'][0]
        layers = [c for c in keymap.children if c.type == 'node']
        layers = [c for c in layers if len([p for p in c.children if ZmkKeymapParser.node_name(p) == 'bindings']) > 0]
        keymap_layers = []

        for layer in layers:
            name = ZmkKeymapParser.node_name(layer)
            bindings = [c for c in layer.children if ZmkKeymapParser.node_name(c) == 'bindings'][0]
            label = [x.text.decode().replace('"', '') for x in ZmkKeymapParser.flatten([c.children for c in layer.children if ZmkKeymapParser.node_name(c) == 'label']) if x.type == 'string_literal']
            label = next(iter(label), None)
            layer_cells = [c for c in bindings.children if c.type == 'integer_cells'][0].children
            keys = []
            cells = []
            for i, cell in enumerate(layer_cells):
                if cell.type != 'comment' and ZmkKeymapParser.node_name(cell) is not None and ZmkKeymapParser.node_name(cell) != '<':
                    cells += [cell.text.decode()]

                if (i == len(layer_cells) - 1 or layer_cells[i + 1].type == 'reference') and len(cells) > 0: 
                    keys += [Key(cells)]
                    cells = []

            keymap_layers += [Layer(name, label, keys)]
        
        return Keymap(keymap_layers, {})

    @staticmethod
    def flatten(l):
        return [item for sublist in l for item in sublist]

    @staticmethod
    def node_name(node):
        if node is None or not hasattr(node, 'type'):
            return None
        elif node.type == 'identifier':
            return node.text.decode()
        else:
            ids = [c for c in node.children if c.type == 'identifier']
            refs = [c for c in node.children if c.type == 'reference']
            props = [c for c in node.children if c.type == 'property']
            return ZmkKeymapParser.node_name(next(iter(ids + refs + props), None))

def parse(keymap, config, input) -> Keymap:
    fw_to_name.update(config)
    match input:
        case 'qmk':
            parser = QmkKeymapParser()
        case 'zmk':
            parser = ZmkKeymapParser()
        case 'nf':
            parser = ZmkNodefreeKeymapParser()
    return parser.parse(keymap)
