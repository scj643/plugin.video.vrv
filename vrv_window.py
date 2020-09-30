import xbmc
import xbmcaddon
import xbmcgui
import os


class VRVWindow(xbmcgui.WindowDialog):
    def __init__(self, headers, control_objects, rows=0, columns=0, layout="poster", background='/home/zero/Pictures/vrv_bg.png'):

        self.controlList = list()
        self.selected_control = None
        self.visible = False
        if layout == "poster":
            image_height = 225
            image_width = 150
        elif layout == "thumb":
            image_height = 150
            image_width = 225
        screen_width = self.getWidth()
        screen_height = self.getHeight()
        #screen_start = 425
        top_margin = 10

        left_margin = 10
        xbmc.log("screen width is %s " % screen_width, xbmc.LOGERROR)
        xbmc.log("screen height is %s" % screen_height, xbmc.LOGERROR)

        self.addControl(xbmcgui.ControlImage(x=0, y=0, width=screen_width, height=screen_height, filename=background,
                             aspectRatio=1))
        self.addControl(xbmcgui.ControlLabel(x=left_margin, y=top_margin, width=screen_width, height=screen_height,
                                             label=headers[0], font="font26"))

        current_x = left_margin
        current_y = top_margin + 40
        x_space = image_width + 25
        y_space = image_height + 25
        column = 1
        row = 1
        if rows:
            max_rows = rows
        else:
            max_rows = 3

        if columns:
            max_cols = columns
        else:
            max_cols = 6

        for item in control_objects:
            image = item.get('art_cache', dict()).get(layout, "")
            control_item = dict()
            xbmc.log("current x is %s " % current_x, xbmc.LOGERROR)
            xbmc.log("current y is %s " % current_y, xbmc.LOGERROR)

            control_item['image'] = \
                xbmcgui.ControlImage(x=current_x, y=current_y, width=image_width, height=image_height, filename=image,
                                     aspectRatio=1)
            control_item['label'] = \
                xbmcgui.ControlButton(x=current_x, y=(current_y + image_height + 2), width=image_width, height=20,
                                      label=item['title'],
                                      font="font10")
            control_item['id'] = item['id']
            self.controlList.append(control_item)
            current_x += x_space
            column += 1
            if column > max_cols:
                current_y += y_space
                current_x = left_margin
                column = 1
                row += 1
                if row-1 < len(headers):
                    self.addControl(xbmcgui.ControlLabel(x=current_x, y=current_y, width=screen_width, height=20,
                                                         label=headers[row-1], font="font26"))
                    current_y += 40
                if row > max_rows:
                    break

            if current_y > screen_height - top_margin - image_height:
                break

        for control in self.controlList:
            self.addControl(control['image'])
            self.addControl(control['label'])

        for control in self.controlList:
            myindex = self.controlList.index(control)
            if myindex > 0:
                prev_control = self.controlList[myindex-1]['label']
            else:

                prev_control = control['label']
            if myindex + 1 < len(self.controlList):
                next_control = self.controlList[myindex + 1]['label']
            else:
                next_control = control['label']
            control['label'].setNavigation(control['label'], control['label'], prev_control, next_control)

    def show(self):
        self.visible = True
        super(VRVWindow,self).show()

    def close(self):
        self.visible = False
        super(VRVWindow,self).close()

    @property
    def isvisible(self):
        return self.visible

    def onControl(self, control):
        xbmc.log("onControl called with %s " % control, xbmc.LOGERROR)
        for con_def in self.controlList:
            if con_def['label'] == control:
                xbmc.log("found button, id %s " % con_def['id'], xbmc.LOGERROR)
                self.selected_control = con_def
                self.close()
