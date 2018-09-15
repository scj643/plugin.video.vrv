import xbmc
import vrvlib

class VRVPlayer(xbmc.Player) :

    def __init__ (self, play_object, session):
        xbmc.Player.__init__(self)
        self.session = session
        self.play_object = play_object
        self.position = 0

    def onPlayBackStarted(self):
        while self.isPlaying():
            xbmc.sleep(500)

        pass

    def onPlayBackEnded(self):
        pass

    def onPlayBackStopped(self):
        #play_object.
        pass

    def onPlayBackPaused(self):
        print("Strted")

    def onPlayBackResumed(self):
        print("Strted")