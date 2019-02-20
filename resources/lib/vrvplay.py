import xbmc
import vrvlib


class VRVPlayer(xbmc.Player):

    def __init__(self, session):
        xbmc.Player.__init__(self)
        self.session = session
        self.position = 0

    def onPlayBackStarted(self):
        while self.isPlaying():
            xbmc.sleep(500)

        pass

    def onPlayBackEnded(self):
        pass

    def onPlayBackStopped(self):
        xbmc.log("VRVPlayer: Playback stopped at %s" % (self.getTime()), xbmc.LOGNOTICE)
        pass

    def onPlayBackPaused(self):
        print("Strted")

    def onPlayBackResumed(self):
        print("Strted")
