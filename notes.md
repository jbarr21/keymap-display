## QMK

./json2yaml keymaps/keymap.json layout.h | yq 'del(.layout)' | keymap draw -o '{split: true, rows: 3, columns: 5, thumbs: 3}' - > /tmp/keymap.svg

## ZMK

❯ cp config/3x5.dtsi /tmp/3x5.dtsi.c && gcc -E /tmp/3x5.dtsi.c -DXTR_LTO="" -DXTR_LMO="" -DXTR_LBO="" -DXTR_RTO="" -DXTR_RMO="" -DXTR_RBO="" -include zmk-nodefree-config/helper.h -include config/combos.dtsi | tee test.dtsi

or

❯ pcpp zmk-nodefree-config/keypos_def/keypos_36keys.h config/3x5.dtsi -DXTR_LTO="" -DXTR_LMO="" -DXTR_LBO="" -DXTR_RTO="" -DXTR_RMO="" -DXTR_RBO="" | grep -vE "^#line" | tee test-pcpp.dtsi