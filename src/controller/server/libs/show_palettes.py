"""Editable holiday color recipes; independent of LED order and output brightness."""
COLOR_KEYS = ('subbass_color','bass_color','lowmid_color','mid_color','uppermid_color',
              'presence_color','treble_color','brilliance_color','beat_color','power_color')
EXTRA_COLORS = {'subbass_color':'#ff2106','lowmid_color':'#05adff','uppermid_color':'#05adff',
                'presence_color':'#991fff','brilliance_color':'#991fff'}
SHOW_MODES = ('classic','auto','comets','waves','ribbons','chase','sparkle','pulse','bounce')
# Repeating a deliberately small palette keeps the holiday recognizable.
_RECIPES = [
 ('christmas','Christmas — red, green & white',['#ff0000','#008000','#ffffff']),
 ('winter','Winter / icy Christmas — blue, cyan & white',['#004cff','#00bfff','#ffffff']),
 ('halloween','Halloween — orange, purple & green',['#ff6000','#8000ff','#00b000']),
 ('thanksgiving','Thanksgiving / fall — amber, rust & gold',['#ff8000','#b03000','#ffcc00']),
 ('independence','Independence Day — red, white & blue',['#ff0000','#ffffff','#003cff']),
 ('memorial','Memorial Day — red, white & blue',['#ff0000','#ffffff','#003cff']),
 ('veterans','Veterans Day — red, white & blue',['#ff0000','#ffffff','#003cff']),
 ('labor','Labor Day — red, white & blue',['#ff0000','#ffffff','#003cff']),
 ('valentines','Valentine’s Day — red, pink & white',['#ff0000','#ff2080','#ffffff']),
 ('st_patricks','St. Patrick’s Day — green, white & gold',['#008000','#ffffff','#ffb000']),
 ('easter','Easter — lavender, pink & mint',['#b080ff','#ff80b0','#70e0a0']),
 ('hanukkah','Hanukkah — blue, white & silver',['#003cff','#ffffff','#b0c0d0']),
 ('new_year','New Year’s Eve — gold, white & purple',['#ffc000','#ffffff','#8000ff']),
 ('juneteenth','Juneteenth — red, green & black',['#ff0000','#008000','#000000']),
]
PALETTES = [{'id':key,'name':name,'colors':{role:colors[i%len(colors)] for i,role in enumerate(COLOR_KEYS)}}
            for key,name,colors in _RECIPES]
PALETTE_IDS = ('custom',) + tuple(p['id'] for p in PALETTES)
