---
role: reference
ideal_count: [1, 1]
data_band: table
comparison: false
family: organizational
description: 'Yellow panel: bold title, black rule, data table with 3 rows x 4 columns (quarterly series)'
when_to_use: Quarterly data table (3 rows x 4 columns).
chrome_note: 'carries native source chrome verbatim: 1 table'
slide_index: 6
slots:
  text_1: {role: title, chars: 32, default: Growth by sector table}
  text_2: {role: footer, chars: 17, default: Annual Review}
  text_3: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_4: {role: page-number, chars: 7, default: '6'}
  text_5: {role: native-text, chars: 2, default: Q1}
  text_6: {role: native-text, chars: 2, default: Q2}
  text_7: {role: native-text, chars: 2, default: Q3}
  text_8: {role: native-text, chars: 2, default: Q4}
  text_9: {role: native-text, chars: 8, default: Series 1}
  text_10: {role: native-text, chars: 3, default: '4.3'}
  text_11: {role: native-text, chars: 3, default: '2.5'}
  text_12: {role: native-text, chars: 3, default: '3.5'}
  text_13: {role: native-text, chars: 3, default: '4.5'}
  text_14: {role: native-text, chars: 8, default: Series 2}
  text_15: {role: native-text, chars: 3, default: '2.4'}
  text_16: {role: native-text, chars: 3, default: '4.4'}
  text_17: {role: native-text, chars: 3, default: '1.8'}
  text_18: {role: native-text, chars: 3, default: '2.8'}
  text_19: {role: native-text, chars: 8, default: Series 3}
  text_20: {role: native-text, chars: 1, default: '2'}
  text_21: {role: native-text, chars: 1, default: '2'}
  text_22: {role: native-text, chars: 1, default: '3'}
  text_23: {role: native-text, chars: 1, default: '5'}
element_tree: ['text text_1 role=title @162,157 1590x102 44pt', 'text text_2 role=footer @1307,991 231x29 12pt', 'text text_3
    role=footer @1548,991 252x79 12pt', 'text text_4 role=page-number @1810,991 100x29 12pt', native table]
source_hash: cb2cf8575b98
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: growth-table
canvas 1920x1080
theme annual-review

rect 0,1 1757x917 fill:chart-series-4
rect 0,1 1757x917 fill:chart-series-4
native graphic1 xml_file:"native/b072dc5e0a45.xml" parts:"W3sidGFibGVfc3R5bGUiOiAiUEdFNmRHSnNVM1I1YkdVZ2VHMXNibk02WVQwaWFIUjBjRG92TDNOamFHVnRZWE11YjNCbGJuaHRiR1p2Y20xaGRITXViM0puTDJSeVlYZHBibWR0YkM4eU1EQTJMMjFoYVc0aUlITjBlV3hsU1dROUluc3lSRFZCUWtJeU5pMHdOVGczTFRSRE16QXRPRGs1T1MwNU1rWTRNVVpFTURNd04wTjlJaUJ6ZEhsc1pVNWhiV1U5SWs1dklGTjBlV3hsTENCT2J5QkhjbWxrSWo0OFlUcDNhRzlzWlZSaWJENDhZVHAwWTFSNFUzUjViR1UrUEdFNlptOXVkRkpsWmlCcFpIZzlJbTFwYm05eUlqNDhZVHB6WTNKbllrTnNjaUJ5UFNJd0lpQm5QU0l3SWlCaVBTSXdJaTgrUEM5aE9tWnZiblJTWldZK1BHRTZjM0puWWtOc2NpQjJZV3c5SWtaR1JrWkdSaUl2UGp3dllUcDBZMVI0VTNSNWJHVStQR0U2ZEdOVGRIbHNaVDQ4WVRwMFkwSmtjajQ4WVRwc1pXWjBQanhoT214dVBqeGhPbTV2Um1sc2JDOCtQQzloT214dVBqd3ZZVHBzWldaMFBqeGhPbkpwWjJoMFBqeGhPbXh1UGp4aE9tNXZSbWxzYkM4K1BDOWhPbXh1UGp3dllUcHlhV2RvZEQ0OFlUcDBiM0ErUEdFNmJHNCtQR0U2Ym05R2FXeHNMejQ4TDJFNmJHNCtQQzloT25SdmNENDhZVHBpYjNSMGIyMCtQR0U2Ykc0K1BHRTZibTlHYVd4c0x6NDhMMkU2Ykc0K1BDOWhPbUp2ZEhSdmJUNDhZVHBwYm5OcFpHVklQanhoT214dVBqeGhPbTV2Um1sc2JDOCtQQzloT214dVBqd3ZZVHBwYm5OcFpHVklQanhoT21sdWMybGtaVlkrUEdFNmJHNCtQR0U2Ym05R2FXeHNMejQ4TDJFNmJHNCtQQzloT21sdWMybGtaVlkrUEM5aE9uUmpRbVJ5UGp4aE9tWnBiR3crUEdFNmJtOUdhV3hzTHo0OEwyRTZabWxzYkQ0OEwyRTZkR05UZEhsc1pUNDhMMkU2ZDJodmJHVlVZbXcrUEM5aE9uUmliRk4wZVd4bFBnPT0ifV0="
line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1590 maxheight:102 autoshrink:true "{{ text_1 | default(\"Growth by sector table\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_2 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_3 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_4 | default(\"6\") }}"
