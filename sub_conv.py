from pyvtt import WebVTTFile
from pyvtt.vttexc import InvalidFile

import xbmc

__plugin__ = "VRV"


def my_log(message, level):
    xbmc.log("[PLUGIN] %s: %s" % (__plugin__, message,), level)


#TODO: Add runtime customizable subtitle options
def convert_subs(vtt_filename, font="Arial", size="26"):
    output_filename = vtt_filename
    try:
        subs = WebVTTFile.open(vtt_filename)
        output_filename = vtt_filename.rstrip('.vtt') + ".ass"
    except InvalidFile:
        my_log("Not a VTT file.",xbmc.LOGDEBUG)
        subs = None
    except IOError:
        my_log("File not found.",xbmc.LOGDEBUG)
        subs = None

    #Internal rendering resolution used for scaling. Messing with this affects font sizes, etc.
    def_res = (720, 480)
    #Offset used for correcting the output.
    offset = (0, -45)
    #File header
    ass_header_temp = "[Script Info]\n" \
                      "; This is an Advanced Sub Station Alpha v4+ script.\n" \
                      "Title: converted from vtt\n" \
                      "ScriptType: v4.00+\n" \
                      "Collisions: Normal\n" \
                      "PlayDepth: 0\n" \
                      "PlayResX: {}\n" \
                      "PlayResY: {}\n\n" \
                      "[V4+ Styles]\n" \
                      "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, " \
                      "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, " \
                      "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"

    ass_header = ass_header_temp.format(def_res[0], def_res[1])

    #Style line template
    line_template = "Style: {Name},{Font},{Fontsize},{PrimaryColour},{SecondaryColour},{OutlineColour},{BackColour}," \
                    "{Bold},{Italic},{Underline},{StrikeOut},{ScaleX},{ScaleY},{Spacing},{Angle},{BorderStyle}," \
                    "{Outline},{Shadow},{Alignment},{MarginL},{MarginR},{MarginV},{Encoding}\n"

    #Event header template
    event_header = "[Events]\n" \
                   "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    #Event line template
    event_template = "Dialogue: {Layer},{Start},{End},{Style},{Name},{MarginL},{MarginR},{MarginV},{Effect},{Text}\n"

    if not font:
        font="Arial"
    if not size:
        size="26"
    #Setup initial values for the styles
    initial_font_settings = {
        'Font':font,"Fontsize":size,
        'PrimaryColour':"&H00FFFFFF", #NOTE: this is AABBGGRR hex notation
        'SecondaryColour':"&H0300FFFF",
        'OutlineColour':"&H00000000",
        'BackColour':"&H02000000",
        'Bold': "0", 'Italic': "0", 'Underline': "0", 'StrikeOut': "0",
        'ScaleX': "100", 'ScaleY': "100", 'Spacing': "0", 'Angle': "0",
        'BorderStyle': "1", 'Outline': "2", 'Shadow': "1",
        'Alignment': "2", 'MarginL': "0", 'MarginR': "0", 'MarginV': "0",
        'Encoding': "1"
    }

    styles = dict()

    styles['dialogue'] = dict(initial_font_settings)
    styles['dialogue']['PrimaryColour'] = "&H0000FFFF"  #set the color to yellow
    styles['dialogue']['Name'] = 'dialogue'

    styles['song_lyrics'] = dict(initial_font_settings)
    styles['song_lyrics']['PrimaryColour'] = "&H00FFFF00"  # set the color to blue
    styles['song_lyrics']['Name'] = 'song_lyrics'

    styles['captions'] = dict(initial_font_settings)
    #copy the initial values, but don't make changes. reserved for future use

    if subs:
        ass_fh = open(output_filename, 'wb')
        #write out the header and the dialogue style
        ass_fh.write(ass_header)
        ass_fh.write(line_template.format(**styles['dialogue']))
        ass_fh.write(line_template.format(**styles['song_lyrics']))
        #find the 'special' sub blocks that specify an alignment
        for item in subs.data:
            if "align" in item.position or "Caption" in item.text or "caption" in item.text:
                #tweak the alignment in the styles (can't set alignment in events)
                # "1" is bottom left, "3" is bottom right (like numpad)
                if "align:left" in item.position:
                    #it's probably not neccessary to do the .replace here
                    styles['captions']['Name'] = item.index.replace('-', '_')
                    styles['captions']['Alignment'] = "1"
                    ass_fh.write(line_template.format(**styles['captions']))
                elif "align:right" in item.position:
                    styles['captions']['Name'] = item.index.replace('-', '_')
                    styles['captions']['Alignment'] = "3"
                    ass_fh.write(line_template.format(**styles['captions']))
                else:
                    styles['captions']['Name'] = item.index.replace('-', '_')
                    styles['captions']['Alignment'] = "2"
                    ass_fh.write(line_template.format(**styles['captions']))

        ass_fh.write("\n\n")
        ass_fh.write(event_header)
        #write out the subtitles: ASS calls these events, VTT has these stored in <c> tags
        for item in subs.data:
            abs_vpos = 10 # don't want the 'default' margin to have the subtitles at
                          # the absolute edge of the screen
            abs_hpos = 0
            pos_parts = item.position.split()
            for item_pos in pos_parts:
                #vtt uses percentages, ass uses pixels. convert
                if 'line' in item_pos:
                    # vtt's 'line' is percentage from top of screen (usually)
                    item_pos_per = item_pos.split(':')[1].rstrip('%')
                    per_float = float(item_pos_per) / 100
                    abs_vpos = per_float * def_res[1]
                    abs_vpos = def_res[1] - abs_vpos + offset[1]
                    abs_vpos = int(abs_vpos)
                if 'position' in item_pos:
                    # while 'position' is percentage from left of screen (usually)
                    item_pos_per = item_pos.split(':')[1].rstrip('%')
                    per_float = float(item_pos_per) / 100
                    abs_hpos = per_float * def_res[0]
                    abs_hpos = abs_hpos + offset[1]
                    abs_hpos = int(abs_hpos)
            item_text = item.text_without_tags.encode('utf-8')
            #handle the timecodes, need to chop off leading 0 and trailing ms position
            if '.' in item.start.to_time().isoformat():
                #isoformat doesn't print trailing zeros in ms position,
                #so we need to account for this. in this case we have ms's
                start_text = item.start.to_time().isoformat()[1:-4]
            else: # we add trailing zero's back
                start_text = item.start.to_time().isoformat()[1:] + '.00'
            if '.' in item.end.to_time().isoformat():
                end_text = item.end.to_time().isoformat()[1:-4]
            else:
                end_text = item.end.to_time().isoformat()[1:] + '.00'

            #create the events, matching the styles to what we used before
            if "caption" in item.text or "Caption" in item.text:
                event = {
                    'Layer':"0",
                    'Start':start_text,
                    'End':end_text,
                    'Style':item.index.replace('-', '_'),
                    'Name':item.index,
                    'MarginL':abs_hpos,
                    'MarginR':"0",
                    'MarginV':abs_vpos,
                    'Effect':"",
                    'Text':item_text
                }
            elif "song" in item.text or "Song" in item.text:
                event = {
                    'Layer': "0",
                    'Start': start_text,
                    'End': end_text,
                    'Style': "song_lyrics",
                    'Name': item.index,
                    'MarginL': abs_hpos,
                    'MarginR': "0",
                    'MarginV': abs_vpos,
                    'Effect': "",
                    'Text': item_text
                }
            else:
                event = {
                    'Layer': "0",
                    'Start': start_text,
                    'End': end_text,
                    'Style': "dialogue",
                    'Name': item.index,
                    'MarginL': abs_hpos,
                    'MarginR': "0",
                    'MarginV': abs_vpos,
                    'Effect': "",
                    'Text': item_text
                }

            ass_fh.write(event_template.format(**event))
        ass_fh.close()
    return output_filename
